"""NBlood as a runtime oracle.

What this module is for, after the visual work moved out of it:

**Keep.**  Questions only the real game can answer.  Does the MAP initialise;
does the player spawn; does a door actually move; does a switch produce the
state change it promises; is the mechanism playable; does the level stay up.
Those are :func:`run_nblood_oracle`, :func:`run_nblood_action_oracle` and
:func:`run_nblood_behavior_oracle`, and they are unchanged.

**Moved.**  Looking at a room.  Judging composition, visibility, materials or
how a space is revealed.  Those now go through ``bloodmap.visual`` and the
XMapEdit observer, which takes a camera pose as a number and answers with what
the renderer painted.  It needs no window, no focus, no key and no timing, so it
is reproducible in a way this file never was.

**Deprecated.**  :func:`run_nblood_viewpoint_capture` and the window-focus and
key-injection helpers underneath it exist only to take a picture of a room, and
that is the job that moved.  They still work and nothing calls them by default.

The line between the two is not "images versus numbers".  It is *what the
question needs*: a running game, or a renderer.  A frame from a running game
carries the game with it -- a pain flash, a monster walking into shot, an
automap someone left on -- which is exactly why the visual questions are better
asked of the editor renderer, and exactly why the behavioural ones cannot be.
"""

from __future__ import annotations

import hashlib
import ctypes
import os
import re
import shutil
import subprocess
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from .analysis import validate_map
from .composition import insert_fragment
from .format import (
    SECTOR_FIELDS, WALL_FIELDS, XSECTOR_SCHEMA, XWALL_SCHEMA,
    encode_map, parse_map, read_map, write_map,
)
from .model import DiskMap, DiskObject, ExtraHeader, PackedExtra
from .duke import read_duke_map


class OracleError(RuntimeError):
    pass


_CONFIG = """[Setup]
ConfigVersion = 109
ForceSetup = 0
NoAutoLoad = 1
InputJoystick = 0
UseJoystickRumble = 0
InputMouse = 0
ModDir = "/"

[Screen Setup]
Polymer = 0
ScreenBPP = 32
ScreenHeight = 480
ScreenMode = 0
ScreenWidth = 640
MaxRefreshFreq = 0
"""

_AUTOEXEC = """echo BLOODMAP_ORACLE_BEGIN
echo BLOODMAP_ORACLE_BOOTSTRAPPED
"""

_BEHAVIOR_AUTOEXEC = """echo BLOODMAP_ORACLE_BEGIN
cl_viewhbob 0
cl_viewvbob 0
bind "E" "gamefunc_Open"
bind "F11" "screenshot"
echo BLOODMAP_ORACLE_BOOTSTRAPPED
"""

# A camera that can only look straight ahead cannot review a ceiling, a sky, or
# anything a player would look up at, so a viewpoint may ask for a pitch.
#
# These are the engine's own defaults rather than a rebinding: NBlood's Blood
# key table (source/blood/src/_functio.h, keydefaults) binds Aim_Up to Home and
# Aim_Down to End, and Aim_* holds the pitch where Look_* on PgUp/PgDn recentres
# it, which is what a still frame needs.  Do not reach for the function keys
# here: in Blood F9 is Quick_Load and F10 opens the quit prompt, so driving them
# instead of an aim control kills the process in the middle of the capture.
PITCH_KEYS = {"up": 0x24, "down": 0x23}  # VK_HOME, VK_END

_EDUKE_CONFIG = """[Misc]
Executions = 1
Locale = "en"

[Updates]
CheckForUpdates = 0

[Setup]
ConfigVersion = 348
ForceSetup = 0
NoAutoLoad = 1
SelectedGRP = "duke3d.grp"
ModDir = "/"

[Screen Setup]
Polymer = 0
ScreenBPP = 32
ScreenHeight = 480
ScreenMode = 0
ScreenWidth = 640
MaxRefreshFreq = 0
"""

_EDUKE_AUTOEXEC = """echo LLMAPPER_EDUKE_ORACLE_BEGIN
echo LLMAPPER_EDUKE_ORACLE_BOOTSTRAPPED
"""
_EDUKE_REVISION_PATTERN = re.compile(r"\bEDuke32 ([^\r\n]+)")

_REQUIRED_MARKERS = {
    "autoexec": "BLOODMAP_ORACLE_BOOTSTRAPPED",
    "game_loop": "Waiting for network players!",
    "map_initialization": "Modern types erased:",
}
_FATAL_PATTERN = re.compile(r"Caught signal|\bFATAL\||\bERROR\|", re.IGNORECASE)
_REVISION_PATTERN = re.compile(r"\bNBlood ([^\r\n]+)")


def assess_nblood_output(log: str, stderr: str, stayed_alive: bool) -> dict[str, Any]:
    """Classify a bounded NBlood run without treating harness termination as failure."""
    combined = log + "\n" + stderr
    markers = {name: value in combined for name, value in _REQUIRED_MARKERS.items()}
    fatal_matches = sorted(set(match.group(0) for match in _FATAL_PATTERN.finditer(combined)))
    revision_match = _REVISION_PATTERN.search(combined)
    passed = stayed_alive and all(markers.values()) and not fatal_matches
    return {
        "status": "pass" if passed else "fail",
        "stayed_alive_for_grace_period": stayed_alive,
        "markers": markers,
        "fatal_indicators": fatal_matches,
        "engine_revision": revision_match.group(1).strip() if revision_match else None,
    }


