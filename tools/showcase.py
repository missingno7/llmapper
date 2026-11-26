"""A competition of views for each named place: measured heats, blind finals, and what each place lacks.

The owner, 2026-11-20, after the first GRAVESEND collage: "do multiple views
from different places and rank them ... like an internal competition, to
really choose the best pictures across the town. Some of them are good and
some of them are not really showing stuff. Take it as an opportunity to
improve critics of the actual map."

So a place's picture is not chosen by the mapper who built it:

``run``      Hundreds of cameras per place (the project's
             `level/showcase-places.json`): a grid
             of standing points thinned to the most spread out, eight
             compass headings and one toward the place, at eye height and
             raised one and three bodies looking down. Every view is
             rendered without a picture and measured
             (`bloodmap.view_score`); the best eight that are not the same
             shot twice are the finalists, rendered as played and again
             emptied with every sign hidden.
``judge``    One blind reader per place gets the eight finalists on one
             sheet, lettered, and is told nothing of what the place is. It
             names the place, ranks the eight, says what spoils each, and
             -- the part that is for the map, not the poster -- what the
             place lacks that keeps even its best picture from being good,
             and the one change to the place that would help. A second
             blind reader names the winner with its signs hidden: a place
             that is not recognised from its best view is not recognised.
``report``   `showcase.md` (the critique, per place) and the collage of
             winners. How often the reader's choice was the measure's own
             first is printed, because that is how the measure earns its
             weights.

.. code-block:: bash

    python -m tools.showcase --project blood-city run     # a new round, every place
    python -m tools.showcase --project blood-city run --place crypt --round 3
    python -m tools.showcase --project blood-city judge --round 3      # GPT-6.2 Sol, high
    python -m tools.showcase --project blood-city report --round 3
    python -m tools.showcase --project blood-city calibrate   # does the measure follow the readers?

`--project` may be left out when `LLMAPPER_PROJECT` names it. A place is a
row of the project's `level/showcase-places.json`: `{"places": {key:
{"focus": [x, y], "radius": r, "camera_radius": R, "floor": z?, "outdoors":
bool?}}}` in the project's plan units.

A project's status may read each place's latest verdict (Gravesend's
`status.py` does: a place not recognised from its best view is an open item).

Rounds live in the project's `reports/showcase/round-N/`: the JSON and the
markdown are committed; the round's MAP and collage stay local and its frames
are in `work/showcase/<project>/` (every camera is in `finalists.json`, so a
frame can be rendered again from the same build).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import pathlib
import random
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import project as P
from bloodmap.format import read_map, write_map
from bloodmap.sector_geom import outline_and_holes, sector_contains
from bloodmap.view_score import Subject, measure_view, score
from bloodmap.viewplan import angle_toward, eye_z
from bloodmap.visual import ObservationRequest, Viewpoint, as_played, run_observation

#: the project a run is of, set by `use`: its plan unit, map, places, rounds, scratch and ground floor
PU = 1024
CITY = PLACES = OUT = WORK = None
STREET, BAND = 0, 12288


def use(project: P.Project) -> None:
    """Point every path and unit here at one project."""
    global PU, CITY, PLACES, OUT, WORK, STREET
    PU, STREET = project.plan_unit, project.ground_z
    CITY, PLACES, OUT = project.map, project.need("showcase_places"), project.need("showcase")
    WORK = ROOT / "work" / "showcase" / project.key

#: how far apart standing points are, and how many survive the thinning
GRID, POSITIONS, FINALISTS = 768, 20, 8
#: (lift above eye, horiz): Build's horiz 100 is level, lower looks down
HEIGHTS = ((0, 100), (16960, 84), (16960, 66), (50880, 70), (50880, 52))
MODEL, EFFORT = "gpt-6.2-sol", "high"
LETTERS = "ABCDEFGH"


def load_places(only: list[str] | None = None) -> dict[str, dict]:
    places = json.loads(PLACES.read_text("utf-8"))["places"]
    return {k: v for k, v in places.items() if not only or k in only}


def _bboxes(level) -> dict[int, tuple[int, int, int, int]]:
    out = {}
    for s in range(len(level.sectors)):
        outer, _ = outline_and_holes(level, s)
        if outer:
            xs = [p[0] for p in outer]
            ys = [p[1] for p in outer]
            out[s] = (min(xs), min(ys), max(xs), max(ys))
    return out


def standing_points(level, place: dict, boxes) -> list[tuple[int, int, int]]:
    """Grid points within the camera radius, each in a sector on the place's floor."""
    fx, fy = place["focus"][0] * PU, place["focus"][1] * PU
    reach = place["camera_radius"] * PU
    floor = place.get("floor", STREET)
    band = place.get("band", BAND)
    #: an outside place is seen from under the sky: a church's portrait
    #: is not taken from its nave
    outdoors = place.get("outdoors", False)
    points = []
    steps = int(reach // GRID)
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            x, y = int(fx + i * GRID), int(fy + j * GRID)
            if (x - fx) ** 2 + (y - fy) ** 2 > reach * reach:
                continue
            best = None
            for s, (x0, y0, x1, y1) in boxes.items():
                if not (x0 < x < x1 and y0 < y < y1):
                    continue
                z = int(level.sectors[s]["fields"]["floor_z"])
                if outdoors and not int(level.sectors[s]["fields"]["ceiling_stat"]) & 1:
                    continue
                if abs(z - floor) > band or not sector_contains(level, s, x, y):
                    continue
                if best is None or abs(z - floor) < best[1]:
                    best = (s, abs(z - floor))
            if best is not None:
                points.append((x, y, best[0]))
    return points


def spread(points, n: int, focus) -> list[tuple[int, int, int]]:
    """Farthest-point thinning, starting nearest the focus."""
    if len(points) <= n:
        return list(points)
    chosen = [min(points, key=lambda p: (p[0] - focus[0]) ** 2 + (p[1] - focus[1]) ** 2)]
    dist = {p: (p[0] - chosen[0][0]) ** 2 + (p[1] - chosen[0][1]) ** 2 for p in points}
    while len(chosen) < n:
        nxt = max(dist, key=dist.get)
        chosen.append(nxt)
        for p in dist:
            dist[p] = min(dist[p], (p[0] - nxt[0]) ** 2 + (p[1] - nxt[1]) ** 2)
    return chosen


def candidates(level, key: str, place: dict, boxes) -> list[Viewpoint]:
    focus = (int(place["focus"][0] * PU), int(place["focus"][1] * PU))
    views = []
    for n, (x, y, s) in enumerate(spread(standing_points(level, place, boxes),
                                         POSITIONS, focus)):
        eye = eye_z(level, s)
        if eye is None:
            continue
        ceiling = int(level.sectors[s]["fields"]["ceiling_z"])
        headings = [a * 256 for a in range(8)]
        if (x - focus[0]) ** 2 + (y - focus[1]) ** 2 > PU * PU:
            toward = int(angle_toward((x, y), focus)) & 2047
            if toward not in headings:
                headings.append(toward)
        for lift, horiz in HEIGHTS:
            z = eye - lift
            if z < ceiling + 2048:
                continue
            for angle in headings:
                vid = f"{key}-{n:02d}-{angle:04d}-{lift}-{horiz}"
                views.append(Viewpoint(
                    view_id=vid, x=x, y=y, z=z, angle=angle, horiz=horiz,
                    sector=s, node=f"showcase:{key}", purpose="showcase",
                    screenshot=False, note=key))
    return views


def _distinct(chosen: list[dict], row: dict) -> bool:
    for c in chosen:
        near = math.dist(c["pose"][:2], row["pose"][:2]) < 1.5 * PU
        turn = abs((c["pose"][3] - row["pose"][3] + 1024) % 2048 - 1024)
        if near and turn < 342 and abs(c["pose"][2] - row["pose"][2]) < 20000:
            return False
    return True


def _render(map_path, out_dir, views, shots: bool):
    import dataclasses

    out_dir.mkdir(parents=True, exist_ok=True)
    views = [dataclasses.replace(v, screenshot=shots) for v in views]
    return run_observation(ObservationRequest(
        map_path=map_path, output_dir=out_dir,
        resource_dir=ROOT / "reference" / "blood", viewpoints=views,
        width=640, height=480,
        screenshots=[v.view_id for v in views] if shots else [],
        brightness=0, rff=None))


def _next_round() -> int:
    done = sorted(int(p.name.split("-")[1]) for p in OUT.glob("round-*"))
    return (done[-1] + 1) if done else 1


def run(number: int | None, only: list[str] | None) -> pathlib.Path:
    from tools.critique import mute_tiles

    number = number or _next_round()
    folder = OUT / f"round-{number}"
    work = WORK / f"round-{number}"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CITY, folder / "observed.MAP")
    played = as_played(folder / "observed.MAP", work, empty=False)
    level = read_map(played).to_level_ir()
    # the naming reader's copy: nobody in it, and no word on any wall
    muted = as_played(folder / "observed.MAP", work / "muted", empty=True)
    disk = read_map(muted)
    quiet = mute_tiles()
    for sprite in disk.sprites:
        if int(sprite.fields["picnum"]) in quiet:
            sprite.fields["cstat"] = int(sprite.fields["cstat"]) | 32768
    write_map(disk, muted)

    boxes = _bboxes(level)
    path = folder / "finalists.json"
    table = json.loads(path.read_text("utf-8")) if path.exists() else {}
    for key, place in load_places(only).items():
        started = time.time()
        views = candidates(level, key, place, boxes)
        if not views:
            print(f"{key}: no standing point")
            continue
        manifest = _render(played, work / "heats" / key, views, shots=False)
        floor = place.get("floor", STREET)
        band = place.get("band", BAND)
        subject = Subject(level, (int(place["focus"][0] * PU), int(place["focus"][1] * PU)),
                          int(place["radius"] * PU), (floor - band, floor + band))
        by_id = {v.view_id: v for v in views}
        rows = []
        for view in manifest.views:
            if view.get("status") != "ok":
                continue
            m = measure_view(view, subject)
            v = by_id[view["id"]]
            rows.append({"id": v.view_id, "pose": [v.x, v.y, v.z, v.angle, v.horiz, v.sector],
                         "measure": m, "score": score(m)})
        rows.sort(key=lambda r: -r["score"])
        finals: list[dict] = []
        for row in rows:
            if _distinct(finals, row):
                finals.append(row)
            if len(finals) == FINALISTS:
                break
        # letters are dealt at random, so a reader that favours A favours
        # nothing the measure did
        letters = list(LETTERS[:len(finals)])
        random.Random(f"{number}-{key}").shuffle(letters)
        for index, row in enumerate(finals):
            row["letter"] = letters[index]
            row["measured_rank"] = index + 1
        finals.sort(key=lambda r: r["letter"])
        picked = [by_id[r["id"]] for r in finals]
        _render(played, work / "finals" / key, picked, shots=True)
        _render(muted, work / "muted-finals" / key, picked, shots=True)
        table[key] = {"title": place["title"], "candidates": len(views),
                      "rendered": len(rows), "finalists": finals}
        path.write_text(json.dumps(table, indent=1), "utf-8")
        print(f"{key}: {len(views)} views, best {finals[0]['score'] if finals else 0}"
              f" ({time.time() - started:.0f}s)")
    return folder


