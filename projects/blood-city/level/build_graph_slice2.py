"""Slice 2 deliverable 6: the whole street graph, on the ground-plane model.

The street network is ONE region per connected network -- a lattice, concave,
with the islands as the space it does not cover. Junctions are the parts of
that plane no island covers and have no exits of their own to declare. The
light field cuts the plane and its islands; the join table decides every
shared record; the channel ledger owns every shade.

Writes `slice2-streets.MAP` and leaves `blood-city-current.MAP` alone.
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
from bloodmap import joins                                        # noqa: E402
from bloodmap.channels import Compilation, RegionLedger           # noqa: E402
from bloodmap.format import write_map                             # noqa: E402
from bloodmap.light_field import Mass, build_field                # noqa: E402
from bloodmap.lightbomb import apply_shade_channel                # noqa: E402
from bloodmap.overlay import (                                    # noqa: E402
    ground_plane_rings, partition_faults, region_area)
from bloodmap.planar_layout import PlanarLayout                   # noqa: E402
from city_solve import Cell, Envelope, Gutter, solve_axis         # noqa: E402
from resolution import (                                          # noqa: E402
    GRADE, SKY_TILE, STREET_SKY, SUN_BEARING, WIDTH_UNITS)

ROAD_TILE, PAVE_TILE, KERB_TILE = 352, 4, 6
RISE = 2048
ROAD_Z = GRADE + RISE
ISLAND_Z = GRADE
BAND = 2048
BASE_SHADE = 8
STEP = 12


def _env(venue_id):
    spec = dict(plan.ENVELOPES[venue_id])
    spec.pop("source", None)
    return Envelope(venue_id, tuple(spec["interior"]),
                    faced=tuple(spec.get("faced", ("south",))))


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


def centroid(ring):
    return (sum(p[0] for p in ring) // len(ring),
            sum(p[1] for p in ring) // len(ring))


def build():
    run = Compilation()
    x = solve_axis("x", X_ORDER, WIDTH_UNITS)
    y = solve_axis("y", Y_ORDER, WIDTH_UNITS)
    layout = PlanarLayout(name="slice2-streets")
    report = {"solved": (x.total, y.total)}

    # --- 1. planes and islands -------------------------------------------
    run.enter("planes")
    strips = []
    for name, lo, hi in x.spans:
        if name not in x.demanded:
            strips.append((lo, 0, hi, y.total))
    for name, lo, hi in y.spans:
        if name not in y.demanded:
            strips.append((0, lo, x.total, hi))
    #: The plane is a polygon WITH HOLES: a street grid encloses its blocks,
    #: and the islands stand in those holes.
    plane = ground_plane_rings(strips)
    report["plane_rings"] = [len(ring) for ring in plane]

    islands = {}
    masses = []
    for x_name, x0, x1 in x.spans:
        if x_name not in x.demanded:
            continue
        for y_name, y0, y1 in y.spans:
            if y_name not in y.demanded:
                continue
            key = f"{x_name}/{y_name}"
            islands[key] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            mx0, my0 = x0 + BAND, y0 + BAND
            mx1 = min(x1 - BAND, mx0 + x.demanded[x_name])
            my1 = min(y1 - BAND, my0 + y.demanded[y_name])
            if mx1 - mx0 >= 2048 and my1 - my0 >= 2048:
                masses.append(Mass(f"mass:{key}",
                                   ((mx0, my0), (mx1, my0), (mx1, my1),
                                    (mx0, my1)), 4 * 16960))
    report["islands"] = len(islands)
    report["masses"] = len(masses)

    # --- 2. declare (nothing yet: no mechanisms in this slice) ------------
    run.enter("declare")

    # --- 3. the light field on its domain --------------------------------
    run.enter("light")
    surfaces = {"plane": (plane, ROAD_Z, ROAD_TILE, KERB_TILE)}
    for key, ring in islands.items():
        surfaces[key] = ([ring], ISLAND_Z, PAVE_TILE, PAVE_TILE)

    ledger = RegionLedger()
    pieces = []
    absorbed = 0
    for surface_id, (rings, floor_z, floor_tile, wall_tile) in \
            sorted(surfaces.items()):
        field = build_field(rings, masses, bearing_units=SUN_BEARING)
        absorbed += len(field["absorbed"])
        #: POST-CONDITION, per surface, before anything is added: the field's
        #: pieces must partition the surface it cut. Area alone is not that
        #: -- it is satisfied by a set that double-counts one region and loses
        #: another of the same size.
        faults = partition_faults([p.rings for p in field["pieces"]], rings)
        if faults:
            report.setdefault("partition_faults", []).append(
                {"surface": surface_id, "faults": faults,
                 "pieces": [[list(map(list, ring)) for ring in p.rings]
                            for p in field["pieces"]],
                 "rings": [list(map(list, ring)) for ring in rings],
                 "masses": [{"id": m.mass_id,
                             "outline": list(map(list, m.outline)),
                             "height": m.height} for m in masses]})
        for index, piece in enumerate(field["pieces"]):
            name = (surface_id if len(field["pieces"]) == 1
                    else f"{surface_id}#{index}")
            layout.add_region(name, piece.rings[0], holes=piece.rings[1:],
                              floor_z=floor_z, ceiling_z=floor_z - STREET_SKY,
                              floor_picnum=floor_tile, ceiling_picnum=SKY_TILE,
                              wall_picnum=wall_tile, floor_shade=BASE_SHADE,
                              parallax_ceiling=True, role="street")
            pieces.append((name, piece, surface_id, floor_z))
    report["pieces"] = len(pieces)
    report["slivers_absorbed"] = absorbed
    report["levels"] = sorted({p.depth for _n, p, _s, _z in pieces})

    # --- pair every piece that shares a wall ------------------------------
    paired = 0
    for index, (a_name, a_piece, _a_sid, _az) in enumerate(pieces):
        for b_name, b_piece, _b_sid, _bz in pieces[index + 1:]:
            for number, edge in enumerate(_shared(a_piece.rings,
                                                  b_piece.rings)):
                layout.add_connection(
                    f"join:{a_name}:{b_name}:{number}", a_name, b_name,
                    role="portal", a1=edge[0], a2=edge[1])
                paired += 1
    report["joins_declared"] = paired

    start = next(name for name, piece, sid, _z in pieces if sid == "plane")
    spot = centroid(layout.regions[start].outer)
    layout.set_player_start(start, x=int(spot[0]), y=int(spot[1]),
                            z=ROAD_Z, angle=0)
    return layout, run, ledger, pieces, report, x, y


def _shared(a_rings, b_rings):
    """EVERY segment the two pieces share, not the first.

    After the weld two pieces routinely share several segments -- a chord that
    a later cut split, an island edge broken by a shadow crossing -- and
    declaring only one leaves the rest as coincident walls nobody paired,
    which `PlanarLayout` reports as unexplained unpaired portal candidates.
    """
    out = []
    for a in a_rings:
        for index, point in enumerate(a):
            nxt = a[(index + 1) % len(a)]
            for b in b_rings:
                for other, start in enumerate(b):
                    end = b[(other + 1) % len(b)]
                    if {tuple(point), tuple(nxt)} == {tuple(start),
                                                      tuple(end)}:
                        out.append((tuple(point), tuple(nxt)))
    return out


def main() -> int:
    layout, run, ledger, pieces, report, _x, _y = build()
    print("solved grid:", report["solved"])
    print({k: v for k, v in report.items() if k != "solved"})
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    print(f"compiled: {len(disk.sectors)} sectors, {len(disk.walls)} walls")

    #: the field's contributions, at the decided conversion
    for name, piece, _sid, _z in pieces:
        if piece.depth:
            sector = compiled.allocations[name].sector_id
            ledger.write(str(sector), "shade", "sun:field", piece.depth * STEP,
                         intent="presentation")
    print("shade channel:", apply_shade_channel(disk, ledger))

    # --- 4. joins ---------------------------------------------------------
    run.enter("joins")
    kinds = {}
    for name, _piece, sid, _z in pieces:
        sector = compiled.allocations[name].sector_id
        kinds[sector] = joins.ROAD if sid == "plane" else joins.PAVEMENT
    applied = joins.apply(disk, kinds, strict=False)
    print("joins:", {k: v for k, v in applied.items() if k != "applied"})

    run.enter("frames")
    out = HERE / "slice2-streets.MAP"
    write_map(disk, out)
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} walls")
    _limits(disk)
    return 0


def _limits(disk):
    import json

    budget = json.load(open(ROOT / "projects/blood-city/project.json"))["budget"]
    counts = {"sectors": len(disk.sectors), "walls": len(disk.walls),
              "sprites": len(disk.sprites)}
    print("limits: " + "  ".join(
        f"{k} {v}/{budget[k + '_limit']} ({100 * v // budget[k + '_limit']}%)"
        for k, v in counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
