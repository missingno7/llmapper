"""Light a room the way Blood lights one: wall by wall, from its lamps.

A level can be correct in every structural sense and still read as flat, and the
reason is usually one number applied to a whole sector. `shades(value)` gives a
room one floor shade, one ceiling shade and one wall shade, so every wall in it
is lit identically and nothing in the room casts or catches anything.

The campaign does not do that. Measured over the playable sectors of all 43
maps, the **spread of shade across a single sector's walls** has a median of 12
and a q3 of 22; a quarter of rooms are near-flat (q1 is 2) and the rest are not.
The monastery's spread was 0 in every room.

The variation is not arbitrary. Splitting the campaign's walls by whether a
light sprite stands within four player widths of them:

===================================  ======  =======  =====
walls, shade relative to their room   q1      median   q3
===================================  ======  =======  =====
within four player widths of a lamp   -10.0    -0.5     0.0
further than that                      -0.5    +2.0    +8.0
===================================  ======  =======  =====

Shade is inverted in Build -- negative is brighter -- so walls near a lamp run
bright and walls away from one run dark, with about twelve shades between the
extremes. Portal walls and solid walls show no difference at all (both median
0), so it is proximity to light and not architecture that decides.

Lamps alone cannot account for it. There is about one torch per hundred
playable sectors, so most rooms have none. Two stronger groupings show up
when the campaign's rooms are split:

* by the **texture** each wall carries -- explains **52%** of the
  within-room variation;
* by the **direction each wall faces** -- explains **81%**.

Neither has a global bias. The median shade offset is 0 for every common
wall tile and for every one of the eight facing octants, so there is no rule
that north walls are dark or that brick is bright. What there is, is a rule
*within a room*: walls facing the same way share a shade, and the room has an
implied direction the light comes from. Which direction is the author's
choice and it differs room to room -- which is exactly why the octant medians
cancel to zero.

So `shade_walls_directionally` gives every room a direction and shades its
walls by how they face it: the lamp where there is one, and the widest way in
where there is not.

This is a finishing pass over an emitted level, in the same family as
`texture_align.align_wall_textures`: it changes how walls are dressed and never
what walls exist.
"""

from __future__ import annotations

from math import hypot
from typing import Any, Iterable

#: The two decoration tiles the campaign actually lights with. Both are drawn at
#: shade -128 in the great majority of their uses -- tile 506 in 132 of 138 and
#: tile 1701 in 47 of 53 -- which is what makes them glow.
#:
#: The wall sconces and emblems (2540-2545) are *not* on this list, though they
#: look like lights: the campaign draws them at shade -8, the ordinary
#: decoration value. Including them was the first version of this set and it
#: made every wall plaque a lamp.
#: Sprites that cast light: a wall torch, a hanging lantern, a chandelier.
#:
#: 641 belongs here on the same evidence the other two do -- the campaign draws
#: it at shade -128 in 86% of its 73 sprites, as it does a torch (506, 89%) and a
#: chandelier (1701, 89%), and does not do to a sconce (510, 25%) or a plaque
#: (915, 0%) -- and looking at the tile settles it: 641 is a chain with a lit
#: lamp on the end of it.
#:
#: The set used to be {506, 1701} because it was derived from what the campaign
#: *animates*, which is a different question. See `FLICKER_TILES`.
LIGHT_TILES = frozenset({506, 641, 1701})

#: Lights whose rooms the campaign gives a moving shade to. Not the same set,
#: and the difference is not an oversight::
#:
#:     tile                 lit sectors    animated
#:     506  wall torch               99         63%
#:     1701 chandelier               28         71%
#:     641  hanging lantern          59          3%
#:     (any unlit playable sector)             ~21%
#:
#: A torch and a chandelier gutter. A lantern is a flame inside a glass, and
#: Blood animates its rooms *less often than rooms with no light in them at all*
#: -- 3% against 21% -- which is far too sharp to be chance across 59 sectors.
#: Whoever built these maps was not flagging "there is a light here", they were
#: drawing the difference between an open flame and a shielded one.
FLICKER_TILES = frozenset({506, 1701})

