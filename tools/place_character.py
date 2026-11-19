"""What a place is made of, layer by layer, against Blood's own rooms.

The owner, walking Gravesend on 2026-11-18: "Some things you created are
simplistic and have certain shapes, but they don't look sophisticated,
there is no combination of decals and textures making it look like
something ... I would like you to come up with some tools or conventions
how to really make the places memorable, have character, more details,
combination of sprites and textures like other Blood levels are doing."

Every gate the city had measured a place's SHAPE (does it compile, does a
sprite fit, is a wall too long). None measured what the shape wears. A
machine hall of one wall tile, one floor tile and six sprites passed all
of them.

A *place* here is one continuous space: a seed sector grown across every
portal wide enough to be the same room, plus the small sectors standing in
it (machines, steps, niches). Its *character* is counted in LAYERS, each
one a separate decision a Blood mapper made about the room:

``field``      the wall tile most of the room wears
``second``     a second wall tile on a tenth or more of the solid wall
``trim``       further tiles, each on 2% or more: bands, panels, frames
``wall_art``   wall-aligned sprites: gauges, signs, stains, windows
``flat_art``   floor/ceiling-aligned sprites: grates, hatches, stains
``standing``   face sprites that are decoration (statnum 0, type 0)
``levels``     three or more floor heights in the one space
``masked``     masked or one-way walls: grates, fences, glass
``light``      a floor shade spread of 12 or more across the place
``motion``     sectors that pan, move, or pulse their light
``machines``   small sectors that wear a floor or wall tile the host does not

A place is thin when it carries fewer layers than three quarters of the
campaign's rooms of its size do. ``--like`` answers the next question --
which Blood rooms wear this palette, and what else do THEY wear -- so a
recipe is transcribed and not invented.

.. code-block:: bash

    python -m tools.place_character MAP --at 43520,8704      # one place
    python -m tools.place_character MAP --sector 126 --like 5
    python -m tools.place_character --norms -o knowledge/blood/design/place-character-v1.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys
from collections import Counter
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEMA = "llmapper.place-character"
SCHEMA_VERSION = 1
NORMS = ROOT / "knowledge" / "blood" / "design" / "place-character-v1.json"

#: a portal this wide joins two sectors of one room; a door is narrower
WIDE = 1536
#: a sector under this area standing in a room is part of it
SMALL = 1_500_000
#: a room worth profiling: a core sector at least this big
CORE = 3_000_000
SECOND, TRIM = 0.10, 0.02
#: SCALE. The owner, 2026-11-18, after walking a crypt 1,536 wide: "There
#: is some general issue in feeling size of things and space ... it feels
#: like a miniature. We should do something to really have sense of space
#: volume". A player is 16,960 z tall -- 1,060 in plan units -- and 384
#: wide, so 1,024 units is 1.7 metres: a "plan unit" is a doorway, not a
#: room. Every place is therefore also reported in bodies and metres, and
#: judged against the campaign's rooms of its own area for its SHORT SIDE
#: and its HEIGHT.
BODY_Z, BODY_XY, BODY_WIDE = 16960, 1060, 384
UNITS_PER_METRE = BODY_XY / 1.8


def metres(units: float) -> float:
    return round(units / UNITS_PER_METRE, 1)
LEVELS, SPREAD = 3, 12
LAYERS = ("second", "trim", "wall_art", "flat_art", "standing", "levels",
          "masked", "light", "motion", "machines")


class Geometry:
    """A read map, indexed the few ways a place needs."""

    def __init__(self, disk: Any):
        self.disk = disk
        self.sectors = [s.fields for s in disk.sectors]
        self.extras = [getattr(s, "extra", None) for s in disk.sectors]
        self.walls = [w.fields for w in disk.walls]
        self.sprites = [s.fields for s in disk.sprites]
        self._area: dict[int, float] = {}
        self.by_sector: dict[int, list[dict]] = {}
        for sprite in self.sprites:
            self.by_sector.setdefault(int(sprite["sector"]), []).append(sprite)

    def wall_ids(self, sector: int) -> range:
        s = self.sectors[sector]
        return range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))

    def length(self, wall: int) -> float:
        a = self.walls[wall]
        b = self.walls[int(a["point2"])]
        return math.hypot(int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"]))

    def area(self, sector: int) -> float:
        if sector not in self._area:
            total = 0
            for w in self.wall_ids(sector):
                a = self.walls[w]
                b = self.walls[int(a["point2"])]
                total += int(a["x"]) * int(b["y"]) - int(b["x"]) * int(a["y"])
            self._area[sector] = abs(total) / 2.0
        return self._area[sector]

    def sky(self, sector: int) -> bool:
        return bool(int(self.sectors[sector]["ceiling_stat"]) & 1)

    def contains(self, sector: int, x: int, y: int) -> bool:
        inside = False
        for w in self.wall_ids(sector):
            a = self.walls[w]
            b = self.walls[int(a["point2"])]
            x0, y0, x1, y1 = int(a["x"]), int(a["y"]), int(b["x"]), int(b["y"])
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        return inside

    def sector_at(self, x: int, y: int) -> int | None:
        hits = [i for i in range(len(self.sectors)) if self.contains(i, x, y)]
        return min(hits, key=self.area) if hits else None


#: Sectors the engine moves on a state (`OperateSector`, triggers.cpp:1680):
#: z-motion, slide and rotate. A room ends at one.
MOVER_TYPES = frozenset({600, 602, 613, 614, 615, 616, 617})


def is_mover(geom: Geometry, sector: int) -> bool:
    """A sector the engine moves: a door, a lift, a leaf.

    A room does not go on through one -- unless the room IS one. E1M1's
    memorial hall is a single slide sector of 180 million square units,
    typed that way for a wall that moves inside it, so the sector a room
    is grown from is always its floor, whatever its type.
    """
    return int(geom.sectors[sector].get("type", 0)) in MOVER_TYPES


def place_of(geom: Geometry, seed: int, avoid: Iterable[int] = ()) -> set[int]:
    """The seed's room: across wide portals, and into the small things in it.

    A room ends at a door and at a neck. Until 2026-11-19 it ended at
    neither: any small sector was taken in whatever the width of the way
    into it AND the room went on from there, so it ran through every door
    leaf and every doorway, and E1M1's whole funeral home -- chapel, halls,
    embalming room, crematorium -- was one "room" of 73 sectors. Now:

    * a sector the engine moves (a door, a lift) is taken in as the room's
      edge and the room does not go on through it;
    * a small sector reached through a narrow way is taken in as a thing
      standing in the room -- a niche, a step, a machine -- and the room
      does not go on from it either. Reached through a wide way it is part
      of the floor, and the room continues.
    """
    # `avoid` is what other rooms have already claimed. Growing through it
    # and subtracting afterwards left a room in pieces joined only through
    # somebody else's floor.
    claimed = set(avoid)
    sky = geom.sky(seed)
    seen, queue = {seed}, [seed]
    while queue:
        here = queue.pop()
        for w in geom.wall_ids(here):
            other = int(geom.walls[w]["next_sector"])
            if other < 0 or other in seen or other in claimed:
                continue
            a, b = geom.sectors[here], geom.sectors[other]
            #: no height in common at rest: a lift shaft, a shut door, a
            #: sealed hole. The room does not go on through it.
            if (min(int(a["floor_z"]), int(b["floor_z"]))
                    <= max(int(a["ceiling_z"]), int(b["ceiling_z"]))):
                continue
            small = geom.area(other) < SMALL
            if geom.sky(other) != sky and not small:
                continue
            wide = geom.length(w) >= WIDE
            if is_mover(geom, other):
                if small or wide:
                    seen.add(other)          # the room's edge, not its floor
                continue
            if wide:
                seen.add(other)
                queue.append(other)
            elif small:
                seen.add(other)              # a thing in the room: a leaf
    return seen


def _fields(extra: Any) -> dict:
    if extra is None:
        return {}
    if isinstance(extra, dict):
        return extra.get("fields", extra)
    return getattr(extra, "fields", {}) or {}


def _moves(extra: Any, sector: dict) -> bool:
    f = _fields(extra)
    if not f:
        return False
    return bool(int(f.get("pan_floor", 0)) or int(f.get("pan_ceiling", 0))
                or int(f.get("amplitude", 0)) or int(f.get("bob_z_range", 0))
                or (int(sector.get("type", 0)) >= 600
                    and int(sector.get("type", 0)) <= 620))


def profile(geom: Geometry, place: Iterable[int]) -> dict[str, Any]:
    place = set(place)
    host = max(place, key=geom.area)
    hs = geom.sectors[host]
    solid: Counter = Counter()
    records, masked = [], 0
    for sector in place:
        for w in geom.wall_ids(sector):
            wall = geom.walls[w]
            length = geom.length(w)
            other = int(wall["next_sector"])
            if other < 0:
                solid[int(wall["picnum"])] += length
                records.append(length)
            elif int(wall["cstat"]) & (16 | 32):
                masked += 1
            elif other in place:
                # a step's face inside the room is wall the room shows
                a, b = geom.sectors[sector], geom.sectors[other]
                rise = abs(int(a["floor_z"]) - int(b["floor_z"]))
                if rise >= 2048 and int(a["floor_z"]) > int(b["floor_z"]):
                    solid[int(wall["picnum"])] += length * min(1.0, rise / 16960)
    total = sum(solid.values()) or 1.0
    shares = sorted(((tile, length / total) for tile, length in solid.items()),
                    key=lambda kv: -kv[1])
    area = sum(geom.area(s) for s in place) or 1.0
    wall_art: Counter = Counter()
    flat_art: Counter = Counter()
    standing: Counter = Counter()
    for sector in place:
        for sprite in geom.by_sector.get(sector, ()):
            if int(sprite.get("status", 0)) != 0 or int(sprite.get("type", 0)) != 0:
                continue
            if int(sprite["cstat"]) & 32768:
                continue
            align = int(sprite["cstat"]) & 48
            target = (wall_art if align == 16 else
                      flat_art if align == 32 else standing)
            target[int(sprite["picnum"])] += 1
    floors = sorted({int(geom.sectors[s]["floor_z"]) for s in place})
    shades = [int(geom.sectors[s]["floor_shade"]) for s in place]
    host_tiles = {int(hs["floor_picnum"]), shares[0][0] if shares else -1}
    machines = 0
    for sector in place:
        if sector == host or geom.area(sector) >= SMALL:
            continue
        s = geom.sectors[sector]
        own = {int(geom.walls[w]["picnum"]) for w in geom.wall_ids(sector)
               if int(geom.walls[w]["next_sector"]) < 0}
        if int(s["floor_z"]) != int(hs["floor_z"]) and (
                int(s["floor_picnum"]) not in host_tiles or own - host_tiles):
            machines += 1
    motion = sum(_moves(geom.extras[s], geom.sectors[s]) for s in place)
    spread = (max(shades) - min(shades)) if shades else 0
    points = [(int(geom.walls[w]["x"]), int(geom.walls[w]["y"]))
              for sector in place for w in geom.wall_ids(sector)]
    spans = (max(x for x, _y in points) - min(x for x, _y in points),
             max(y for _x, y in points) - min(y for _x, y in points))
    #: floor a body can stand on: not the solids standing in the room
    free = sum(geom.area(s) for s in place
               if abs(int(geom.sectors[s]["floor_z"]) - int(hs["floor_z"]))
               <= 4096)
    seconds = [t for t, share in shares[1:] if share >= SECOND]
    trims = [t for t, share in shares[1:] if TRIM <= share < SECOND]
    layers = {
        "second": bool(seconds),
        "trim": bool(trims),
        "wall_art": bool(wall_art),
        "flat_art": bool(flat_art),
        "standing": bool(standing),
        "levels": len(floors) >= LEVELS,
        "masked": masked > 0,
        "light": spread >= SPREAD,
        "motion": motion > 0,
        "machines": machines > 0,
    }
    return {
        "host": host,
        "sectors": len(place),
        "sky": geom.sky(host),
        "area_M": round(area / 1e6, 2),
        "clear_bodies": round((int(hs["floor_z"]) - int(hs["ceiling_z"])) / 16960, 2),
        "short_side": min(spans), "long_side": max(spans),
        "metres": [metres(min(spans)), metres(max(spans)),
                   round((int(hs["floor_z"]) - int(hs["ceiling_z"]))
                         / BODY_Z * 1.8, 1)],
        "free_floor_share": round(free / area, 2),
        "solid_wall": round(total),
        "wall_tiles": [(t, round(share, 3)) for t, share in shares if share >= TRIM],
        "wall_tile_count": len([1 for _t, share in shares if share >= TRIM]),
        "dominant_share": round(shares[0][1], 3) if shares else 0.0,
        "median_record": round(statistics.median(records)) if records else 0,
        "floor_tile": int(hs["floor_picnum"]),
        "ceiling_tile": int(hs["ceiling_picnum"]),
        "wall_art": dict(wall_art.most_common()),
        "wall_art_per_10k": round(sum(wall_art.values()) * 10000 / total, 2),
        "flat_art": dict(flat_art.most_common()),
        "flat_art_per_M": round(sum(flat_art.values()) * 1e6 / area, 2),
        "standing": dict(standing.most_common()),
        "standing_per_M": round(sum(standing.values()) * 1e6 / area, 2),
        "floor_levels": len(floors),
        "shade_spread": spread,
        "masked_walls": masked,
        "moving_sectors": motion,
        "machines": machines,
        "layers": layers,
        "layer_count": sum(layers.values()),
    }


def places(geom: Geometry) -> list[set[int]]:
    """Every room of a map with a core big enough to be a room."""
    taken: set[int] = set()
    out = []
    for sector in sorted(range(len(geom.sectors)), key=geom.area, reverse=True):
        if sector in taken or geom.area(sector) < CORE:
            continue
        place = place_of(geom, sector, taken)
        taken |= place
        out.append(place)
    # What is left is the passages: a corridor is several sectors none of
    # which is a room's worth, and with rooms ending at their doors nothing
    # claims it. Grown the same way, it is a place when all of it together
    # is as big as a room's core.
    for sector in sorted(range(len(geom.sectors)), key=geom.area, reverse=True):
        if sector in taken or is_mover(geom, sector):
            continue
        place = place_of(geom, sector, taken)
        if sum(geom.area(member) for member in place) >= CORE:
            taken |= place
            out.append(place)
    return out


def campaign_maps() -> list[pathlib.Path]:
    from bloodmap.corpus import list_corpus_maps

    return [m.path for m in list_corpus_maps(population="blood-campaign")]


def _size_band(area_m: float) -> str:
    return ("small" if area_m < 8 else "medium" if area_m < 30
            else "large" if area_m < 80 else "hall")


def norms(maps: Iterable[pathlib.Path]) -> dict[str, Any]:
    from bloodmap.format import read_map

    rows = []
    for path in maps:
        try:
            geom = Geometry(read_map(path))
        except Exception:                                   # noqa: BLE001
            continue
        for place in places(geom):
            p = profile(geom, place)
            if p["solid_wall"] < 4096:
                continue
            p["map"] = pathlib.Path(path).stem
            rows.append(p)
    bands: dict[str, Any] = {}
    for sky in (False, True):
        for band in ("small", "medium", "large", "hall"):
            sub = [r for r in rows if r["sky"] == sky
                   and _size_band(r["area_M"]) == band]
            if len(sub) < 8:
                continue
            counts = sorted(r["layer_count"] for r in sub)
            q = lambda f: counts[min(len(counts) - 1, int(f * len(counts)))]
            bands[f"{'outdoor' if sky else 'indoor'}/{band}"] = {
                "n": len(sub),
                "layer_count": {"p25": q(0.25), "p50": q(0.5), "p75": q(0.75)},
                "layer_rate": {name: round(sum(r["layers"][name] for r in sub)
                                           / len(sub), 3) for name in LAYERS},
                "short_side": {"p25": sorted(r["short_side"] for r in sub)[
                    len(sub) // 4], "p50": statistics.median(
                        r["short_side"] for r in sub)},
                "clear_bodies": {"p25": sorted(r["clear_bodies"] for r in sub)[
                    len(sub) // 4], "p50": statistics.median(
                        r["clear_bodies"] for r in sub)},
                "wall_tile_count_p50": statistics.median(
                    r["wall_tile_count"] for r in sub),
                "dominant_share_p50": round(statistics.median(
                    r["dominant_share"] for r in sub), 3),
                "wall_art_per_10k_p75": round(sorted(
                    r["wall_art_per_10k"] for r in sub)[int(0.75 * len(sub))], 2),
            }
    index = [{k: r[k] for k in ("map", "host", "sky", "area_M", "wall_tiles",
                                "floor_tile", "ceiling_tile", "wall_art",
                                "flat_art", "standing", "layer_count",
                                "floor_levels", "shade_spread",
                                "moving_sectors", "machines", "masked_walls")}
             for r in rows]
    return {"$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "places": len(rows), "bands": bands, "index": index}


def load_norms() -> dict[str, Any]:
    return json.loads(NORMS.read_text("utf-8"))


def judge(p: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Where a place sits among Blood's rooms of its size, and what it lacks."""
    key = f"{'outdoor' if p['sky'] else 'indoor'}/{_size_band(p['area_M'])}"
    band = reference["bands"].get(key)
    if band is None:
        return {"band": key, "thin": False, "missing": [], "cramped": []}
    #: a layer most of Blood's rooms of this size carry and this one lacks
    missing = [name for name in LAYERS
               if not p["layers"][name] and band["layer_rate"][name] >= 0.5]
    #: smaller than three quarters of Blood's rooms of this area
    cramped = []
    if "short_side" in band:
        if p["short_side"] < band["short_side"]["p25"]:
            cramped.append(f"short side {p['short_side']} "
                           f"(campaign p25 {band['short_side']['p25']})")
        if p["clear_bodies"] < band["clear_bodies"]["p25"]:
            cramped.append(f"height {p['clear_bodies']} bodies "
                           f"(campaign p25 {band['clear_bodies']['p25']})")
    return {"band": key, "cramped": cramped,
            "campaign_p25": band["layer_count"]["p25"],
            "campaign_p50": band["layer_count"]["p50"],
            "thin": p["layer_count"] < band["layer_count"]["p25"],
            "missing": missing}


