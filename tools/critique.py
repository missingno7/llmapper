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

A round is a packet (`prepare`) and its reviews (`record`), kept by the
project whose place it judges (`projects/<name>/reports/critique/<slug>`);
Blood's own frames beside it come from the study of that slug, which every
level shares. `verdict` reads them: a place PASSES a round only if the
recognition reader names its kind unprompted and no reader marks a
blocking defect. The mapper may not call a place done on its own frames.

.. code-block:: bash

    python -m tools.critique --project blood-city prepare station --poses railway --kind station
    python -m tools.critique --project blood-city record station --round 1 --reader recognition \\
        --named "warehouse loading dock" --sure 2 --score 2 \\
        --blocking "the train reads as a striped wall" --file review.md
    python -m tools.critique --project blood-city verdict station

`--project` may be left out when `LLMAPPER_PROJECT` names it.

``change`` hands a mechanism's before/after pairs (`tools.mechanism_look`)
to readers who are told neither what the mechanism is nor which frame is
which, and scores whether they can say what changed and which came after:

.. code-block:: bash

    python -m tools.critique change work/mech/e1m5-s84/pair.json --model <model>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import project as P

STUDIES = ROOT / "knowledge" / "blood" / "studies"
READERS = ("recognition", "comparison", "use", "sense")


def mute_tiles() -> set[int]:
    """Every tile the library reads as words: signs, boards, letters (`bloodmap.tile_looks.word_tiles`)."""
    from bloodmap.tile_looks import word_tiles

    return set(word_tiles())


def prepare(project: P.Project, slug: str, poses: list[str], kind: str, study: str | None = None) -> pathlib.Path:
    """A new round of one place: our frames three ways, Blood's own beside them, and what they are frames OF.

    `study` names the shelf study whose seeds are Blood's frames (`knowledge/blood/studies/<study>`),
    when the place's slug is not the study's. The packet records the map's SHA-256, the poses' and
    every frame's: a reader's answer is about those bytes, and a later save makes it historical.
    """
    from bloodmap.format import read_map
    from tools.look import digest, observe, pose_hash, poses_for

    folder = project.rounds(slug)
    done = sorted(int(p.name.split("-")[1]) for p in folder.glob("round-*"))
    number = (done[-1] + 1) if done else 1
    packet = folder / f"round-{number}"
    (packet / "reference").mkdir(parents=True, exist_ok=True)
    source = digest(project.map)
    level = read_map(project.map).to_level_ir()
    views = []
    for name in poses:
        views += poses_for(project, level, name)
    about = {"project": project.key, "pose_sets": poses, "poses_sha256": pose_hash(project, poses)}
    #: `ours_empty` is the place with nobody and nothing to pick up in it
    #: (the owner: "without enemies and pickups ... to get rid of visual
    #: noise"): what the comparison and sense readers should judge the
    #: BUILDING on. `ours_mute` is emptied too, and every word in it hidden
    #: (sprites and walls): a reader who must name the place from its shapes
    #: should not name it from a clerk or a sign.
    frames = {}
    for sub, empty, mute in (("ours", False, False), ("ours_mute", True, True), ("ours_empty", True, False)):
        observe(project.map, views, packet / sub, empty=empty, mute=mute, about=about)
        #: neutral names, so a pose's name tells a reader nothing
        for index, frame in enumerate(sorted((packet / sub / "frames").glob("*.png"))):
            named = frame.with_name(f"view_{index + 1:02d}.png")
            frame.rename(named)
            frames[named.relative_to(packet).as_posix()] = digest(named)
    #: Blood's own, from the study's seeds
    count = 0
    for sheet in sorted((STUDIES / (study or slug)).glob("*/frames.png")):
        count += 1
        shutil.copyfile(sheet, packet / "reference" / f"ref_{count:02d}.png")
    if digest(project.map) != source:
        raise RuntimeError(f"{project.map} was saved while the packet was made: prepare it again")
    (packet / "packet.json").write_text(json.dumps(
        {"project": project.key, "slug": slug, "kind": kind, "round": number, "poses": poses,
         "views": len(views), "references": count, "study": study or slug,
         "readers": list(READERS), "map": project.map.relative_to(ROOT).as_posix(), "source_sha256": source,
         "poses_sha256": about["poses_sha256"], "frames": frames}, indent=1), "utf-8")
    return packet


def record(project: P.Project, slug: str, number: int, reader: str, named: str, sure: int,
           score: int, blocking: list[str], text: str) -> None:
    if reader not in READERS:
        raise SystemExit(f"reader must be one of {READERS}")
    packet = project.rounds(slug) / f"round-{number}"
    (packet / f"review-{reader}.md").write_text(text, "utf-8")
    path = packet / "reviews.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    data[reader] = {"named": named, "sure": sure, "score": score,
                    "blocking": [b for b in blocking if b]}
    path.write_text(json.dumps(data, indent=1), "utf-8")


