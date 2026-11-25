"""Per-building facade variation, applied after compile.

E3M1's street network carries **13 distinct facade tiles, none of them more
than 22% of its street-facing wall length**.  Gravesend carried one tile per
district, applied to every mass in it, so every building on a street was the
same building -- the "stamped block" blandness the project was warned about,
arriving as a texture fault rather than a geometry one.

The city's massing is the E2M6 form: one region per district with its
buildings carved as holes.  A hole loop *is* a building's street face, so
this pass recovers the loops of each street sector and gives each hole its
own facade from its district's tile-set, while the region's outer loop --
the city's edge, not a building -- takes plain masonry.

Runs on the compiled layout, so it needs no grammar support and no geometry
change.  It is a pipeline stage, not a patch: every district and every
future block inherits it.
"""

from __future__ import annotations

from materials import FACADES, MASONRY

#: Per district, the tile-set a building may wear.  Every id is one E3M1
#: uses on its own street-facing walls; the first is the district's primary
#: (the identity tile), the rest its neighbours-in-family.  Shares come out
#: near E3M1's spread (no tile over ~40% within a district).
TILE_SETS = {
    "theatre_row":  [400, 401, 380],   # grey ashlar family: the grand street
    "old_crossing": [384, 418, 181],   # red brick and boarding: the old quarter
    "market_slip":  [380, 401, 417],   # civic stone: the river gate
    "foundry_ward": [393, 417, 384],   # industrial brick
}


#: the owner's facade tiles that have windows in their art (looked at, and
#: named so on the tile sheet): the blank ones are 417, 418, 181, 414, 406
WINDOWED = {380, 384, 393, 397, 400, 401}
BACK_EXTRA = 397
#: A facade and THE SAME WALL WITHOUT ITS WINDOW. The owner, 2026-11-19:
#: "380 is building facade with windows and 381 is the same thing just
#: without windows, so if you want to have just a wall of that building it
#: should have this texture to look good." 380/381 are his; the other three
#: pairs are read off the art, which sits side by side in the tile set the
#: same way: 384's brick is 385 ("rough tan brickwork"), 393's clay is 394
#: ("clay wall"), 397's boards are 396 (which he has not named).
BLANK_OF = {380: 381, 384: 385, 393: 394, 397: 396}


def _fields(item):
    """LevelIR nests its record under 'fields'; DiskMap objects expose it."""
    if isinstance(item, dict):
        return item.get("fields", item)
    return item.fields


def _loops_of(level, wall_ids) -> list[list[int]]:
    """Wall ids of each loop, from the allocation's own wall set."""
    remaining = set(int(w) for w in wall_ids)
    loops = []
    while remaining:
        first = min(remaining)
        loop = []
        wall = first
        while True:
            loop.append(wall)
            remaining.discard(wall)
            wall = int(_fields(level.walls[wall])["point2"])
            if wall == first or wall not in remaining and wall != first:
                break
        loops.append(loop)
    return loops


def _loop_extent(level, loop: list[int]) -> tuple[int, int, float]:
    xs = [int(_fields(level.walls[w])["x"]) for w in loop]
    ys = [int(_fields(level.walls[w])["y"]) for w in loop]
    span = (max(xs) - min(xs)) * (max(ys) - min(ys))
    return min(xs), min(ys), span


#: A building's back along the city's edge, in units: the lengths cycle so
#: the edge has no beat. E3M1's longest tall wall that is not a facade is
#: 8,704; ours was one brick wall 49,152 long down a whole side.
BACK_LENGTHS = (5120, 7168, 6144, 8192)
BACK_MAX = 9216


def split_backs(layout, districts) -> dict:
    """Cut the city's edge into building-sized walls, before compile.

    The owner, 2026-11-18: "the things that should probably be buildings
    have wall textures". The plan always said the north, east and west
    edges were `building_back`; the build painted them as one boundary wall
    apiece, because one wall record carries one tile. A vertex every
    building's length gives each back its own record for `apply` to paint.
    """
    regions = [layout.regions[r] for r in districts if r in layout.regions]
    if not regions:
        return {"edge": None, "vertices": 0}
    xs = [x for r in regions for x, _y in r.outer]
    ys = [y for r in regions for _x, y in r.outer]
    edge = (min(xs), min(ys), max(xs), max(ys))
    added = 0
    for region in regions:
        points = [(int(x), int(y)) for x, y in region.outer]
        out = []
        for i, (x0, y0) in enumerate(points):
            x1, y1 = points[(i + 1) % len(points)]
            out.append((x0, y0))
            on_edge = ((x0 == x1 and x0 in (edge[0], edge[2]))
                       or (y0 == y1 and y0 in (edge[1], edge[3])))
            length = abs(x1 - x0) + abs(y1 - y0)
            if not on_edge or length <= BACK_MAX:
                continue
            sx = (x1 > x0) - (x1 < x0)
            sy = (y1 > y0) - (y1 < y0)
            done, k = 0, (abs(x0) + abs(y0)) // 1024
            while True:
                step = BACK_LENGTHS[k % len(BACK_LENGTHS)]
                if length - done - step < 4096:
                    break
                done += step
                k += 1
                out.append((x0 + sx * done, y0 + sy * done))
                added += 1
        region.outer = tuple(out)
    return {"edge": list(edge), "vertices": added}


