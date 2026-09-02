"""Slice 1: the west street alone, on the ground-plane model.

One road, built the way the owner's model says a street is built, so the model
can be proved on something small before the city is rebuilt on it:

    the STREET is the ground plane          tile 352 at grade + 2048
    a PAVEMENT is an island standing on it  tile 4 at grade, 2048 up
    the KERB is the island's own edge       tile 6 on the ROAD-side record
    a MASS stands on an island              and throws a shadow on the road
    the SHADOW is a light overlay           cut across road and pavement alike
    a LAMP stands on a pavement             never in the road
    a SHOPFRONT is an insert in a hole      through its own 512 recess

Nothing here is carved out of anything. The road is emitted whole and then
CUT -- by the kerb where an island lies on it, by the shadow where a mass
falls across it -- and the pieces inherit the road's surface and its frame, so
the material runs on through both cuts as though neither were there. That is
the property this slice exists to prove, because it is the one the old
"insert a sector where there is room" idiom could never give.

It writes its own map (`slice1-west-street.MAP`) and leaves blood-city-current
alone. The city is not half-rebuilt while the model is being proved on it.

.. code-block:: bash

    python projects/blood-city/level/build_street_slice.py
"""

from __future__ import annotations

import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from bloodmap.format import write_map                            # noqa: E402
from bloodmap.overlay import (                                   # noqa: E402
    Cut, HeightIsland, kerb_records, split_convex)
from bloodmap.planar_layout import PlanarLayout                  # noqa: E402
from bloodmap.surface import (                                   # noqa: E402
    Insert, Opening, RecordOwner, Surface)
from bloodmap.texture_frame import WallRunFrame                  # noqa: E402
from bloodmap.player_space import PLAYER_PROFILES                 # noqa: E402
from bloodmap.street import end_wall, termination_faults          # noqa: E402
from resolution import (                                         # noqa: E402
    GRADE, SHADE_LIT, SHADE_SHADOW, SKY_TILE, STREET_SKY, SUN_BEARING,
    SUN_BEARING_DEGREES, SUN_SHADOW_PER_HEIGHT, WIDTH_UNITS)

STANDING = PLAYER_PROFILES["blood"].standing_height

#: E3M1, measured: the road wears 352 and the pavement 4; the kerb band on the
#: road-side record wears 6; the island stands 2048 above the road.
ROAD_TILE = 352
PAVE_TILE = 4
KERB_TILE = 6
FACADE_TILE = 400
RISE = 2048
#: The road is the GROUND PLANE and the pavements stand on it, so the road's
#: floor is BELOW grade -- Blood's z grows downward, so numerically larger.
ROAD_Z = GRADE + RISE

#: The solve's band (E3M1's mode: 2048 on six of its fourteen pavements).
BAND = 2048
#: One class-minimum street between the two islands.
ROAD_W = WIDTH_UNITS["street"]

#: The slice's own extent: one block of road with an island either side.
RUN = 20480
X0 = 0
ISLAND_D = 8192

#: A mass 4 player-heights tall, and its shadow as long as it is tall
#: (SUN_SHADOW_PER_HEIGHT = 1.0, the 45-degree convention).
MASS_H = 4 * 16960
MASS_W = 6144
MASS_D = 5120


def _rect(x0, y0, x1, y1):
    return [(int(x0), int(y0)), (int(x1), int(y0)),
            (int(x1), int(y1)), (int(x0), int(y1))]


def shadow_polygon(mass_rect, height):
    """Where a mass throws its shadow, at the level's one sun.

    The bearing is the direction the shadow is cast TOWARDS
    (`resolution.SUN_BEARING`, a Build angle), and the length is the mass's
    height at the 45-degree elevation convention. The polygon is the mass's
    footprint swept along that vector, which is convex whenever the footprint
    is -- the property `overlay.split_convex` needs.
    """
    length = int(height * SUN_SHADOW_PER_HEIGHT)
    radians = math.radians(SUN_BEARING * 360.0 / 2048.0)
    dx = int(round(length * math.cos(radians)))
    dy = int(round(length * math.sin(radians)))
    x0, y0, x1, y1 = mass_rect
    #: The sweep of an axis-aligned box along one vector: take the two corners
    #: the vector leads from and the two it leads to.
    base = _rect(x0, y0, x1, y1)
    moved = [(x + dx, y + dy) for x, y in base]
    points = base + moved
    #: convex hull of eight points, monotone chain
    points = sorted(set(points))
    def half(seq):
        out = []
        for point in seq:
            while len(out) >= 2:
                ax, ay = out[-2]
                bx, by = out[-1]
                if (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax) > 0:
                    break
                out.pop()
            out.append(point)
        return out
    hull = half(points)[:-1] + half(reversed(points))[:-1]
    return hull, (dx, dy)