def _map_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    disk = read_map(path)
    errors = [item for item in validate_map(disk) if item.severity == "error"]
    if errors:
        first = errors[0]
        raise OracleError(
            f"{path} failed structural validation: {first.code} at {first.location}: {first.message}"
        )
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "counts": {
            "sectors": len(disk.sectors),
            "walls": len(disk.walls),
            "sprites": len(disk.sprites),
        },
    }


def _duke_map_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    disk = read_duke_map(path)
    errors = [item for item in disk.to_build_ir().validate() if item.severity == "error"]
    if errors:
        first = errors[0]
        raise OracleError(
            f"{path} failed shared Build validation: {first.code} at {first.location}: {first.message}"
        )
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "counts": {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)},
    }


def _hidden_process_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return {"startupinfo": startup, "creationflags": subprocess.CREATE_NO_WINDOW}


def _interactive_process_options() -> dict[str, Any]:
    """Leave NBlood attached to the interactive desktop for SDL raw input."""
    return {}


def _probe_map(
    map_path: Path,
    *,
    nblood: Path,
    game_dir: Path,
    grace_seconds: float,
    work_dir: Path,
) -> dict[str, Any]:
    identity = _map_identity(map_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    for name in ("nblood.log", "stdout.txt", "stderr.txt"):
        candidate = work_dir / name
        if candidate.exists():
            candidate.unlink()
    shutil.copy2(map_path, work_dir / "oracle.MAP")
    (work_dir / "oracle.cfg").write_text(_CONFIG, encoding="utf-8", newline="\n")
    (work_dir / "autoexec.cfg").write_text(_AUTOEXEC, encoding="utf-8", newline="\n")

    command = [
        str(nblood),
        "-usecwd",
        "-game_dir", str(game_dir),
        "-cfg", "oracle.cfg",
        "-map", "oracle.MAP",
        "-noautoload",
        "-quick",
        "-nosetup",
    ]
    stdout_path, stderr_path = work_dir / "stdout.txt", work_dir / "stderr.txt"
    stayed_alive = False
    returncode: int | None = None
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command, cwd=work_dir, stdout=stdout, stderr=stderr,
            **_hidden_process_options(),
        )
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline and process.poll() is None:
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
        stayed_alive = process.poll() is None
        if stayed_alive:
            process.kill()
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait(timeout=5)
            raise OracleError(f"NBlood process {process.pid} could not be reaped") from exc

    log = (work_dir / "nblood.log").read_text(encoding="utf-8", errors="replace") \
        if (work_dir / "nblood.log").exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    assessment = assess_nblood_output(log, stderr_text, stayed_alive)
    assessment.update(
        identity=identity,
        grace_seconds=grace_seconds,
        terminated_by_harness=stayed_alive,
        early_exit_code=None if stayed_alive else returncode,
    )
    if assessment["status"] != "pass":
        useful_lines = [
            line for line in (log + "\n" + stderr_text).splitlines()
            if "BLOODMAP_ORACLE" in line or _FATAL_PATTERN.search(line)
        ]
        assessment["failure_excerpt"] = useful_lines[-20:]
    return assessment


