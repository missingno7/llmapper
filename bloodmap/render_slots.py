"""What the Build renderer draws on each wall, band by band.

The map stores two tiles per wall, `picnum` and `over_picnum`, and the
project's usage table counted them by where they are STORED -- one-sided,
two-sided, overlay. The engine draws by BAND, and which of the two tiles a
band shows depends on the wall's flags and on the two sectors' heights. A
tile stored on a two-sided wall may draw on an upper step, on a lower step,
in the middle as a mask, or nowhere at all; the project had no reader for
this, so fabric on an unmasked two-sided wall passed every gate and drew
nothing in the band a player walks through.

This module is that reader. It is a transcription of the classic renderer's
wall pass, `classicDrawBunches` in `NBlood/source/build/src/engine.cpp`, and
of the deferred masked-wall pass, `renderDrawMaskedWall`; every rule below
cites the line it was read from. Vanilla only: none of this sits under
NOONE_EXTENSIONS or gModernMap.

The law, for a wall seen from its own sector:

* **one-sided** (`nextsector < 0`): `picnum` fills the whole span from the
  sector's ceiling to its floor -- `engine.cpp:4938-4940`
  `if (nextsectnum < 0 || (wal->cstat&32))` then
  `setup_globals_wall1(wal, (nextsectnum < 0) ? wal->picnum : wal->overpicnum)`.
* **two-sided upper step**: `picnum`, only where the neighbour's ceiling is
  LOWER than this sector's at either end of the wall -- `:4690` the step is
  skipped when `(cz[2] <= cz[0]) && (cz[3] <= cz[1])`, else `:4720`
  `setup_globals_wall1(wal, wal->picnum)`. Skipped outright when both
  ceilings are parallaxed (`:4688`), which is the sky bypass.
* **two-sided lower step**: `picnum`, only where the neighbour's floor is
  HIGHER than this sector's at either end -- `:4801` skipped when
  `(fz[2] >= fz[0]) && (fz[3] >= fz[1])`, else `:4832-4833`
  `twal = (wal->cstat&2) ? &wall[wal->nextwall] : wal;
  setup_globals_wall1(twal, twal->picnum)` -- cstat bit 2 swaps in the
  PARTNER wall's picnum. Both floors parallaxed skips it (`:4799`).
* **masked middle**: `over_picnum`, only when `(cstat&48) == 16` (`:4685`
  `maskwall[maskwallcnt++] = z`), drawn later by `renderDrawMaskedWall`
  between the lower of the two ceilings and the higher of the two floors --
  `:7214-7215` `z1 = max(nsec->ceilingz, sec->ceilingz); z2 =
  min(nsec->floorz, sec->floorz)`, `:7231` `setup_globals_wall1(wal,
  wal->overpicnum)`.
* **one-way middle**: `over_picnum`, when `cstat&32`, through the same
  branch as a one-sided wall (`:4938-4940`), after the steps have been
  drawn; it is opaque and occupies the middle band between the steps.
* **blocking (cstat&1) and hitscan (cstat&64) draw nothing.** Neither bit
  is read anywhere in the wall pass. They are clip masks: `clip.cpp:1491`
  `dawalclipmask = (cliptype & 65535)` with `build.h:225` `CLIPMASK0 =
  (1<<16)+1` -- bit 1 stops movement -- and `build.h:226` `CLIPMASK1 =
  (256<<16)+64` -- bit 64 stops hitscans. A blocked, hitscan two-sided wall
  with no drawn band is an invisible fence.
* **the mirror bypass**: Blood's `mirrors.cpp:466-469` -- a wall whose
  `picnum` is `kMirrorTile` (504, `:37`) gets `cstat |= CSTAT_WALL_1WAY` and
  `overpicnum = kMirrorTile` at level start, so the game turns it into a
  one-way wall and renders the reflection through it; a wall whose
  `overpicnum` is 504 with a stack type is a room-over-room link (`:442`).
  The mirror tile is therefore exempt from any "must draw" rule.
* **slopes**: endpoint heights come from `getzsofslopeptr`
  (`engine.cpp:14333-14352`): `z += scale(heinum, j, i)` with `j` the
  perpendicular distance from the sector's first wall and `i` the first
  wall's length, applied only when stat bit 2 is set. Blood runs with
  `enginecompatibilitymode = ENGINE_19960925` (`blood.cpp:1890`) so the
  EDUKE32 `shift` is 0. This transcription uses an exact integer square
  root where the engine uses its `nsqrtasm` table, so a sloped endpoint can
  differ from the engine by a unit; nothing here depends on that unit.

Everything is a pure function over a disk map from `bloodmap.format.read_map`
(or one built in memory with the same field names).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

#: Wall cstat bits, as the engine reads them. Not the sprite bits.
CSTAT_BLOCK = 1
CSTAT_SWAP_BOTTOM = 2
CSTAT_ALIGN_BOTTOM = 4
CSTAT_XFLIP = 8
CSTAT_MASKED = 16
CSTAT_ONE_WAY = 32
CSTAT_HITSCAN = 64
CSTAT_TRANSLUCENT = 128

#: Surface stat bits.
STAT_PARALLAX = 1
STAT_SLOPED = 2

#: `mirrors.cpp:37 #define kMirrorTile 504`.
MIRROR_TILE = 504

#: The parallax backdrops -- every tile the campaign ever puts on a
#: parallaxed surface (`bloodmap.usage_kinds.sky_family` is the derived
#: source; this is the same three, held here so the reader has no upward
#: dependency).
SKY_FAMILY = frozenset({2500, 3491, 3678})

#: The rendered-slot vocabulary. These are the bands the engine can draw on
#: a wall, which is not the same list as the fields the map stores.
ONE_SIDED_MIDDLE = "one_sided_middle"
TWO_SIDED_UPPER = "two_sided_upper"
TWO_SIDED_LOWER = "two_sided_lower"
MASKED_MIDDLE = "masked_middle"
ONEWAY_MIDDLE = "oneway_middle"
RENDERED_WALL_SLOTS = (ONE_SIDED_MIDDLE, TWO_SIDED_UPPER, TWO_SIDED_LOWER,
                       MASKED_MIDDLE, ONEWAY_MIDDLE)


@dataclass(frozen=True)
class Band:
    """One band the engine draws on a wall, seen from the wall's own sector.

    `top` and `bottom` are z at the wall's two endpoints (start, end), in
    Build units where z grows downward; `height` is the taller end.
    """

    band: str
    tile: int
    reason: str
    source_wall: int
    field: str
    top: tuple[int, int]
    bottom: tuple[int, int]

    @property
    def height(self) -> int:
        return max(self.bottom[0] - self.top[0], self.bottom[1] - self.top[1])

    def as_dict(self) -> dict[str, Any]:
        return {"band": self.band, "tile": self.tile, "reason": self.reason,
                "source_wall": self.source_wall, "field": self.field,
                "top": list(self.top), "bottom": list(self.bottom),
                "height": self.height}


@dataclass(frozen=True)
class WallDraw:
    """Everything the engine draws for one wall from its own side."""

    wall: int
    sector: int
    next_sector: int
    next_wall: int
    picnum: int
    over_picnum: int
    cstat: int
    bands: tuple[Band, ...]
    skipped: tuple[str, ...]
    sloped: bool

    @property
    def draws_picnum(self) -> bool:
        return any(b.field == "picnum" and b.source_wall == self.wall
                   for b in self.bands)

    @property
    def draws_over_picnum(self) -> bool:
        return any(b.field == "over_picnum" for b in self.bands)

    def as_dict(self) -> dict[str, Any]:
        return {"wall": self.wall, "sector": self.sector,
                "next_sector": self.next_sector, "next_wall": self.next_wall,
                "picnum": self.picnum, "over_picnum": self.over_picnum,
                "cstat": self.cstat, "sloped": self.sloped,
                "bands": [b.as_dict() for b in self.bands],
                "skipped": list(self.skipped)}


# ---------------------------------------------------------------------------
# heights
# ---------------------------------------------------------------------------

def _c_div(numerator: int, denominator: int) -> int:
    """C integer division: truncates toward zero, as `scale()` does."""
    quotient = abs(numerator) // abs(denominator)
    return quotient if (numerator < 0) == (denominator < 0) else -quotient


def wall_owners(disk: Any) -> dict[int, int]:
    """wall index -> the sector whose loop it belongs to."""
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index
    return owner


def surface_z(disk: Any, sector_index: int, x: int, y: int) -> tuple[int, int]:
    """(ceiling z, floor z) of a sector at a point: `getzsofslopeptr`.

    `engine.cpp:14335-14351`: the flat z unless stat bit 2 is set on the
    surface; then `j = dmulscale3(d.x, y - wal->y, -d.y, x - wal->x)` over
    the sector's FIRST wall `d`, `i = nsqrtasm(uhypsq(d.x, d.y)) << 5`, and
    `z += scale(heinum, j, i)`.
    """
    fields = disk.sectors[sector_index].fields
    ceiling = int(fields["ceiling_z"])
    floor = int(fields["floor_z"])
    cstat = int(fields["ceiling_stat"])
    fstat = int(fields["floor_stat"])
    if not ((cstat | fstat) & STAT_SLOPED):
        return ceiling, floor
    first = disk.walls[int(fields["wall_ptr"])].fields
    second = disk.walls[int(first["point2"])].fields
    dx = int(second["x"]) - int(first["x"])
    dy = int(second["y"]) - int(first["y"])
    length = math.isqrt(dx * dx + dy * dy) << 5
    if length == 0:
        return ceiling, floor
    j = (dx * (int(y) - int(first["y"])) - dy * (int(x) - int(first["x"]))) >> 3
    if cstat & STAT_SLOPED:
        ceiling += _c_div(int(fields["ceiling_heinum"]) * j, length)
    if fstat & STAT_SLOPED:
        floor += _c_div(int(fields["floor_heinum"]) * j, length)
    return ceiling, floor


def _sloped(disk: Any, sector_index: int) -> bool:
    fields = disk.sectors[sector_index].fields
    return bool((int(fields["ceiling_stat"]) | int(fields["floor_stat"]))
                & STAT_SLOPED)


# ---------------------------------------------------------------------------
# the wall pass
# ---------------------------------------------------------------------------

def wall_draw(disk: Any, wall_index: int,
              owners: dict[int, int] | None = None) -> WallDraw:
    """What the engine draws for one wall, seen from its own sector.

    Pass `owners` from `wall_owners` when calling this for many walls; it is
    the whole-map fact this reader needs.
    """
    owner = owners if owners is not None else wall_owners(disk)
    wall = disk.walls[wall_index].fields
    sector_index = owner[wall_index]
    sector = disk.sectors[sector_index].fields
    end = disk.walls[int(wall["point2"])].fields
    x0, y0 = int(wall["x"]), int(wall["y"])
    x1, y1 = int(end["x"]), int(end["y"])
    cstat = int(wall["cstat"])
    picnum = int(wall["picnum"])
    over = int(wall["over_picnum"])
    next_sector = int(wall["next_sector"])
    next_wall = int(wall["next_wall"])

    # engine.cpp:4670-4673 -- cz/fz at both endpoints in both sectors.
    cz0, fz0 = surface_z(disk, sector_index, x0, y0)
    cz1, fz1 = surface_z(disk, sector_index, x1, y1)
    bands: list[Band] = []
    skipped: list[str] = []
    sloped = _sloped(disk, sector_index)

    if next_sector < 0:
        # engine.cpp:4938-4940 -- a white wall draws picnum ceiling to floor.
        if fz0 > cz0 or fz1 > cz1:
            bands.append(Band(ONE_SIDED_MIDDLE, picnum,
                              "one-sided wall: picnum from ceiling to floor "
                              "(engine.cpp:4938-4940)",
                              wall_index, "picnum", (cz0, cz1), (fz0, fz1)))
        else:
            skipped.append("one-sided wall in a zero-height sector draws "
                           "nothing")
        return WallDraw(wall_index, sector_index, next_sector, next_wall,
                        picnum, over, cstat, tuple(bands), tuple(skipped),
                        sloped)

    neighbour = disk.sectors[next_sector].fields
    cz2, fz2 = surface_z(disk, next_sector, x0, y0)
    cz3, fz3 = surface_z(disk, next_sector, x1, y1)
    sloped = sloped or _sloped(disk, next_sector)

    # engine.cpp:4688-4724 -- the upper step.
    if (int(sector["ceiling_stat"]) & STAT_PARALLAX
            and int(neighbour["ceiling_stat"]) & STAT_PARALLAX):
        skipped.append("upper step: both ceilings parallaxed, the sky is "
                       "drawn instead (engine.cpp:4688)")
    elif cz2 <= cz0 and cz3 <= cz1:
        skipped.append("upper step: the neighbour's ceiling is not lower at "
                       "either end (engine.cpp:4690)")
    else:
        bands.append(Band(TWO_SIDED_UPPER, picnum,
                          "upper step: picnum where the neighbour's ceiling "
                          "is lower (engine.cpp:4720)",
                          wall_index, "picnum", (cz0, cz1), (cz2, cz3)))

    # engine.cpp:4799-4836 -- the lower step, with the cstat&2 swap.
    if (int(sector["floor_stat"]) & STAT_PARALLAX
            and int(neighbour["floor_stat"]) & STAT_PARALLAX):
        skipped.append("lower step: both floors parallaxed (engine.cpp:4799)")
    elif fz2 >= fz0 and fz3 >= fz1:
        skipped.append("lower step: the neighbour's floor is not higher at "
                       "either end (engine.cpp:4801)")
    else:
        if cstat & CSTAT_SWAP_BOTTOM and 0 <= next_wall < len(disk.walls):
            source = next_wall
            tile = int(disk.walls[next_wall].fields["picnum"])
            reason = ("lower step: cstat&2 swaps in the partner wall's "
                      "picnum (engine.cpp:4832-4833)")
        else:
            source, tile = wall_index, picnum
            reason = ("lower step: picnum where the neighbour's floor is "
                      "higher (engine.cpp:4832-4833)")
        bands.append(Band(TWO_SIDED_LOWER, tile, reason, source, "picnum",
                          (fz2, fz3), (fz0, fz1)))

    # The middle band: between the lower ceiling and the higher floor.
    top = (max(cz0, cz2), max(cz1, cz3))
    bottom = (min(fz0, fz2), min(fz1, fz3))
    open_middle = bottom[0] > top[0] or bottom[1] > top[1]
    if cstat & CSTAT_ONE_WAY:
        # engine.cpp:4938-4940 -- drawn as a white wall wearing overpicnum.
        if open_middle:
            bands.append(Band(ONEWAY_MIDDLE, over,
                              "one-way wall: over_picnum fills the middle "
                              "band, opaque (engine.cpp:4938-4940)",
                              wall_index, "over_picnum", top, bottom))
        else:
            skipped.append("one-way middle: the opening between the two "
                           "sectors has no height")
    elif cstat & CSTAT_MASKED:
        # engine.cpp:4685 defers it; :7214-7231 draws overpicnum there.
        if open_middle:
            bands.append(Band(MASKED_MIDDLE, over,
                              "masked wall: over_picnum between the lower "
                              "ceiling and the higher floor "
                              "(engine.cpp:4685, 7214-7231)",
                              wall_index, "over_picnum", top, bottom))
        else:
            skipped.append("masked middle: the opening between the two "
                           "sectors has no height (engine.cpp:7214-7215)")
    else:
        skipped.append("middle: neither masked (cstat&16) nor one-way "
                       "(cstat&32), so the opening is see-through and "
                       "over_picnum is never read (engine.cpp:4685, 4938)")
    return WallDraw(wall_index, sector_index, next_sector, next_wall, picnum,
                    over, cstat, tuple(bands), tuple(skipped), sloped)


def render_slots(disk: Any) -> list[WallDraw]:
    """Every wall's drawn bands, index-aligned with `disk.walls`."""
    owners = wall_owners(disk)
    return [wall_draw(disk, index, owners) for index in range(len(disk.walls))]