def build():
    layout = PlanarLayout(name="slice1-west-street")
    records = RecordOwner()
    report = {"pieces": 0, "kerb_records": 0, "lamps": 0, "inserts": 0}

    west_x1 = X0 + ISLAND_D
    road_x0, road_x1 = west_x1, west_x1 + ROAD_W
    east_x0 = road_x1

    #: --- the ground plane, emitted WHOLE and then cut ---------------------
    road_outline = _rect(road_x0, 0, road_x1, RUN)

    #: --- the shadow, from the mass on the west island ---------------------
    mass_west = (X0 + BAND, 4096, X0 + BAND + MASS_W, 4096 + MASS_D)
    shadow, vector = shadow_polygon(mass_west, MASS_H)

    #: The cut across the road is the shadow's leading edge. One half-plane,
    #: at the sun's bearing, so the road comes apart into a lit piece and a
    #: shadowed one and nothing else changes about either.
    lead = _shadow_edge(shadow, vector, road_outline)
    if lead is None:
        raise SystemExit(
            "the mass throws no shadow across this road: move it, or the "
            "slice proves nothing about a shadow cut")
    #: ONE CUT, ACROSS EVERYTHING IT CROSSES. A shadow does not stop at the
    #: kerb, and cutting only the road would leave the island's road-facing
    #: edge spanning two road pieces with nothing to pair against -- which is
    #: exactly the "unpaired portal" the compiler refused the first time. The
    #: overlay is one half-plane and every surface it crosses comes apart on
    #: it, which is what makes the pieces line up along the kerb.
    surfaces = {
        "road": (road_outline, ROAD_Z, ROAD_TILE, KERB_TILE, "road"),
        "west_island": (_rect(X0, 0, west_x1, RUN), ROAD_Z - RISE, PAVE_TILE,
                        FACADE_TILE, "island"),
        "east_island": (_rect(east_x0, 0, east_x0 + ISLAND_D, RUN),
                        ROAD_Z - RISE, PAVE_TILE, FACADE_TILE, "island"),
    }
    pieces = []
    by_surface = {}
    for surface_id, (outline, floor_z, floor_tile, wall_tile, kind) in             surfaces.items():
        lit, shaded = split_convex(outline, lead)
        halves = []
        for half_name, poly, shade in (("lit", lit, SHADE_LIT),
                                       ("shadow", shaded, SHADE_SHADOW)):
            if not poly:
                continue
            name = f"{surface_id}:{half_name}"
            #: THE SKY IS A MATERIAL, not the floor tile copied upward. The
            #: first cut of this slice gave every parallaxed ceiling its own
            #: floor's tile, and `parallax-wears-a-sky-tile` reported all five
            #: as errors -- the law was there, the slice had simply never been
            #: run through the gates the city build runs.
            layout.add_region(
                name, poly, floor_z=floor_z, ceiling_z=floor_z - STREET_SKY,
                floor_picnum=floor_tile, ceiling_picnum=SKY_TILE,
                wall_picnum=wall_tile, floor_shade=shade, wall_shade=shade,
                parallax_ceiling=True, role="street")
            halves.append((half_name, name, poly))
            pieces.append((name, poly, shade, kind, surface_id))
            report["pieces"] += 1
        by_surface[surface_id] = halves
        #: the two halves of one surface are the same surface, so they are a
        #: portal and nothing else changes across it
        if len(halves) == 2:
            layout.add_connection(f"shadow_edge:{surface_id}",
                                  halves[0][1], halves[1][1], role="portal")
            report["shadow_edges"] = report.get("shadow_edges", 0) + 1

    #: --- the islands as declared height islands ---------------------------
    islands = {}
    for name, x0, x1 in (("west_island", X0, west_x1),
                         ("east_island", east_x0, east_x0 + ISLAND_D)):
        islands[name] = HeightIsland(name, tuple(_rect(x0, 0, x1, RUN)),
                                     rise=RISE, kerb_tile=KERB_TILE,
                                     floor_picnum=PAVE_TILE)

    #: --- the kerb: the island's own edge, on the ROAD-side record ---------
    #:
    #: Paired half by half, so a piece of pavement meets the piece of road on
    #: its own side of the shadow. The tile goes on the ROAD's record: the
    #: band that draws faces the road, and giving it to the island is how
    #: Gravesend's kerbs ended up wearing the houses.
    kerbs = []
    for island_id, island in islands.items():
        road_facing = [record["edge"] for record in
                       kerb_records(island, "road", road_outline)
                       if _faces_road(record["edge"], road_x0, road_x1)]
        for half_name, island_piece, island_poly in by_surface[island_id]:
            road_piece = next((n for h, n, _p in by_surface["road"]
                               if h == half_name), None)
            if road_piece is None:
                continue
            for edge in road_facing:
                clipped = _shared_edge(island_poly,
                                       dict((n, p) for _h, n, p
                                            in by_surface["road"])[road_piece],
                                       edge[0][0])
                if clipped is None:
                    continue
                layout.add_connection(
                    f"kerb:{island_id}:{half_name}", road_piece, island_piece,
                    role="portal", a1=clipped[0], a2=clipped[1])
                layout.paint_wall(road_piece, clipped[0], clipped[1],
                                  picnum=KERB_TILE)
                kerbs.append({"road_piece": road_piece, "island": island_piece,
                              "edge": clipped, "picnum": KERB_TILE,
                              "rise": RISE})
                report["kerb_records"] += 1
    report["kerbs"] = kerbs

    #: --- one mass on each island, with a facade Surface and a hole --------
    facade = Surface(
        "west_mass:street_face", "west_mass",
        WallRunFrame(tile=FACADE_TILE),
        openings=(Opening("shopfront", (mass_west[0] + 1024, mass_west[3],
                                        mass_west[0] + 4096, mass_west[3]),
                          "shopfront"),))
    insert = Insert("west_mass:shop", "shopfront", "shopfront",
                    holder_regions=("west_mass:recess",))
    report["surface"] = facade.surface_id
    report["insert_lawful"] = insert.lawful
    report["inserts"] = 1

    #: --- lamps stand on the pavements, never in the road -------------------
    #: On a PIECE of pavement, not on the island: the island is a source-level
    #: thing and the compiler only knows the pieces the overlay left.
    for index, (island_id, x) in enumerate(
            (("west_island", X0 + BAND // 2),
             ("east_island", east_x0 + ISLAND_D - BAND // 2))):
        for half_name, piece, poly in by_surface[island_id]:
            #: The centroid, not the bounding box's middle: the shadow cut is
            #: oblique, so a piece of pavement is a trapezoid and the middle
            #: of its bounds is routinely outside it. The compiler caught
            #: exactly that -- "sprite position is outside its sector".
            spot = _centroid(poly)
            layout.add_sprite(f"lamp:{index}:{half_name}", piece,
                              x=int(spot[0]), y=int(spot[1]),
                              z=int(ROAD_Z - RISE), picnum=506,
                              type=0, status=0, cstat=0, x_repeat=32,
                              y_repeat=32, angle=0)
            report["lamps"] += 1

    #: A body standing ON THE ROAD, which is where the kerb has to read from.
    #: Placed at the piece's centroid for the same reason the lamps are.
    road_piece, road_poly = next(
        (name, poly) for name, poly, _s, kind, _sid in pieces
        if kind == "road")
    spot = _centroid(road_poly)
    layout.set_player_start(road_piece, x=int(spot[0]), y=int(spot[1]),
                            z=ROAD_Z, angle=512)
    return layout, records, report, {
        "road_outline": road_outline, "shadow": shadow, "lead": lead,
        "islands": islands, "mass_west": mass_west, "pieces": pieces}


def _shadow_edge(shadow, vector, target):
    """The shadow boundary that actually falls across `target`.

    A shadow cast nearly along a street runs beside it, so the edge a body on
    the road sees is one of the shadow's SIDES, not its far end -- and which
    side depends on where the mass stands. Rather than reason about it, both
    candidates are tried and the one that genuinely splits the target is
    returned. A cut that does not split anything is not a shadow edge on this
    road, and saying so is better than emitting a boundary nobody can see.
    """
    dx, dy = vector
    perp = (-dy, dx)
    ordered = sorted(shadow, key=lambda p: p[0] * perp[0] + p[1] * perp[1])
    for corner in (ordered[0], ordered[-1]):
        cut = Cut(corner, (corner[0] + dx, corner[1] + dy))
        left, right = split_convex(target, cut)
        if left and right:
            return cut
    return None


def _centroid(polygon):
    """A point guaranteed inside a convex polygon."""
    return (sum(p[0] for p in polygon) // len(polygon),
            sum(p[1] for p in polygon) // len(polygon))


def _shared_edge(poly_a, poly_b, x):
    """The vertical stretch of x = `x` that both polygons touch.

    A kerb record is only as long as the two pieces actually share, and after
    a shadow cut that is a fraction of the island's side. Returning None where
    they share nothing is how "this half of the pavement does not touch this
    half of the road" is said.
    """
    def span(poly):
        ys = [p[1] for p in poly if p[0] == x]
        return (min(ys), max(ys)) if len(ys) >= 2 else None

    a, b = span(poly_a), span(poly_b)
    if a is None or b is None:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if hi - lo < 512:
        return None
    return ((x, lo), (x, hi))


def _faces_road(edge, road_x0, road_x1):
    (ax, _ay), (bx, _by) = edge
    return ax == bx and ax in (road_x0, road_x1)


def _edge_touches(edge, outline):
    ys = [p[1] for p in outline]
    (ax, ay), (bx, by) = edge
    lo, hi = min(ay, by), max(ay, by)
    return not (hi <= min(ys) or lo >= max(ys))


def main() -> int:
    layout, records, report, geometry = build()
    compiled = layout.compile()

    from bloodmap.texture_align import wall_art_sizes
    from bloodmap.texture_frame import frame_map

    art = wall_art_sizes("reference/blood")
    if art:
        print("texture frames:", frame_map(compiled.level, art_sizes=art,
                                           records=records,
                                           owner="surface:street"))
    disk = compiled.level.to_disk_map()

    #: --- the slice's own gates, before it is written ----------------------
    from bloodmap.street_model import (
        kerb_faults, sees_the_kerb, shadow_edge_faults)
    from bloodmap.texture_frame import (
        WallRunFrame, auto_align_walls, run_partition, sector_index, world_u)

    owners = sector_index(disk)
    faults = kerb_faults(disk, report["kerbs"], owners=owners)
    print(f"kerb gate: {len(report['kerbs'])} declared records, "
          f"{len(faults)} fault(s)")
    for line in faults:
        print("   ", line)

    edges = [(geometry["lead"].a, geometry["lead"].b)]
    shadow = shadow_edge_faults(disk, edges, SUN_BEARING_DEGREES, 6.0)
    print(f"sun gate: {len(edges)} shadow edge(s), {len(shadow)} off-bearing")
    for line in shadow:
        print("   ", line)

    #: THE FRAME SURVIVES THE CUTS. Resolve each run, then let the ported '>'
    #: try to improve it: a road cut by a kerb and a shadow must be a fixed
    #: point of the editor's own align, or the material does not run through.
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
    print(f"frame gate: the editor would change {moved} wall(s) after the "
          f"kerb and shadow cuts")

    road_sector = next(i for i, s in enumerate(disk.sectors)
                       if int(s.fields["floor_picnum"]) == ROAD_TILE)
    view = sees_the_kerb(disk, road_sector, owners)
    print(f"sightline gate: from road s{road_sector} the faces standing up "
          f"wear {view['kerb_tiles']}, above them {view['materials_above']}")

    if faults or shadow or moved:
        print("FAIL: slice 1 did not meet its own gates; the map was not "
              "written")
        return 1

    out = HERE / "slice1-west-street.MAP"
    write_map(disk, out)
    print("slice 1:", {k: v for k, v in report.items() if k != "kerbs"})
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} walls, "
          f"{len(disk.sprites)} sprites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
