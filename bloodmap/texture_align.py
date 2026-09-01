"""Put a wall texture's seam where Blood puts it.

Build tiles a wall texture vertically: one repeat covers
``tile_pixels * 2048 / y_repeat`` z units, and the campaign leaves ``y_repeat``
at 8 on 98% of its one-sided walls, so the scale is fixed and the wall height is
whatever it is.  When the height is not a whole number of repeats -- which it is
not for 46% of the campaign's one-sided walls -- the leftover has to go
somewhere, and where it goes is the difference between a wall that reads as
built and one whose texture is visibly cut across the middle.

Blood deals with it by panning.  ``y_panning`` is non-zero on **46%** of the
walls that do not tile evenly against **20%** of the ones that do: it is the
tool the designers reached for precisely when a texture would otherwise be cut
awkwardly, at more than twice the rate.

There is no single rule to recover, because they panned by hand.  Of the 16,718
panned one-sided walls in the campaign, 22% sit exactly on the floor-anchored
value and the rest cluster on other multiples of 32 and 64 -- aligning the tile
to a feature rather than to the floor.  But the floor-anchored value is the
modal choice by a wide margin (2,835 walls exactly on it, against 1,003 for the
next cluster), and it is the one an author can apply without judging each tile:
it drives the seam up to the ceiling, where a ceiling or an upper band hides it,
instead of leaving it across the middle of the wall.

So this is a *default*, not a correction.  It only touches walls that carry no
panning already, because a wall that has been panned deliberately has been
judged, and that judgement is worth more than this rule.
"""

from __future__ import annotations

from typing import Any

#: Build's vertical wall texture scale: one repeat spans
#: ``tile_pixels * TEXTURE_SPAN_SCALE / y_repeat`` z units.
TEXTURE_SPAN_SCALE = 2048

#: y_panning is one byte covering a whole repeat.
PANNING_PERIOD = 256

#: How close to a whole number of repeats counts as tiling evenly. Below this a
#: seam lands within a fraction of a texture of an edge and reads as intentional.
EVEN_TOLERANCE = 0.08


#: Build's horizontal texel scale. A wall wears its tile at NATURAL size when
#: `length / x_repeat == 2 * tile_width`; measured across the whole DOOR-*
#: tutorial family, 3440 walls sit exactly there and the next cluster (1286)
#: is twice as dense. So this is the scale to compute against when a texture
#: should simply look right.
NATURAL_TEXEL_SCALE = 2


def natural_x_repeat(length: float, tile_width: int, *,
                     scale: int = NATURAL_TEXEL_SCALE) -> int:
    """The `x_repeat` that wears `tile_width` at natural size over `length`."""
    if tile_width <= 0:
        raise ValueError("tile_width must be positive")
    return max(1, int(round(abs(length) / (scale * tile_width))))


def texel_scale(length: float, tile_width: int, x_repeat: int) -> float:
    """How stretched a wall's texture is: 2.0 is natural, 4.0 is twice that."""
    if x_repeat <= 0 or tile_width <= 0:
        return 0.0
    return (abs(length) / x_repeat) / tile_width


def repeat_span(tile_height: int, y_repeat: int) -> int:
    """Z units covered by one vertical repeat of a wall texture."""
    if tile_height <= 0 or y_repeat <= 0:
        return 0
    return tile_height * TEXTURE_SPAN_SCALE // y_repeat


def course_z(anchor_z: int, tile_height: int, y_repeat: int, row: int, *,
             y_panning: int = 0, upward: bool = True) -> int:
    """World z of one texture row, given the wall edge the texture hangs from.

    `anchor_z` is the z of the texture's own origin edge -- the head of an
    opening for the top step of a two-sided wall, the sector ceiling when the
    wall is aligned to it. `upward` is how the tile runs from there: Blood's z
    grows downward, so a row measured up from the anchor has a smaller z.

    This is what makes a painted band placeable: `art.course_rows` says which
    row the band is on, and this says where that row lands in the world.
    """
    span = repeat_span(int(tile_height), int(y_repeat))
    if span <= 0 or tile_height <= 0:
        return int(anchor_z)
    per_row = span / float(tile_height)
    offset = (int(row) + int(y_panning) * tile_height / PANNING_PERIOD) * per_row
    return int(round(anchor_z - offset if upward else anchor_z + offset))