def like(p: dict[str, Any], reference: dict[str, Any], count: int = 5) -> list:
    """Blood's rooms that wear this place's palette, richest first."""
    mine = {t for t, _s in p["wall_tiles"]} | {p["floor_tile"], p["ceiling_tile"]}
    scored = []
    for row in reference["index"]:
        theirs = ({t for t, _s in row["wall_tiles"]}
                  | {row["floor_tile"], row["ceiling_tile"]})
        shared = len(mine & theirs)
        if shared >= 2:
            scored.append((shared, row["layer_count"], row))
    scored.sort(key=lambda item: (-item[0], -item[1]))
    return [row for _s, _l, row in scored[:count]]


def names() -> dict[int, str]:
    path = ROOT / "knowledge" / "blood" / "design" / "owner-anchors-v1.json"
    try:
        data = json.loads(path.read_text("utf-8"))
    except OSError:
        return {}
    return {int(a["picnum"]): a.get("label_en", "") for a in data["anchors"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("map", nargs="?")
    parser.add_argument("--at", help="x,y of a point in the place")
    parser.add_argument("--sector", type=int)
    parser.add_argument("--like", type=int, default=0)
    parser.add_argument("--norms", action="store_true")
    parser.add_argument("--all", action="store_true",
                        help="every place of the map, thinnest first")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    if args.norms:
        result = norms(campaign_maps())
        out = pathlib.Path(args.output or NORMS)
        out.write_text(json.dumps(result, indent=1), "utf-8")
        print(f"{result['places']} places -> {out}")
        for key, band in result["bands"].items():
            print(key, band["n"], band["layer_count"])
        return 0
    from bloodmap.format import read_map

    geom = Geometry(read_map(args.map))
    reference = load_norms() if NORMS.exists() else {"bands": {}, "index": []}
    label = names()
    if args.all:
        rows = []
        for place in places(geom):
            p = profile(geom, place)
            if p["solid_wall"] >= 4096:
                rows.append((p, judge(p, reference)))
        rows.sort(key=lambda r: r[0]["layer_count"])
        for p, verdict in rows:
            print(f"s{p['host']:<4} {verdict['band']:<15} layers "
                  f"{p['layer_count']:>2} (p25 {verdict.get('campaign_p25', '-')})"
                  f"{'  THIN' if verdict['thin'] else ''}  lacks "
                  f"{','.join(verdict['missing']) or '-'}")
        return 0
    if args.sector is not None:
        seed = args.sector
    else:
        x, y = (int(v) for v in args.at.split(","))
        seed = geom.sector_at(x, y)
    p = profile(geom, place_of(geom, seed))
    verdict = judge(p, reference)
    print(json.dumps({**p, "verdict": verdict}, indent=1))
    for row in like(p, reference, args.like):
        tiles = ", ".join(f"{t} {label.get(t, '?')} {share:.0%}"
                          for t, share in row["wall_tiles"])
        print(f"\n{row['map']} s{row['host']}  layers {row['layer_count']}"
              f"\n  walls: {tiles}"
              f"\n  wall art: {row['wall_art']}\n  flat art: {row['flat_art']}"
              f"\n  standing: {row['standing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