#: How bright a sprite must be drawn to be treated as a light.
LIGHT_SHADE = -64

#: Distance over which a lamp's influence falls off, and the offsets at each end.
#:
#: These were -6 to +6 over four player widths, a twelve-unit gradient centred on
#: nothing in particular, and the far end had the wrong sign. Measuring the
#: campaign's walls against their distance from the nearest burning sprite gives
#: a curve, not a guess::
#:
#:     distance from a torch    median wall shade    n
#:     under 1 player width                     8    389
#:     1 to 3                                  17    831
#:     3 to 6                                  24    595
#:     6 or more                               28    937
#:     (a room with no light in it)            31    63,027
#:
#: Two things follow that the old constants got wrong. The pool is **twenty-three
#: shades deep**, not twelve. And *every* wall in a lit room is brighter than a
#: wall in an unlit one, even six player widths off -- so the far offset is -3,
#: not +6: a lamp lifts the whole room and then pools on top of that.
#:
#: Read as offsets from the unlit baseline of 31, the medians are -23, -14, -7,
#: -3, which a straight line from -23 to -3 over six player widths fits to
#: within two shades at every measured point.
FALLOFF = 6 * 384
NEAR_OFFSET = -23
FAR_OFFSET = -3

#: Half the shade difference between a wall facing the light and one facing
#: away. Twelve between the extremes is the campaign's median within-room spread.
DIRECTIONAL_AMPLITUDE = 6

#: Build stores shade in a signed byte.
SHADE_MIN, SHADE_MAX = -128, 127


def _sector_walls(level: Any, sector_index: int) -> range:
    sector = level.sectors[sector_index]
    fields = sector["fields"] if isinstance(sector, dict) else sector.fields
    start = int(fields["wall_ptr"])
    return range(start, start + int(fields["wall_count"]))


def _fields(item: Any) -> dict[str, Any]:
    return item["fields"] if isinstance(item, dict) else item.fields


def lights_by_sector(level: Any, *, tiles: Iterable[int] = LIGHT_TILES,
                     max_shade: int = LIGHT_SHADE) -> dict[int, list[tuple[int, int]]]:
    """Where the lamps are, indexed by the sector they stand in."""
    wanted = frozenset(int(t) for t in tiles)
    out: dict[int, list[tuple[int, int]]] = {}
    for sprite in level.sprites:
        fields = _fields(sprite)
        if int(fields["picnum"]) not in wanted:
            continue
        if int(fields["shade"]) > max_shade:
            continue
        out.setdefault(int(fields["sector"]), []).append(
            (int(fields["x"]), int(fields["y"])))
    return out


def light_offset(distance: float, *, falloff: int = FALLOFF,
                 near: int = NEAR_OFFSET, far: int = FAR_OFFSET) -> int:
    """The shade a wall takes at this distance from the nearest lamp."""
    if distance >= falloff:
        return far
    t = max(0.0, distance) / float(falloff)
    return int(round(near + (far - near) * t))


