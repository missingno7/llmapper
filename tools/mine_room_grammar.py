"""Interior room grammar: what a Blood venue map is made of.

Written for the four owner-picked references -- E6M1 (shop), E3M4 (hospital),
E3M3 (sewers), E4M9 (mall) -- plus the church/cemetery precedents.  The city
mining passes measured streets from outside; this one measures the inside:
how spaces cluster, which chambers repeat (a mall's units, a hospital's
wards), how wide the circulation is, what the water does, what hangs on the
walls, and what the map spends its channels on.

    python -m tools.mine_room_grammar E6M1 E3M4 E3M3 E4M9 E1M1 E1M5 \\
        -o projects/blood-city/references/room-grammar.json

Derived measures only; naming a cluster "ward" or "storefront" happens in
the pattern documents, marked interpreted, with sector ids to argue with.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.blood_types import SPRITE_TYPES
from bloodmap.patterns import corpus_map_path
from tools.mine_city_norms import MapGeom, load_source
from tools.mine_mechanisms import observe as observe_channels
from tools.mine_stacks import observe as observe_stacks

SCHEMA = "llmapper.room-grammar"
SCHEMA_VERSION = 1


def _percentiles(values, digits=1):
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {"n": len(ordered), "min": round(ordered[0], digits),
            "median": round(statistics.median(ordered), digits),
            "p90": round(ordered[len(ordered) * 9 // 10], digits),
            "max": round(ordered[-1], digits)}


def shape_class(geom: MapGeom, sector_id: int) -> tuple:
    """A sector outline up to rotation/reflection/translation: the edge-length
    sequence rounded to 64 units, canonicalized.  Congruent chambers -- a
    mall's repeated units, a crypt's cells -- share a class."""
    walls = geom.sector_walls[sector_id]
    lengths = [round(geom.wall_length(w) / 64) for w in walls]
    if not lengths:
        return ()
    best = None
    for seq in (lengths, lengths[::-1]):
        for shift in range(len(seq)):
            rotated = tuple(seq[shift:] + seq[:shift])
            if best is None or rotated < best:
                best = rotated
    return best


def bbox_metrics(geom: MapGeom, sector_id: int) -> dict:
    points = [geom.wall_xy(w) for w in geom.sector_walls[sector_id]]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w, d = max(xs) - min(xs), max(ys) - min(ys)
    long_side, short_side = max(w, d), max(1, min(w, d))
    return {"aspect": round(long_side / short_side, 2), "short": short_side,
            "long": long_side,
            "fill": round(geom.area[sector_id] / max(1, w * d), 2)}


def walkable_spaces(geom: MapGeom) -> list[set[int]]:
    """Sectors merged over portals the player walks through at grade."""
    crouch = geom.profile.crouch_height or int(geom.profile.standing_height * 0.75)
    adjacency = defaultdict(set)
    for s in range(len(geom.sectors)):
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0:
                continue
            if (geom.gap(s, o) >= crouch or geom.is_door_sector(o)
                    or geom.is_door_sector(s)) and abs(geom.rise(s, o)) <= geom.profile.max_step:
                adjacency[s].add(o)
                adjacency[o].add(s)
    seen, out = set(), []
    for start in range(len(geom.sectors)):
        if start in seen:
            continue
        comp = {start}
        seen.add(start)
        queue = [start]
        while queue:
            cur = queue.pop()
            for o in adjacency[cur]:
                if o not in seen:
                    seen.add(o)
                    comp.add(o)
                    queue.append(o)
        out.append(comp)
    out.sort(key=lambda c: -sum(geom.area[s] for s in c))
    return out


def concourse_rhythm(geom: MapGeom, space: set[int]) -> dict:
    """Portal spacing along the largest space: the storefront rhythm.

    Every red wall leading out of the space to a walkable pocket is a
    'frontage opening'; their widths and gaps along the boundary are the
    rhythm a mall or a shop street runs on."""
    openings = []
    for s in space:
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0 or o in space:
                continue
            width = geom.wall_length(w)
            if width < geom.profile.min_passage_width:
                continue
            if geom.gap(s, o) <= 0 and not geom.is_door_sector(o):
                continue
            (x1, y1), (x2, y2) = geom.wall_segment(w)
            openings.append({"wall": w, "width": round(width),
                             "mid": ((x1 + x2) / 2, (y1 + y2) / 2),
                             "into": o})
    gaps = []
    if len(openings) >= 3:
        remaining = openings[1:]
        current = openings[0]
        ordered = [current]
        while remaining:
            nxt = min(remaining, key=lambda e: math.hypot(
                e["mid"][0] - current["mid"][0], e["mid"][1] - current["mid"][1]))
            remaining.remove(nxt)
            gaps.append(round(math.hypot(nxt["mid"][0] - current["mid"][0],
                                         nxt["mid"][1] - current["mid"][1])))
            ordered.append(nxt)
            current = nxt
    return {"openings": len(openings),
            "opening_width": _percentiles([o["width"] for o in openings], 0),
            "nearest_spacing": _percentiles([g for g in gaps if g < 16384], 0),
            "opening_walls": [o["wall"] for o in openings][:40]}


def water_metrics(geom: MapGeom) -> dict:
    underwater = []
    depth_marked = []
    for i, sector in enumerate(geom.sectors):
        extra = sector.extra
        if extra is None:
            continue
        if int(extra.fields.get("underwater", 0) or 0):
            underwater.append(i)
        if int(extra.fields.get("depth", 0) or 0):
            depth_marked.append(i)
    # Walkway-over-channel: adjacent pairs with a modest floor step where the
    # lower sector is elongated (the channel) -- the sewer ledge signature.
    ledge_pairs = 0
    steps = []
    for s in range(len(geom.sectors)):
        for w in geom.sector_walls[s]:
            o = int(geom.walls[w].fields["next_sector"])
            if o < 0 or o <= s:
                continue
            rise = abs(geom.rise(s, o))
            if 1024 <= rise <= 8192 and geom.gap(s, o) > 0:
                steps.append(rise)
                low = s if geom.floor_z[s] > geom.floor_z[o] else o
                if bbox_metrics(geom, low)["aspect"] >= 3:
                    ledge_pairs += 1
    return {"underwater_sectors": len(underwater),
            "underwater_ids": underwater[:12],
            "shallow_depth_sectors": len(depth_marked),
            "walk_step_census_z": _percentiles([float(v) for v in steps], 0),
            "ledge_over_channel_pairs": ledge_pairs}


def light_metrics(geom: MapGeom) -> dict:
    shades = [int(s.fields["floor_shade"]) for s in geom.sectors]
    animated = []
    for i, sector in enumerate(geom.sectors):
        extra = sector.extra
        if extra is not None and int(extra.fields.get("amplitude", 0) or 0):
            animated.append(i)
    return {"floor_shade": _percentiles([float(v) for v in shades], 0),
            "animated_shade_sectors": len(animated),
            "animated_ids": animated[:16]}


def sprite_language(geom: MapGeom) -> dict:
    align = Counter()
    picnums = Counter()
    dudes = Counter()
    for sprite in geom.sprites:
        bits = int(sprite.fields["cstat"]) & 48
        align[{0: "face", 16: "wall", 32: "floor"}.get(bits, "other")] += 1
        picnums[int(sprite.fields["picnum"])] += 1
        entry = SPRITE_TYPES.get(int(sprite.fields.get("type", 0)))
        if entry and entry.get("category") == "dude":
            dudes[entry["name"]] += 1
    return {"alignment": dict(align), "picnums_top15": picnums.most_common(15),
            "dudes": dict(dudes.most_common(10))}


def analyze(name: str) -> dict:
    geom = load_source(name, "blood", corpus_map_path(name))
    spaces = walkable_spaces(geom)
    big = spaces[0]

    classes = Counter()
    class_members = defaultdict(list)
    for s in range(len(geom.sectors)):
        if geom.area[s] < 256 * 256:
            continue
        cls = shape_class(geom, s)
        classes[cls] += 1
        class_members[cls].append(s)
    repeated = [
        {"count": count, "sample_sectors": class_members[cls][:8],
         "area": round(geom.area[class_members[cls][0]]),
         "aspect": bbox_metrics(geom, class_members[cls][0])["aspect"]}
        for cls, count in classes.most_common(12) if count >= 3
    ]

    corridors = [s for s in range(len(geom.sectors))
                 if geom.area[s] > 512 * 512 and bbox_metrics(geom, s)["aspect"] >= 3
                 and bbox_metrics(geom, s)["fill"] >= 0.7]
    corridor_widths = [bbox_metrics(geom, s)["short"] for s in corridors]

    mech = observe_channels(corpus_map_path(name))
    return {
        "map": name,
        "totals": {"sectors": len(geom.sectors), "walls": len(geom.walls),
                   "sprites": len(geom.sprites)},
        "walkable_spaces": [
            {"sectors": len(space), "area": round(sum(geom.area[s] for s in space)),
             "sample": sorted(space)[:8]}
            for space in spaces[:8]
        ],
        "repeated_chamber_classes": repeated,
        "corridors": {"count": len(corridors),
                      "width": _percentiles([float(v) for v in corridor_widths], 0),
                      "ids": corridors[:16]},
        "concourse_rhythm": concourse_rhythm(geom, big),
        "water": water_metrics(geom),
        "light": light_metrics(geom),
        "sprites": sprite_language(geom),
        "stacks": [
            {k: row.get(k) for k in ("family", "paired", "congruent",
                                     "overlaps_in_plan", "upper_sector", "lower_sector")}
            for row in observe_stacks(name, geom.disk)
        ],
        "channels": {"user_channels": mech["user_channels"],
                     "reserved_uses": mech["reserved_uses"]},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="+")
    parser.add_argument("-o", "--output",
                        default="projects/blood-city/references/room-grammar.json")
    args = parser.parse_args(argv)
    payload = {"$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
               "per_map": [analyze(name) for name in args.maps]}
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for record in payload["per_map"]:
        print(record["map"], record["totals"],
              "spaces:", len(record["walkable_spaces"]),
              "repeated:", len(record["repeated_chamber_classes"]),
              "channels:", record["channels"]["user_channels"])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