def verdict(project: P.Project, slug: str) -> list[dict]:
    """Every round a project has had of one place, oldest first, and whether each passes."""
    out = []
    for packet in sorted(project.rounds(slug).glob("round-*"),
                         key=lambda p: int(p.name.split("-")[1])):
        meta = json.loads((packet / "packet.json").read_text("utf-8"))
        path = packet / "reviews.json"
        reviews = json.loads(path.read_text("utf-8")) if path.exists() else {}
        #: a round owes the readers the process had when it was run
        owed = meta.get("readers", ["recognition", "comparison", "use"])
        missing = [r for r in owed if r not in reviews]
        # an American reader's "theater" names a theatre
        plain = lambda text: text.lower().replace("theater", "theatre")  # noqa: E731
        recognised = plain(meta["kind"]) in plain(reviews.get("recognition", {}).get("named", ""))
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


def prepare_things(project: P.Project, slug: str) -> pathlib.Path:
    import random

    from bloodmap import visual as look
    from bloodmap.format import read_map
    from tools.look import hide_words, poses_for

    folder = project.rounds(slug)
    spec = json.loads((folder / "things.json").read_text("utf-8"))
    done = sorted(int(p.name.split("-")[1]) for p in folder.glob("things-*"))
    number = (done[-1] + 1) if done else 1
    packet = folder / f"things-{number}"
    (packet / "q").mkdir(parents=True, exist_ok=True)
    played = look.as_played(project.map, packet / "render", empty=True)
    hide_words(played)
    views = poses_for(project, read_map(played).to_level_ir(), spec["poses"])
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


def ask_things(project: P.Project, slug: str, number: int, models: list[str], effort: str,
               workers: int = 8, repeat: int = 1) -> dict:
    """Every (model, view) asked by its own worker, all in parallel.

    `repeat` asks each one that many times: a reader that names the same
    picture two ways is telling you how much one answer is worth.
    """
    import concurrent.futures
    import subprocess
    import time

    packet = project.rounds(slug) / f"things-{number}"
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


def score_things(project: P.Project, slug: str, number: int) -> dict:
    packet = project.rounds(slug) / f"things-{number}"
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


# ---------------------------------------------------------------------------
# change: two frames of one place, before and after, a reader told NOTHING
# ---------------------------------------------------------------------------
#: The owner wants the critic to "tell that it works the intended way".
#: `tools.mechanism_look` renders a mechanism's rest and fired poses from
#: one camera; this hands each pair to a reader in random order, never
#: saying what the mechanism is or which frame is which, and scores whether
#: the reader can tell what changed and which came after. A pair whose
#: frames are identical is kept as a control: the right answer is "nothing".
CHANGE_PROMPT = """You are shown TWO screenshots (attached images, first A then B) \
from a 1997 first-person shooter level, taken from the same spot. They show \
the same place before and after something happened. Do not run any commands \
or read any files. Look only at the two images and answer in exactly this \
form, nothing else:
STATUS: done
CHANGED: <what is different between A and B, at most 20 words, or "nothing">
AFTER: <A or B: which one shows the place after it happened, or "cannot tell">
SURE: <1-5>
WHY: <at most 20 words: what in the pictures makes you say so>
"""


def prepare_change(pair_json: pathlib.Path) -> pathlib.Path:
    """A packet of before/after questions from one `mechanism_look` pair.json."""
    import random

    pair = json.loads(pathlib.Path(pair_json).read_text("utf-8"))
    folder = pathlib.Path(pair_json).parent
    done = sorted(int(p.name.split("-")[1]) for p in folder.glob("change-*"))
    number = (done[-1] + 1) if done else 1
    packet = folder / f"change-{number}"
    (packet / "q").mkdir(parents=True, exist_ok=True)
    shuffle = random.Random(f"{pair['map']}|{pair['root']}|{number}")
    key = {}
    rows = [row for row in pair["pairs"] if "rest" in row]
    shuffle.shuffle(rows)
    for index, row in enumerate(rows):
        name = f"q_{index + 1:02d}"
        after = shuffle.choice("AB")
        first, second = ((row["rest"], row["posed"]) if after == "B"
                         else (row["posed"], row["rest"]))
        shutil.copyfile(first, packet / "q" / f"{name}_A.png")
        shutil.copyfile(second, packet / "q" / f"{name}_B.png")
        key[name] = {"pose": row["pose"]["id"], "after": after,
                     "differ": row["differ"], "finding": row["finding"]}
    (packet / "key.json").write_text(json.dumps(
        {"pair": str(pair_json), "map": pair["map"], "root": pair["root"],
         "questions": key}, indent=1), "utf-8")
    return packet