def shade_walls_by_light(level: Any, *, tiles: Iterable[int] = LIGHT_TILES,
                         falloff: int = FALLOFF, near: int = NEAR_OFFSET,
                         far: int = FAR_OFFSET) -> dict[str, Any]:
    """Vary each lit room's wall shades by distance to its lamps.

    A sector with no lamp in it is left alone rather than darkened: the campaign
    keeps a quarter of its rooms near-flat, and a room with nothing in it to cast
    light has no reason to have a gradient.

    The offset is applied to the shade the wall already carries, so an author's
    deliberate choice on one wall survives as a relative decision.
    """
    lamps = lights_by_sector(level, tiles=tiles)
    lit_rooms = 0
    touched = 0
    spreads: list[int] = []
    for index in range(len(level.sectors)):
        here = lamps.get(index)
        if not here:
            continue
        lit_rooms += 1
        before: list[int] = []
        after: list[int] = []
        for wall_index in _sector_walls(level, index):
            fields = _fields(level.walls[wall_index])
            ax, ay = int(fields["x"]), int(fields["y"])
            nxt = int(fields["point2"])
            bx, by = int(_fields(level.walls[nxt])["x"]), int(_fields(level.walls[nxt])["y"])
            mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
            distance = min(hypot(mx - lx, my - ly) for lx, ly in here)
            shade = int(fields["shade"])
            before.append(shade)
            shade = max(SHADE_MIN, min(SHADE_MAX, shade + light_offset(
                distance, falloff=falloff, near=near, far=far)))
            fields["shade"] = shade
            after.append(shade)
            touched += 1
        if after:
            spreads.append(max(after) - min(after))
    spreads.sort()
    return {
        "lit_rooms": lit_rooms,
        "walls_shaded": touched,
        "median_spread": spreads[len(spreads) // 2] if spreads else 0,
        "basis": (
            "the campaign's within-room wall shade spread has a median of 12, and "
            "walls within four player widths of a lamp sit at q1 -10 against +8 "
            "for walls beyond it"
        ),
    }


def _wall_midpoint_and_normal(level: Any, wall_index: int) -> tuple[float, float, float, float]:
    fields = _fields(level.walls[wall_index])
    ax, ay = int(fields["x"]), int(fields["y"])
    nxt = int(fields["point2"])
    bx, by = int(_fields(level.walls[nxt])["x"]), int(_fields(level.walls[nxt])["y"])
    dx, dy = bx - ax, by - ay
    length = hypot(dx, dy) or 1.0
    # Inward normal for Build's wall winding: the left-hand side of a -> b.
    return (ax + bx) / 2.0, (ay + by) / 2.0, dy / length, -dx / length


def light_direction(level: Any, sector_index: int,
                    lamps: dict[int, list[tuple[int, int]]]) -> tuple[float, float] | None:
    """Where this room's light comes from, as a unit vector.

    A lamp in the room is the answer when there is one. Otherwise the light
    comes in through the room's widest opening, which is deterministic, needs
    nothing the map does not already say, and matches how a room actually reads.
    Returns None for a sealed room with no lamp, which is left flat.
    """
    walls = _sector_walls(level, sector_index)
    xs: list[int] = []
    ys: list[int] = []
    for wall_index in walls:
        fields = _fields(level.walls[wall_index])
        xs.append(int(fields["x"]))
        ys.append(int(fields["y"]))
    if not xs:
        return None
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)

    here = lamps.get(sector_index)
    if here:
        lx = sum(p[0] for p in here) / len(here)
        ly = sum(p[1] for p in here) / len(here)
        length = hypot(lx - cx, ly - cy)
        if length > 1.0:
            return ((lx - cx) / length, (ly - cy) / length)

    widest = None
    for wall_index in walls:
        fields = _fields(level.walls[wall_index])
        if int(fields.get("next_sector", -1)) < 0:
            continue
        mx, my, _nx, _ny = _wall_midpoint_and_normal(level, wall_index)
        nxt = int(fields["point2"])
        span = hypot(int(_fields(level.walls[nxt])["x"]) - int(fields["x"]),
                     int(_fields(level.walls[nxt])["y"]) - int(fields["y"]))
        if widest is None or span > widest[0]:
            widest = (span, mx, my)
    if widest is None:
        return None
    length = hypot(widest[1] - cx, widest[2] - cy)
    if length <= 1.0:
        return None
    return ((widest[1] - cx) / length, (widest[2] - cy) / length)



