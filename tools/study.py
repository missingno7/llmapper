"""Study how Blood built a thing before building one.

The owner, 2026-11-18, after a crypt built from the word "crypt" came out
as a brick room with grey boxes: "It should be something like, I would
like to build this, I am checking these levels how they did it, etc. to
get inspiration and really think stuff through. This should allow you to
learn by yourself, if you need some tools or database to maintain for
yourself you can make it. Something that would give you tools to be a
really good mapper."

A study is the step BEFORE the layout, and it is kept:

1. **say what is to be built** (`--want`), in a sentence;
2. **find where Blood built it**: seeds named by hand (``E1M1:150`` is a
   map and a sector in the place), and the campaign's other places that
   wear the same palette (`tools.place_character --like`);
3. **look**: each seed is rendered as the game shows it (control sprites
   hidden), from several standing points, with a plan drawn the way the
   editor draws it (+Y down);
4. **measure**: size in metres and bodies, what stands in it, which tiles
   on which surfaces -- every tile with its picture and its other uses
   (`tools.tile_usage`), every sprite with its type decoded;
5. **think**: `notes.md`, written by the mapper after looking -- what
   makes the place read as what it is, what will be transcribed, what
   will NOT be, what is still unknown. The tool writes the headings and
   refuses to call a study done while they are empty.

Studies live in ``knowledge/blood/studies/<slug>/`` and are indexed in
``knowledge/blood/studies/index.json``: a database the mapper maintains
for itself. `projects/blood-city/level/character.py` names the study each
place was built from, and the build says which named places have none.

.. code-block:: bash

    python -m tools.study crypt --want "a crypt under a parish church" \\
        --seed E1M1:150 --seed E3M8:445 --like 3
    python -m tools.study --list
    python -m tools.study crypt --check        # are the notes written?
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

STUDIES = ROOT / "knowledge" / "blood" / "studies"
INDEX = STUDIES / "index.json"
HEADINGS = ("What I want to build", "Where Blood built it",
            "What makes it read as that", "Sizes",
            "What I will transcribe", "What I will not do, and why",
            "What I still do not know")
UNWRITTEN = "_(not written yet)_"


def _sprites_of(geom, place, type_names) -> list[dict]:
    rows: dict = {}
    for sector in place:
        for sprite in geom.by_sector.get(sector, ()):
            if int(sprite["cstat"]) & 32768:
                continue
            kind = int(sprite.get("type", 0))
            align = {0: "face", 16: "wall", 32: "flat"}.get(
                int(sprite["cstat"]) & 48, "face")
            key = (int(sprite["picnum"]), kind, align)
            row = rows.setdefault(key, {
                "tile": key[0], "type": kind,
                "type_name": (type_names.get(kind) or {}).get("name", ""),
                "align": align, "count": 0,
                "repeats": [int(sprite["x_repeat"]), int(sprite["y_repeat"])],
                "pal": int(sprite["pal"]),
                "over_floor_bodies": round(
                    (int(geom.sectors[sector]["floor_z"]) - int(sprite["z"]))
                    / 16960, 2)})
            row["count"] += 1
    return sorted(rows.values(), key=lambda r: -r["count"])


def _things(geom, place, host) -> list[dict]:
    """The small sectors standing in the room: what its furniture is."""
    hs = geom.sectors[host]
    out = []
    for sector in sorted(place):
        if sector == host:
            continue
        s = geom.sectors[sector]
        points = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
                  for w in geom.wall_ids(sector)]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        out.append({
            "sector": sector, "corners": len(points),
            "size": [max(xs) - min(xs), max(ys) - min(ys)],
            "rise_bodies": round((int(hs["floor_z"]) - int(s["floor_z"]))
                                 / 16960, 2),
            "floor_tile": int(s["floor_picnum"]),
            "sloped": bool(int(s["floor_heinum"])),
            "type": int(s["type"]),
            "wall_tiles": sorted({int(geom.walls[w]["picnum"])
                                  for w in geom.wall_ids(sector)})})
    return out


def _plan(geom, place, path: pathlib.Path) -> None:
    from PIL import Image, ImageDraw

    points = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
              for s in place for w in geom.wall_ids(s)]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    x1, y1 = max(p[0] for p in points), max(p[1] for p in points)
    scale = min(0.2, 900 / max(1, x1 - x0, y1 - y0))
    pad = 30
    image = Image.new("RGB", (int((x1 - x0) * scale) + 2 * pad,
                              int((y1 - y0) * scale) + 2 * pad), "white")
    draw = ImageDraw.Draw(image)

    def at(x, y):                       # +Y DOWN, as the editor draws it
        return ((x - x0) * scale + pad, (y - y0) * scale + pad)

    for sector in place:
        for w in geom.wall_ids(sector):
            a = geom.walls[w]
            b = geom.walls[int(a["point2"])]
            draw.line([at(int(a["x"]), int(a["y"])),
                       at(int(b["x"]), int(b["y"]))],
                      fill="red" if int(a["next_sector"]) < 0 else "blue")
        if len(place) < 60:
            inside = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
                      for w in geom.wall_ids(sector)]
            cx = sum(p[0] for p in inside) / len(inside)
            cy = sum(p[1] for p in inside) / len(inside)
            draw.text(at(cx, cy), str(sector), fill="black")
    #: a body, to scale, in the corner: 384 wide
    draw.rectangle([4, 4, 4 + 384 * scale, 4 + 384 * scale], outline="green")
    draw.text((8 + 384 * scale, 4), "a body's width", fill="green")
    image.save(path)


def _frames(map_path, geom, place, host, out_dir: pathlib.Path) -> list[str]:
    """Stand in the room's corners and middle and look across it."""
    import look
    from bloodmap.format import read_map

    level = read_map(map_path).to_level_ir()
    points = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
              for w in geom.wall_ids(host)]
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    floor = int(geom.sectors[host]["floor_z"])
    #: WHERE TO STAND. The first version stood a fifth of the way in from
    #: the four furthest corners and looked at the centroid; the agents who
    #: used it reported "cameras sit in corners facing walls", black frames
    #: and near-mirror pairs, and re-rendered most places by hand. Now: the
    #: open floor is sampled, a standing point must have a body and a half
    #: of clear floor round it, the four chosen are far from one another,
    #: and each looks at WHAT IS IN the room -- the things standing in it
    #: and its decoration -- or, in an empty room, down its longest sight.
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    segments = []
    for sector in place:
        for w in geom.wall_ids(sector):
            a = geom.walls[w]
            b = geom.walls[int(a["point2"])]
            if int(a["next_sector"]) < 0 or int(a["next_sector"]) in place:
                segments.append(((int(a["x"]), int(a["y"])),
                                 (int(b["x"]), int(b["y"]))))

    def clearance(x, y):
        best = 1e9
        for (ax, ay), (bx, by) in segments:
            dx, dy = bx - ax, by - ay
            length = dx * dx + dy * dy
            k = 0 if not length else max(0.0, min(1.0, (
                (x - ax) * dx + (y - ay) * dy) / length))
            best = min(best, math.hypot(x - ax - k * dx, y - ay - k * dy))
        return best

    step = max(256, int(max(max(xs) - min(xs), max(ys) - min(ys)) / 24))
    open_floor = []
    for x in range(min(xs) + step // 2, max(xs), step):
        for y in range(min(ys) + step // 2, max(ys), step):
            if geom.contains(host, x, y):
                room = clearance(x, y)
                if room >= 400:
                    open_floor.append((room, x, y))
    subjects = []
    for sector in place:
        if sector != host:
            inside = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
                      for w in geom.wall_ids(sector)]
            subjects.append((sum(p[0] for p in inside) / len(inside),
                             sum(p[1] for p in inside) / len(inside)))
        for sprite in geom.by_sector.get(sector, ()):
            if (not int(sprite["cstat"]) & 32768
                    and int(sprite.get("status", 0)) in (0, 4)):
                subjects.append((int(sprite["x"]), int(sprite["y"])))
    if subjects:
        cx = sum(s[0] for s in subjects) / len(subjects)
        cy = sum(s[1] for s in subjects) / len(subjects)
    chosen = []
    #: far from the subject first (so it is in view), then far from each
    #: other; a point hard against the subject sees nothing of it
    for room, x, y in sorted(open_floor, key=lambda r: -(
            math.hypot(r[1] - cx, r[2] - cy) + 2 * min(r[0], 1500))):
        if math.hypot(x - cx, y - cy) < 900:
            continue
        if all(math.hypot(x - c[0], y - c[1]) > max(1500, 6 * step)
               for c in chosen):
            chosen.append((x, y))
        if len(chosen) == 7:
            break
    views = []
    for index, (x, y) in enumerate(chosen):
        if len(views) == 4:
            break
        #: stand in the room itself, not on something standing in it
        if any(geom.contains(other, x, y) for other in place
               if other != host):
            continue
        sector = host
        z = look.eye_z(level, sector)
        if z is None:
            continue
        views.append(look.Viewpoint(
            view_id=f"corner_{index}", x=x, y=y, z=z,
            angle=int(look.angle_toward((x, y), (cx, cy))) & 2047,
            horiz=look.LEVEL, sector=sector, node=f"study:{index}",
            purpose="reference", screenshot=True, note="across the room"))
    if not views:
        return []
    look.run_observation(look.ObservationRequest(
        map_path=look.as_played(map_path, out_dir), output_dir=out_dir,
        resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
        width=640, height=480, screenshots=[v.view_id for v in views],
        brightness=0, rff=None))
    from PIL import Image

    from PIL import ImageStat

    #: a frame of one flat colour shows nothing: leave it off the sheet
    good = []
    for view in views:
        frame = out_dir / "frames" / f"{view.view_id}.png"
        if frame.exists():
            picture = Image.open(frame).convert("L")
            dark = sum(picture.histogram()[:8]) / (picture.width
                                                    * picture.height)
            #: ... and so does one that is mostly pure black
            if ImageStat.Stat(picture).stddev[0] >= 6 and dark < 0.6:
                good.append(frame)
    if not good:
        return []
    sheet = Image.new("RGB", (1280, 480 * ((len(good) + 1) // 2)))
    for index, frame in enumerate(good):
        sheet.paste(Image.open(frame), ((index % 2) * 640,
                                        (index // 2) * 480))
    sheet.save(out_dir / "frames.png")
    return [str(out_dir / "frames.png")]


def study_seed(seed: str, folder: pathlib.Path, floor: int | None) -> dict:
    from bloodmap.blood_types import SPRITE_TYPES
    from bloodmap.format import read_map
    from bloodmap.patterns import corpus_map_path
    from tools import place_character as pc

    name, sector = seed.split(":")
    #: "E1M1:150!" is the one sector and the small things standing in it,
    #: for a room that opens wide onto the rest of its building
    alone = sector.endswith("!")
    sector = sector.rstrip("!")
    path = (pathlib.Path(name) if name.upper().endswith(".MAP")
            else corpus_map_path(name))
    geom = pc.Geometry(read_map(path))
    if alone:
        place, queue = {int(sector)}, [int(sector)]
        while queue:
            here = queue.pop()
            for w in geom.wall_ids(here):
                other = int(geom.walls[w]["next_sector"])
                if (other >= 0 and other not in place
                        and geom.area(other) < pc.SMALL):
                    place.add(other)
                    queue.append(other)
    else:
        place = pc.place_of(geom, int(sector))
    profile = pc.profile(geom, place)
    host = profile["host"]
    out = folder / seed.replace(":", "_").replace("!", "").replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    _plan(geom, place, out / "plan.png")
    frames = _frames(path, geom, place, host, out)
    names = pc.names()
    return {
        "seed": seed, "map": str(path), "host": host,
        "sectors": sorted(place), "metres": profile["metres"],
        "area_M": profile["area_M"], "clear_bodies": profile["clear_bodies"],
        "free_floor_share": profile["free_floor_share"],
        "shade_spread": profile["shade_spread"],
        "floor": [profile["floor_tile"], names.get(profile["floor_tile"], "")],
        "ceiling": [profile["ceiling_tile"],
                    names.get(profile["ceiling_tile"], "")],
        "walls": [[t, share, names.get(t, "")]
                  for t, share in profile["wall_tiles"]],
        "things": _things(geom, place, host),
        "sprites": _sprites_of(geom, place, SPRITE_TYPES),
        "plan": str(out / "plan.png"), "frames": frames,
    }


def notes_written(folder: pathlib.Path) -> list[str]:
    """The headings of `notes.md` still empty."""
    path = folder / "notes.md"
    if not path.exists():
        return list(HEADINGS)
    text = path.read_text("utf-8")
    missing = []
    for index, heading in enumerate(HEADINGS):
        start = text.find(f"## {heading}")
        if start < 0:
            missing.append(heading)
            continue
        end = text.find("\n## ", start + 4)
        body = text[start + len(heading) + 3:end if end >= 0 else None].strip()
        if not body or UNWRITTEN in body:
            missing.append(heading)
    return missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--want", default="")
    parser.add_argument("--seed", action="append", default=[])
    parser.add_argument("--like", type=int, default=0)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    STUDIES.mkdir(parents=True, exist_ok=True)
    index = (json.loads(INDEX.read_text("utf-8")) if INDEX.exists()
             else {"$schema": "llmapper.studies", "studies": {}})
    if args.list:
        for slug, row in index["studies"].items():
            folder = STUDIES / slug
            left = notes_written(folder)
            print(f"{slug:<16} {row['want'][:50]:<50} seeds "
                  f"{','.join(row['seeds'])}  "
                  f"{'DONE' if not left else 'notes owed: ' + str(len(left))}")
        return 0
    folder = STUDIES / args.slug
    if args.check:
        left = notes_written(folder)
        print("done" if not left else "notes owed:\n  " + "\n  ".join(left))
        return 1 if left else 0
    folder.mkdir(parents=True, exist_ok=True)
    seeds = [study_seed(seed, folder, None) for seed in args.seed]
    like = []
    if args.like and seeds:
        from tools import place_character as pc

        reference = pc.load_norms()
        probe = {"wall_tiles": [(t, s) for t, s, _n in seeds[0]["walls"]],
                 "floor_tile": seeds[0]["floor"][0],
                 "ceiling_tile": seeds[0]["ceiling"][0]}
        like = [{"map": row["map"], "host": row["host"],
                 "area_M": row["area_M"], "walls": row["wall_tiles"],
                 "wall_art": row["wall_art"], "standing": row["standing"]}
                for row in pc.like(probe, reference, args.like + 1)
                if not (row["map"] == pathlib.Path(seeds[0]["map"]).stem
                        and row["host"] == seeds[0]["host"])][:args.like]
    tiles = sorted({t for s in seeds for t, _sh, _n in s["walls"]}
                   | {s["floor"][0] for s in seeds}
                   | {s["ceiling"][0] for s in seeds}
                   | {thing["floor_tile"] for s in seeds
                      for thing in s["things"]}
                   | {row["tile"] for s in seeds for row in s["sprites"][:8]})
    from tools import tile_usage

    pictures = {str(t): tile_usage.picture(t, folder / "tiles") for t in tiles}
    data = {"slug": args.slug, "want": args.want,
            "date": datetime.date.today().isoformat(),
            "seeds": seeds, "like": like, "tiles": pictures}
    (folder / "study.json").write_text(json.dumps(data, indent=1), "utf-8")
    notes = folder / "notes.md"
    if not notes.exists():
        notes.write_text(
            f"# Study: {args.slug}\n\n" + "\n".join(
                f"## {heading}\n\n{UNWRITTEN}\n" for heading in HEADINGS),
            "utf-8")
    index["studies"][args.slug] = {
        "want": args.want, "seeds": args.seed, "date": data["date"]}
    INDEX.write_text(json.dumps(index, indent=1), "utf-8")
    for seed in seeds:
        print(f"{seed['seed']}: {seed['metres'][0]} x {seed['metres'][1]} m, "
              f"{seed['metres'][2]} m high; {len(seed['things'])} things; "
              f"walls {[(t, n) for t, _s, n in seed['walls'][:4]]}")
        print(f"   plan {seed['plan']}\n   frames {seed['frames']}")
    for row in like:
        print(f"like: {row['map']} s{row['host']} {row['area_M']}M")
    print(f"tiles drawn: {len(pictures)} -> {folder / 'tiles'}")
    left = notes_written(folder)
    print(f"notes: {notes} ({'done' if not left else str(len(left)) + ' headings owed'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
