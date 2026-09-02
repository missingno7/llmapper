"""Slice 2: the whole street network on the ground-plane model, no masses.

Every edge of `city_plan.EDGES` as a ground plane at its class width, every
solved cell as a pavement island standing 2048 on it, junction squares where
roads cross, kerbs on the road-side records, end walls where a road stops, and
one sun cutting the shadows of placeholder masses at the solved envelopes'
heights -- so slice 3 replaces masses, not shadows.

It writes `slice2-streets.MAP` and leaves `blood-city-current.MAP` alone.

The node grid is the SOLVED one, not the plan's running sums: `city_solve`
sizes each column and row from the envelopes standing in it and each gutter
from its class minimum, and the nodes are read off that. So the streets land
where the buildings need them rather than where a norm put them.
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import city_plan as plan                                          # noqa: E402
from bloodmap.format import write_map                             # noqa: E402
from bloodmap.planar_layout import PlanarLayout                   # noqa: E402
from bloodmap.street import end_wall, termination_faults          # noqa: E402
from city_solve import Cell, Envelope, Gutter, solve_axis         # noqa: E402
from resolution import (                                          # noqa: E402
    GRADE, SUN_BEARING_DEGREES, SUN_BEARING_TOLERANCE_DEGREES, WIDTH_UNITS)
from street_build import (                                        # noqa: E402
    ISLAND_Z, PAVE_TILE, ROAD_TILE, ROAD_Z, STANDING, Island, Mass, Road,
    centroid, emit)

BAND = 2048
#: E3M1's pavement-only path between abutting houses (s10/s11).
PATH = 512


def _env(venue_id):
    spec = dict(plan.ENVELOPES[venue_id])
    spec.pop("source", None)
    return Envelope(venue_id, tuple(spec["interior"]),
                    faced=tuple(spec.get("faced", ("south",))))


#: The solved axes. Cells carry the envelopes that stand in them; gutters are
#: the corridors between, at class minimum.
X_ORDER = [Gutter("lane_west", "lane"),
           Cell("col_a", (_env("aldermack"), _env("saloon"),
                          _env("shooting_parlor"))),
           Gutter("west_street", "street"),
           Cell("col_b", (_env("market_hall"), _env("ferry_office"))),
           Gutter("avenue", "avenue"),
           Cell("col_c", (_env("church"), _env("arcade"), _env("pawn_shop"))),
           Gutter("spur", "street")]
Y_ORDER = [Gutter("lane_north", "lane"),
           Cell("row_1", (_env("aldermack"), _env("church"))),
           Gutter("theatre_row", "row"),
           Cell("row_2", (_env("arcade"), _env("market_hall"))),
           Gutter("market_street", "street"),
           Cell("row_3", (_env("works_canteen"), _env("workshop_bar"))),
           Gutter("quay", "row")]


def build():
    x = solve_axis("x", X_ORDER, WIDTH_UNITS)
    y = solve_axis("y", Y_ORDER, WIDTH_UNITS)
    layout = PlanarLayout(name="slice2-streets")

    #: --- roads: one ground plane per gutter, full width of the city -------
    roads = []
    for name, lo, hi in x.spans:
        if name in x.demanded:
            continue
        roads.append(Road(f"x:{name}", (lo, 0, hi, y.total),
                          width_class=_class(X_ORDER, name)))
    for name, lo, hi in y.spans:
        if name in y.demanded:
            continue
        roads.append(Road(f"y:{name}", (0, lo, x.total, hi),
                          width_class=_class(Y_ORDER, name)))

    #: --- islands: one per solved cell, the whole block between corridors --
    islands = []
    masses = []
    for x_name, x0, x1 in x.spans:
        if x_name not in x.demanded:
            continue
        for y_name, y0, y1 in y.spans:
            if y_name not in y.demanded:
                continue
            island_id = f"{x_name}/{y_name}"
            islands.append(Island(island_id, (x0, y0, x1, y1), band=BAND))
            #: A PLACEHOLDER mass at the cell's own demand, inset by the band,
            #: so its shadow is the shadow slice 3's real mass will cast. The
            #: height is the envelope's, which is what makes this a stand-in
            #: rather than a guess.
            mx0, my0 = x0 + BAND, y0 + BAND
            mx1, my1 = min(x1 - BAND, mx0 + x.demanded[x_name]), \
                min(y1 - BAND, my0 + y.demanded[y_name])
            if mx1 - mx0 >= 2048 and my1 - my0 >= 2048:
                masses.append(Mass(f"mass:{island_id}", (mx0, my0, mx1, my1),
                                   height=4 * STANDING, island=island_id))

    built = emit(layout, roads, islands, masses)

    #: --- end walls: every road that stops at the edge of the city ---------
    ends = []
    for road in roads:
        rx0, ry0, rx1, ry1 = road.rect
        vertical = (rx1 - rx0) < (ry1 - ry0)
        for at_start in (True, False):
            if vertical:
                cap = (rx0, ry0 - PATH, rx1, ry0) if at_start else \
                    (rx0, ry1, rx1, ry1 + PATH)
            else:
                cap = (rx0 - PATH, ry0, rx0, ry1) if at_start else \
                    (rx1, ry0, rx1 + PATH, ry1)
            ends.append(end_wall(
                [(cap[0], cap[1]), (cap[2], cap[1]),
                 (cap[2], cap[3]), (cap[0], cap[3])],
                road_floor_z=ROAD_Z, standing_height=STANDING,
                facade_tile=road.facade_tile,
                name=f"end:{road.road_id}:{'a' if at_start else 'b'}"))
    built.ends = ends

    road_piece, road_poly = next((n, p) for n, p, _s, kind, _sid in built.pieces
                                 if kind == "road")
    spot = centroid(road_poly)
    layout.set_player_start(road_piece, x=int(spot[0]), y=int(spot[1]),
                            z=ROAD_Z, angle=512)
    return layout, built, x, y


def _class(order, name):
    for item in order:
        if isinstance(item, Gutter) and item.gutter_id == name:
            return item.width_class
    return "street"


def main() -> int:
    layout, built, x, y = build()
    print(f"solved grid: {x.total} x {y.total}")
    print(f"roads {len({p[4] for p in built.pieces if p[3] == 'road'})} "
          f"islands {len({p[4] for p in built.pieces if p[3] == 'island'})} "
          f"pieces {len(built.pieces)} kerbs {len(built.kerbs)} "
          f"junctions {len(built.junctions)} shadow edges "
          f"{len(built.shadow_edges)} lamps {built.lamps} "
          f"ends {len(built.ends)}")

    compiled = layout.compile()

    from bloodmap.texture_align import wall_art_sizes
    from bloodmap.texture_frame import frame_map

    art = wall_art_sizes("reference/blood")
    if art:
        print("texture frames:", {
            k: v for k, v in frame_map(compiled.level, art_sizes=art).items()
            if k != "basis"})

    disk = compiled.level.to_disk_map()
    faults = _gates(disk, built, x, y)
    out = HERE / "slice2-streets.MAP"
    if faults:
        print(f"FAIL: {len(faults)} gate fault(s); the map was not written")
        for line in faults[:12]:
            print("   ", line)
        return 1
    write_map(disk, out)
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} walls, "
          f"{len(disk.sprites)} sprites")
    _limits(disk)
    return 0


def _gates(disk, built, x, y):
    from bloodmap.street_model import (
        kerb_faults, sees_the_kerb, shadow_edge_faults)
    from bloodmap.texture_align import wall_art_sizes
    from bloodmap.texture_frame import (
        auto_align_walls, run_partition, sector_index)

    owners = sector_index(disk)
    out = []
    out += kerb_faults(disk, built.kerbs, owners=owners)
    print(f"kerb gate: {len(built.kerbs)} declared, {len(out)} fault(s)")

    shadow = shadow_edge_faults(disk, built.shadow_edges, SUN_BEARING_DEGREES,
                                SUN_BEARING_TOLERANCE_DEGREES)
    print(f"sun gate: {len(built.shadow_edges)} edges, {len(shadow)} off")
    out += shadow

    ends = termination_faults(disk, built.ends, standing_height=STANDING)
    print(f"termination gate: {len(built.ends)} declared, {len(ends)} fault(s)")
    out += ends

    art = wall_art_sizes("reference/blood")
    moved = 0
    if art:
        keys = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")
        for run in run_partition(disk, art_sizes=art, owners=owners):
            before = {w: {k: int(disk.walls[w].fields[k]) for k in keys}
                      for w in run}
            auto_align_walls(disk, run[0], flags=0x01, art_sizes=art,
                             owners=owners)
            moved += sum(1 for w in run
                         if any(int(disk.walls[w].fields[k]) != before[w][k]
                                for k in keys))
    print(f"frame gate: the editor would change {moved} wall(s)")
    if moved:
        out.append(f"{moved} walls are not a fixed point of the editor's align")

    roads = [i for i, s in enumerate(disk.sectors)
             if int(s.fields["floor_picnum"]) == ROAD_TILE]
    tiles = set()
    for sector_id in roads:
        tiles.update(sees_the_kerb(disk, sector_id, owners)["kerb_tiles"])
    print(f"sightline gate: from {len(roads)} road pieces a body sees "
          f"{sorted(tiles)}")
    if tiles - {6}:
        out.append(f"a body on the road sees {sorted(tiles - {6})}, not a kerb")

    widths = {name: WIDTH_UNITS[_class(X_ORDER + Y_ORDER, name)]
              for name in list(x.demanded) + list(y.demanded)}
    for name, lo, hi in x.spans + y.spans:
        if name in x.demanded or name in y.demanded:
            continue
        want = WIDTH_UNITS.get(_class(X_ORDER + Y_ORDER, name))
        if want and hi - lo < want:
            out.append(f"{name} is {hi - lo}, under its class minimum {want}")
    print("width gate: every corridor at or above its class minimum")

    from bloodmap import rules_blood                              # noqa: F401
    from bloodmap.rules import RULES

    if art:
        magnitude = RULES["material-is-drawn-at-campaign-size"].check(disk)
        print(f"magnitude gate: {len(magnitude.violations)} violation(s)")
        out += [f"{v.location}: {v.detail}" for v in magnitude.violations]
    return out


def _limits(disk):
    import json

    budget = json.load(open(ROOT / "projects/blood-city/project.json"))["budget"]
    counts = {
        "sectors": len(disk.sectors), "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "xsectors": sum(1 for s in disk.sectors if s.extra is not None),
        "xwalls": sum(1 for w in disk.walls if w.extra is not None),
        "xsprites": sum(1 for s in disk.sprites if s.extra is not None)}
    print("limits: " + "  ".join(
        f"{k} {v}/{budget[k + '_limit']} ({100 * v // budget[k + '_limit']}%)"
        for k, v in counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