def run_nblood_oracle(
    candidate: str | Path,
    *,
    nblood: str | Path,
    game_dir: str | Path,
    baseline: str | Path | None = None,
    grace_seconds: float = 5.0,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run candidate and optional baseline through a bounded external NBlood load smoke."""
    candidate_path = Path(candidate).resolve()
    nblood_path = Path(nblood).resolve()
    game_path = Path(game_dir).resolve()
    baseline_path = Path(baseline).resolve() if baseline is not None else None
    if not candidate_path.is_file():
        raise OracleError(f"candidate MAP does not exist: {candidate_path}")
    if not nblood_path.is_file():
        raise OracleError(f"NBlood executable does not exist: {nblood_path}")
    if not game_path.is_dir():
        raise OracleError(f"NBlood game-data directory does not exist: {game_path}")
    if baseline_path is not None and not baseline_path.is_file():
        raise OracleError(f"baseline MAP does not exist: {baseline_path}")
    if not 1.0 <= grace_seconds <= 60.0:
        raise OracleError("grace_seconds must be between 1 and 60")

    def execute(root: Path) -> dict[str, Any]:
        probes: dict[str, Any] = {}
        if baseline_path is not None:
            probes["baseline"] = _probe_map(
                baseline_path, nblood=nblood_path, game_dir=game_path,
                grace_seconds=grace_seconds, work_dir=root / "baseline",
            )
        probes["candidate"] = _probe_map(
            candidate_path, nblood=nblood_path, game_dir=game_path,
            grace_seconds=grace_seconds, work_dir=root / "candidate",
        )
        passed = all(item["status"] == "pass" for item in probes.values())
        revisions = sorted({item["engine_revision"] for item in probes.values() if item["engine_revision"]})
        return {
            "$schema": "bloodmap.nblood-oracle-report",
            "schema_version": 1,
            "status": "pass" if passed else "fail",
            "engine_revisions": revisions,
            "probes": probes,
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="bloodmap-nblood-oracle-") as directory:
        return execute(Path(directory))


def _probe_eduke32_map(
    map_path: Path,
    *,
    eduke32: Path,
    game_dir: Path,
    startup_timeout: float,
    grace_seconds: float,
    work_dir: Path,
) -> dict[str, Any]:
    identity = _duke_map_identity(map_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "eduke32.log", "stdout.txt", "stderr.txt", "settings.cfg",
        "llmapper.cfg", "oracle.cfg",  # oracle.cfg cleans up pre-v1.0 harness runs
    ):
        candidate = work_dir / name
        if candidate.exists():
            candidate.unlink()
    shutil.copy2(map_path, work_dir / "oracle.MAP")
    # Keep the engine config basename different from oracle.MAP. EDuke32 looks
    # for a map-local ``oracle.cfg`` and would otherwise execute the INI file
    # as console commands after loading the board.
    (work_dir / "llmapper.cfg").write_text(_EDUKE_CONFIG, encoding="utf-8", newline="\n")
    (work_dir / "autoexec.cfg").write_text(_EDUKE_AUTOEXEC, encoding="utf-8", newline="\n")
    command = [
        str(eduke32), "-usecwd", "-j", str(game_dir), "-cfg", "llmapper.cfg",
        "-map", "oracle.MAP", "-nosetup",
    ]
    stdout_path, stderr_path = work_dir / "stdout.txt", work_dir / "stderr.txt"
    stayed_alive, board_loaded = False, False
    returncode: int | None = None
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command, cwd=work_dir, stdout=stdout, stderr=stderr,
            **_hidden_process_options(),
        )
        startup_deadline = started + startup_timeout
        while time.monotonic() < startup_deadline and process.poll() is None:
            log = (work_dir / "eduke32.log").read_text(encoding="utf-8", errors="replace") \
                if (work_dir / "eduke32.log").exists() else ""
            # Current EDuke32 revisions announce a command-line board as a
            # "User Map" and then enter the game loop without emitting the
            # older "Board loaded." message.
            if "Board loaded." in log or "User Map: /oracle.MAP" in log:
                board_loaded = True
                break
            time.sleep(0.1)
        if board_loaded:
            grace_deadline = time.monotonic() + grace_seconds
            while time.monotonic() < grace_deadline and process.poll() is None:
                time.sleep(min(0.1, max(0.0, grace_deadline - time.monotonic())))
            stayed_alive = process.poll() is None
        if process.poll() is None:
            process.kill()
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait(timeout=5)
            raise OracleError(f"EDuke32 process {process.pid} could not be reaped") from exc
    log = (work_dir / "eduke32.log").read_text(encoding="utf-8", errors="replace") \
        if (work_dir / "eduke32.log").exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    combined = log + "\n" + stderr_text
    fatal = sorted(set(match.group(0) for match in _FATAL_PATTERN.finditer(combined)))
    markers = {
        "autoexec": "LLMAPPER_EDUKE_ORACLE_BOOTSTRAPPED" in combined,
        "game_data": "Using duke3d.grp as main data file." in combined,
        "board_loaded": board_loaded,
    }
    revision = _EDUKE_REVISION_PATTERN.search(combined)
    passed = stayed_alive and all(markers.values()) and not fatal
    result = {
        "status": "pass" if passed else "fail",
        "identity": identity,
        "engine_revision": revision.group(1).strip() if revision else None,
        "markers": markers,
        "fatal_indicators": fatal,
        "startup_seconds": time.monotonic() - started - (grace_seconds if stayed_alive else 0),
        "grace_seconds": grace_seconds,
        "stayed_alive_for_grace_period": stayed_alive,
        "terminated_by_harness": stayed_alive,
        "early_exit_code": None if stayed_alive else returncode,
    }
    if not passed:
        result["failure_excerpt"] = [
            line for line in combined.splitlines()
            if "LLMAPPER_EDUKE" in line or "Board loaded" in line or "User Map:" in line
            or _FATAL_PATTERN.search(line)
        ][-30:]
    return result


def run_eduke32_oracle(
    candidate: str | Path,
    *,
    eduke32: str | Path,
    game_dir: str | Path,
    baseline: str | Path | None = None,
    startup_timeout: float = 30.0,
    grace_seconds: float = 3.0,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load Duke v7 MAPs in EDuke32 and require an initialized, healthy board."""
    candidate_path, executable, game_path = Path(candidate).resolve(), Path(eduke32).resolve(), Path(game_dir).resolve()
    baseline_path = Path(baseline).resolve() if baseline else None
    if not candidate_path.is_file():
        raise OracleError(f"candidate Duke MAP does not exist: {candidate_path}")
    if not executable.is_file():
        raise OracleError(f"EDuke32 executable does not exist: {executable}")
    if not game_path.is_dir():
        raise OracleError(f"Duke3D game-data directory does not exist: {game_path}")
    if baseline_path is not None and not baseline_path.is_file():
        raise OracleError(f"baseline Duke MAP does not exist: {baseline_path}")
    if not 2.0 <= startup_timeout <= 120.0 or not 1.0 <= grace_seconds <= 60.0:
        raise OracleError("EDuke32 startup timeout/grace period is outside the safe bounds")

    def execute(root: Path) -> dict[str, Any]:
        probes = {}
        if baseline_path is not None:
            probes["baseline"] = _probe_eduke32_map(
                baseline_path, eduke32=executable, game_dir=game_path,
                startup_timeout=startup_timeout, grace_seconds=grace_seconds,
                work_dir=root / "baseline",
            )
        probes["candidate"] = _probe_eduke32_map(
            candidate_path, eduke32=executable, game_dir=game_path,
            startup_timeout=startup_timeout, grace_seconds=grace_seconds,
            work_dir=root / "candidate",
        )
        return {
            "$schema": "llmapper.eduke32-oracle-report",
            "schema_version": 1,
            "status": "pass" if all(item["status"] == "pass" for item in probes.values()) else "fail",
            "engine_revisions": sorted({item["engine_revision"] for item in probes.values() if item["engine_revision"]}),
            "probes": probes,
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="llmapper-eduke32-") as directory:
        return execute(Path(directory))


def _empty_struct(fields: list[tuple[str, str]]) -> dict[str, int]:
    return {name: 0 for name, _codec in fields}


def _empty_extra(schema: list[tuple[str, int, bool]]) -> dict[str, int]:
    return {name: 0 for name, _bits, _signed in schema}


def _static_scenario_map() -> DiskMap:
    sector = _empty_struct(SECTOR_FIELDS)
    sector.update(wall_ptr=0, wall_count=4, ceiling_z=-8192, floor_z=8192, extra=-1)
    walls: list[DiskObject] = []
    for index, (x, y) in enumerate(((0, 0), (1024, 0), (1024, 1024), (0, 1024))):
        wall = _empty_struct(WALL_FIELDS)
        wall.update(
            x=x, y=y, point2=(index + 1) % 4, next_wall=-1, next_sector=-1,
            picnum=0, over_picnum=-1, extra=-1,
        )
        walls.append(DiskObject(wall))
    header = {
        "start_x": 512, "start_y": 512, "start_z": 0, "start_angle": 0,
        "start_sector": 0, "sky_bits": 0, "visibility": 800, "matt_id": 0,
        "sky_type": 0, "revision": 1, "num_sectors": 1, "num_walls": 4,
        "num_sprites": 0,
    }
    extra_header = ExtraHeader(
        copyright=b"\0" * 64, xsprite_size=56, xwall_size=24, xsector_size=60,
        xmp_signature=b"\0" * 3, xmp_header_version=0, xmp_map_flags=0,
        xmp_board_width=0, xmp_board_height=0, xmp_palette=0,
        xmp_sky_repeat_count=0, xmp_sky_visibility=0, reserved=b"\0" * 37,
    )
    return parse_map(encode_map(DiskMap(
        version=0x0700, header=header, extra_header=extra_header, sky_offsets=[0],
        sectors=[DiskObject(sector)], walls=walls, sprites=[],
        source_crc32=0, source_size=0,
    )))


def build_zmotion_behavior_scenario(directory: str | Path) -> dict[str, Any]:
    """Build public synthetic baseline/candidate MAPs for a composed trigger scenario."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    source = _static_scenario_map()
    source.sectors[0].fields.update(type=600, extra=1)
    xsector = _empty_extra(XSECTOR_SCHEMA)
    xsector.update(
        reference=0, rx_id=100, busy_time_a=5, busy_time_b=5, interruptable=1,
        off_ceiling_z=-8192, on_ceiling_z=-4096,
        off_floor_z=8192, on_floor_z=8192, marker_0=-1, marker_1=-1,
    )
    source.sectors[0].extra = PackedExtra("XSECTOR", xsector)
    source.walls[1].fields["extra"] = 1
    xwall = _empty_extra(XWALL_SCHEMA)
    xwall.update(reference=1, tx_id=100, command=1, decoupled=1, trigger_push=1)
    source.walls[1].extra = PackedExtra("XWALL", xwall)
    source = parse_map(encode_map(source))

    baseline = source.to_level_ir()
    baseline.translate(4096, 0, 0)
    fragment = source.to_level_ir().extract([0])
    composition = insert_fragment(_static_scenario_map().to_level_ir(), fragment, dx=4096)
    candidate = composition.level
    candidate.player_start.update(x=4608, y=512, z=0, angle=0, sector=1)

    baseline_path, candidate_path = root / "baseline.MAP", root / "candidate.MAP"
    write_map(baseline.to_disk_map(), baseline_path)
    write_map(candidate.to_disk_map(), candidate_path)
    return {
        "name": "wall-push-zmotion-v1",
        "baseline": baseline_path,
        "candidate": candidate_path,
        "action": {
            "input": "Open",
            "source": "wall[1].XWALL",
            "channel": 100,
            "target": "sector[0].XSECTOR",
            "command": "On",
            "effect": "ceiling_z -8192 -> -4096",
        },
        "composition": composition.report(),
    }


def _window_for_process(process: subprocess.Popen[Any], timeout: float = 5.0) -> int:
    if os.name != "nt":
        raise OracleError("the screenshot behavior oracle currently requires Windows")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        windows: list[tuple[int, int]] = []

        @callback_type
        def collect(window: int, _parameter: int) -> bool:
            owner = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(ctypes.c_void_p(window), ctypes.byref(owner))
            if owner.value == process.pid and user32.IsWindowVisible(ctypes.c_void_p(window)):
                class_name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(ctypes.c_void_p(window), class_name, len(class_name))
                windows.append((1 if class_name.value == "SDL_app" else 0, int(window)))
            return True

        user32.EnumWindows(collect, 0)
        if windows:
            return max(windows)[1]
        time.sleep(0.05)
    raise OracleError(f"NBlood process {process.pid} did not create a controllable window")


def _focus_window(window: int, attempts: int = 5) -> None:
    """Take the foreground, working around Windows' foreground lock.

    ``SetForegroundWindow`` is refused whenever another process owns the
    foreground lock, which happens routinely when the harness runs from an
    active terminal.  Tapping a modifier releases the lock for this thread, and
    attaching to the foreground thread's input queue makes the request legal.
    Neither trick changes what a successful focus means, only how often it works.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    target = ctypes.c_void_p(window)
    for attempt in range(attempts):
        user32.ShowWindow(target, 9)  # SW_RESTORE
        user32.SetWindowPos(target, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0003)
        user32.SetWindowPos(target, ctypes.c_void_p(-2), 0, 0, 0, 0, 0x0003)
        user32.BringWindowToTop(target)
        # A synthetic ALT press releases this thread's foreground lock.
        user32.keybd_event(0x12, user32.MapVirtualKeyW(0x12, 0), 0, 0)
        user32.keybd_event(0x12, user32.MapVirtualKeyW(0x12, 0), 2, 0)
        foreground = ctypes.c_void_p(user32.GetForegroundWindow())
        owner = ctypes.c_ulong()
        foreground_thread = user32.GetWindowThreadProcessId(foreground, ctypes.byref(owner))
        our_thread = kernel32.GetCurrentThreadId()
        attached = bool(
            foreground_thread and foreground_thread != our_thread
            and user32.AttachThreadInput(our_thread, foreground_thread, True)
        )
        try:
            user32.SetForegroundWindow(target)
            user32.SetActiveWindow(target)
        finally:
            if attached:
                user32.AttachThreadInput(our_thread, foreground_thread, False)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and int(user32.GetForegroundWindow() or 0) != window:
            time.sleep(0.01)
        if int(user32.GetForegroundWindow() or 0) == window:
            return
        time.sleep(0.2 * (attempt + 1))
    raise OracleError("Windows did not make the NBlood window foreground")


def _press_key(window: int, virtual_key: int) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    _focus_window(window)
    time.sleep(0.2)
    scan_code = user32.MapVirtualKeyW(virtual_key, 0)
    user32.keybd_event(virtual_key, scan_code, 0, 0)
    # Keep the synthetic key pulse below a game tick. Longer pulses can repeat
    # screenshot bindings and sample several frames instead of one controlled view.
    time.sleep(0.005)
    user32.keybd_event(virtual_key, scan_code, 2, 0)


def _wait_for_map_initialization(
    process: subprocess.Popen[Any], log_path: Path, timeout: float,
) -> None:
    deadline = time.monotonic() + timeout
    marker = _REQUIRED_MARKERS["map_initialization"]
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OracleError(f"NBlood exited before MAP initialization with code {process.returncode}")
        if log_path.exists() and marker in log_path.read_text(encoding="utf-8", errors="replace"):
            return
        time.sleep(0.05)
    raise OracleError(f"NBlood did not initialize the behavior MAP within {timeout:g} seconds")


def _capture_screenshots(work_dir: Path, window: int, timeout: float = 3.0) -> list[Path]:
    """Press the bound screenshot key once and return the files it produced."""
    screenshot_dir = work_dir / "screenshots"
    before = {item.name for item in screenshot_dir.glob("blud*.png")} if screenshot_dir.exists() else set()
    _press_key(window, 0x7A)  # F11, bound to NBlood's screenshot command.
    deadline = time.monotonic() + timeout
    last_count, stable_since = -1, time.monotonic()
    created: list[Path] = []
    while time.monotonic() < deadline:
        current = sorted(
            (item for item in screenshot_dir.glob("blud*.png") if item.name not in before),
            key=lambda item: item.name,
        ) if screenshot_dir.exists() else []
        if len(current) != last_count:
            last_count, stable_since = len(current), time.monotonic()
        created = current
        if created and time.monotonic() - stable_since >= 0.25:
            break
        time.sleep(0.05)
    if not created:
        raise OracleError("NBlood did not produce a screenshot for the controlled key")
    return created


def _capture_hashes(work_dir: Path, window: int, timeout: float = 3.0) -> dict[str, Any]:
    created = _capture_screenshots(work_dir, window, timeout)
    hashes = sorted({hashlib.sha256(item.read_bytes()).hexdigest() for item in created})
    return {"files": len(created), "unique_sha256": hashes}


def _probe_behavior_map(
    map_path: Path, *, nblood: Path, game_dir: Path,
    startup_timeout: float, settle_seconds: float, work_dir: Path,
) -> dict[str, Any]:
    identity = _map_identity(map_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = work_dir / "screenshots"
    if screenshot_dir.exists():
        shutil.rmtree(screenshot_dir)
    for name in ("nblood.log", "stdout.txt", "stderr.txt"):
        candidate = work_dir / name
        if candidate.exists():
            candidate.unlink()
    shutil.copy2(map_path, work_dir / "oracle.MAP")
    (work_dir / "oracle.cfg").write_text(_CONFIG, encoding="utf-8", newline="\n")
    (work_dir / "autoexec.cfg").write_text(_BEHAVIOR_AUTOEXEC, encoding="utf-8", newline="\n")
    command = [
        str(nblood), "-usecwd", "-game_dir", str(game_dir),
        "-cfg", "oracle.cfg", "-map", "oracle.MAP",
        "-noautoload", "-quick", "-nosetup",
    ]
    stdout_path, stderr_path = work_dir / "stdout.txt", work_dir / "stderr.txt"
    control_error: str | None = None
    before_view: dict[str, Any] = {"files": 0, "unique_sha256": []}
    idle_view: dict[str, Any] = {"files": 0, "unique_sha256": []}
    after_view: dict[str, Any] = {"files": 0, "unique_sha256": []}
    stayed_alive = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command, cwd=work_dir, stdout=stdout, stderr=stderr,
            **_interactive_process_options(),
        )
        try:
            _wait_for_map_initialization(process, work_dir / "nblood.log", startup_timeout)
            time.sleep(2.0)
            window = _window_for_process(process)
            before_view = _capture_hashes(work_dir, window)
            time.sleep(settle_seconds)
            idle_view = _capture_hashes(work_dir, window)
            _press_key(window, 0x45)  # E, bound to gamefunc_Open.
            time.sleep(settle_seconds)
            after_view = _capture_hashes(work_dir, window)
            stayed_alive = process.poll() is None
        except (OSError, OracleError) as exc:
            control_error = str(exc)
        finally:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    log = (work_dir / "nblood.log").read_text(encoding="utf-8", errors="replace") \
        if (work_dir / "nblood.log").exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    assessment = assess_nblood_output(log, stderr_text, stayed_alive)
    stable_views = (
        len(before_view["unique_sha256"]) == 1
        and len(idle_view["unique_sha256"]) == 1
        and len(after_view["unique_sha256"]) == 1
    )
    idle_unchanged = stable_views and before_view["unique_sha256"] == idle_view["unique_sha256"]
    state_changed = stable_views and idle_view["unique_sha256"] != after_view["unique_sha256"]
    if control_error or not stable_views or not idle_unchanged or not state_changed:
        assessment["status"] = "fail"
    assessment.update(
        identity=identity,
        input_control_error=control_error,
        before_view=before_view,
        idle_control_view=idle_view,
        after_view=after_view,
        stable_views=stable_views,
        idle_control_unchanged=idle_unchanged,
        visible_state_changed=state_changed,
        terminated_by_harness=stayed_alive,
    )
    return assessment


def run_nblood_action_oracle(
    map_path: str | Path,
    *,
    nblood: str | Path,
    game_dir: str | Path,
    startup_timeout: float = 15.0,
    settle_seconds: float = 2.0,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Press Use once in a supplied MAP and require a stable visible state change."""
    if os.name != "nt":
        raise OracleError("the screenshot action oracle currently requires Windows")
    candidate = Path(map_path).resolve()
    nblood_path = Path(nblood).resolve()
    game_path = Path(game_dir).resolve()
    if not candidate.is_file():
        raise OracleError(f"action-oracle MAP does not exist: {candidate}")
    if not nblood_path.is_file():
        raise OracleError(f"NBlood executable does not exist: {nblood_path}")
    if not game_path.is_dir():
        raise OracleError(f"NBlood game-data directory does not exist: {game_path}")
    if not 1.0 <= startup_timeout <= 60.0:
        raise OracleError("startup_timeout must be between 1 and 60")
    if not 0.5 <= settle_seconds <= 30.0:
        raise OracleError("settle_seconds must be between 0.5 and 30")

    def execute(root: Path) -> dict[str, Any]:
        probe = _probe_behavior_map(
            candidate,
            nblood=nblood_path,
            game_dir=game_path,
            startup_timeout=startup_timeout,
            settle_seconds=settle_seconds,
            work_dir=root,
        )
        return {
            "$schema": "bloodmap.nblood-action-oracle-report",
            "schema_version": 1,
            "status": probe["status"],
            "action": {"input": "Open", "virtual_key": "E"},
            "probe": probe,
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="bloodmap-nblood-action-") as directory:
        return execute(Path(directory))


def _probe_viewpoint_map(
    map_path: Path, *, nblood: Path, game_dir: Path,
    startup_timeout: float, settle_seconds: float, work_dir: Path, image_path: Path,
    pitch_taps: int = 0,
) -> dict[str, Any]:
    """Load one pose-variant MAP and preserve exactly one deterministic view."""
    identity = _map_identity(map_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = work_dir / "screenshots"
    if screenshot_dir.exists():
        shutil.rmtree(screenshot_dir)
    for name in ("nblood.log", "stdout.txt", "stderr.txt"):
        candidate = work_dir / name
        if candidate.exists():
            candidate.unlink()
    shutil.copy2(map_path, work_dir / "oracle.MAP")
    (work_dir / "oracle.cfg").write_text(_CONFIG, encoding="utf-8", newline="\n")
    # The behavior autoexec is reused verbatim: it disables view bob (needed for a
    # repeatable frame) and binds the screenshot command.
    (work_dir / "autoexec.cfg").write_text(_BEHAVIOR_AUTOEXEC, encoding="utf-8", newline="\n")
    # -nodudes: a viewpoint frame is evidence about architecture.  With monsters
    # spawned the camera takes damage while it settles, so the frame comes back
    # as a red pain flash, a cultist filling the shot, or a death screen -- and
    # on an original campaign map it is usually all three.
    command = [
        str(nblood), "-usecwd", "-game_dir", str(game_dir),
        "-cfg", "oracle.cfg", "-map", "oracle.MAP",
        "-noautoload", "-quick", "-nosetup", "-nodudes",
    ]
    stdout_path, stderr_path = work_dir / "stdout.txt", work_dir / "stderr.txt"
    capture_error: str | None = None
    captured: dict[str, Any] = {"files": 0, "image": None, "image_sha256": None}
    stayed_alive = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command, cwd=work_dir, stdout=stdout, stderr=stderr,
            **_interactive_process_options(),
        )
        try:
            _wait_for_map_initialization(process, work_dir / "nblood.log", startup_timeout)
            time.sleep(settle_seconds)
            window = _window_for_process(process)
            # SetForegroundWindow loses races against whatever else is on the
            # interactive desktop.  A focus failure says nothing about the MAP,
            # so retry a bounded number of times before reporting it.
            if pitch_taps:
                key = PITCH_KEYS["up" if pitch_taps > 0 else "down"]
                for _ in range(min(abs(int(pitch_taps)), 64)):
                    _press_key(window, key)
                    time.sleep(0.02)
                time.sleep(0.4)
            files: list[Path] = []
            last: OracleError | None = None
            for attempt in range(4):
                try:
                    files = _capture_screenshots(work_dir, window)
                    break
                except OracleError as exc:
                    last = exc
                    time.sleep(0.5 * (attempt + 1))
            if not files:
                raise last or OracleError("no screenshot was produced for this viewpoint")
            image_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(files[0], image_path)
            captured = {
                "files": len(files),
                "image": str(image_path),
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            }
            stayed_alive = process.poll() is None
        except (OSError, OracleError) as exc:
            capture_error = str(exc)
        finally:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    log = (work_dir / "nblood.log").read_text(encoding="utf-8", errors="replace") \
        if (work_dir / "nblood.log").exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    assessment = assess_nblood_output(log, stderr_text, stayed_alive)
    if capture_error or captured["image"] is None:
        assessment["status"] = "fail"
    assessment.update(
        identity=identity,
        capture_error=capture_error,
        capture=captured,
        terminated_by_harness=stayed_alive,
    )
    return assessment


def run_nblood_viewpoint_capture(
    requests: list[dict[str, Any]],
    *,
    nblood: str | Path,
    game_dir: str | Path,
    image_dir: str | Path,
    startup_timeout: float = 20.0,
    settle_seconds: float = 2.5,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Capture one preserved PNG per declared viewpoint pose.

    .. deprecated::
       Use ``bloodmap.visual.run_observation`` instead.  This launches the game
       once per viewpoint, focuses its window, injects a screenshot key and
       waits for a file to appear; the frame it returns has the running game in
       it and the whole path is timing-dependent.  The observer renders the same
       pose from the same MAP with no process to focus and no key to press, and
       returns what was painted as well as a picture of it.

       Kept because a frame from the actual game is still the only way to
       photograph a *running* state -- a door mid-travel, a switch after it
       fires -- which the static observer cannot show.

    Each request supplies ``viewpoint_id``, a prepared pose-variant ``map`` path,
    and the ``resolved`` viewpoint record whose sector/XYZ/angle are recorded next
    to the image so a later reader can tell what the camera was actually shown.
    """
    if os.name != "nt":
        raise OracleError("the NBlood viewpoint capture currently requires Windows")
    nblood_path = Path(nblood).resolve()
    game_path = Path(game_dir).resolve()
    images = Path(image_dir).resolve()
    if not nblood_path.is_file():
        raise OracleError(f"NBlood executable does not exist: {nblood_path}")
    if not game_path.is_dir():
        raise OracleError(f"NBlood game-data directory does not exist: {game_path}")
    if not requests:
        raise OracleError("viewpoint capture requires at least one request")
    if not 1.0 <= startup_timeout <= 120.0:
        raise OracleError("startup_timeout must be between 1 and 120")
    if not 0.5 <= settle_seconds <= 30.0:
        raise OracleError("settle_seconds must be between 0.5 and 30")

    def execute(root: Path) -> dict[str, Any]:
        views: list[dict[str, Any]] = []
        for index, request in enumerate(requests):
            viewpoint_id = str(request["viewpoint_id"])
            variant = Path(request["map"]).resolve()
            if not variant.is_file():
                raise OracleError(f"viewpoint variant MAP does not exist: {variant}")
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in viewpoint_id)
            probe = _probe_viewpoint_map(
                variant, nblood=nblood_path, game_dir=game_path,
                startup_timeout=startup_timeout, settle_seconds=settle_seconds,
                work_dir=root / f"{index:02d}-{safe}", image_path=images / f"{safe}.png",
                pitch_taps=int(request.get("pitch_taps") or 0),
            )
            views.append({
                "viewpoint_id": viewpoint_id,
                "pitch_taps": int(request.get("pitch_taps") or 0),
                "resolved": deepcopy(request.get("resolved", {})),
                "variant_map_sha256": probe["identity"].get("sha256"),
                "status": probe["status"],
                "image": probe["capture"]["image"],
                "image_sha256": probe["capture"]["image_sha256"],
                "engine_revision": probe["engine_revision"],
                "probe": probe,
            })
        revisions = sorted({item["engine_revision"] for item in views if item["engine_revision"]})
        return {
            "$schema": "llmapper.nblood-viewpoint-capture",
            "schema_version": 1,
            "status": "pass" if all(item["status"] == "pass" for item in views) else "fail",
            "engine_revisions": revisions,
            "image_dir": str(images),
            "views": views,
            "limitations": [
                "an image hash proves stability, never visual quality",
                "one frame per pose; no motion, no lighting animation, no player behavior",
                "captured with -nodudes: evidence about architecture, never about encounters",
                "pitch is applied as engine Aim_Up/Aim_Down taps, so it is approximate",
            ],
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="bloodmap-nblood-views-") as directory:
        return execute(Path(directory))


def assess_behavior_equivalence(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    initial_equal = baseline["before_view"]["unique_sha256"] == candidate["before_view"]["unique_sha256"]
    idle_equal = baseline["idle_control_view"]["unique_sha256"] == candidate["idle_control_view"]["unique_sha256"]
    final_equal = baseline["after_view"]["unique_sha256"] == candidate["after_view"]["unique_sha256"]
    both_changed = baseline["visible_state_changed"] and candidate["visible_state_changed"]
    both_idle_unchanged = baseline["idle_control_unchanged"] and candidate["idle_control_unchanged"]
    both_stable = baseline["stable_views"] and candidate["stable_views"]
    passed = (
        baseline["status"] == "pass" and candidate["status"] == "pass"
        and initial_equal and idle_equal and final_equal
        and both_idle_unchanged and both_changed and both_stable
    )
    return {
        "status": "pass" if passed else "fail",
        "initial_view_equal": initial_equal,
        "idle_control_view_equal": idle_equal,
        "final_view_equal": final_equal,
        "both_idle_controls_unchanged": both_idle_unchanged,
        "both_states_changed": both_changed,
        "both_views_stable": both_stable,
    }


def run_nblood_behavior_oracle(
    *, nblood: str | Path, game_dir: str | Path,
    startup_timeout: float = 15.0, settle_seconds: float = 2.0,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Compare a synthetic trigger/Z-motion scenario before and after composition."""
    if os.name != "nt":
        raise OracleError("the screenshot behavior oracle currently requires Windows")
    nblood_path, game_path = Path(nblood).resolve(), Path(game_dir).resolve()
    if not nblood_path.is_file():
        raise OracleError(f"NBlood executable does not exist: {nblood_path}")
    if not game_path.is_dir():
        raise OracleError(f"NBlood game-data directory does not exist: {game_path}")
    if not 1.0 <= startup_timeout <= 60.0:
        raise OracleError("startup_timeout must be between 1 and 60")
    if not 0.5 <= settle_seconds <= 30.0:
        raise OracleError("settle_seconds must be between 0.5 and 30")

    def execute(root: Path) -> dict[str, Any]:
        scenario = build_zmotion_behavior_scenario(root / "inputs")
        baseline = _probe_behavior_map(
            scenario["baseline"], nblood=nblood_path, game_dir=game_path,
            startup_timeout=startup_timeout, settle_seconds=settle_seconds,
            work_dir=root / "baseline",
        )
        candidate = _probe_behavior_map(
            scenario["candidate"], nblood=nblood_path, game_dir=game_path,
            startup_timeout=startup_timeout, settle_seconds=settle_seconds,
            work_dir=root / "candidate",
        )
        equivalence = assess_behavior_equivalence(baseline, candidate)
        return {
            "$schema": "bloodmap.nblood-behavior-oracle-report",
            "schema_version": 1,
            "status": equivalence["status"],
            "scenario": {
                "name": scenario["name"],
                "action": scenario["action"],
                "composition": scenario["composition"],
            },
            "equivalence": equivalence,
            "probes": {"baseline": baseline, "candidate": candidate},
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="bloodmap-nblood-behavior-") as directory:
        return execute(Path(directory))


def run_gzdoom_oracle(
    iwad: str | Path,
    *,
    gzdoom: str | Path,
    map_name: str,
    pwad: str | Path | None = None,
    grace_seconds: float = 4.0,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Bounded GZDoom map-load smoke. GZDoom is an oracle, not a package dependency."""
    iwad_path = Path(iwad).resolve()
    gzdoom_path = Path(gzdoom).resolve()
    pwad_path = Path(pwad).resolve() if pwad is not None else None
    if not iwad_path.is_file():
        raise OracleError(f"IWAD does not exist: {iwad_path}")
    if not gzdoom_path.is_file():
        raise OracleError(f"GZDoom executable does not exist: {gzdoom_path}")
    if pwad_path is not None and not pwad_path.is_file():
        raise OracleError(f"PWAD does not exist: {pwad_path}")
    if not 1.0 <= grace_seconds <= 60.0:
        raise OracleError("grace_seconds must be between 1 and 60")

    def execute(root: Path) -> dict[str, Any]:
        root.mkdir(parents=True, exist_ok=True)
        log_path = root / "gzdoom.log"
        if log_path.exists():
            log_path.unlink()
        command = [
            str(gzdoom_path),
            "-iwad", str(iwad_path),
            "-nosound", "-nomusic", "-nologo", "-stdout",
            "+map", map_name,
        ]
        if pwad_path is not None:
            command[4:4] = ["-file", str(pwad_path)]
        stdout_path, stderr_path = root / "stdout.txt", root / "stderr.txt"
        stayed_alive = False
        returncode: int | None = None
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command, cwd=root, stdout=stdout, stderr=stderr,
                **_hidden_process_options(),
            )
            deadline = time.monotonic() + grace_seconds
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                time.sleep(0.2)
            else:
                stayed_alive = True
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            returncode = process.poll()
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        combined = "\n".join((log, stdout_text, stderr_text))
        marker = map_name.upper() in combined.upper()
        fatal = bool(re.search(r"execution could not continue|fatal error|access violation", combined, re.I))
        status = "pass" if stayed_alive and marker and not fatal else "fail"
        return {
            "$schema": "llmapper.gzdoom-oracle-report",
            "schema_version": 1,
            "status": status,
            "map": map_name,
            "stayed_alive": stayed_alive,
            "map_marker_seen": marker,
            "fatal": fatal,
            "returncode": returncode,
            "iwad": str(iwad_path),
            "pwad": str(pwad_path) if pwad_path else "",
        }

    if work_dir is not None:
        return execute(Path(work_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="bloodmap-gzdoom-oracle-") as directory:
        return execute(Path(directory))
