"""Walk round a THING in one of Blood's maps and photograph it.

`tools.study` photographs a room from inside it. That is the wrong camera
for an object that stands in a room -- a locomotive, a ship, a statue, a
machine: the study of E1M4's and E1M3's engines came back as one wheel
filling a frame and a black sheet. The owner, 2026-11-18, of the fourth
Gravesend locomotive: "made from one texture ... You should study more
textures, decals combinations and locomotives in other levels."

This stands cameras on a ring round a point -- a sprite of a given tile,
or a coordinate -- wherever there is floor a player could stand on, each
looking at the thing, and lists what the thing is MADE of: the wall,
floor and ceiling tiles within reach, with the library's reading of each,
and every sprite with its alignment and size. A thing is its surfaces and
its decals together; the list is the recipe.

.. code-block:: bash

    python -m tools.look_at E1M4 --tile 2322 -o knowledge/blood/studies/locomotive/E1M4
    python -m tools.look_at TEDE1M7 --at -40189,27654 --radius 5000 -o out
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))


def _fields(item):
    return item["fields"] if isinstance(item, dict) else item.fields


def recipe(disk, x: int, y: int, reach: int) -> dict:
    """What stands within `reach` of (x, y): surfaces and decals."""
    from tools import catalog

    looks = catalog.tile_looks()
    owners = catalog.owner_names() if hasattr(catalog, "owner_names") else {}

    def say(tile):
        row = looks.get(int(tile), {})
        name = owners.get(int(tile)) if isinstance(owners, dict) else None
        return str(name or row.get("looks") or "?")

    sectors = [_fields(s) for s in disk.sectors]
    walls = [_fields(w) for w in disk.walls]
    solid, masked, flats = (collections.Counter() for _ in range(3))
    for s in sectors:
        hit = False
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            f = walls[w]
            if abs(int(f["x"]) - x) > reach or abs(int(f["y"]) - y) > reach:
                continue
            hit = True
            solid[int(f["picnum"])] += 1
            if int(f["cstat"]) & (16 | 32) and int(f["next_sector"]) >= 0:
                masked[int(f["over_picnum"])] += 1
        if hit:
            flats[(int(s["floor_picnum"]), "floor")] += 1
            if not int(s["ceiling_stat"]) & 1:
                flats[(int(s["ceiling_picnum"]), "ceiling")] += 1
    decals = collections.Counter()
    for sprite in disk.sprites:
        f = _fields(sprite)
        if abs(int(f["x"]) - x) > reach or abs(int(f["y"]) - y) > reach:
            continue
        align = {0: "face", 16: "wall", 32: "floor"}.get(int(f["cstat"]) & 48,
                                                        "other")
        decals[(int(f["picnum"]), align, int(f["x_repeat"]),
                int(f["y_repeat"]))] += 1
    return {
        "walls": [{"tile": t, "count": n, "is": say(t)}
                  for t, n in solid.most_common(16)],
        "masked": [{"tile": t, "count": n, "is": say(t)}
                   for t, n in masked.most_common(8)],
        "flats": [{"tile": t, "on": on, "count": n, "is": say(t)}
                  for (t, on), n in flats.most_common(12)],
        "sprites": [{"tile": t, "align": a, "repeat": [xr, yr], "count": n,
                     "is": say(t)}
                    for (t, a, xr, yr), n in decals.most_common(30)],
    }


def ring(level, x: int, y: int, radius: int, count: int, near_z=None):
    """Cameras round (x, y) where a player could stand, looking at it."""
    import look
    from bloodmap.viewplan import angle_toward, eye_z
    from bloodmap.visual import Viewpoint

    out = []
    for step in range(count * 3):
        if len(out) >= count:
            break
        turn = 2 * math.pi * step / count
        #: a second and third lap try nearer in, for a thing in a cutting
        scale = (1.0, 0.65, 1.4)[step // count]
        px = int(x + math.cos(turn) * radius * scale)
        py = int(y + math.sin(turn) * radius * scale)
        sector = look.sector_at(level, px, py, near_z)
        if sector is None:
            continue
        z = eye_z(level, sector)
        if z is None:
            continue
        out.append(Viewpoint(
            view_id=f"round_{len(out):02d}", x=px, y=py, z=z,
            angle=int(angle_toward((px, py), (x, y))) & 2047,
            horiz=look.LEVEL, sector=sector, node=f"round:{len(out)}",
            purpose="loop", screenshot=True, note="walking round the thing"))
    return out


def look_at(map_name: str, out: pathlib.Path, *, tile=None, at=None,
            radius: int = 3500, count: int = 6, reach: int = 3000,
            empty: bool = False) -> dict:
    import look
    from bloodmap.format import read_map
    from bloodmap.corpus import corpus_map_path

    path = pathlib.Path(map_name)
    if not path.exists():
        path = corpus_map_path(map_name)
    disk = read_map(path)
    if at is None:
        hits = [_fields(s) for s in disk.sprites
                if int(_fields(s)["picnum"]) == int(tile)]
        if not hits:
            raise SystemExit(f"{map_name}: no sprite wears tile {tile}")
        x = sum(int(f["x"]) for f in hits) // len(hits)
        y = sum(int(f["y"]) for f in hits) // len(hits)
        near_z = int(hits[0]["z"])
    else:
        x, y = at
        near_z = None
    out.mkdir(parents=True, exist_ok=True)
    played = look.as_played(path, out, empty=empty)
    level = read_map(played).to_level_ir()
    views = ring(level, x, y, radius, count, near_z)
    if views:
        look.run_observation(look.ObservationRequest(
            map_path=played, output_dir=out,
            resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
            width=640, height=480, screenshots=[v.view_id for v in views],
            brightness=0, rff=None))
    report = {"map": str(map_name), "at": [x, y], "views": len(views),
              "recipe": recipe(disk, x, y, reach)}
    (out / "recipe.json").write_text(json.dumps(report, indent=1), "utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("map")
    parser.add_argument("--tile", type=int)
    parser.add_argument("--at", help="x,y in world units")
    parser.add_argument("--radius", type=int, default=3500)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--reach", type=int, default=3000)
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--empty", action="store_true",
                        help="hide enemies and pickups: the thing alone")
    args = parser.parse_args(argv)
    if args.tile is None and not args.at:
        parser.error("name the thing: --tile or --at")
    at = tuple(int(v) for v in args.at.split(",")) if args.at else None
    report = look_at(args.map, pathlib.Path(args.out), tile=args.tile, at=at,
                     radius=args.radius, count=args.count, reach=args.reach,
                     empty=args.empty)
    print(f"{report['map']} at {report['at']}: {report['views']} views")
    for key in ("walls", "masked", "flats", "sprites"):
        print(f"  {key}:")
        for row in report["recipe"][key][:14]:
            print("    ", {k: v for k, v in row.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