#: What a room's shade spread should be, before it is halved into an amplitude.
#:
#: A single number gave every room in this level a spread of exactly 12 -- q1,
#: median, q3 and p90 all 12 -- which is the campaign's median and therefore the
#: most defensible constant available, and still wrong: the campaign's spread is
#: a *distribution*, q1 2 and q3 22 and p90 34, and 23% of its rooms are flat.
#: Applying an average everywhere produces a level with no light in it, which is
#: what "contrast 18 against 48" was measuring.
#:
#: Three things move it, all of them readable off the sector:
#:
#: ==================  =========  =============
#: split                 median    n
#: ==================  =========  =============
#: has a lamp                 24  135
#: no lamp                    12  13,114
#: 8+ walls                   19  3,894
#: fewer                       9  9,355
#: parallax ceiling           19  1,697
#: roofed                     11  11,552
#: ==================  =========  =============
#:
#: So: a base from the room's size, more if something in it is burning, more if
#: it is open to the sky. The three add because in the corpus they stack -- a big
#: outdoor room with a lamp sits near the lamp p90 of 46.
BASE_SPREAD_SMALL = 8
BASE_SPREAD_LARGE = 18
LAMP_SPREAD_BONUS = 12
OUTDOOR_SPREAD_BONUS = 8

#: Above this a sector counts as a large room for shading. The campaign's split
#: at 8 walls separates a median spread of 19 from one of 9.
LARGE_ROOM_WALLS = 8