# ---------------------------------------------------------------------------
# questions asked of the result
# ---------------------------------------------------------------------------

def bands_of_pair(draws: list[WallDraw], wall_index: int) -> list[Band]:
    """The bands drawn on either side of a wall: its own and its partner's."""
    own = draws[wall_index]
    out = list(own.bands)
    if 0 <= own.next_wall < len(draws):
        out.extend(draws[own.next_wall].bands)
    return out


def bands_showing_picnum(draws: list[WallDraw], wall_index: int) -> list[Band]:
    """Where, on either side, the wall's authored picnum is on screen.

    By tile VALUE: the partner drawing the same tile on its own step counts,
    because that is how the campaign's pelmets are built -- E1M1 walls
    1203-1207 wear 146 on the side that draws nothing while their partners
    1102-1106 draw 146 on the 65536-unit ceiling step above the curtain.
    """
    picnum = draws[wall_index].picnum
    return [b for b in bands_of_pair(draws, wall_index) if b.tile == picnum]


def bands_sourced_from(draws: list[WallDraw], wall_index: int) -> list[Band]:
    """The bands whose tile is READ from this wall's own picnum field.

    Its own bands, plus the partner's lower step when the partner carries
    the cstat&2 swap.
    """
    return [b for b in bands_of_pair(draws, wall_index)
            if b.source_wall == wall_index and b.field == "picnum"]


