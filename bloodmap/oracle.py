from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .analysis import validate_map
from .format import read_map


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


def _hidden_process_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return {"startupinfo": startup, "creationflags": subprocess.CREATE_NO_WINDOW}


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
