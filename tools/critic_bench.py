"""Which model is the best critic? A test with answers nobody argues about.

The owner, 2026-11-19: "I would like to know which model is best critic,
compare also sonnet and Haiku with them, also test gpt 6.2 sol. Question
is how to do objective test."

A critic of a level does two things, and each can be tested against a
truth that does not depend on anybody's taste:

``naming``  Shown one view and told nothing, does it say what the place
            or thing IS? The truth is Blood's own: views of places in
            the campaign and its add-ons whose identity is not in
            doubt (a bar with stools and bottles, a church with pews
            and an altar, a carriage, a locomotive). Chosen by eye from
            the studies' frames, once, before any model was asked.
``faults``  Shown one view, does it say that something is physically
            wrong -- and WHAT? The truth is PLANTED: the city's map is
            copied and one thing in it is broken on purpose (the rails
            turned across the track, a barrel lifted into the air, the
            station's name hung upside down, track laid through the
            waiting hall, the engine's wheels above its boiler, chairs
            floating). Each broken view has its CLEAN twin, and every
            naming view is a clean view too: a critic that cries fault
            at everything scores no better than one that never does.

One question, one picture, one reader, nothing else in sight; every
model gets the same words. Scores: naming hits, faults caught, faults
caught AND correctly named, false alarms on clean views, seconds.

.. code-block:: bash

    python -m tools.critic_bench build
    python -m tools.critic_bench ask --model gpt-6.2-sol --model gpt-6-luna
    python -m tools.critic_bench claude-jobs --model sonnet   # prints jobs
    python -m tools.critic_bench score
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import random
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

BENCH = ROOT / "knowledge" / "blood" / "critic-bench" / "v1"
STUDIES = ROOT / "knowledge" / "blood" / "studies"
CITY = ROOT / "projects" / "blood-city" / "level" / "blood-city-current.MAP"
SANDBOX = ROOT.parent / (ROOT.name + "-critique-sandbox")

PROMPT = """You are shown ONE screenshot from a 1997 first-person shooter \
level (Build engine: low resolution, flat sprites). Look only at that one \
image. Answer in exactly this form, nothing else:
NAME: <the main thing or place shown, at most 6 words>
SURE: <1-5>
FAULT: <yes or no>
WHAT: <at most 20 words: the fault, or "nothing">