def undrawn_walls(disk: Any, *, draws: list[WallDraw] | None = None,
                  exempt: set[int] | None = None) -> list[dict[str, Any]]:
    """Walls whose authored picnum is on screen nowhere, from either side.

    The defect the reader was written for: the city's stage curtain put the
    fabric tile on unmasked two-sided walls whose neighbour's ceiling is
    higher and whose floors are flush, so no band draws on their side, and
    the partner draws the auditorium's own wall tile on the step above.

    Exempt by default: the sky family and the mirror tile, which bypass the
    wall pass on purpose; and tile 0, which is the editor's blank rather
    than an authored tile.
    """
    found = draws if draws is not None else render_slots(disk)
    skip = set(SKY_FAMILY) | {MIRROR_TILE, 0}
    if exempt:
        skip |= set(exempt)
    out = []
    for draw in found:
        if draw.picnum in skip:
            continue
        if bands_showing_picnum(found, draw.wall):
            continue
        out.append({
            "wall": draw.wall, "sector": draw.sector,
            "next_sector": draw.next_sector, "next_wall": draw.next_wall,
            "picnum": draw.picnum, "cstat": draw.cstat,
            "partner_picnum": (found[draw.next_wall].picnum
                               if 0 <= draw.next_wall < len(found) else None),
            "pair_draws": sorted({(b.band, b.tile)
                                  for b in bands_of_pair(found, draw.wall)}),
            "skipped": list(draw.skipped),
        })
    return out
