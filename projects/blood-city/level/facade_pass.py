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


def apply(level, compiled, districts) -> dict:
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
                    if int(_fields(level.walls[wall])["next_sector"]) < 0:
                        _fields(level.walls[wall])["picnum"] = MASONRY.wall
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
                tile = tiles[((x0 // 1024) + (y0 // 1024) * 3) % len(tiles)]
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


def world_align_facades(level, compiled, districts) -> dict:
    """Phase every street wall's texture to world position, not to its own
    start vertex.

    E3M1 does this on 43 of its 61 street-facing walls.  It is what makes a
    bay grid exist at all: with the phase locked to world coordinates, tile
    boundaries fall on world multiples of 1024 everywhere in the district,
    so an opening snapped to that grid never cuts a painted window -- and
    the wall above the opening continues the same grid, because it is
    phased from the same rule rather than from where it happens to start.
    """
    from bloodmap.texture_align import wall_art_sizes
    art = wall_art_sizes("reference/blood")
    report = {"walls_phased": 0, "skipped_scale": 0}
    for region_id in districts:
        allocation = compiled.allocations.get(region_id)
        if allocation is None:
            continue
        for wall_id in allocation.wall_ids:
            fields = _fields(level.walls[wall_id])
            x1, y1 = int(fields["x"]), int(fields["y"])
            nxt = _fields(level.walls[int(fields["point2"])])
            x2, y2 = int(nxt["x"]), int(nxt["y"])
            length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            repeat = int(fields["x_repeat"])
            if not length or not repeat:
                continue
            if abs(length / (repeat * 8) - UNITS_PER_TILE_PIXEL) > 0.5:
                report["skipped_scale"] += 1     # not at the facade scale
                continue
            width = art.get(int(fields["picnum"]), (64, 128))[0]
            horizontal = abs(x2 - x1) >= abs(y2 - y1)
            start = x1 if horizontal else y1
            sign = 1 if ((x2 - x1) if horizontal else (y2 - y1)) > 0 else -1
            fields["x_panning"] = int(
                (sign * start / UNITS_PER_TILE_PIXEL)) % width
            report["walls_phased"] += 1
    return report


def face_landmark(level, rect, tile, *, frieze=None, band=None) -> dict:
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
    """
    x0, y0, x1, y1 = rect
    painted = friezed = 0
    for index in range(len(level.walls)):
        fields = _fields(level.walls[index])
        if int(fields.get("next_sector", -1)) >= 0:
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
