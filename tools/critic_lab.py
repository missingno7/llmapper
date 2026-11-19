"""The station as a laboratory: what can a critic tell, and from where?

The owner, 2026-11-19: "That station is your playground, test its limits,
explore what critics can tell about it."

`tools.critic_bench` asked which critic is best. This asks what the best
one (GPT-6.2 Sol at high effort) can be made to tell, by changing ONE
thing at a time and watching the answer:

``distance``   the same carriage from one body away to the far side of
               the hall, along the platform, and from the track: from
               where does a carriage become a carriage?
``engine``     the locomotive from all round.
``ablate``     the locomotive and the carriage with one part taken away
               (wheels, smoke, horned face, chimney and dome; the door,
               the bill, the curtains, the livery): which part carries
               the identity? A part whose loss changes no answer is
               decoration; one whose loss changes it is the thing.
``prompts``    the same six views asked four ways: name it; list what
               you see, then name it; choose among eight kinds of place;
               and, told what it is meant to be, say the one change that
               would help most.
``brightness`` the same views at the renderer's brightness 0 and 8:
               every reader says "very dark" -- is the darkness in the
               map or in the frame?

Every case is one picture and one reader. Answers are kept, keyed by
what was changed, so a rerun asks only what is new.

.. code-block:: bash

    python -m tools.critic_lab run        # render, ask, report
    python -m tools.critic_lab report
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

LAB = ROOT / "knowledge" / "blood" / "critic-bench" / "lab-1"
CITY = ROOT / "projects" / "blood-city" / "level" / "blood-city-current.MAP"
SANDBOX = ROOT.parent / (ROOT.name + "-critique-sandbox")
MODEL, EFFORT = "gpt-6.2-sol", "high"

TRAIN = ["carriage", "train", "railcar", "rail car", "railway car", "coach",
         "tram", "wagon", "boxcar", "locomotive", "steam engine", "subway"]
STATION = ["station", "platform", "railway", "railroad", "rail"]

HEAD = ("You are shown ONE screenshot from a 1997 first-person shooter level "
        "(Build engine: low resolution, flat sprites). Do not run any "
        "commands or read any files; the screenshot is attached. ")
KINDS = ("a church", "a warehouse", "a prison", "a railway station",
         "a sewer", "a hotel", "a factory", "a city street")
PROMPTS = {
    "name": HEAD + "Answer in exactly this form, nothing else:\n"
            "NAME: <the main thing or place shown, at most 6 words>\n"
            "SURE: <1-5>\nWHY: <at most 20 words>",
    "list": HEAD + "Answer in exactly this form, nothing else:\n"
            "SEEN: <the five most recognisable things in the picture, "
            "comma separated>\n"
            "NAME: <the main thing or place shown, at most 6 words>\n"
            "SURE: <1-5>",
    "choice": HEAD + "This view is from one of these kinds of place: "
              + ", ".join(KINDS) + ". Answer in exactly this form, nothing "
              "else:\nNAME: <one of those, word for word>\nSURE: <1-5>\n"
              "WHY: <at most 20 words>",
    "fix": HEAD + "This is MEANT to be: {truth}. Answer in exactly this "
           "form, nothing else:\n"
           "NAME: <what it actually looks like to you, at most 6 words>\n"
           "READS: <yes or no: would you have guessed what it is meant "
           "to be?>\n"
           "FIX: <the ONE change to what is built that would most help it "
           "read as that, at most 25 words>",
}

#: view -> (camera x, y, look-at x, y in plan units of 1,024; floor z)
P, T = -12288, 2048                 # platform level, track level
VIEWS = {
    # the carriage's door, nearer and farther
    "door_1": (15.4, -15.5, 15.0, -16.4, P),
    "door_2": (15.4, -14.6, 15.0, -16.4, P),
    "door_3": (15.4, -13.4, 15.0, -16.4, P),
    "door_4": (15.4, -12.0, 15.0, -16.4, P),
    "door_5": (15.4, -10.5, 15.0, -16.4, P),
    "door_6": (15.4, -9.0, 15.0, -16.4, P),
    # along the platform, and from the track
    "along_w": (10.8, -15.2, 16.0, -16.4, P),
    "along_e": (21.6, -15.2, 14.0, -16.4, P),
    "track_1": (15.4, -20.0, 15.4, -18.4, T),
    "track_2": (15.4, -21.6, 15.4, -18.4, T),
    "track_3": (15.4, -23.4, 15.4, -18.4, T),
    "track_far": (4.5, -21.5, 14.0, -18.0, T),
    # the engine from all round
    "eng_w": (23.2, -15.4, 26.3, -17.6, P),
    "eng_mid": (25.5, -15.2, 26.3, -17.6, P),
    "eng_e": (28.6, -14.8, 25.0, -17.4, P),
    "eng_balcony": (27.6, -14.0, 25.4, -17.4, -32768),
    "eng_track_e": (29.6, -21.2, 26.3, -17.8, T),
    "eng_track_n": (26.0, -22.8, 26.3, -17.8, T),
    "eng_front": (29.8, -17.6, 26.0, -17.6, T),
    # places
    "ticket": (10.4, -12.0, 7.0, -12.3, P),
    "hall": (17.6, -8.6, 9.5, -12.5, P),
    "waiting": (18.6, -10.8, 21.8, -13.2, P),
    "goods": (38.6, -20.2, 43.0, -22.5, T),
}
TRUTH = {
    "door_2": "the door of a railway carriage standing at a platform",
    "door_5": "a railway carriage seen from the station hall",
    "eng_e": "a steam locomotive",
    "eng_w": "a steam locomotive seen from its cab end",
    "ticket": "a railway station's ticket window",
    "hall": "the hall of a small railway station",
    "waiting": "a railway station's waiting room",
}


def _f(item):
    return item["fields"] if isinstance(item, dict) else item.fields


def _hide(disk, tiles):
    for sprite in disk.sprites:
        s = _f(sprite)
        if int(s["picnum"]) in tiles and int(s["y"]) < 0:
            s["cstat"] = int(s["cstat"]) | 32768


def _flatten(disk, rects):
    import l3_station as st

    top = st.BED_Z - 13312 - 17408                     # the boiler's top
    for sector in disk.sectors:
        s = _f(sector)
        pts = [(int(_f(disk.walls[w])["x"]), int(_f(disk.walls[w])["y"]))
               for w in range(int(s["wall_ptr"]),
                              int(s["wall_ptr"]) + int(s["wall_count"]))]
        box = (min(p[0] for p in pts), min(p[1] for p in pts),
               max(p[0] for p in pts), max(p[1] for p in pts))
        if box in rects:
            s["floor_z"] = top


def _repaint(disk, old, new):
    for wall in disk.walls:
        w = _f(wall)
        if int(w["picnum"]) == old and int(w["y"]) < 0:
            w["picnum"] = new


def variant(disk, name: str) -> None:
    """One named change to the map. `full` changes nothing."""
    import l3_station as st

    wheels, smoke, face = {2320}, {754, 672}, {634}
    if name in ("full", "bright"):
        return
    if name == "no_wheels":
        _hide(disk, wheels)
    elif name == "no_smoke":
        _hide(disk, smoke)
    elif name == "no_face":
        _hide(disk, face)
    elif name == "no_chimney":
        _flatten(disk, {st.CHIMNEY, st.DOME})
        _hide(disk, smoke)
    elif name == "bare_engine":
        _hide(disk, wheels | smoke | face | {st.CAB_WINDOW})
        _flatten(disk, {st.CHIMNEY, st.DOME})
    elif name == "only_wheels":
        _hide(disk, smoke | face | {st.CAB_WINDOW})
        _flatten(disk, {st.CHIMNEY, st.DOME})
    elif name == "no_door":
        _repaint(disk, st.CAR_DOOR_TILE, st.LIVERY)
    elif name == "no_bill":
        _hide(disk, {st.BILL})
    elif name == "no_curtains":
        _hide(disk, {st.CURTAIN})
    elif name == "brick_livery":
        _repaint(disk, st.LIVERY, st.HALL_WALL)
    else:
        raise SystemExit(f"no such variant: {name}")


#: experiment -> [(variant, view, prompt)]
def plan() -> dict:
    out = {}
    out["distance"] = [("full", v, "name") for v in (
        "door_1", "door_2", "door_3", "door_4", "door_5", "door_6",
        "along_w", "along_e", "track_1", "track_2", "track_3", "track_far")]
    out["engine"] = [("full", v, "name") for v in (
        "eng_w", "eng_mid", "eng_e", "eng_balcony", "eng_track_e",
        "eng_track_n", "eng_front")]
    out["ablate_engine"] = [(name, view, "name") for name in (
        "full", "no_wheels", "no_smoke", "no_face", "no_chimney",
        "only_wheels", "bare_engine") for view in ("eng_e", "eng_track_e")]
    out["ablate_car"] = [(name, view, "name") for name in (
        "full", "no_door", "no_bill", "no_curtains", "brick_livery")
        for view in ("door_2", "door_5", "track_2")]
    six = ("door_2", "door_5", "eng_e", "ticket", "hall", "waiting")
    out["prompts"] = [("full", view, prompt) for view in six
                      for prompt in ("name", "list", "choice", "fix")]
    out["brightness"] = [(name, view, "name") for name in ("full", "bright")
                         for view in six + ("eng_w", "goods")]
    return out


def render(cases) -> None:
    import look
    from bloodmap.format import read_map, write_map
    from bloodmap.viewplan import angle_toward, eye_z
    from bloodmap.visual import Viewpoint
    from tools import critique

    quiet = critique.mute_tiles()
    wanted: dict = {}
    for name, view, _prompt in cases:
        wanted.setdefault(name, set()).add(view)
    SANDBOX.mkdir(exist_ok=True)
    for name, views in sorted(wanted.items()):
        folder = LAB / "render" / name
        missing = [v for v in sorted(views)
                   if not (SANDBOX / f"lab-{name}-{v}.png").exists()]
        if not missing:
            continue
        played = look.as_played(CITY, folder, empty=True)
        disk = read_map(played)
        for sprite in disk.sprites:
            if int(sprite.fields["picnum"]) in quiet:
                sprite.fields["cstat"] = int(sprite.fields["cstat"]) | 32768
        variant(disk, name)
        write_map(disk, played)
        level = read_map(played).to_level_ir()
        points = []
        for view in missing:
            px, py, tx, ty, near = VIEWS[view]
            x, y = int(px * 1024), int(py * 1024)
            sector = look.sector_at(level, x, y, near)
            z = eye_z(level, sector) if sector is not None else None
            if z is None:
                print(f"  ! {name}/{view}: no place to stand")
                continue
            points.append(Viewpoint(
                view_id=view, x=x, y=y, z=z,
                angle=int(angle_toward((x, y), (int(tx * 1024),
                                                int(ty * 1024)))) & 2047,
                horiz=look.LEVEL, sector=sector, node=f"lab:{view}",
                purpose="loop", screenshot=True, note="lab"))
        look.run_observation(look.ObservationRequest(
            map_path=played, output_dir=folder,
            resource_dir=pathlib.Path("reference/blood"), viewpoints=points,
            width=640, height=480, screenshots=[v.view_id for v in points],
            brightness=8 if name == "bright" else 0, rff=None))
        for view in missing:
            frame = folder / "frames" / f"{view}.png"
            if frame.exists():
                shutil.copyfile(frame, SANDBOX / f"lab-{name}-{view}.png")


def _fields_of(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        head, sep, rest = line.partition(":")
        if sep and head.strip().isupper() and len(head) < 12:
            out[head.strip().lower()] = rest.strip()
    return out


def ask(cases, workers: int = 12) -> dict:
    path = LAB / "answers.json"
    answers = json.loads(path.read_text("utf-8")) if path.exists() else {}
    cx = pathlib.Path.home() / ".codex-dashboard" / "cx.py"

    def one(case):
        name, view, prompt = case
        image = SANDBOX / f"lab-{name}-{view}.png"
        if not image.exists():
            return case, {"error": "no frame"}
        text = PROMPTS[prompt].replace("{truth}", TRUTH.get(view, "?"))
        started = time.time()
        run = subprocess.run(
            [sys.executable, str(cx), "run", "-n", f"lab-{name}-{view}",
             "-C", str(SANDBOX), "-m", MODEL, "-e", EFFORT, "-s", "read-only",
             "--", "-i", str(image)],
            input=text, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        row = _fields_of(run.stdout)
        row["seconds"] = round(time.time() - started, 1)
        if run.returncode or "name" not in row:
            row["error"] = (run.stdout + run.stderr)[-200:]
        return case, row

    todo = sorted({c for c in cases
                   if "name" not in answers.get("|".join(c), {})})
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for case, row in pool.map(one, todo):
            answers["|".join(case)] = row
    LAB.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answers, indent=1), "utf-8")
    return answers


def _is(words, said: str) -> bool:
    said = said.lower()
    return any(word in said for word in words)


def report() -> None:
    answers = json.loads((LAB / "answers.json").read_text("utf-8"))
    for experiment, cases in plan().items():
        print(f"\n== {experiment}")
        for case in cases:
            row = answers.get("|".join(case), {})
            name, view, prompt = case
            said = row.get("name", row.get("error", "?"))
            mark = ("TRAIN  " if _is(TRAIN, said) else
                    "station" if _is(STATION, said) else "  --   ")
            extra = " | ".join(f"{k}: {row[k]}" for k in
                               ("seen", "reads", "fix") if k in row)
            print(f"  {mark} {name:13s} {view:12s} {prompt:6s} "
                  f"{said} (sure {row.get('sure', '-')})"
                  + (f" | {extra}" if extra else ""))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)
    if args.command == "run":
        cases = [c for name, rows in plan().items() for c in rows
                 if not args.only or name == args.only]
        render(cases)
        ask(cases)
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
