"""Exact motion parameters for Duke3D's hardcoded moving sectors.

Duke3D does not let a mapper state how far a door travels.  Every moving
sector in the classic game runs a *hardcoded* routine whose extent, speed and
direction are recovered from a handful of fields that do not look like motion
fields at all: the sector's ``extra``, the effector's ``ang``, its ``pal``, and
in one case a hardcoded constant in ``actors.cpp``.  Blood is the opposite: its
``kSectorSlide``/``kSectorRotate`` sectors read the extent straight out of a
marker sprite, so any angle and any distance is expressible.

Converting one to the other therefore needs Duke's constants written down
rather than guessed, which is what this module is.  Every number below is cited
to the EDuke32 file and function it comes from.

The two engines agree on one thing exactly, and that agreement is what makes a
faithful conversion possible at all:

``A_MoveSector`` (``actors.cpp``) places **every** wall of the sector at
``effector.xy + rotate(origin[w], T3)`` where ``origin[w]`` was captured at
spawn as ``wall[w].xy - effector.xy``.  Blood's ``TranslateSector``
(``triggers.cpp``) with ``bAllWalls`` set does the same thing.  ``bAllWalls`` is
true exactly for ``kSectorSlide`` (616) and ``kSectorRotate`` (617), which is
why those two are the right targets for the effectors that call
``A_MoveSector``, and why SE20 -- which does *not* call it -- is not one of them.

.. rubric:: Timebase

Duke's effectors run at 30 Hz.  Blood's ``busyTime`` is in tenths of a second
(``triggers.cpp`` computes delays as ``(120 * busyTime) / 10`` tics at 120 Hz).
So a Duke motion lasting *n* effector ticks lasts ``n / 30`` seconds and wants
``busyTime = n / 3``.
"""

from __future__ import annotations

from typing import Any
from math import ceil

from .duke import DukeDiskMap
from .duke_semantics import GPSPEED_TILE

#: ``premap.cpp`` initialises every sector's ``extra`` to this before a GPSPEED
#: sprite in the sector overrides it.  ``game.cpp`` then copies it into the
#: effector as ``sprite.yvel``, which the movement code reads through ``SP(i)``.
#: Every SE11/SE15/SE20/SE0 in the 52-map corpus has ``y_velocity == 0`` on
#: disk, so the map file never carries this value: it is always the sector's.
DEFAULT_SECTOR_EXTRA = 256

#: Duke effector ticks per second.
DUKE_TICKS_PER_SECOND = 30

#: ``actors.cpp`` SE_11: the swing stops at ``t_data[4] <= -511 || >= 512``.
#: Unlike ST30 this bound is a constant, so a swinging door is always a quarter
#: turn no matter what the sector's ``extra`` says.
SWING_ANGLE = 512

#: ``A_MoveSector`` translation step for SE15, from ``pSprite->xvel = 16``.
SLIDE_STEP = 16

#: ``A_MoveSector`` translation step for SE20, from ``pSprite->xvel = +/-8``.
STRETCH_STEP = 8


def sector_extra(duke: DukeDiskMap, sector_id: int) -> int:
    """The value the engine will have in ``sector.extra`` at effector spawn.

    A GPSPEED sprite (tile 10) in the sector sets it; otherwise it keeps
    ``premap.cpp``'s 256.  This is the single number behind every hardcoded
    extent and speed below, which is why it is worth naming.
    """
    speeds = [
        int(sprite.lotag)
        for sprite in duke.sprites
        if sprite.picnum == GPSPEED_TILE and sprite.sector == sector_id
    ]
    return speeds[-1] if speeds else DEFAULT_SECTOR_EXTRA


def busy_time(ticks: int) -> int:
    """Blood ``busyTime`` (tenths of a second) for a Duke motion of *ticks*."""
    return max(1, min(4095, int(round(ticks / 3.0))))