def tile_of(district: str, x0: int, y0: int) -> int:
    """The front of the building whose outline's least corner is there."""
    tiles = TILE_SETS[district]
    return tiles[((x0 // 1024) + (y0 // 1024) * 3) % len(tiles)]


def apply(level, compiled, districts, edge=None) -> dict:
    """Vary facades per building.  `districts` maps region_id -> district."""
    report = {"buildings": 0, "walls": 0, "by_tile": {}, "boundary_walls": 0}
    for region_id, district in districts.items():
        allocation = compiled.allocations.get(region_id)
        if allocation is None:
            continue
        tiles = TILE_SETS[district]
        loops = _loops_of(level, allocation.wall_ids)
        if not loops:
            continue
        # The largest-extent loop is the district's own edge, not a building.
        extents = [_loop_extent(level, loop) for loop in loops]
        outer = max(range(len(loops)), key=lambda i: extents[i][2])
        for index, loop in enumerate(loops):
            if index == outer:
                for wall in loop:
                    record = _fields(level.walls[wall])
                    if int(record["next_sector"]) >= 0:
                        continue
                    nxt = _fields(level.walls[int(record["point2"])])
                    x0, y0 = int(record["x"]), int(record["y"])
                    x1, y1 = int(nxt["x"]), int(nxt["y"])
                    length = abs(x1 - x0) + abs(y1 - y0)
                    on_edge = edge is not None and (
                        (x0 == x1 and x0 in (edge[0], edge[2]))
                        or (y0 == y1 and y0 in (edge[1], edge[3])))
                    if on_edge and length >= 1024:
                        #: the city's edge IS the backs of its buildings
                        #: (`city_plan.BOUNDARY`: building_back), one
                        #: building to a segment (`split_backs`)
                        key = (min(x0, x1) // 1024) + (min(y0, y1) // 1024) * 3
                        #: The owner, 2026-11-18: "We should have more
                        #: windows in buildings around the city." A third
                        #: of the edge (47k of 159k) drew the district's
                        #: BLANK tiles -- 417, 418, 181 -- so a building's
                        #: back was a wall with no window in it. A back
                        #: wears only the tiles with windows in their art,
                        #: and the wooden front (397) joins them.
                        backs = [t for t in tiles if t in WINDOWED] + [BACK_EXTRA]
                        record["picnum"] = backs[key % len(backs)]
                        report["back_walls"] = report.get("back_walls", 0) + 1
                    else:
                        record["picnum"] = MASONRY.wall
                        report["boundary_walls"] += 1
                continue
            # Deterministic per building, and stable under re-compiles:
            # keyed on where the building stands, not on loop order.
            x0, y0, span = extents[index]
            # A mass small enough to walk around in a few steps is a
            # monument, a kiosk, a gatehouse -- masonry, not a facade with
            # storeys of windows.  (The plaza monument read as a tower.)
            if span <= (3 * 1024) ** 2:
                tile = MASONRY.wall
            else:
                tile = tile_of(district, x0, y0)
            painted = 0
            for wall in loop:
                if int(_fields(level.walls[wall])["next_sector"]) < 0:
                    _fields(level.walls[wall])["picnum"] = tile
                    painted += 1
            if painted:
                report["buildings"] += 1
                report["walls"] += painted
                report["by_tile"][tile] = report["by_tile"].get(tile, 0) + painted
    return report


#: Build anchors a one-sided wall's texture to its sector's ceiling, but a
#: two-sided wall's *upper step* to the bottom of that step -- the head of
#: the opening.  A facade with banding therefore breaks phase over every
#: entrance unless the header is told to anchor at the ceiling like the wall
#: it continues.  Our headers are 180,224 tall against a 32,768 tile repeat:
#: 5.5 repeats, so the two anchors sit exactly half a tile apart, which is
#: what "textures aren't aligned at entrances" looks like.
#:
#: E3M1 sets this flag on 21 of its 35 street headers; DWE3M1 and TEDE1M2
#: mostly leave it clear, and their facades are plainer tiles where the
#: phase does not show.  Ours are banded, so we follow E3M1.
ALIGN_TO_CEILING = 4


def align_headers(level, compiled, districts) -> dict:
    """Anchor the wall above every street opening to the facade's own phase."""
    report = {"headers": 0, "heights": {}}
    for region_id in districts:
        allocation = compiled.allocations.get(region_id)
        if allocation is None:
            continue
        for wall_id in allocation.wall_ids:
            fields = _fields(level.walls[wall_id])
            other = int(fields["next_sector"])
            if other < 0:
                continue
            here = _fields(level.sectors[allocation.sector_id])
            there = _fields(level.sectors[other])
            header = int(there["ceiling_z"]) - int(here["ceiling_z"])
            if header <= 0:
                continue          # no upper step: nothing above the opening
            fields["cstat"] = int(fields["cstat"]) | ALIGN_TO_CEILING
            report["headers"] += 1
            report["heights"][header] = report["heights"].get(header, 0) + 1
    return report


#: A facade tile is 64 pixels wide and the campaign draws its street walls
#: at 16 world units per tile pixel (measured: 133 of 152 E3M1 street walls,
#: 216 of 260 in TEDE1M2).  So a facade bay -- one painted window and its
#: pier -- is 1024 units, and openings should land BETWEEN bays.
UNITS_PER_TILE_PIXEL = 16
BAY = 1024


def snap_opening(start: int, width: int) -> tuple[int, int]:
    """Put an opening on the bay grid: whole bays, edges between windows.

    An entrance cut at an arbitrary width slices the windows painted on the
    facade in half, which is what "the entrance should copy the windows, not
    cut them" describes.  E3M1's modal street opening is exactly one bay
    (1024) and whole-bay openings are its largest class.
    """
    snapped = int(round(start / BAY)) * BAY
    bays = max(1, int(round(width / BAY)))
    return snapped, bays * BAY


#: `world_align_facades` lived here until 2026-09-02 and is gone. It phased
#: every street wall's texture from its own world coordinate, which is what
#: makes a bay grid exist -- tile boundaries on world multiples of 1024
#: everywhere in a district, so an opening snapped to that grid never cuts a
#: painted window. It fought `texture_frame.frame_map` for the same field and
#: nothing decided between them (owner queue item 16).
#:
#: The conflict was an artefact of the per-wall representation. A run whose
#: U-ORIGIN is a world point gives the district-wide bay grid AND still
#: accumulates across its own doorways, so both facts hold at once:
#: `texture_frame.world_u` computes that origin and `frame_map(world_phase=)`
#: takes it. Measured on this map, the frame puts 640 of 1694 walls on the
#: world bay grid against this function's 607, and continuity rises with it
#: (bend solid-solid x 91% -> 98%).
#:
#: `align_headers` above is NOT replaced by any of that and stays: it sets
#: cstat 4 (kWallOrgOutside), which makes a header peg to the facade's own
#: ceiling instead of to the step (`GetWallZPeg`, xmpmaped.cpp:3009-3011),
#: and the frame DEPENDS on that bit rather than deciding it.


def face_landmark(level, rect, tile, *, frieze=None, band=None, deepest=None) -> dict:
    """Give one mass its own face, overriding the district's.

    A landmark that wears the district's brick is not a landmark.  St
    Gallow's first frame from the avenue was a flat brick wall with a small
    dark door in it and a strip of a different brick above the door where
    the porch reveal showed through -- so the church read as a patched
    tenement.

    Blood faces its own church in the stone it lines it with: 36% of E1M5's
    exterior wall length is tile 406, the same moulded pale stone as its
    nave, and another 10% is 409, the meander frieze.  So this repaints
    every solid wall lying on the mass's boundary -- the porch reveal
    included, which is what closes the patch -- and optionally runs the
    frieze along the walls whose bottom sits in a named height band.

    The mass's outline is a line in plan, and the sewer runs under it: a
    wall whose room's floor is deeper than ``deepest`` is under the street
    and is left as it is. (The west leg's walk and the plague pit beside
    the churchyard wore the church's pale stone.)
    """
    x0, y0, x1, y1 = rect
    painted = friezed = 0
    floor_of = {}
    if deepest is not None:
        for sector in level.sectors:
            f = _fields(sector)
            for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
                floor_of[w] = int(f["floor_z"])
    for index in range(len(level.walls)):
        fields = _fields(level.walls[index])
        if int(fields.get("next_sector", -1)) >= 0:
            continue
        if deepest is not None and floor_of.get(index, 0) > deepest:
            continue
        after = _fields(level.walls[int(fields["point2"])])
        ax, ay = int(fields["x"]), int(fields["y"])
        bx, by = int(after["x"]), int(after["y"])
        mx, my = (ax + bx) / 2, (ay + by) / 2
        on_edge = ((abs(mx - x0) < 1 or abs(mx - x1) < 1) and y0 <= my <= y1) \
            or ((abs(my - y0) < 1 or abs(my - y1) < 1) and x0 <= mx <= x1)
        if not on_edge:
            continue
        fields["picnum"] = int(tile)
        painted += 1
        if frieze is not None and band is not None:
            length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if band[0] <= length <= band[1]:
                fields["picnum"] = int(frieze)
                friezed += 1
    return {"landmark_walls": painted, "frieze_walls": friezed}