def room_amplitude(level: Any, index: int, lamps: Any) -> int:
    """Half the shade spread this room should carry, from what it is."""
    fields = _fields(level.sectors[index])
    walls = int(fields["wall_count"])
    spread = BASE_SPREAD_LARGE if walls >= LARGE_ROOM_WALLS else BASE_SPREAD_SMALL
    if lamps.get(index):
        spread += LAMP_SPREAD_BONUS
    if int(fields.get("ceiling_stat", 0)) & 1:
        spread += OUTDOOR_SPREAD_BONUS
    return max(1, spread // 2)


def shade_walls_directionally(level: Any, *, tiles: Iterable[int] = LIGHT_TILES,
                              amplitude: int | None = None,
                              playable: Iterable[int] | None = None) -> dict[str, Any]:
    """Give every room an implied light direction and shade its walls by it.

    A wall facing the light is brightened by the room's amplitude and one facing
    away is darkened by the same, with a cosine between, so the spread across a
    room is twice its amplitude.

    That amplitude is a property of the room rather than of the pass -- see
    `room_amplitude`. Pass one explicitly to override every room with it, which
    is what this used to do to all of them.

    The offset is added to whatever shade the wall already carries, so this
    modulates an author's choice rather than replacing it.
    """
    lamps = lights_by_sector(level, tiles=tiles)
    allowed = None if playable is None else {int(i) for i in playable}
    lit = 0
    touched = 0
    spreads: list[int] = []
    for index in range(len(level.sectors)):
        if allowed is not None and index not in allowed:
            continue
        direction = light_direction(level, index, lamps)
        if direction is None:
            continue
        lit += 1
        room = amplitude if amplitude is not None else room_amplitude(level, index, lamps)
        after: list[int] = []
        for wall_index in _sector_walls(level, index):
            fields = _fields(level.walls[wall_index])
            _mx, _my, nx, ny = _wall_midpoint_and_normal(level, wall_index)
            # A wall whose inward normal points back along the light faces it.
            facing = -(nx * direction[0] + ny * direction[1])
            shade = int(fields["shade"]) - int(round(room * facing))
            fields["shade"] = max(SHADE_MIN, min(SHADE_MAX, shade))
            after.append(int(fields["shade"]))
            touched += 1
        if after:
            spreads.append(max(after) - min(after))
    spreads.sort()
    return {
        "rooms_shaded": lit,
        "walls_shaded": touched,
        "median_spread": spreads[len(spreads) // 2] if spreads else 0,
        "spread_q1": spreads[len(spreads) // 4] if spreads else 0,
        "spread_q3": spreads[3 * len(spreads) // 4] if spreads else 0,
        "basis": (
            "wall facing explains 81% of the campaign's within-room shade "
            "variation, with no global bias -- every facing octant has a median "
            "offset of 0, so the direction is chosen per room; the amplitude "
            "comes from the room's size, its lamps and whether it is open to sky"
        ),
    }




#: What a Blood sector's shade is, given only what kind of space it is.
#:
#: A level should not be a list of shade numbers. This project's was: fifty-nine
#: `shades(N)` calls and fourteen `sky_shades(N)`, each a judgement about how
#: dark one room ought to be relative to the others, none of them checkable and
#: all of them in the author's way.
#:
#: They are also, mostly, not judgements. Grouping the campaign's 13,649
#: playable sectors by what they *are* accounts for nearly all of the variation::
#:
#:     roofed                      median 32
#:     open to the sky             median 16
#:     over 100 player widths sq   median 24  (against 30-31 for anything smaller)
#:     containing a flame          median 16  (against 30 without)
#:
#: The last of those is not an authoring decision at all -- it is what happens
#: when you put a torch in a room, and `bloodmap.lightbomb` now derives it by
#: casting the light. The other three are properties the region already
#: declares: whether its ceiling is parallax, and how big its floor is.
#:
#: So the author says what the room is and this says what shade it is. Anything
#: that genuinely wants a number -- a stair's shade ramp, say -- still passes
#: one, and an explicit value is never overwritten.
ROOFED_SHADE = 32
OUTDOOR_SHADE = 16

#: Above this a space is a hall, and the campaign lights it about seven shades
#: brighter than a room. In player widths squared.
HALL_AREA = 100.0
HALL_RELIEF = 7

#: The campaign's own relations between the three surfaces of a sector: the
#: median wall carries exactly its floor's shade, a roofed ceiling two more, and
#: a parallax ceiling is 0 in the q1, the median and the q3 alike -- it is the
#: sky's brightness rather than a surface's.
WALL_OVER_FLOOR = 0
CEILING_OVER_FLOOR = 2
PARALLAX_CEILING_SHADE = 0


def derived_shade(*, outdoor: bool, area_player_widths: float) -> dict[str, int]:
    """Floor, ceiling and wall shade for a space of this description."""
    floor = OUTDOOR_SHADE if outdoor else ROOFED_SHADE
    if area_player_widths > HALL_AREA:
        floor -= HALL_RELIEF
    ceiling = PARALLAX_CEILING_SHADE if outdoor else floor + CEILING_OVER_FLOOR
    return {
        "floor_shade": floor,
        "ceiling_shade": ceiling,
        "wall_shade": floor + WALL_OVER_FLOOR,
    }


#: What the campaign's surfaces actually sit at, over 108,504 walls and 13,649
#: playable sectors::
#:
#:     surface     q1   median   q3
#:     wall        20       31   39
#:     floor       18       30   38
#:     ceiling     20       34   42
#:
#: This level sat at 18 / 22 / 16 -- between eight and eighteen shades brighter
#: than Blood everywhere at once, which is not a style, it is a level with the
#: lights left on. It matters more than it sounds: a frame's contrast is the
#: spread between its brightest and darkest surface, and the campaign's bright
#: end is a sprite drawn fullbright at -128 while its dark end is a wall at 30 or
#: 40 or 60. This level had the same fullbright sprites -- more of them per
#: sector than the campaign's q3 -- and nothing dark for them to be bright
#: against, so its frames measured a contrast of 33 against E1M1's 55.
CORPUS_SHADE = {"wall": 31, "floor": 30, "ceiling": 34}


def match_corpus_shade(level: Any, *, targets: dict[str, int] | None = None,
                       playable: Iterable[int] | None = None) -> dict[str, Any]:
    """Slide each family of surfaces until its median is the campaign's.

    One offset per family, so every relative decision an author made -- a dark
    crypt, a lit chapel, the gradient a lamp casts -- survives intact. Only the
    level's overall exposure moves.

    Parallax ceilings are left alone: their shade is the sky's brightness rather
    than a surface's, and the campaign's night sky is not lit like its masonry.
    """
    want = dict(CORPUS_SHADE if targets is None else targets)
    allowed = None if playable is None else {int(i) for i in playable}
    walls: list[Any] = []
    floors: list[Any] = []
    ceilings: list[Any] = []
    for index in range(len(level.sectors)):
        if allowed is not None and index not in allowed:
            continue
        fields = _fields(level.sectors[index])
        floors.append(fields)
        if not int(fields.get("ceiling_stat", 0)) & 1:
            ceilings.append(fields)
        for wall_index in _sector_walls(level, index):
            walls.append(_fields(level.walls[wall_index]))

    def median(values: list[int]) -> int:
        ordered = sorted(values)
        return ordered[len(ordered) // 2] if ordered else 0

    report: dict[str, Any] = {}
    for name, holders, key in (("wall", walls, "shade"),
                               ("floor", floors, "floor_shade"),
                               ("ceiling", ceilings, "ceiling_shade")):
        if not holders:
            continue
        offset = int(want[name]) - median([int(h[key]) for h in holders])
        for holder in holders:
            holder[key] = max(SHADE_MIN, min(SHADE_MAX, int(holder[key]) + offset))
        report[f"{name}_offset"] = offset
        report[f"{name}_surfaces"] = len(holders)
    report["basis"] = (
        "the campaign's median playable wall, floor and ceiling shades are 31, "
        "30 and 34; a level brighter than that has no dark for its fullbright "
        "sprites to read against"
    )
    return report



#: What the campaign's underwater sectors sit at: floor shade median 26 (q1 16,
#: q3 35) and ceiling 30, over 618 sectors. This level's flooded run was at 52
#: and 57 -- so dark that the only thing you could tell about it was that you
#: were in it.
UNDERWATER_SHADE = {"floor": 26, "ceiling": 30}

#: Light moving on water. 112 of the campaign's 618 underwater sectors animate
#: their shade, 69 of them on wave 7 -- `flicker2`, the same irregular table its
#: torches use -- at a median amplitude of -4.
#:
#: -4 rather than a torch's larger swing: this is not a flame guttering, it is
#: the surface above breaking up the light, and it should read as movement
#: without the room appearing to pulse.
RIPPLE_WAVE = 7
RIPPLE_AMPLITUDE = -4
RIPPLE_FREQUENCY = 3


def ripple_underwater_sectors(level: Any, *, wave: int = RIPPLE_WAVE,
                              amplitude: int = RIPPLE_AMPLITUDE,
                              frequency: int = RIPPLE_FREQUENCY) -> dict[str, Any]:
    """Move the shade of every sector that is under water.

    `sectorfx.cpp` adds ``GetWaveValue(wave, phase * 8 + freq * totalclock,
    amplitude)`` to a sector's shade each tick, and `shadeAlways` is what makes
    it run when nothing has triggered the sector -- water is not triggered by
    anything, so without it the surface would be still.

    Each sector gets its own phase, so a run of flooded rooms ripples out of step
    rather than pulsing as one object.
    """
    touched = 0
    for index in range(len(level.sectors)):
        sector = level.sectors[index]
        if not isinstance(sector, dict):
            continue
        blood = sector.get("blood")
        if not blood:
            continue
        extra = blood["fields"]
        if not int(extra.get("underwater", 0) or 0):
            continue
        extra.update(
            shade_wave=int(wave),
            amplitude=int(amplitude),
            shade_frequency=int(frequency),
            shade_always=1,
            shade_floor=1,
            shade_ceiling=1,
            shade_walls=1,
            shade_phase=(index * 71) % 256,
        )
        touched += 1
    return {
        "sectors_rippled": touched,
        "basis": (
            "112 of the campaign's 618 underwater sectors animate their shade, "
            "69 on wave 7 at a median amplitude of -4"
        ),
    }


#: A torch flickers. `sectorfx.cpp` drives sector shade from a wave table, and
#: wave 7 is `flicker2` -- an irregular table, not a sine -- which the campaign
#: reaches for more than any other: 1,205 of its 2,823 animated sectors.
FLICKER_WAVE = 7

#: Amplitude is added to the sector's shade, and shade is inverted, so a
#: negative amplitude brightens. -4 is the campaign's commonest value (453) and
#: sits at the subtle end; -48 is its other cluster, a slow deep pulse.
FLICKER_AMPLITUDE = -4

#: Ticks per cycle. With wave 7 the campaign clusters at 5, 4 and 2.
FLICKER_FREQUENCY = 4

#: Without this the effect only runs while the sector is *busy* -- that is,
#: while it is moving. 1,194 of the campaign's animated sectors leave it clear
#: for exactly that reason, and they are lifts and doors. A room that just has a
#: torch in it needs it set, or nothing happens at all.
SHADE_ALWAYS = 1

#: Phase is what stops every torch in a level pulsing in unison. The campaign
#: uses 148 distinct values from 0 to 255 across its 1,629 always-on sectors.
PHASE_MODULUS = 256

#: An odd multiplier, so consecutive sectors land far apart in phase rather than
#: in a visible ramp.
PHASE_STRIDE = 71


def flicker_lit_sectors(level: Any, *, tiles: Iterable[int] = FLICKER_TILES,
                        amplitude: int = FLICKER_AMPLITUDE,
                        wave: int = FLICKER_WAVE,
                        frequency: int = FLICKER_FREQUENCY) -> dict[str, Any]:
    """Give every room with a lamp in it an animated shade.

    Blood animates the shade of **20.7%** of its playable sectors -- a median of
    17% per map -- and the presence of a lamp more than triples the odds: 65% of
    campaign sectors containing a torch or hanging lamp are animated, against 20%
    of those without. A level whose every room is lit at one fixed number is
    missing an effect the game uses in one room in five.

    The form is the campaign's modal one for a lit room: wave 7 (`flicker2`),
    a small negative amplitude, all three surfaces, `shadeAlways` set, and a
    per-sector phase so the torches do not breathe together.

    This runs after `shade_walls_directionally`, and does not conflict with it:
    that pass sets the *base* shade each wall rests at, and this adds a moving
    offset on top at run time.
    """
    # The XSECTOR is allocated here rather than through `LevelBuilder`, which
    # deep-copies the level it is handed: routing this pass through it mutated a
    # throwaway and reported nine sectors changed while the emitted map had
    # none. A finishing pass has to edit the level it was given.
    from .construction import _empty_fields
    from .format import XSECTOR_SCHEMA

    lamps = lights_by_sector(level, tiles=tiles)
    used = {int(_fields(s)["extra"]) for s in level.sectors if int(_fields(s)["extra"]) > 0}
    touched = 0
    for index in sorted(lamps):
        if not 0 <= index < len(level.sectors):
            continue
        sector = level.sectors[index]
        if not isinstance(sector, dict):
            continue
        if sector.get("blood") is None:
            extra_id = 1
            while extra_id in used:
                extra_id += 1
            if extra_id >= 1024:
                break
            used.add(extra_id)
            blood_fields = _empty_fields(XSECTOR_SCHEMA)
            blood_fields["reference"] = index
            blood_fields.update(marker_0=-1, marker_1=-1)
            sector["fields"]["extra"] = extra_id
            sector["blood"] = {"kind": "XSECTOR", "fields": blood_fields,
                               "opaque_tail_hex": ""}
        sector["blood"]["fields"].update(
            amplitude=int(amplitude), shade_wave=int(wave),
            shade_frequency=int(frequency), shade_always=SHADE_ALWAYS,
            shade_floor=1, shade_ceiling=1, shade_walls=1,
            shade_phase=(index * PHASE_STRIDE) % PHASE_MODULUS,
        )
        touched += 1
    return {
        "sectors_flickering": touched,
        "share_of_sectors": round(touched / max(1, len(level.sectors)), 3),
        "basis": (
            "20.7% of campaign playable sectors animate their shade, and 65% of "
            "those containing a lamp do; wave 7 is flicker2, its commonest"
        ),
    }
