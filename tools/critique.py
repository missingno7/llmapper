"""Criticism as a process: three readers who cannot be kind by accident.

The owner, 2026-11-18, on the first Gravesend Station: "Your train station
looks like something where you need a lot of imagination and it is
partially ripoff of E1M2 without deeper context knowledge, try to make it
better, iterate on it -- also improve the process of criticism."

What was wrong with the process: the mapper rendered six frames of a
thing it had just built, recognised what it had meant, and wrote "reads
as one". One blind reviewer per build scored a mixed bag of places, long
after the building. Nothing asked the three questions that matter:

``recognition``  Shown frames with every sign, board and letter HIDDEN,
                 what does a stranger say this is, and how sure? A place
                 that is a station only because a wall says TICKETS
                 needs imagination. (The words are hidden by the
                 library: every tile it reads as a sign or a letter.)
``comparison``   Shown our frames beside Blood's own of the same kind,
                 unlabelled as to which is which: which is the better
                 place and why, what does the other have that this one
                 lacks, and where is one a thin copy of the other?
``use``          Given the brief and the plan, walk it as the person it
                 is for (a passenger: where do I buy a ticket, wait,
                 board, and where does the line go?). What is missing,
                 what is in the wrong place, what has no purpose?

``sense``        Does each thing point, face and sit the way it must
                 to WORK? Rails along the train, a door on the platform
                 side, a sign where its reader stands, a seat facing
                 something, a lamp over what it lights, wheels under the
                 vehicle. Added after two rounds of three readers passed
                 over rails laid ACROSS a train: nobody had been asked.

A round is a packet (`prepare`) and its reviews (`record`), kept under
the study. `verdict` reads them: a place PASSES a round only if the
recognition reader names its kind unprompted and no reader marks a
blocking defect. The mapper may not call a place done on its own frames.

.. code-block:: bash

    python -m tools.critique prepare station --poses railway --kind station
    python -m tools.critique record station --round 1 --reader recognition \\
        --named "warehouse loading dock" --sure 2 --score 2 \\
        --blocking "the train reads as a striped wall" --file review.md
    python -m tools.critique verdict station
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

STUDIES = ROOT / "knowledge" / "blood" / "studies"
READERS = ("recognition", "comparison", "use", "sense")
CITY = ROOT / "projects" / "blood-city" / "level" / "blood-city-current.MAP"


def mute_tiles() -> set[int]:
    """Every tile the library reads as words: signs, boards, letters."""
    from tools import catalog

    #: ... and any bill or poster the library tagged as carrying text
    #: (round 2's reader: "a poster with legible lettering is still in")
    return {tile for tile, row in catalog.tile_looks().items()
            if row.get("class") in ("sign", "letter")
            or "text" in row.get("tags", ())}


def prepare(slug: str, poses: list[str], kind: str) -> pathlib.Path:
    import look
    from bloodmap.format import read_map, write_map

    folder = STUDIES / slug / "critique"
    done = sorted(int(p.name.split("-")[1]) for p in folder.glob("round-*"))
    number = (done[-1] + 1) if done else 1
    packet = folder / f"round-{number}"
    for sub in ("ours", "ours_mute", "ours_empty", "reference"):
        (packet / sub).mkdir(parents=True, exist_ok=True)
    level = read_map(CITY).to_level_ir()
    views = []
    for name in poses:
        views += look.poses_for(level, name)
    quiet = mute_tiles()
    #: `ours_empty` is the place with nobody and nothing to pick up in it
    #: (the owner: "without enemies and pickups ... to get rid of visual
    #: noise"): what the comparison and sense readers should judge the
    #: BUILDING on. `ours_mute` is emptied too: a reader who must name the
    #: place from its shapes should not name it from a clerk.
    for sub, hide in (("ours", False), ("ours_mute", True),
                      ("ours_empty", False)):
        played = look.as_played(CITY, packet / sub,
                                empty=sub != "ours")
        if hide:
            disk = read_map(played)
            for sprite in disk.sprites:
                if int(sprite.fields["picnum"]) in quiet:
                    sprite.fields["cstat"] = int(sprite.fields["cstat"]) | 32768
            write_map(disk, played)
        look.run_observation(look.ObservationRequest(
            map_path=played, output_dir=packet / sub,
            resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
            width=640, height=480, screenshots=[v.view_id for v in views],
            brightness=0, rff=None))
        #: neutral names, so a pose's name tells a reader nothing
        frames = sorted((packet / sub / "frames").glob("*.png"))
        for index, frame in enumerate(frames):
            frame.rename(frame.with_name(f"view_{index + 1:02d}.png"))
    #: Blood's own, from the study's seeds
    count = 0
    for sheet in sorted((STUDIES / slug).glob("*/frames.png")):
        count += 1
        shutil.copyfile(sheet, packet / "reference" / f"ref_{count:02d}.png")
    (packet / "packet.json").write_text(json.dumps(
        {"slug": slug, "kind": kind, "round": number, "poses": poses,
         "views": len(views), "references": count,
         "readers": list(READERS)}, indent=1), "utf-8")
    return packet


def record(slug: str, number: int, reader: str, named: str, sure: int,
           score: int, blocking: list[str], text: str) -> None:
    if reader not in READERS:
        raise SystemExit(f"reader must be one of {READERS}")
    packet = STUDIES / slug / "critique" / f"round-{number}"
    (packet / f"review-{reader}.md").write_text(text, "utf-8")
    path = packet / "reviews.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    data[reader] = {"named": named, "sure": sure, "score": score,
                    "blocking": [b for b in blocking if b]}
    path.write_text(json.dumps(data, indent=1), "utf-8")


def verdict(slug: str) -> list[dict]:
    out = []
    for packet in sorted((STUDIES / slug / "critique").glob("round-*"),
                         key=lambda p: int(p.name.split("-")[1])):
        meta = json.loads((packet / "packet.json").read_text("utf-8"))
        path = packet / "reviews.json"
        reviews = json.loads(path.read_text("utf-8")) if path.exists() else {}
        #: a round owes the readers the process had when it was run
        owed = meta.get("readers", ["recognition", "comparison", "use"])
        missing = [r for r in owed if r not in reviews]
        recognised = (meta["kind"].lower() in
                      reviews.get("recognition", {}).get("named", "").lower())
        blocking = [f"{reader}: {b}" for reader, row in reviews.items()
                    for b in row["blocking"]]
        out.append({
            "round": meta["round"], "kind": meta["kind"],
            "reviews_missing": missing,
            "named": reviews.get("recognition", {}).get("named"),
            "recognised_without_words": recognised,
            "scores": {r: row["score"] for r, row in reviews.items()},
            "blocking": blocking,
            "passes": not missing and recognised and not blocking})
    return out


# ---------------------------------------------------------------------------
# things: one view, one thing, a reader told NOTHING
# ---------------------------------------------------------------------------
#: The owner, 2026-11-19: "Are you doing review the way that you show
#: certain thing without telling what it is and then compare description
#: with what it supposed to be?" Only for the place as a whole. So: one
#: view per THING, one cheap reader per view who sees nothing else, a key
#: of what each was built to be, and controls -- Blood's own things, whose
#: answers are known -- so that a reader's miss on ours can be weighed
#: against how often that reader misses Blood's. "Try to make cheap
#: efficient loop using cheaper models ... how reliable they are."
THING_PROMPT = """You are shown ONE screenshot (attached image) from a 1997 \
first-person shooter level. Do not run any commands or read any files. \
Look only at the attached image and answer in exactly this form, nothing else:
STATUS: done
NAME: <the main thing or place shown, at most 6 words>
SURE: <1-5>
WHY: <at most 20 words: what you see that makes you say so>
ODD: <at most 20 words: anything that looks wrong or unreadable, or "nothing">
"""
#: where the readers run: an empty folder OUTSIDE the repository, so no
#: reader can find the key, the level's source or another reader's answer
SANDBOX = ROOT.parent / (ROOT.name + "-critique-sandbox")


def prepare_things(slug: str) -> pathlib.Path:
    import random

    import look
    from bloodmap.format import read_map, write_map

    spec = json.loads((STUDIES / slug / "things.json").read_text("utf-8"))
    folder = STUDIES / slug / "critique"
    done = sorted(int(p.name.split("-")[1]) for p in folder.glob("things-*"))
    number = (done[-1] + 1) if done else 1
    packet = folder / f"things-{number}"
    (packet / "q").mkdir(parents=True, exist_ok=True)
    played = look.as_played(CITY, packet / "render", empty=True)
    disk = read_map(played)
    quiet = mute_tiles()
    for sprite in disk.sprites:
        if int(sprite.fields["picnum"]) in quiet:
            sprite.fields["cstat"] = int(sprite.fields["cstat"]) | 32768
    write_map(disk, played)
    views = look.poses_for(read_map(played).to_level_ir(), spec["poses"])
    look.run_observation(look.ObservationRequest(
        map_path=played, output_dir=packet / "render",
        resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
        width=640, height=480, screenshots=[v.view_id for v in views],
        brightness=0, rff=None))
    rows = []
    for view_id, row in spec["ours"].items():
        frame = packet / "render" / "frames" / f"{view_id}.png"
        if frame.exists():
            rows.append({"id": view_id, "ours": True, "file": str(frame),
                         **row})
    for row in spec["controls"]:
        rows.append({**row, "ours": False, "file": str(ROOT / row["file"])})
    random.Random(number).shuffle(rows)
    key = {}
    for index, row in enumerate(rows):
        name = f"q_{index + 1:02d}"
        shutil.copyfile(row["file"], packet / "q" / f"{name}.png")
        key[name] = {k: row[k] for k in ("id", "ours", "expect", "accept")}
    (packet / "key.json").write_text(json.dumps(key, indent=1), "utf-8")
    return packet


def _parse(text: str) -> dict:
    out = {"name": "", "sure": 0, "why": "", "odd": ""}
    for line in text.splitlines():
        head, _, rest = line.partition(":")
        head = head.strip().lower()
        if head in ("name", "why", "odd"):
            out[head] = rest.strip()
        elif head == "sure":
            digits = "".join(c for c in rest if c.isdigit())
            out["sure"] = int(digits[:1] or 0)
    return out


def ask_things(slug: str, number: int, models: list[str], effort: str,
               workers: int = 8, repeat: int = 1) -> dict:
    """Every (model, view) asked by its own worker, all in parallel.

    `repeat` asks each one that many times: a reader that names the same
    picture two ways is telling you how much one answer is worth.
    """
    import concurrent.futures
    import subprocess
    import time

    packet = STUDIES / slug / "critique" / f"things-{number}"
    key = json.loads((packet / "key.json").read_text("utf-8"))
    SANDBOX.mkdir(exist_ok=True)
    cx = pathlib.Path.home() / ".codex-dashboard" / "cx.py"
    path = packet / "answers.json"
    answers = json.loads(path.read_text("utf-8")) if path.exists() else {}

    def one(reader, model, q):
        image = SANDBOX / f"{slug}-{number}-{q}.png"
        if not image.exists():
            shutil.copyfile(packet / "q" / f"{q}.png", image)
        started = time.time()
        run = subprocess.run(
            [sys.executable, str(cx), "run", "-n", f"thing-{reader}-{q}",
             "-C", str(SANDBOX), "-m", model, "-e", effort, "-s", "read-only",
             "--", "-i", str(image)],
            input=THING_PROMPT, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        row = _parse(run.stdout)
        row["seconds"] = round(time.time() - started, 1)
        row["ok"] = run.returncode == 0 and bool(row["name"])
        if not row["ok"]:
            row["error"] = (run.stdout + run.stderr)[-300:]
        return reader, q, row

    readers = [(m if repeat == 1 else f"{m}#{k + 1}", m)
               for m in models for k in range(repeat)]
    todo = [(reader, model, q) for reader, model in readers for q in key
            if not answers.get(reader, {}).get(q, {}).get("ok")]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for reader, q, row in pool.map(lambda a: one(*a), todo):
            answers.setdefault(reader, {})[q] = row
    path.write_text(json.dumps(answers, indent=1), "utf-8")
    return answers


def score_things(slug: str, number: int) -> dict:
    packet = STUDIES / slug / "critique" / f"things-{number}"
    key = json.loads((packet / "key.json").read_text("utf-8"))
    answers = json.loads((packet / "answers.json").read_text("utf-8"))

    def hit(q, row):
        said = row.get("name", "").lower()
        return any(word in said for word in key[q]["accept"])

    models = {}
    for model, rows in answers.items():
        control = [q for q in rows if not key[q]["ours"] and rows[q]["ok"]]
        ours = [q for q in rows if key[q]["ours"] and rows[q]["ok"]]
        times = sorted(r["seconds"] for r in rows.values())
        models[model] = {
            "answered": sum(1 for r in rows.values() if r["ok"]),
            "failed": sum(1 for r in rows.values() if not r["ok"]),
            "controls_named": [sum(hit(q, rows[q]) for q in control),
                               len(control)],
            "ours_named": [sum(hit(q, rows[q]) for q in ours), len(ours)],
            "seconds_median": times[len(times) // 2] if times else 0}
    things = {}
    for q, row in key.items():
        said = {m: answers[m][q] for m in answers if q in answers[m]
                and answers[m][q]["ok"]}
        things[row["id"]] = {
            "q": q, "ours": row["ours"], "expect": row["expect"],
            "named": {m: r["name"] for m, r in said.items()},
            "sure": {m: r["sure"] for m, r in said.items()},
            "odd": {m: r["odd"] for m, r in said.items()},
            "hits": sum(hit(q, r) for r in said.values()),
            "asked": len(said)}
    report = {"models": models, "things": things}
    (packet / "score.json").write_text(json.dumps(report, indent=1), "utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("slug")
    prep.add_argument("--poses", action="append", required=True)
    prep.add_argument("--kind", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("slug")
    rec.add_argument("--round", type=int, required=True)
    rec.add_argument("--reader", required=True)
    rec.add_argument("--named", default="")
    rec.add_argument("--sure", type=int, default=0)
    rec.add_argument("--score", type=int, required=True)
    rec.add_argument("--blocking", action="append", default=[])
    rec.add_argument("--file", required=True)
    ver = sub.add_parser("verdict")
    ver.add_argument("slug")
    things = sub.add_parser("things", help="blind per-thing naming")
    things.add_argument("slug")
    things.add_argument("--round", type=int, default=0,
                        help="an existing things round; 0 prepares a new one")
    things.add_argument("--model", action="append", default=[])
    things.add_argument("--effort", default="low")
    things.add_argument("--workers", type=int, default=8)
    things.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args(argv)
    if args.command == "things":
        number = args.round
        if not number:
            packet = prepare_things(args.slug)
            number = int(packet.name.split("-")[1])
            print(packet)
        if args.model:
            ask_things(args.slug, number, args.model, args.effort,
                       args.workers, args.repeat)
            report = score_things(args.slug, number)
            for model, row in report["models"].items():
                print(f"{model}: controls {row['controls_named']}, ours "
                      f"{row['ours_named']}, failed {row['failed']}, "
                      f"median {row['seconds_median']}s")
            for name, row in sorted(report["things"].items(),
                                    key=lambda kv: (not kv[1]["ours"], kv[0])):
                mark = "ok   " if row["hits"] == row["asked"] else (
                    "MISS " if not row["hits"] else "SPLIT")
                print(f" {mark} {name:14s} meant: {row['expect']}")
                for model, said in row["named"].items():
                    print(f"        {model}: {said} (sure "
                          f"{row['sure'][model]}) odd: {row['odd'][model]}")
        return 0
    if args.command == "prepare":
        packet = prepare(args.slug, args.poses, args.kind)
        print(packet)
    elif args.command == "record":
        record(args.slug, args.round, args.reader, args.named, args.sure,
               args.score, args.blocking,
               pathlib.Path(args.file).read_text("utf-8"))
    else:
        for row in verdict(args.slug):
            print(f"round {row['round']}: "
                  f"{'PASSES' if row['passes'] else 'does not pass'}; "
                  f"named {row['named']!r} "
                  f"({'recognised' if row['recognised_without_words'] else 'NOT recognised'} "
                  f"without words); scores {row['scores']}; "
                  f"missing {row['reviews_missing']}")
            for line in row["blocking"]:
                print("   blocking -- " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