def _parse_change(text: str) -> dict:
    out = {"changed": "", "after": "", "sure": 0, "why": ""}
    for line in text.splitlines():
        head, _, rest = line.partition(":")
        head = head.strip().lower()
        if head in ("changed", "why"):
            out[head] = rest.strip()
        elif head == "after":
            said = rest.strip().upper()
            out["after"] = said[:1] if said[:1] in ("A", "B") else "?"
        elif head == "sure":
            digits = "".join(c for c in rest if c.isdigit())
            out["sure"] = int(digits[:1] or 0)
    return out


def ask_change(packet: pathlib.Path, models: list[str], effort: str,
               workers: int = 8) -> dict:
    """Every (model, question) asked by its own worker, in the sandbox."""
    import concurrent.futures
    import subprocess

    key = json.loads((packet / "key.json").read_text("utf-8"))["questions"]
    SANDBOX.mkdir(exist_ok=True)
    cx = pathlib.Path.home() / ".codex-dashboard" / "cx.py"
    tag = f"{packet.parent.name}-{packet.name}"

    def one(model, q):
        images = []
        for side in ("A", "B"):
            image = SANDBOX / f"{tag}-{q}_{side}.png"
            shutil.copyfile(packet / "q" / f"{q}_{side}.png", image)
            images += ["-i", str(image)]
        run = subprocess.run(
            [sys.executable, str(cx), "run", "-n", f"change-{q}", "-C", str(SANDBOX),
             "-m", model, "-e", effort, "-s", "read-only", "--", *images],
            input=CHANGE_PROMPT, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        row = _parse_change(run.stdout)
        row["ok"] = run.returncode == 0 and bool(row["changed"])
        if not row["ok"]:
            row["error"] = (run.stdout + run.stderr)[-300:]
        return model, q, row

    path = packet / "answers.json"
    answers = json.loads(path.read_text("utf-8")) if path.exists() else {}
    todo = [(m, q) for m in models for q in key
            if not answers.get(m, {}).get(q, {}).get("ok")]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for model, q, row in pool.map(lambda a: one(*a), todo):
            answers.setdefault(model, {})[q] = row
    path.write_text(json.dumps(answers, indent=1), "utf-8")
    scored = {}
    for model, rows in answers.items():
        moved = [q for q in rows if rows[q]["ok"] and key[q]["differ"]]
        still = [q for q in rows if rows[q]["ok"] and not key[q]["differ"]]
        scored[model] = {
            "after_right": [sum(rows[q]["after"] == key[q]["after"] for q in moved),
                            len(moved)],
            "said_nothing_when_nothing": [
                sum("nothing" in rows[q]["changed"].lower() for q in still), len(still)],
            "answers": {q: {**rows[q], "truth": key[q]} for q in rows}}
    (packet / "score.json").write_text(json.dumps(scored, indent=1), "utf-8")
    return scored


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", default=None, help=f"whose place is judged: a directory under projects/ (or ${P.ENV})")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("slug")
    prep.add_argument("--poses", action="append", required=True)
    prep.add_argument("--kind", required=True)
    prep.add_argument("--study", default=None, help="the shelf study Blood's frames come from, when it is not the slug")
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
    change = sub.add_parser("change", help="blind before/after of a mechanism_look pair")
    change.add_argument("pair", help="a pair.json written by tools.mechanism_look")
    change.add_argument("--round", type=int, default=0,
                        help="an existing change round; 0 prepares a new one")
    change.add_argument("--model", action="append", default=[])
    change.add_argument("--effort", default="low")
    change.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    if args.command == "change":
        folder = pathlib.Path(args.pair).parent
        packet = (folder / f"change-{args.round}" if args.round
                  else prepare_change(pathlib.Path(args.pair)))
        print(packet)
        for model, row in (ask_change(packet, args.model, args.effort, args.workers)
                           if args.model else {}).items():
            print(f"{model}: after named right {row['after_right']}, "
                  f"'nothing' on identical pairs {row['said_nothing_when_nothing']}")
            for q, said in sorted(row["answers"].items()):
                print(f"   {q} ({said['truth']['pose']}, after={said['truth']['after']}): "
                      f"said after={said['after']} sure {said['sure']}: {said['changed']}")
        return 0
    try:
        project = P.named(args.project)
    except P.ProjectError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.command == "things":
        number = args.round
        if not number:
            packet = prepare_things(project, args.slug)
            number = int(packet.name.split("-")[1])
            print(packet)
        if args.model:
            ask_things(project, args.slug, number, args.model, args.effort,
                       args.workers, args.repeat)
            report = score_things(project, args.slug, number)
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
        packet = prepare(project, args.slug, args.poses, args.kind, args.study)
        print(packet)
    elif args.command == "record":
        record(project, args.slug, args.round, args.reader, args.named, args.sure,
               args.score, args.blocking,
               pathlib.Path(args.file).read_text("utf-8"))
    else:
        for row in verdict(project, args.slug):
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