def _frame(number: int, key: str, view_id: str, muted: bool = False) -> pathlib.Path:
    kind = "muted-finals" if muted else "finals"
    return WORK / f"round-{number}" / kind / key / "frames" / f"{view_id}.png"


def sheet(number: int, key: str, finals: list[dict]) -> pathlib.Path:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 480, 360
    canvas = Image.new("RGB", (4 * W, 2 * H), "black")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arialbd.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    for i, row in enumerate(finals):
        im = Image.open(_frame(number, key, row["id"])).convert("RGB").resize((W, H))
        x, y = (i % 4) * W, (i // 4) * H
        canvas.paste(im, (x, y))
        draw.rectangle((x, y, x + 46, y + 46), fill=(255, 220, 0))
        draw.text((x + 23, y + 23), row["letter"], font=font, fill="black", anchor="mm")
    out = WORK / f"round-{number}" / "sheets" / f"{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


RANK_PROMPT = """You are shown ONE image: a sheet of eight screenshots, lettered \
A to H, from a 1997 first-person shooter level (Build engine: low resolution, \
flat sprites, dark). All eight were taken in or of the same place, from \
different spots, heights and angles. Do not run any commands or read any \
files. Look only at the attached image.

You are choosing the one picture for a poster of this level: the one that \
shows this place best -- what it is, its character, its things -- not the \
prettiest wall. Then, as a critic of the LEVEL, say what the place itself \
lacks.

Answer in exactly this form, nothing else:
STATUS: done
PLACE: <what this place is, at most 6 words>
RANK: <all eight letters, best first, separated by spaces>
BEST: <at most 20 words: why that picture shows the place best>
A: <at most 15 words: what it shows, and what spoils it>
B: <...>
C: <...>
D: <...>
E: <...>
F: <...>
G: <...>
H: <...>
LACKS: <at most 30 words: what the place lacks that keeps even the best picture from being good>
FIX: <at most 30 words: the one change to the PLACE (not the camera) that would most improve it>
"""


def _ask(prompt: str, image: pathlib.Path, name: str) -> str:
    from tools.critique import SANDBOX

    SANDBOX.mkdir(exist_ok=True)
    local = SANDBOX / image.name
    shutil.copyfile(image, local)
    cx = pathlib.Path.home() / ".codex-dashboard" / "cx.py"
    run_ = subprocess.run(
        [sys.executable, str(cx), "run", "-n", name, "-C", str(SANDBOX), "-m", MODEL,
         "-e", EFFORT, "-s", "read-only", "--", "-i", str(local)],
        input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return run_.stdout if run_.returncode == 0 else ""


def _parse_rank(text: str) -> dict:
    out: dict = {"notes": {}}
    for line in text.splitlines():
        head, _, rest = line.partition(":")
        head, rest = head.strip(), rest.strip()
        if head.upper() in ("PLACE", "BEST", "LACKS", "FIX"):
            out[head.lower()] = rest
        elif head.upper() == "RANK":
            out["rank"] = [c for c in rest.upper() if c in LETTERS]
        elif len(head) == 1 and head.upper() in LETTERS:
            out["notes"][head.upper()] = rest
    return out


def judge(number: int, only: list[str] | None, workers: int = 6) -> dict:
    from tools.critique import THING_PROMPT, _parse

    folder = OUT / f"round-{number}"
    table = json.loads((folder / "finalists.json").read_text("utf-8"))
    path = folder / "verdicts.json"
    verdicts = json.loads(path.read_text("utf-8")) if path.exists() else {}
    keys = [k for k in table if (not only or k in only) and table[k]["finalists"]]

    def one(key):
        finals = table[key]["finalists"]
        img = sheet(number, key, finals)
        text = _ask(RANK_PROMPT, img, f"showcase-{number}-{key}")
        row = _parse_rank(text)
        row["ok"] = bool(row.get("rank"))
        if not row["ok"]:
            row["raw"] = text[-400:]
            return key, row
        best = next(r for r in finals if r["letter"] == row["rank"][0])
        muted = _frame(number, key, best["id"], muted=True)
        named = _parse(_ask(THING_PROMPT, muted, f"showcase-{number}-{key}-name"))
        accept = load_places([key])[key]["accept"]
        named["recognised"] = any(w in named.get("name", "").lower() for w in accept)
        row["blind_name"] = named
        row["winner"] = best["id"]
        return key, row

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for key, row in pool.map(one, keys):
            verdicts[key] = row
            print(f"{key}: {row.get('rank')} {row.get('place', '')!r}"
                  f" named {row.get('blind_name', {}).get('name', '')!r}")
    path.write_text(json.dumps(verdicts, indent=1), "utf-8")
    return verdicts


def _spearman(a: list[str], b: list[str]) -> float | None:
    common = [x for x in a if x in b]
    n = len(common)
    if n < 3:
        return None
    ra = {x: i for i, x in enumerate([x for x in a if x in common])}
    rb = {x: i for i, x in enumerate([x for x in b if x in common])}
    d2 = sum((ra[x] - rb[x]) ** 2 for x in common)
    return round(1 - 6 * d2 / (n * (n * n - 1)), 2)


def report(number: int) -> pathlib.Path:
    from PIL import Image, ImageDraw, ImageFont

    folder = OUT / f"round-{number}"
    table = json.loads((folder / "finalists.json").read_text("utf-8"))
    verdicts = json.loads((folder / "verdicts.json").read_text("utf-8"))
    lines = [f"# Showcase, round {number}", "",
             "Generated by `python -m tools.showcase report`. Each place's views were "
             "measured (`bloodmap.view_score`), its eight best distinct views were "
             f"ranked blind by {MODEL} ({EFFORT}), and the winner was named again with "
             "every sign and person hidden. LACKS and FIX are the reader's, about the "
             "place, not the camera: they are the round's critique of the map.", ""]
    agree, firsts, named = [], 0, 0
    rows = []
    for key, entry in table.items():
        v = verdicts.get(key)
        if not v or not v.get("ok"):
            continue
        measured = [r["letter"] for r in
                    sorted(entry["finalists"], key=lambda r: r["measured_rank"])]
        rho = _spearman(v["rank"], measured)
        if rho is not None:
            agree.append(rho)
        firsts += v["rank"][0] == measured[0]
        bn = v.get("blind_name", {})
        named += bool(bn.get("recognised"))
        rows.append((key, entry, v, rho, bn))
    lines += [f"- places judged: {len(rows)}",
              f"- recognised from their best view with signs hidden: {named} of {len(rows)}",
              f"- reader's first = measure's first: {firsts} of {len(rows)}; "
              f"mean rank agreement (Spearman) {sum(agree) / len(agree):.2f}" if agree else "", "",
              "| place | reader calls it | blind name of the winner | recognised | winner (measured rank) |",
              "| --- | --- | --- | --- | --- |"]
    for key, entry, v, rho, bn in rows:
        win = next(r for r in entry["finalists"] if r["letter"] == v["rank"][0])
        lines.append(f"| {entry['title']} | {v.get('place', '')} | {bn.get('name', '')} "
                     f"| {'yes' if bn.get('recognised') else '**no**'} | {win['letter']} "
                     f"({win['measured_rank']}) |")
    lines.append("")
    for key, entry, v, rho, bn in rows:
        win = next(r for r in entry["finalists"] if r["letter"] == v["rank"][0])
        x, y, z, a, h, s = win["pose"]
        lines += [f"## {entry['title']} (`{key}`)", "",
                  f"- **lacks:** {v.get('lacks', '')}",
                  f"- **fix:** {v.get('fix', '')}",
                  f"- best view {win['letter']}: {v.get('best', '')} -- camera x {x} y {y} "
                  f"z {z} angle {a} horiz {h} (sector {s})",
                  f"- blind, signs hidden: \"{bn.get('name', '')}\" (sure {bn.get('sure', 0)}); "
                  f"odd: {bn.get('odd', '')}",
                  f"- rank {' '.join(v['rank'])}, measured A-H; agreement {rho}", ""]
        for letter in v["rank"]:
            lines.append(f"  - {letter}: {v['notes'].get(letter, '')}")
        lines.append("")
    md = folder / "showcase.md"
    md.write_text("\n".join(lines) + "\n", "utf-8")

    W, H, COLS, GAP, TOP = 640, 480, 5, 8, 120
    n = len(rows)
    rows_n = (n + COLS - 1) // COLS
    canvas = Image.new("RGB", (COLS * W + (COLS + 1) * GAP, TOP + rows_n * (H + GAP) + GAP),
                       (12, 4, 4))
    draw = ImageDraw.Draw(canvas)

    def font(size):
        for name in ("impact.ttf", "arialbd.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default()

    draw.text((canvas.width // 2, TOP // 2 + 4), "G R A V E S E N D", font=font(84),
              fill=(200, 24, 16), anchor="mm")
    cap = font(26)
    for i, (key, entry, v, rho, bn) in enumerate(rows):
        im = Image.open(_frame(number, key, v["winner"])).convert("RGB")
        x = GAP + (i % COLS) * (W + GAP)
        y = TOP + (i // COLS) * (H + GAP)
        canvas.paste(im, (x, y))
        band = Image.new("RGBA", (W, 40), (0, 0, 0, 170))
        canvas.paste(band, (x, y + H - 40), band)
        draw.text((x + 12, y + H - 20), entry["title"], font=cap, fill=(235, 220, 200), anchor="lm")
    canvas.save(folder / "collage.png")
    print(md, folder / "collage.png")
    return md


def calibrate() -> dict:
    """How well each measured number, and the score, follow the readers.

    Over every judged round: the mean rank correlation, within each set of
    eight finalists, between a number and the reader's order, and how often
    the score's own first pick was the reader's. Run it after new rounds,
    before trusting or changing `bloodmap.view_score.score`.
    """
    keys = ("subject", "things", "variety", "sectors", "dominant", "sky", "unwritten")
    acc: dict[str, list[float]] = {k: [] for k in keys + ("score",)}
    firsts = n = 0
    for folder in sorted(OUT.glob("round-*")):
        if not (folder / "verdicts.json").exists():
            continue
        table = json.loads((folder / "finalists.json").read_text("utf-8"))
        verdicts = json.loads((folder / "verdicts.json").read_text("utf-8"))
        for key, entry in table.items():
            v = verdicts.get(key)
            if not v or not v.get("ok") or len(v.get("rank", [])) < len(entry["finalists"]):
                continue
            order = [r["letter"] for r in entry["finalists"]]
            reader = v["rank"]
            for k in keys:
                values = {r["letter"]: r["measure"][k] for r in entry["finalists"]}
                rho = _spearman(reader, sorted(order, key=lambda l: -values[l]))
                if rho is not None:
                    acc[k].append(rho)
            scored = {r["letter"]: score(r["measure"]) for r in entry["finalists"]}
            rho = _spearman(reader, sorted(order, key=lambda l: -scored[l]))
            if rho is not None:
                acc["score"].append(rho)
            firsts += max(scored, key=scored.get) == reader[0]
            n += 1
    out = {k: round(sum(v) / len(v), 3) for k, v in acc.items() if v}
    out["rankings"], out["score_first_is_readers"] = n, firsts
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=None, help=f"whose places: a directory under projects/ (or ${P.ENV})")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("calibrate", help="how well the measure follows the readers")
    for name in ("run", "judge", "report"):
        p = sub.add_parser(name)
        p.add_argument("--round", type=int, default=None)
        if name != "report":
            p.add_argument("--place", action="append", default=None)
    args = parser.parse_args(argv)
    try:
        use(P.named(args.project))
    except P.ProjectError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.command == "calibrate":
        print(json.dumps(calibrate(), indent=1))
        return 0
    if args.command == "run":
        print(run(args.round, args.place))
    else:
        number = args.round or (_next_round() - 1)
        if args.command == "judge":
            judge(number, args.place)
        else:
            report(number)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
