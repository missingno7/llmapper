"""One street profile for any Build map, in units a body understands.

Tile numbers do not cross from Duke Nukem 3D to Blood, and neither do raw
coordinates: Blood is built at 3:2 of Duke (`conversion.GAME_PROFILES`,
measured on the hand-converted E3L1 pair) and its shade table has twice the
steps. What does cross is **structure, stated in bodies**: how tall a kerb is
against the player, how much of a street is pavement, whether glass shares a
wall with a facade, what stands at the end of a street, how many different
heights a street's walls reach, how bright a road is.

So every number here is either a count, a share, or a length divided by the
game's own standing height (z) or by that height over sixteen (xy, the
engine's 16:1). A Duke map and a Blood map then answer the same question in
the same unit, and a row of this table is a question a Blood author can act
on without ever naming a Duke tile.

Kinds of statement, kept apart in the output:

* ``native``   read straight off map fields (a count, a z difference);
* ``derived``  computed from them with a stated threshold;
* nothing here is an interpretation. What a frame LOOKS like is
  `tools/duke_view.py`'s business and a reviewer's.

.. code-block:: bash

    python -m tools.city_profile maps/duke3d/DukCity1.map \\
        maps/blood/campaign/E3M1.MAP projects/blood-city/level/blood-city-current.MAP
    python -m tools.city_profile --json work/profile.json <maps...>
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: A standing body, in each game's z. Blood's is measured
#: (`blood-player-body`); Duke's is Blood's at the 3:2 the E3L1 pair gives.
BODY_Z = {"blood": 16960, "duke3d": 16960 * 2 / 3}
#: Blood's shade table has twice Duke's steps (`conversion.convert_shade`).
SHADE_SCALE = {"blood": 1, "duke3d": 2}
#: Duke's editor-only marker tiles (DEFS.CON 1..10).
DUKE_MARKERS = frozenset(range(1, 11))

#: A step this low is a kerb; up to a body it is a step or a plinth; above
#: that it is a wall or a mass. Thresholds, stated so they can be argued with.
KERB_MAX = 0.30
STEP_MAX = 1.0
#: A pocket this shallow in front of an opening is a reveal or a porch.
POCKET_MAX = 1.5


def load(path: pathlib.Path) -> tuple[str, Any]:
    """(game, disk). Duke first: its header is a plain version 7."""
    from bloodmap.duke import DukeMapError, read_duke_map
    from bloodmap.format import read_map

    try:
        return "duke3d", read_duke_map(path)
    except (DukeMapError, Exception):
        return "blood", read_map(path)


def _weighted_median(pairs) -> float | None:
    pairs = sorted((v, w) for v, w in pairs if w > 0)
    total = sum(w for _v, w in pairs)
    if not total:
        return None
    acc = 0.0
    for value, weight in pairs:
        acc += weight
        if acc >= total / 2:
            return value
    return pairs[-1][0]


def profile(disk: Any, game: str) -> dict[str, Any]:
    body_z = BODY_Z[game]
    body_xy = body_z / 16.0
    shade_k = SHADE_SCALE[game]
    S = [s.fields for s in disk.sectors]
    W = [w.fields for w in disk.walls]

    owner = {}
    for index, s in enumerate(S):
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            owner[w] = index

    def length(w: int) -> float:
        a, b = W[w], W[int(W[w]["point2"])]
        return ((int(b["x"]) - int(a["x"])) ** 2
                + (int(b["y"]) - int(a["y"])) ** 2) ** 0.5

    def area(index: int) -> float:
        s = S[index]
        total = 0
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            a, b = W[w], W[int(W[w]["point2"])]
            total += int(a["x"]) * int(b["y"]) - int(b["x"]) * int(a["y"])
        return abs(total) / 2.0

    open_ = {i for i, s in enumerate(S) if int(s["ceiling_stat"]) & 1}
    backing = {i for i in open_ if int(S[i]["floor_z"]) == int(S[i]["ceiling_z"])}
    street = open_ - backing
    out: dict[str, Any] = {"game": game, "body_z": body_z}
    open_area = sum(area(i) for i in street)
    out["native"] = {
        "sectors": len(S), "walls": len(W), "sprites": len(disk.sprites),
        "open_sky_sectors": len(street), "sky_backings": len(backing),
    }
    if not street:
        out["derived"] = {"note": "no open-sky sector"}
        return out

    # ---- what a street's walls reach ---------------------------------------
    faces = collections.Counter()          # one-sided, floor to sky, by half-body
    face_len = 0.0
    seg = []
    face_shade = []
    tiles = collections.Counter()
    steps = {"kerb": [], "step": [], "mass": []}
    step_len = collections.Counter()
    kerb_pairs = collections.Counter()
    doors = []                              # open -> roofed
    pockets = 0
    perimeter = 0.0
    for w, f in enumerate(W):
        here = owner.get(w)
        if here not in street:
            continue
        L = length(w)
        perimeter += L
        seg.append(L / body_xy)
        nxt = int(f["next_sector"])
        s = S[here]
        if nxt < 0:
            h = (int(s["floor_z"]) - int(s["ceiling_z"])) / body_z
            faces[round(h * 2) / 2] += L
            face_len += L
            face_shade.append((int(f["shade"]) * shade_k, L))
            tiles[int(f["picnum"])] += L
            continue
        t = S[nxt]
        if nxt in street:
            rise = (int(s["floor_z"]) - int(t["floor_z"])) / body_z
            if rise > 0.01:                 # looking up at something raised
                kind = ("kerb" if rise <= KERB_MAX else
                        "step" if rise <= STEP_MAX else "mass")
                steps[kind].append((rise, L))
                step_len[kind] += L
                if kind == "kerb":
                    kerb_pairs[(int(t["floor_picnum"]), int(s["floor_picnum"]))] += L
                if kind == "mass":
                    faces[round(rise * 2) / 2] += L
                    face_len += L
                    face_shade.append((int(f["shade"]) * shade_k, L))
        elif nxt not in backing:
            head = (int(s["floor_z"]) - int(t["ceiling_z"])) / body_z
            sill = (int(s["floor_z"]) - int(t["floor_z"])) / body_z
            xs, ys = [], []
            for k in range(int(t["wall_ptr"]), int(t["wall_ptr"]) + int(t["wall_count"])):
                xs.append(int(W[k]["x"]))
                ys.append(int(W[k]["y"]))
            short = min(max(xs) - min(xs), max(ys) - min(ys)) / body_xy
            pocket = int(t["wall_count"]) <= 8 and short <= POCKET_MAX
            pockets += pocket
            doors.append({"width": L / body_xy, "head": head, "sill": sill,
                          "pocket": pocket,
                          "masked": bool(int(f["cstat"]) & 16)})

    total_faces = sum(faces.values()) or 1.0
    modal = faces.most_common(1)[0] if faces else (0, 0)
    heights = sorted(h for h, L in faces.items() if L / total_faces >= 0.02)

    def step_summary(kind):
        rows = steps[kind]
        return {"walls": len(rows),
                "length_bodies": round(step_len[kind] / body_xy, 1),
                "rise_bodies_median": (round(_weighted_median(rows), 3)
                                       if rows else None)}

    # ---- the ground --------------------------------------------------------
    floor_area = collections.Counter()
    floor_shade = []
    for i in street:
        a = area(i)
        floor_area[int(S[i]["floor_picnum"])] += a
        floor_shade.append((int(S[i]["floor_shade"]) * shade_k, a))
    ground_tiles = [(t, round(a / open_area, 3)) for t, a in
                    floor_area.most_common() if a / open_area >= 0.02]
    floors = sorted({int(S[i]["floor_z"]) for i in street})
    skies = sorted({int(S[i]["ceiling_z"]) for i in street})

    # ---- glass -------------------------------------------------------------
    glass = banded = on_street = 0
    for w, f in enumerate(W):
        if not int(f["cstat"]) & 16 or int(f["next_sector"]) < 0:
            continue
        if not int(f.get("over_picnum", 0)) > 0:
            continue
        here = owner.get(w)
        if here is None:
            continue
        a, b = S[here], S[int(f["next_sector"])]
        glass += 1
        banded += (int(a["floor_z"]) != int(b["floor_z"])
                   or int(a["ceiling_z"]) != int(b["ceiling_z"]))
        on_street += (here in street or int(f["next_sector"]) in street)

    # ---- things standing outdoors -----------------------------------------
    align = collections.Counter()
    sprite_tiles = collections.Counter()
    for sprite in disk.sprites:
        f = sprite.fields
        if int(f["sector"]) not in street or int(f["cstat"]) & 0x8000:
            continue
        if game == "duke3d" and int(f["picnum"]) in DUKE_MARKERS:
            continue
        if game == "blood" and (int(f.get("statnum", f.get("status", 0))) not in (0,)
                                or int(f.get("type", 0)) not in (0, 30, 32)):
            continue
        kind = {0: "face", 16: "wall", 32: "floor"}.get(int(f["cstat"]) & 48,
                                                        "other")
        align[kind] += 1
        sprite_tiles[int(f["picnum"])] += 1
    area_bodies = open_area / (body_xy * body_xy)

    out["derived"] = {
        "open_area_bodies2": round(area_bodies),
        "street_wall": {
            "length_bodies": round(face_len / body_xy),
            "heights_bodies_over_2pct": heights,
            "distinct_heights": len(heights),
            "modal_height_bodies": modal[0],
            "share_at_modal_height": round(modal[1] / total_faces, 3),
            "shade_median": _weighted_median(face_shade),
            "tiles_over_1pct": sum(1 for _t, L in tiles.items()
                                   if L / (sum(tiles.values()) or 1) >= 0.01),
            "segment_bodies_median": round(statistics.median(seg), 2),
        },
        "ground": {
            "tiles_over_2pct_of_area": ground_tiles,
            "distinct_floor_heights": len(floors),
            "distinct_sky_heights": len(skies),
            "shade_median": _weighted_median(floor_shade),
            "kerb": step_summary("kerb"),
            "step": step_summary("step"),
            "mass": step_summary("mass"),
            "kerb_per_100_bodies_of_street_wall": round(
                100 * step_len["kerb"] / (face_len or 1), 1),
            "kerb_floor_pairs_upper_lower": [
                [list(pair), round(L / body_xy, 1)]
                for pair, L in kerb_pairs.most_common(4)],
        },
        "openings_off_the_street": {
            "count": len(doors),
            "per_100_bodies_of_street_wall": round(
                100 * len(doors) / ((face_len / body_xy) or 1), 2),
            "width_bodies_median": (round(statistics.median(
                d["width"] for d in doors), 2) if doors else None),
            "head_bodies_median": (round(statistics.median(
                d["head"] for d in doors), 2) if doors else None),
            "with_a_sill_share": (round(sum(d["sill"] > 0.05 for d in doors)
                                        / len(doors), 3) if doors else None),
            "into_a_pocket_share": (round(pockets / len(doors), 3)
                                    if doors else None),
            "masked_share": (round(sum(d["masked"] for d in doors) / len(doors),
                                   3) if doors else None),
        },
        "glass": {
            "masked_two_sided_walls": glass,
            "sharing_a_record_with_a_step_band_share": (
                round(banded / glass, 3) if glass else None),
            "on_a_street_record_share": (
                round(on_street / glass, 3) if glass else None),
        },
        "standing_outdoors": {
            "sprites": sum(align.values()),
            "per_1000_bodies2": round(1000 * sum(align.values())
                                      / (area_bodies or 1), 2),
            "by_alignment": dict(align),
            "commonest_tiles": sprite_tiles.most_common(10),
        },
    }
    return out


#: An interior smaller than this many square bodies is a cupboard, a porch
#: or a display, and would make every map's median "one room".
INTERIOR_MIN_BODIES2 = 20


def interiors(disk: Any, game: str) -> dict[str, Any]:
    """How much is going on INSIDE: one row per map, medians per interior.

    An interior is a connected group of roofed sectors at least half a body
    tall. The owner asked for "more complex interiors" (2026-11-17), and
    complex has to mean something a build can be held to: how many floor and
    ceiling heights one interior holds, over what range, in how many
    materials, and how far apart its darkest and brightest floors are.
    """
    body_z = BODY_Z[game]
    body_xy = body_z / 16.0
    shade_k = SHADE_SCALE[game]
    S = [s.fields for s in disk.sectors]
    W = [w.fields for w in disk.walls]

    def area(index: int) -> float:
        s = S[index]
        total = 0
        for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
            a, b = W[w], W[int(W[w]["point2"])]
            total += int(a["x"]) * int(b["y"]) - int(b["x"]) * int(a["y"])
        return abs(total) / 2.0 / (body_xy * body_xy)

    roofed = {i for i, s in enumerate(S)
              if not int(s["ceiling_stat"]) & 1
              and int(s["floor_z"]) - int(s["ceiling_z"]) > 0.5 * body_z}
    seen: set[int] = set()
    groups = []
    for start in sorted(roofed):
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            index = stack.pop()
            group.append(index)
            s = S[index]
            for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
                nxt = int(W[w]["next_sector"])
                if nxt in roofed and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        groups.append(group)
    big = [g for g in groups if sum(area(i) for i in g) >= INTERIOR_MIN_BODIES2]

    def med(values):
        values = list(values)
        return round(statistics.median(values), 2) if values else None

    def walls_of(group):
        for i in group:
            s = S[i]
            for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
                yield W[w]

    sloped = sum(1 for g in big for i in g
                 if (int(S[i]["floor_stat"]) & 2 and int(S[i]["floor_heinum"]))
                 or (int(S[i]["ceiling_stat"]) & 2 and int(S[i]["ceiling_heinum"])))
    total = sum(len(g) for g in big) or 1
    return {
        "interiors": len(big),
        "sectors": med(len(g) for g in big),
        "floor_heights": med(len({int(S[i]["floor_z"]) for i in g}) for g in big),
        "ceiling_heights": med(len({int(S[i]["ceiling_z"]) for i in g}) for g in big),
        "floor_range_bodies": med(
            (max(int(S[i]["floor_z"]) for i in g)
             - min(int(S[i]["floor_z"]) for i in g)) / body_z for g in big),
        "floor_tiles": med(len({int(S[i]["floor_picnum"]) for i in g}) for g in big),
        "wall_tiles": med(len({int(w["picnum"]) for w in walls_of(g)}) for g in big),
        "floor_shade_spread": med(
            (max(int(S[i]["floor_shade"]) for i in g)
             - min(int(S[i]["floor_shade"]) for i in g)) * shade_k for g in big),
        "sloped_sector_share": round(sloped / total, 3),
        "barred_or_glazed_walls": sum(
            1 for g in big for w in walls_of(g)
            if int(w["cstat"]) & 16 and int(w["next_sector"]) >= 0),
    }


INTERIOR_ROWS = [
    ("interiors of 20 bodies2 or more", "interiors"),
    ("sectors per interior", "sectors"),
    ("floor heights per interior", "floor_heights"),
    ("ceiling heights per interior", "ceiling_heights"),
    ("floor range, bodies", "floor_range_bodies"),
    ("floor tiles per interior", "floor_tiles"),
    ("wall tiles per interior", "wall_tiles"),
    ("floor shade spread (Blood scale)", "floor_shade_spread"),
    ("sloped sectors, share", "sloped_sector_share"),
    ("barred or glazed walls indoors", "barred_or_glazed_walls"),
]


def interior_table(found: dict[str, dict]) -> str:
    names = list(found)
    lines = ["| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, key in INTERIOR_ROWS:
        lines.append(f"| {label} | " + " | ".join(
            "-" if found[n].get(key) is None else str(found[n][key])
            for n in names) + " |")
    return "\n".join(lines)


ROWS = [
    ("open-sky sectors", lambda p: p["native"]["open_sky_sectors"]),
    ("sky backings (no height)", lambda p: p["native"]["sky_backings"]),
    ("street wall: distinct heights", lambda p: p["derived"]["street_wall"]["distinct_heights"]),
    ("street wall: modal height, bodies", lambda p: p["derived"]["street_wall"]["modal_height_bodies"]),
    ("street wall: share at that height", lambda p: p["derived"]["street_wall"]["share_at_modal_height"]),
    ("street wall: tiles over 1% of length", lambda p: p["derived"]["street_wall"]["tiles_over_1pct"]),
    ("street wall: median segment, bodies", lambda p: p["derived"]["street_wall"]["segment_bodies_median"]),
    ("street wall: median shade (Blood scale)", lambda p: p["derived"]["street_wall"]["shade_median"]),
    ("ground: median shade (Blood scale)", lambda p: p["derived"]["ground"]["shade_median"]),
    ("ground: floor tiles over 2% of area", lambda p: len(p["derived"]["ground"]["tiles_over_2pct_of_area"])),
    ("ground: distinct floor heights", lambda p: p["derived"]["ground"]["distinct_floor_heights"]),
    ("kerb: rise, bodies", lambda p: p["derived"]["ground"]["kerb"]["rise_bodies_median"]),
    ("kerb: length per 100 of street wall", lambda p: p["derived"]["ground"]["kerb_per_100_bodies_of_street_wall"]),
    ("steps 0.3-1 body: walls", lambda p: p["derived"]["ground"]["step"]["walls"]),
    ("masses over 1 body: walls", lambda p: p["derived"]["ground"]["mass"]["walls"]),
    ("openings per 100 bodies of street wall", lambda p: p["derived"]["openings_off_the_street"]["per_100_bodies_of_street_wall"]),
    ("opening: median width, bodies", lambda p: p["derived"]["openings_off_the_street"]["width_bodies_median"]),
    ("opening: median head, bodies", lambda p: p["derived"]["openings_off_the_street"]["head_bodies_median"]),
    ("openings into a pocket, share", lambda p: p["derived"]["openings_off_the_street"]["into_a_pocket_share"]),
    ("openings with a sill, share", lambda p: p["derived"]["openings_off_the_street"]["with_a_sill_share"]),
    ("glass walls", lambda p: p["derived"]["glass"]["masked_two_sided_walls"]),
    ("glass sharing a record with a band", lambda p: p["derived"]["glass"]["sharing_a_record_with_a_step_band_share"]),
    ("glass on a street record", lambda p: p["derived"]["glass"]["on_a_street_record_share"]),
    ("sprites outdoors per 1000 bodies2", lambda p: p["derived"]["standing_outdoors"]["per_1000_bodies2"]),
]


def table(profiles: dict[str, dict]) -> str:
    names = list(profiles)
    lines = ["| | " + " | ".join(names) + " |",
             "|---|" + "---|" * len(names)]
    for label, pick in ROWS:
        cells = []
        for name in names:
            try:
                value = pick(profiles[name])
            except (KeyError, TypeError):
                value = None
            cells.append("-" if value is None else str(value))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="+")
    parser.add_argument("--json", default=None)
    parser.add_argument("--interiors", action="store_true",
                        help="the interior table instead of the street one")
    args = parser.parse_args(argv)
    profiles = {}
    for text in args.maps:
        path = pathlib.Path(text)
        game, disk = load(path)
        profiles[path.stem] = (interiors(disk, game) if args.interiors
                               else profile(disk, game))
    print(interior_table(profiles) if args.interiors else table(profiles))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(profiles, indent=2), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