def floor_anchored_panning(height: int, span: int) -> int:
    """The panning that drives the leftover to the top of the wall."""
    if span <= 0:
        return 0
    leftover = (height % span) / span
    return round((1.0 - leftover) * PANNING_PERIOD) % PANNING_PERIOD


def tiles_evenly(height: int, span: int, *, tolerance: float = EVEN_TOLERANCE) -> bool:
    if span <= 0:
        return True
    leftover = (height % span) / span
    return leftover <= tolerance or leftover >= 1.0 - tolerance


def align_wall_textures(level: Any, art_sizes: dict[int, tuple[int, int]]) -> dict[str, Any]:
    """Anchor un-panned, unevenly-tiling one-sided walls to the floor.

    Returns what it did, so a caller can report the change rather than take it
    on trust. Two-sided walls are left alone: their visible bands depend on the
    neighbour's floor and ceiling as well, and which band a tile belongs to is a
    judgement this does not make.
    """
    owner: dict[int, int] = {}
    for index, sector in enumerate(level.sectors):
        fields = sector["fields"] if isinstance(sector, dict) else sector.fields
        start = int(fields["wall_ptr"])
        for wall in range(start, start + int(fields["wall_count"])):
            owner[wall] = index

    changed = 0
    skipped_panned = 0
    already_even = 0
    for index, wall in enumerate(level.walls):
        fields = wall["fields"] if isinstance(wall, dict) else wall.fields
        if int(fields["next_sector"]) >= 0:
            continue
        if int(fields["y_panning"]):
            skipped_panned += 1
            continue
        sector_id = owner.get(index)
        if sector_id is None:
            continue
        size = art_sizes.get(int(fields["picnum"]))
        if size is None:
            continue
        span = repeat_span(int(size[1]), int(fields["y_repeat"]))
        if not span:
            continue
        sector = level.sectors[sector_id]
        sector_fields = sector["fields"] if isinstance(sector, dict) else sector.fields
        height = abs(int(sector_fields["floor_z"]) - int(sector_fields["ceiling_z"]))
        if tiles_evenly(height, span):
            already_even += 1
            continue
        fields["y_panning"] = floor_anchored_panning(height, span)
        changed += 1

    return {
        "walls_anchored": changed,
        "already_tiling_evenly": already_even,
        "left_alone_because_panned": skipped_panned,
        "basis": (
            "the campaign pans 46% of one-sided walls that do not tile evenly "
            "against 20% of those that do, and the floor-anchored value is its "
            "modal choice"
        ),
    }



#: Beyond this turn a corner is an outside edge, and the campaign treats it as
#: the end of a run: only 23% of reflex joins continue the texture against 82%
#: of collinear ones.
RUN_BREAK_DEGREES = 100.0


def _wall_angle(level: Any, this: int, nxt: int) -> float:
    """The turn in degrees from one wall onto the next, 0 for collinear."""
    import math

    def point(index: int) -> tuple[int, int]:
        fields = level.walls[index]
        fields = fields["fields"] if isinstance(fields, dict) else fields.fields
        return int(fields["x"]), int(fields["y"])

    def field(index: int, name: str) -> int:
        fields = level.walls[index]
        fields = fields["fields"] if isinstance(fields, dict) else fields.fields
        return int(fields[name])

    ax, ay = point(this)
    bx, by = point(nxt)
    cx, cy = point(field(nxt, "point2"))
    ux, uy = bx - ax, by - ay
    vx, vy = cx - bx, cy - by
    return abs(math.degrees(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)))