FAULT means something in the picture is physically impossible or absurd \
AS BUILT: an object hanging in mid-air, something upside down, something \
laid the wrong way round for it to work, a thing where it cannot be. \
Darkness, pixelation, flat or low-resolution textures, a red or strange \
sky, blood and monsters are NORMAL for this game and are NOT faults. \
Most pictures have no fault."""

RAIL = ["carriage", "train", "railcar", "rail car", "railway car", "coach",
        "tram", "wagon", "boxcar", "locomotive"]
BAR = ["bar", "saloon", "tavern", "pub", "restaurant", "diner", "cafe",
       "lounge", "inn"]
DOCK = ["dock", "pier", "wharf", "boardwalk", "jetty", "quay", "harbour",
        "harbor", "boathouse", "waterfront"]
#: (path under the studies, what it is, words that count as naming it)
NAMING = [
    ("station/E1M2_34/frames/corner_3.png", "railway track (E1M2)",
     ["rail", "track", "train", "subway", "tunnel"]),
    ("station/maps_blood_community_STATION.MAP_125/frames/corner_0.png",
     "railway carriage, parked (community STATION)",
     RAIL),
    ("crypt/E1M1_150/frames/corner_2.png", "crypt (E1M1)",
     ["crypt", "tomb", "mausoleum", "catacomb", "burial", "sepulch",
      "graveyard", "cemetery", "morgue", "coffin", "sarcophag"]),
    ("saloon/DWE3M1_238/frames/corner_0.png", "saloon (Death Wish)", BAR),
    ("saloon/E1M2_278/frames/corner_1.png", "bar with stools (E1M2)", BAR),
    ("saloon/E2M4_434/frames/corner_0.png", "kitchen (E2M4)",
     ["kitchen", "butcher", "meat", "galley", "pantry", "scullery"]),
    ("church/E3M4_286/frames/corner_0.png", "chapel with pews and altar",
     ["church", "chapel", "cathedral", "altar", "temple", "shrine",
      "sanctuary", "nave"]),
    ("harbour/DWE3M4_548/frames/corner_1.png", "boardwalk / pier at night",
     DOCK + ["carnival", "fair", "promenade"]),
    ("harbour/DWE2M6_627/frames/corner_2.png", "under a pier, over water",
     DOCK + ["water", "bridge", "under"]),
    ("theatre/E1M1_122/frames/corner_2.png", "funeral parlour (E1M1)",
     ["funeral", "memorial", "mortuary", "wake", "chapel", "parlour",
      "parlor", "viewing"]),
    ("theatre/maps_blood_community_FORDTHEA.MAP_252/frames/corner_2.png",
     "cinema / theatre", ["theatre", "theater", "cinema", "movie",
                          "auditorium", "screening"]),
    ("locomotive/round_E1M4/frames/round_03.png", "steam locomotive (E1M4)",
     ["locomotive", "steam engine", "train", "steam train"]),
]


def _f(item):
    return item["fields"] if isinstance(item, dict) else item.fields


def _plant(disk, fault: str) -> int:
    """Break exactly one thing. Returns how many records were changed."""
    import l3_station as st
    from tools import critique

    changed = 0
    north = [s for s in disk.sprites if int(_f(s)["y"]) < 0]
    if fault == "rails_across":
        for sector in disk.sectors:
            s = _f(sector)
            if int(s["floor_picnum"]) == st.TRACK:
                s["floor_stat"] = int(s["floor_stat"]) ^ 4
                changed += 1
    elif fault == "barrel_in_air":
        for sprite in north:
            if int(_f(sprite)["picnum"]) == 925:
                _f(sprite)["z"] = int(_f(sprite)["z"]) - 16000
                changed += 1
    elif fault == "name_upside_down":
        words = critique.mute_tiles()
        for sprite in disk.sprites:
            s = _f(sprite)
            if (int(s["picnum"]) in words and abs(int(s["y"])) < 700
                    and 13000 < int(s["x"]) < 19500):
                s["cstat"] = int(s["cstat"]) | 8
                changed += 1
    elif fault == "track_through_hall":
        x0, y0, x1, y1 = st.HALL
        for sector in disk.sectors:
            s = _f(sector)
            w = _f(disk.walls[int(s["wall_ptr"])])
            if (x0 <= int(w["x"]) <= x1 and y0 <= int(w["y"]) <= y1
                    and int(s["floor_z"]) == st.HALL_Z
                    and int(s["floor_picnum"]) == st.FLOOR):
                s["floor_picnum"] = st.TRACK
                changed += 1
    elif fault == "wheels_on_top":
        for sprite in north:
            if int(_f(sprite)["picnum"]) == st.WHEELS["picnum"]:
                _f(sprite)["z"] = int(_f(sprite)["z"]) - 30000
                changed += 1
    elif fault == "chairs_in_air":
        for sprite in north:
            if int(_f(sprite)["picnum"]) == st.CHAIR:
                _f(sprite)["z"] = int(_f(sprite)["z"]) - 9000
                changed += 1
    else:
        raise SystemExit(f"no such fault: {fault}")
    return changed


#: fault -> (the pose it is seen from, words that count as naming it)
FAULTS = {
    "rails_across": ("from_track", ["rail", "track", "sleeper", "tie"]),
    "barrel_in_air": ("nose", ["barrel", "float", "mid-air", "midair",
                               "hover", "air"]),
    "name_upside_down": ("street_door", ["upside", "invert", "flipped",
                                         "letter", "sign", "text"]),
    "track_through_hall": ("hall", ["rail", "track"]),
    "wheels_on_top": ("nose", ["wheel"]),
    "chairs_in_air": ("inside", ["chair", "float", "mid-air", "midair",
                                 "hover", "air", "furniture"]),
}


def build() -> pathlib.Path:
    import look
    from bloodmap.format import read_map, write_map

    (BENCH / "q").mkdir(parents=True, exist_ok=True)
    rows = []
    for path, truth, accept in NAMING:
        rows.append({"kind": "naming", "truth": truth, "accept": accept,
                     "fault": None, "file": str(STUDIES / path)})

    def render(tag, fault, poses):
        folder = BENCH / "render" / tag
        played = look.as_played(CITY, folder, empty=True)
        if fault:
            disk = read_map(played)
            count = _plant(disk, fault)
            if not count:
                raise SystemExit(f"{fault}: nothing to break")
            write_map(disk, played)
        level = read_map(played).to_level_ir()
        views = [v for v in look.poses_for(level, "railway")
                 if v.view_id in poses]
        look.run_observation(look.ObservationRequest(
            map_path=played, output_dir=folder,
            resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
            width=640, height=480, screenshots=[v.view_id for v in views],
            brightness=0, rff=None))
        return folder / "frames"

    poses = sorted({pose for pose, _ in FAULTS.values()})
    clean = render("clean", None, poses)
    for pose in poses:
        rows.append({"kind": "clean", "truth": f"our station: {pose}",
                     "accept": [], "fault": None,
                     "file": str(clean / f"{pose}.png")})
    for fault, (pose, words) in FAULTS.items():
        frames = render(fault, fault, [pose])
        rows.append({"kind": "fault", "truth": fault, "accept": words,
                     "fault": fault, "file": str(frames / f"{pose}.png")})
    random.Random(1).shuffle(rows)
    key = {}
    for index, row in enumerate(rows):
        name = f"b_{index + 1:02d}"
        shutil.copyfile(row["file"], BENCH / "q" / f"{name}.png")
        key[name] = {k: row[k] for k in ("kind", "truth", "accept", "fault")}
    (BENCH / "key.json").write_text(json.dumps(key, indent=1), "utf-8")
    SANDBOX.mkdir(exist_ok=True)
    for name in key:
        shutil.copyfile(BENCH / "q" / f"{name}.png",
                        SANDBOX / f"bench-{name}.png")
    return BENCH


def parse(text: str) -> dict:
    out = {"name": "", "sure": 0, "fault": None, "what": ""}
    for line in text.splitlines():
        head, _, rest = line.partition(":")
        head, rest = head.strip().lower(), rest.strip()
        if head == "name":
            out["name"] = rest
        elif head == "what":
            out["what"] = rest
        elif head == "sure":
            digits = "".join(c for c in rest if c.isdigit())
            out["sure"] = int(digits[:1] or 0)
        elif head == "fault":
            out["fault"] = rest.lower().startswith("y")
    out["ok"] = bool(out["name"]) and out["fault"] is not None
    return out


def _answers() -> dict:
    path = BENCH / "answers.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


def ask(models: list[str], effort: str, workers: int) -> None:
    """The GPT readers, each (model, view) its own `cx` worker."""
    key = json.loads((BENCH / "key.json").read_text("utf-8"))
    answers = _answers()
    cx = pathlib.Path.home() / ".codex-dashboard" / "cx.py"
    prompt = ("Do not run any commands or read any files; the screenshot is "
              "attached.\n" + PROMPT)

    def one(model, q):
        #: "name@effort" asks the same model at another effort, as its own
        #: row: does thinking longer buy a better critic?
        name, _, own = model.partition("@")
        started = time.time()
        run = subprocess.run(
            [sys.executable, str(cx), "run", "-n", f"bench-{name}-{q}",
             "-C", str(SANDBOX), "-m", name, "-e", own or effort, "-s",
             "read-only",
             "--", "-i", str(SANDBOX / f"bench-{q}.png")],
            input=prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        row = parse(run.stdout)
        row["seconds"] = round(time.time() - started, 1)
        if run.returncode or not row["ok"]:
            row["ok"] = False
            row["error"] = (run.stdout + run.stderr)[-300:]
        return model, q, row

    todo = [(m, q) for m in models for q in key
            if not answers.get(m, {}).get(q, {}).get("ok")]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for model, q, row in pool.map(lambda a: one(*a), todo):
            answers.setdefault(model, {})[q] = row
    (BENCH / "answers.json").write_text(json.dumps(answers, indent=1), "utf-8")


def claude_job(model: str, q: str) -> str:
    """The same question for a Claude reader, who answers into a file."""
    out = BENCH / "claude" / model / f"{q}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    return (f"Read exactly one file with the Read tool: "
            f"{SANDBOX / f'bench-{q}.png'} . Read no other file, run no "
            f"command, search for nothing.\n\n{PROMPT}\n\nWrite your answer "
            f"(those four lines only) with the Write tool to {out} and then "
            f"reply with the single word: done")


def ingest() -> None:
    answers = _answers()
    for folder in sorted((BENCH / "claude").glob("*")):
        for path in sorted(folder.glob("b_*.txt")):
            row = parse(path.read_text("utf-8", errors="replace"))
            row["seconds"] = None
            answers.setdefault(f"claude-{folder.name}", {})[path.stem] = row
    (BENCH / "answers.json").write_text(json.dumps(answers, indent=1), "utf-8")


def score() -> dict:
    key = json.loads((BENCH / "key.json").read_text("utf-8"))
    answers = _answers()
    table = {}
    for model, rows in answers.items():
        good = {q: r for q, r in rows.items() if r.get("ok")}
        naming = [q for q in good if key[q]["kind"] == "naming"]
        faults = [q for q in good if key[q]["kind"] == "fault"]
        cleans = [q for q in good if key[q]["kind"] != "fault"]

        def has(q, field):
            said = good[q][field].lower()
            return any(word in said for word in key[q]["accept"])

        named = sum(has(q, "name") for q in naming)
        caught = sum(bool(good[q]["fault"]) for q in faults)
        right = sum(bool(good[q]["fault"]) and has(q, "what") for q in faults)
        alarms = sum(bool(good[q]["fault"]) for q in cleans)
        times = sorted(r["seconds"] for r in good.values() if r["seconds"])
        table[model] = {
            "answered": len(good), "of": len(key),
            "named": [named, len(naming)],
            "faults_caught": [caught, len(faults)],
            "faults_named": [right, len(faults)],
            "false_alarms": [alarms, len(cleans)],
            #: one number: the mean of the three rates that matter
            "score": round((named / max(1, len(naming))
                            + right / max(1, len(faults))
                            + 1 - alarms / max(1, len(cleans))) / 3, 3),
            "seconds_median": times[len(times) // 2] if times else None,
            "missed_faults": [key[q]["truth"] for q in faults
                              if not (good[q]["fault"] and has(q, "what"))],
            "misnamed": [f"{key[q]['truth']} -> {good[q]['name']}"
                         for q in naming if not has(q, "name")],
            "alarms_on": [f"{key[q]['truth']}: {good[q]['what']}"
                          for q in cleans if good[q]["fault"]]}
    (BENCH / "score.json").write_text(json.dumps(table, indent=1), "utf-8")
    return table


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    asking = sub.add_parser("ask")
    asking.add_argument("--model", action="append", required=True)
    asking.add_argument("--effort", default="low")
    asking.add_argument("--workers", type=int, default=10)
    jobs = sub.add_parser("claude-jobs")
    jobs.add_argument("--model", required=True)
    job = sub.add_parser("claude-job")
    job.add_argument("--model", required=True)
    job.add_argument("--q", required=True)
    sub.add_parser("score")
    args = parser.parse_args(argv)
    if args.command == "claude-job":
        print(claude_job(args.model, args.q))
        return 0
    if args.command == "build":
        print(build())
    elif args.command == "ask":
        ask(args.model, args.effort, args.workers)
    elif args.command == "claude-jobs":
        key = json.loads((BENCH / "key.json").read_text("utf-8"))
        print(json.dumps({q: claude_job(args.model, q) for q in key}))
    if args.command in ("ask", "score"):
        if args.command == "score":
            ingest()
        table = score()
        for model, row in sorted(table.items(),
                                 key=lambda kv: -kv[1]["score"]):
            print(f"{model:16s} score {row['score']:.3f}  named "
                  f"{row['named']}  faults caught {row['faults_caught']} "
                  f"named {row['faults_named']}  false alarms "
                  f"{row['false_alarms']}  answered {row['answered']}/"
                  f"{row['of']}  median {row['seconds_median']}s")
        for model, row in table.items():
            print(f"\n{model}")
            for label in ("misnamed", "missed_faults", "alarms_on"):
                for line in row[label]:
                    print(f"   {label}: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