def swinging_door(duke: DukeDiskMap, sprite: Any) -> dict[str, int]:
    """SE11 / ST23: a quarter turn about the effector sprite.

    ``game.cpp`` spawn sets ``T4 = (ang > 1024) ? 2 : -2``; ``actors.cpp`` then
    steps ``t_data[2] += (SP(i) >> 3) * T4`` per tick and stops at 512.  So the
    hinge is the effector. ST23 reverses T4 before moving, so the first
    operation turns negative for ``ang > 1024``, positive otherwise.
    """
    extra = sector_extra(duke, sprite.sector)
    # ST23 negates the spawn T4 BEFORE the first movement (sector.cpp).
    direction = -1 if int(sprite.angle) > 1024 else 1
    step = max(1, (extra >> 3) * 2)
    ticks = max(1, ceil((511 if direction < 0 else 512) / step))
    # The final A_MoveSector follows T3 &= 0xffffff00, including signed floor.
    angle = ((direction * ticks * step) // 256) * 256
    return {
        "angle": angle,
        "direction": direction,
        "step_per_tick": step,
        "ticks": ticks,
        "sector_extra": extra,
    }


def tagged_z_motion(duke: DukeDiskMap, sector_id: int) -> dict[str, Any]:
    """Transcribe ST16-22 endpoints and SetAnimation's extra*4 Z step at 30Hz."""
    sector = duke.sectors[sector_id]
    tag = int(sector.lotag) & 0x3fff
    if tag not in {16, 17, 18, 19, 20, 21, 22}:
        raise ValueError(f"ST{tag} is not a tagged Z motion")
    neighbors = [duke.sectors[i] for i in dict.fromkeys(
        int(duke.walls[w].next_sector)
        for w in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
        if duke.walls[w].next_sector >= 0)]
    ceiling, floor = int(sector.ceiling_z), int(sector.floor_z)
    on_ceiling, on_floor = ceiling, floor
    def neighbor(surface, z, direction):
        values = [int(getattr(n, surface + "_z")) for n in neighbors]
        values = [v for v in values if (v > z if direction > 0 else v < z)]
        if not values:
            raise ValueError(f"No {surface} neighbor {'below' if direction > 0 else 'above'} Z {z}")
        return min(values) if direction > 0 else max(values)
    # prelevel sets the open bit on ordinary ST20/ST22 with a positive gap.
    opened = bool(int(sector.lotag) & 0x8000) or (int(sector.lotag) in {20, 22} and floor > ceiling)
    if tag in {16, 17}:
        try:
            on_floor = neighbor("floor", floor, 1)
        except ValueError:
            on_floor = neighbor("floor", floor, -1)
    elif tag in {18, 19}:
        try:
            on_floor = neighbor("floor", floor, -1)
        except ValueError:
            on_floor = neighbor("floor", floor, 1)
        on_ceiling = ceiling + on_floor - floor
    elif tag == 20:
        if opened:
            # SE9 supplies a closing height instead of the floor, when present.
            light = next((s for s in reversed(duke.sprites) if s.picnum == 1 and s.lotag == 9 and s.sector == sector_id), None)
            on_ceiling = int(light.z) if light else floor
        else:
            try:
                on_ceiling = neighbor("ceiling", ceiling, -1)
            except ValueError:
                on_ceiling = floor  # REDODOOR's explicit fallback.
    elif tag == 21:
        on_floor = neighbor("floor", ceiling, 1) if floor == ceiling else ceiling
    else:
        if opened:
            on_ceiling = on_floor = (ceiling + floor) >> 1
        else:
            on_ceiling = neighbor("ceiling", ceiling, -1)
            on_floor = neighbor("floor", floor, 1)
    speed = sector_extra(duke, sector_id)
    if speed <= 0:
        raise ValueError(f"Non-positive GPSPEED/sector extra {speed}; no invented velocity")
    distances = {"ceiling": abs(on_ceiling-ceiling), "floor": abs(on_floor-floor)}
    ticks = {k: ceil(v / (speed * 4)) for k, v in distances.items() if v}
    return {"tag": tag, "off_ceiling_z": ceiling, "on_ceiling_z": on_ceiling,
            "off_floor_z": floor, "on_floor_z": on_floor, "speed": speed,
            "ticks": max(ticks.values(), default=0), "surface_ticks": ticks,
            "kind": {16:"platform",17:"platform",18:"elevator",19:"elevator",
                     20:"ceiling-door",21:"floor-door",22:"splitting-door"}[tag]}


def sliding_door(duke: DukeDiskMap, sprite: Any) -> dict[str, int]:
    """SE15 / ST25: a rigid translation along the effector's angle.

    ``actors.cpp`` runs ``t_data[3]`` from 0 to ``SP(i) >> 3`` while
    ``A_MoveSector`` advances the effector 16 units per tick, so the leaf
    travels ``16 * (extra >> 3)`` units -- 512 at the default extra, not the
    sprite's texture repeat.  Operating the door adds 1024 to the effector
    angle (``sector.cpp`` ST_25), which is how the same effector runs the
    return trip; Blood expresses that as the pair of markers instead.
    """
    extra = sector_extra(duke, sprite.sector)
    ticks = max(1, extra >> 3)
    return {
        "distance": SLIDE_STEP * ticks,
        # ST25 adds 1024 before its first A_MoveSector, not after travel.
        "angle": (int(sprite.angle) + 1024) & 2047,
        "ticks": ticks,
        "sector_extra": extra,
    }


def stretch_bridge(duke: DukeDiskMap, sprite: Any) -> dict[str, Any]:
    """SE20 / ST27: the one moving sector that is *not* a rigid body.

    SE20 never calls ``A_MoveSector``.  ``game.cpp`` spawn records the two walls
    of the sector nearest the effector into ``T2``/``T3``, and ``actors.cpp``
    drags only those two, 8 units per tick along the effector angle, until
    ``t_data[3]`` reaches ``SP(i)``.  The rest of the sector stays put, so the
    sector stretches rather than moves.

    That is Blood's ``kSectorSlideMarked`` (614) exactly: ``TranslateSector``
    with ``bAllWalls`` clear moves only the walls flagged ``cstat & 16384``.
    Lowering SE20 to 616 would move the whole bridge instead of extending it.
    """
    extra = sector_extra(duke, sprite.sector)
    ticks = max(1, extra // STRETCH_STEP)
    return {
        "distance": STRETCH_STEP * ticks,
        "angle": int(sprite.angle) & 2047,
        "ticks": ticks,
        "walls": nearest_walls(duke, sprite, count=2),
        "sector_extra": extra,
    }


def rotate_rise_bridge(duke: DukeDiskMap, sprite: Any, pivot: Any) -> dict[str, int]:
    """SE0 in an ST30 sector: rotate about the SE1 pivot *and* change floor Z.

    ``actors.cpp`` runs ``tempang`` 0 -> 256 in steps of 4 -- always 64 ticks --
    while adding ``l * (extra >> 5)`` to the rotation each tick, so the total
    turn is ``2 * extra`` rather than a constant: a quarter turn at the default
    extra, and proportionally less if a GPSPEED slows it down.

    In the same loop the sector's ``floorz`` walks toward the effector's ``z``
    at 512 units per tick.  Blood's ``RDoorBusy`` calls ``ZTranslateSector``
    beside ``TranslateSector``, so one type-617 sector reproduces both halves --
    but only if the caller supplies the floor endpoint as well as the marker.

    Direction is ``clipdist``, which spawn sets from the effector's ``pal``.

    The centre is the subtle part. The ST30 branch of the movement code never
    touches the effector's position -- it leaves ``xvel`` at 0 and never assigns
    ``sprite->x`` from the pivot, unlike the orbiting branch -- so the sector
    turns about *the effector*, wherever that is. Spawn moves the effector onto
    the pivot only when its angle is exactly 512. An SE0 authored at any other
    angle therefore turns about itself, and using the pivot for it swings the
    sector through an arc it never travels.
    """
    extra = sector_extra(duke, sprite.sector)
    direction = 1 if int(sprite.pal) else -1
    ticks = 64
    snapped = int(sprite.angle) == 512
    centre_x = int(pivot.x) if snapped else int(sprite.x)
    centre_y = int(pivot.y) if snapped else int(sprite.y)
    return {
        "angle": (64 * (extra >> 5)) * direction,
        "direction": direction,
        "ticks": ticks,
        "floor_z": int(sprite.z),
        "sector_extra": extra,
        "snapped_to_pivot": snapped,
        "centre_x": centre_x,
        "centre_y": centre_y,
        "pivot_x": int(pivot.x),
        "pivot_y": int(pivot.y),
    }


def rotating_sector(duke: DukeDiskMap, sprite: Any, pivot: Any) -> dict[str, int]:
    """SE0 outside ST30: a continuous turn about the SE1 pivot.

    There is no extent.  ``actors.cpp`` adds ``l * (extra >> 3)`` every tick for
    as long as the pivot's ``t_data[0]`` is set, and the direction comes from
    the *pivot's* angle rather than the effector's.  A full turn therefore takes
    ``2048 / (extra >> 3)`` ticks, which is the only figure a bounded Blood
    rotation can be built from.

    Spawn snaps the effector onto the pivot when its angle is 512, which is how
    196 of the corpus's 210 SE0s are authored; the rest orbit at a radius.
    Either way the motion is a rigid turn about the pivot.
    """
    extra = sector_extra(duke, sprite.sector)
    direction = -1 if int(pivot.angle) > 1024 else 1
    step = max(1, extra >> 3)
    return {
        "step_per_tick": step,
        "direction": direction,
        "ticks_per_turn": max(1, 2048 // step),
        "sector_extra": extra,
        "pivot_x": int(pivot.x),
        "pivot_y": int(pivot.y),
        "snapped_to_pivot": int(sprite.angle) == 512,
    }


def sepldist(dx: int, dy: int) -> int:
    """Build's ``FindDistance2D``, which is not the Euclidean one.

    ``build/include/common.h`` calls it "Ken's reverse-engineering job": an
    octagonal approximation good to a few percent.  SE20 picks the walls it
    drags with this, so ranking by true distance can choose a different pair
    for a wall that sits near the boundary between two candidates.
    """
    x, y = abs(int(dx)), abs(int(dy))
    if not y:
        return x
    if not x:
        return y
    if x < y:
        x, y = y, x
    y += y >> 1
    return x - (x >> 5) - (x >> 7) + (y >> 2) + (y >> 6)


def nearest_walls(duke: DukeDiskMap, sprite: Any, *, count: int = 2) -> list[int]:
    """The *count* walls of the effector's sector nearest to it.

    ``game.cpp`` picks these one at a time with ``FindDistance2D``, keeping a
    strictly smaller distance, so ties resolve to the lower wall index.
    Sorting by ``(distance, index)`` reproduces that.
    """
    sector = duke.sectors[sprite.sector]
    start = int(sector.wall_ptr)
    end = start + int(sector.wall_count)
    ranked = sorted(
        range(start, end),
        key=lambda w: (
            sepldist(int(sprite.x) - int(duke.walls[w].x), int(sprite.y) - int(duke.walls[w].y)),
            w,
        ),
    )
    return ranked[:count]