def align_wall_runs(level: Any, art_sizes: dict[int, tuple[int, int]], *,
                    continuous_portal_sectors: set[int] | None = None) -> dict[str, Any]:
    """Carry a wall texture across a corner instead of restarting it there.

    Blood advances the horizontal texture coordinate by ``x_repeat * 8`` tile
    pixels along a wall, so a run continues when

        x_panning(next) == (x_panning(this) + x_repeat(this) * 8) % tile_width

    A level built without this leaves every wall starting at panning zero, which
    puts a hard vertical seam at every vertex -- including the vertices that are
    not corners at all, the ones where a long wall was split to hang a doorway
    off it. That is what "the textures aren't aligned" looks like from inside.
    This level continued 3% of its same-tile joins; the campaign's 43 maps run
    from 34% to 69%, median 48%.

    The campaign says where a run ends, too, and it is not everywhere:

        collinear (<5 deg)     82% continued
        bend (5-100 deg)       44%
        reflex (>100 deg)      23%
        solid to solid         74%
        portal to portal       33%

    So a run is carried around anything short of an outside corner, and is not
    carried between two portal walls -- there the visible surface is an upper or
    lower band whose extent depends on the neighbouring sector, and the campaign
    mostly leaves those alone.  A named frontage loop may opt in through
    ``continuous_portal_sectors``: an arcade concourse is one deliberately
    continuous interior face, so its window/door cuts must not restart the same
    wallpaper at every aperture.
    """
    continuous_portal_sectors = set(continuous_portal_sectors or ())
    changed = 0
    runs = 0
    for sector_id, sector in enumerate(level.sectors):
        fields = sector["fields"] if isinstance(sector, dict) else sector.fields
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        if count < 2:
            continue
        walls = list(range(start, start + count))

        def face(index: int) -> Any:
            wall = level.walls[index]
            return wall["fields"] if isinstance(wall, dict) else wall.fields

        def continues(this: int, nxt: int) -> bool:
            a, b = face(this), face(nxt)
            if int(a["picnum"]) != int(b["picnum"]):
                return False                      # a change of material
            if (int(a["next_sector"]) >= 0 and int(b["next_sector"]) >= 0
                    and sector_id not in continuous_portal_sectors):
                return False                      # both are portal bands
            if int(b["x_panning"]):
                return False                      # somebody panned it on purpose
            return _wall_angle(level, this, nxt) < RUN_BREAK_DEGREES

        # Start each loop at a break so a run is never cut in the middle by the
        # arbitrary place the wall list happens to begin.
        order = walls
        for offset, wall in enumerate(walls):
            previous = walls[offset - 1]
            if int(face(previous)["point2"]) != wall or not continues(previous, wall):
                order = walls[offset:] + walls[:offset]
                break

        carried: int | None = None
        for wall in order:
            a = face(wall)
            nxt = int(a["point2"])
            size = art_sizes.get(int(a["picnum"]))
            width = int(size[0]) if size else 0
            if carried is not None and width > 0:
                a["x_panning"] = carried % width
                changed += 1
            if not (start <= nxt < start + count) or width <= 0:
                carried = None
                continue
            if continues(wall, nxt):
                base = carried if carried is not None else int(a["x_panning"])
                carried = (base + int(a["x_repeat"]) * 8) % width
            else:
                if carried is not None:
                    runs += 1
                carried = None
        if carried is not None:
            runs += 1

    return {
        "walls_repanned": changed,
        "runs": runs,
        "continuous_portal_sectors": len(continuous_portal_sectors),
        "basis": (
            "the campaign continues 82% of collinear joins and 74% of "
            "solid-to-solid ones, but only 23% of reflex corners and 33% of "
            "portal-to-portal joins"
        ),
    }


#: Where the Blood ART lives when nobody says otherwise. Alignment needs real
#: tile pixel heights: a hand-written size table covers whatever its author
#: happened to list, and a wall tile missing from it is silently left unaligned.
DEFAULT_ART_DIRECTORY = "reference/blood"


def wall_art_sizes(directory: str = DEFAULT_ART_DIRECTORY) -> dict[int, tuple[int, int]]:
    """Tile pixel sizes for alignment, or an empty map if the ART is absent.

    Returning empty rather than raising keeps a level buildable without the
    game's data; the alignment pass then reports that it anchored nothing, which
    is the truth rather than a silent pass.
    """
    try:
        from .art import read_art_directory

        return {
            picnum: (int(tile.width), int(tile.height))
            for picnum, tile in read_art_directory(directory).items()
            if tile.height
        }
    except Exception:
        return {}


def sprite_tile_extents(directory: str = DEFAULT_ART_DIRECTORY) -> dict[int, tuple[int, int]]:
    """picnum -> (tile pixel height, picanm yofs), for seating sprites.

    `placement.seated_z` needs both: Blood's centre is
    ``tilesiz[picnum].y / 2 + picanm[picnum].yofs``, and the offset is not always
    zero. Returns an empty map when the ART is absent, which makes a seated
    placement fail loudly at compile time rather than silently mis-seat.
    """
    try:
        from .art import decode_picanm, read_art_directory

        out: dict[int, tuple[int, int]] = {}
        for picnum, tile in read_art_directory(directory).items():
            if not tile.height:
                continue
            picanm = tile.picanm
            yofs = decode_picanm(picanm)["yofs"] if isinstance(picanm, int) else 0
            out[picnum] = (int(tile.height), int(yofs))
        return out
    except Exception:
        return {}
