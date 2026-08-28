"""Set-pieces: the furniture Blood builds out of sectors, mined by shape.

A Blood piano is not a sprite.  E1M1 builds it out of three sectors -- a
tall wooden body (43: 1024x3072, 2.17 player heights of it, flats 34/390)
and two thin stepped strips beside it (126 and 127: 128x2560, keyboard flat
620, at two different heights) -- with a candelabrum standing on it and
three `kGenSound` (type 708) emitters inside.  Its furnace is four sectors:
a fire-flat chamber, a metal-lined box, and two crawlable mouths.

Neither is a prefab anyone declared.  They are *compositions*, and the only
way to author one deliberately is to know what the class looks like.  So
this detects furniture-like sectors -- small, adjacent to a bigger host
room, standing at a different level or wearing different flats -- groups
them into pieces, and clusters the pieces by signature.

Class names are INTERPRETED and applied afterwards by a reader.
Signatures, proportions and occurrences are DERIVED, and are what this file
actually asserts.

    python tools/mine_set_pieces.py -o knowledge/blood/design/set-pieces-v1.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bloodmap.format import read_map

PLAYER = 16960          # a standing human, in z units
PLAN = 1024             # the project's plan unit, for footprints

#: A sector big enough to stand around in is a room, not furniture.
HOST_AREA = 4_000_000
#: A piece bigger than this is a room with a step in it, not an object.
PIECE_AREA = 8_000_000
DOOR_TYPES = {600, 602, 604, 614, 616, 618}
SOUND_TYPES = {708, 709, 710, 711}


def sector_geometry(m, index):
    s = m.sectors[index]
    pts = [(m.walls[w].x, m.walls[w].y)
           for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
    total = 0.0
    for i, (ax, ay) in enumerate(pts):
        bx, by = pts[(i + 1) % len(pts)]
        total += ax * by - bx * ay
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "area": abs(total) / 2,
        "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys),
        "neighbours": {m.walls[w].next_sector
                       for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)} - {-1},
        "walls": collections.Counter(
            m.walls[w].picnum
            for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)),
    }


def band(value, edges):
    for i, edge in enumerate(edges):
        if value < edge:
            return i
    return len(edges)


def collect(path):
    """Every set-piece in one map."""
    m = read_map(path)
    geo = {i: sector_geometry(m, i) for i in range(len(m.sectors))
           if m.sectors[i].wall_count >= 3}
    by_sector = collections.defaultdict(list)
    for sp in m.sprites:
        by_sector[sp.sector].append(sp)

    hosts = {i for i, g in geo.items() if g["area"] >= HOST_AREA}
    furniture = set()
    examined = 0
    for i, g in geo.items():
        s = m.sectors[i]
        if i in hosts or s.type in DOOR_TYPES:
            continue
        examined += 1
        near = [n for n in g["neighbours"] if n in hosts]
        if not near:
            continue
        host = m.sectors[near[0]]
        # Furniture stands at a different level from the room it is in, or
        # is faced in different material.  A sector matching its host on
        # both is simply part of the room.
        if (s.floor_z != host.floor_z
                or s.floor_picnum != host.floor_picnum
                or s.ceiling_picnum != host.ceiling_picnum):
            furniture.add(i)

    # A second tier touches only the tier below it.  E1M1's piano is three
    # sectors and 127 -- the lower of the two keyboard strips -- borders
    # nothing but 43 and 126, so the first pass never saw it and the piano
    # came out as a two-sector object missing half its keyboard.  Grow the
    # set transitively over small sectors, capped so a piece cannot walk
    # away down a corridor.
    for _ in range(4):
        grown = set()
        for i, g in geo.items():
            if i in furniture or i in hosts or m.sectors[i].type in DOOR_TYPES:
                continue
            if g["area"] >= HOST_AREA:
                continue
            if g["neighbours"] & furniture:
                grown.add(i)
        if not grown:
            break
        furniture |= grown

    out, seen = [], set()
    for start in sorted(furniture):
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            cur = stack.pop()
            group.append(cur)
            for n in geo[cur]["neighbours"]:
                if n in furniture and n not in seen:
                    seen.add(n)
                    stack.append(n)
        if sum(geo[i]["area"] for i in group) > PIECE_AREA or len(group) > 8:
            continue
        host_ids = [n for i in group for n in geo[i]["neighbours"] if n in hosts]
        if not host_ids:
            continue
        host_id = collections.Counter(host_ids).most_common(1)[0][0]
        host = m.sectors[host_id]

        x0 = min(geo[i]["x0"] for i in group)
        y0 = min(geo[i]["y0"] for i in group)
        x1 = max(geo[i]["x1"] for i in group)
        y1 = max(geo[i]["y1"] for i in group)
        width, depth = (x1 - x0) / PLAN, (y1 - y0) / PLAN
        if width <= 0 or depth <= 0:
            continue
        tiers = sorted({(host.floor_z - m.sectors[i].floor_z) / PLAYER
                        for i in group})
        sprites, gizmos, sounds = [], [], []
        for i in group:
            for sp in by_sector.get(i, []):
                if sp.type in SOUND_TYPES:
                    sounds.append(sp.type)
                elif sp.type:
                    gizmos.append(sp.type)
                else:
                    sprites.append(sp.picnum)
        walls = collections.Counter()
        for i in group:
            walls.update(geo[i]["walls"])
        out.append({
            "sectors": sorted(group),
            "host": host_id,
            "footprint_plan": [round(width, 2), round(depth, 2)],
            "tiers": [round(t, 2) for t in tiers],
            "rise": round(max(tiers), 2),
            "drop": round(min(tiers), 2),
            "tall": round(max((m.sectors[i].floor_z - m.sectors[i].ceiling_z)
                              / PLAYER for i in group), 2),
            "floors": sorted({m.sectors[i].floor_picnum for i in group}),
            "ceilings": sorted({m.sectors[i].ceiling_picnum for i in group}),
            "walls": [t for t, _ in walls.most_common(4)],
            "sprites": sorted(set(sprites)),
            "gizmos": sorted(set(gizmos)),
            "sounds": sorted(set(sounds)),
        })
    return out, examined


def signature(row):
    width, depth = row["footprint_plan"]
    longer, shorter = max(width, depth), max(0.01, min(width, depth))
    return (
        len(row["sectors"]),
        band(row["rise"], (0.05, 0.25, 0.5, 1.0, 2.0)),
        band(longer / shorter, (1.5, 3.0, 6.0)),
        band(longer, (1.0, 2.0, 4.0)),
        bool(row["sounds"]),
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--min-occurrences", type=int, default=4)
    args = ap.parse_args(argv)

    classes = collections.defaultdict(list)
    examined = found = 0
    for path in sorted(glob.glob("maps/blood/*.MAP")):
        name = pathlib.Path(path).stem
        try:
            rows, seen = collect(path)
        except Exception:
            continue
        examined += seen
        for row in rows:
            row["map"] = name
            found += 1
            classes[signature(row)].append(row)

    def q(values, p):
        values = sorted(values)
        return round(values[min(len(values) - 1, int(len(values) * p))], 2)

    out = []
    for key, rows in sorted(classes.items(), key=lambda kv: -len(kv[1])):
        if len(rows) < args.min_occurrences:
            continue
        floors = collections.Counter(t for r in rows for t in r["floors"])
        walls = collections.Counter(t for r in rows for t in r["walls"])
        sprites = collections.Counter(t for r in rows for t in r["sprites"])
        gizmos = collections.Counter(t for r in rows for t in r["gizmos"])
        sounds = collections.Counter(t for r in rows for t in r["sounds"])
        out.append({
            "signature": {"sectors": key[0], "rise_band": key[1],
                          "aspect_band": key[2], "size_band": key[3],
                          "has_sound": key[4]},
            "occurrences": len(rows),
            "maps": sorted({r["map"] for r in rows}),
            "footprint_plan": {
                "width": [q([r["footprint_plan"][0] for r in rows], p)
                          for p in (0.1, 0.5, 0.9)],
                "depth": [q([r["footprint_plan"][1] for r in rows], p)
                          for p in (0.1, 0.5, 0.9)]},
            "rise_player_heights": [q([r["rise"] for r in rows], p)
                                    for p in (0.1, 0.5, 0.9)],
            "own_height_player_heights": [q([r["tall"] for r in rows], p)
                                          for p in (0.1, 0.5, 0.9)],
            "tier_counts": collections.Counter(
                len(r["tiers"]) for r in rows).most_common(3),
            "floor_palette": floors.most_common(6),
            "wall_palette": walls.most_common(6),
            "attendant_sprites": sprites.most_common(6),
            "gizmos": gizmos.most_common(4),
            "sounds": sounds.most_common(4),
            "examples": rows[:12],
        })

    report = {
        "$schema": "llmapper.set-pieces",
        "schema_version": 1,
        "note": ("Signatures, proportions and occurrences are DERIVED. "
                 "Class names, where present, are INTERPRETED by a reader."),
        "sectors_examined": examined,
        "pieces_found": found,
        "classes": out,
    }
    pathlib.Path(args.output).write_text(json.dumps(report, indent=1),
                                         encoding="utf-8")
    print(f"wrote {args.output}: {found} pieces, {len(out)} classes "
          f"with >= {args.min_occurrences} occurrences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
