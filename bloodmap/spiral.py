"""A spiral stair, and the observation that it is nothing new.

A helix overlaps itself, but only across turns. Cut it into turns and every
piece is planar. So a spiral is not an exception to the layer model, it is the
layer model applied to one structure: the overlap is strictly between turns, the
stair is its own connector, and adjacent steps never share ground.

E3M1's spiral says so exactly. Sectors 15-40, twenty-six of them, and the pairs
that overlap are 15x30, 16x31, 17x32, 18x33 -- always the same offset, one full
turn apart. Twenty-four pairs, every one of them `vertically_disjoint`, fifteen
to sixteen portal hops apart because the walk between them goes all the way
round. Nothing in `bloodmap.overlap_visibility` special-cases any of it.

What E3M1's spiral is made of
-----------------------------

Measured, not remembered::

    rise per step      2048 z, exactly -- 23 of them, plus two flat joints
    turn per step      22.5 degrees, so 16 steps to a full turn
    rise per turn      32,768 z -- one wall-texture repeat
    clear height       24,576 z, constant; the ceiling tracks the floor
    footprint          6.67 x 6.70 body widths
    radius             0.65 body widths inner, 3.58 outer
    step               4 walls, about 2 body areas
    surfaces           floor 390 on the steps, 304 on the landings
    joins the map      at two places only, one at each end

And the safety is arithmetic rather than judgement. Clear height is 24,576 and
the rise per turn is 32,768, so the ceiling of one turn sits **8,192** below the
floor of the next -- which is also, exactly, the slab BB4 puts between its
storeys. The bands are disjoint before anyone thinks about it.

Three numbers to be careful with
--------------------------------

The clear height is **1.45 player heights**, not 4.36. 24,576 / 5,632 is 4.36,
and 5,632 is ``0x1600`` -- an offset from a sprite's centre that this project
mistook for the standing body for a long time. The body is 16,960. The same
constant turns E3M1's 47,104-unit climb into "9 player heights"; it is 2.78.
Anywhere a spiral number looks three times too large, that is why.

What the author states, and what is derived
-------------------------------------------

Not "how many turns". A designer knows two things: how high it has to climb, and
which way the player is facing when they step off. Turns are a consequence.

Total rise `R`, swept angle `A`, step rise `r` and step angle `a` are bound by
``R/A = r/a`` -- E3M1 sits at 91 z per degree. Fix the endpoints and the
steepness is decided before a single step exists. The one free variable is how
many whole turns to add before the exit angle::

    A = 360*k + exit_angle,    k = 0, 1, 2, ...

Every `k` lands the player facing the same way and they differ only in
steepness, so :func:`spiral_stair` derives `k` and says which it chose and why.

It derives against the **corpus's own step rise**, not against the player's
limit. `max_step` is 4,096 and a stair built to it is a ladder: it is used here
only as the refusal threshold. The target is E3M1's 2,048.

Tread depth is the constraint nobody thinks of. Depth at a radius is
``radius * step_angle`` in radians, so a small radius with a wide step angle
gives an inner tread nobody can stand on. E3M1 runs 97 units at the newel and
540 at the outer wall against a 384-unit body -- you walk the outside, which is
how spirals work. The minimum radius is therefore derived from the step angle
rather than left to the author to get wrong.

One thing that did not survive contact with the geometry
--------------------------------------------------------

"One layer per turn" is the right description and the wrong declaration. A turn
is a helical ramp, not a slab: its sixteen steps span 32,768 of floor, so the
band of a whole turn is 32,768 + 24,576 = **57,344** tall against a pitch of
32,768, and two consecutive turn-bands necessarily intersect. Declaring them as
`bloodmap.layers` bands would trip `layer-bands-intersect` correctly.

What is actually disjoint is each *pair* -- step `i` against step `i+16` -- and
that is what `overlap_visibility` checks, per pair, with no knowledge that a
helix is involved. So the turn is recorded on each step as intent, and the
safety is left where it really lives. The claim "nothing special-cases a helix"
survives; the claim "a turn is a layer" does not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .planar_geom import area2
from .vocabulary import Anchor, Structure, VocabularyError

#: One standing Blood human and one body width. `bloodmap.player_space`.
PLAYER_HEIGHT = 16960
PLAYER_WIDTH = 384

#: E3M1, measured. Sixteen steps to a turn.
STEP_ANGLE = 22.5
#: The rise a spiral step actually uses in the corpus. `vocabulary.staircase`
#: defaults to 4096 because that is the commonest rise for a *straight* run;
#: E3M1's spiral uses 2048 for all twenty-three of its steps.
TARGET_STEP_RISE = 2048
#: The player's maximum step. Used only to refuse, never as a target: a stair
#: built to the limit is a ladder.
MAX_STEP = 4096
#: 16 * 2048. One wall-texture repeat, which is the unit this project builds on.
RISE_PER_TURN = STEP_ANGLE and int(360 / STEP_ANGLE) * TARGET_STEP_RISE

#: Constant, and the ceiling tracks the floor step for step. 1.45 player heights.
CLEAR_HEIGHT = 24576

#: E3M1's radii, in Build units. The inner one is a newel: nothing in that map
#: contains the axis point, so the middle is solid masonry rather than a void.
INNER_RADIUS = 248
OUTER_RADIUS = 1375

#: E3M1's surfaces: the steps and the landings are deliberately different.
STEP_FLOOR_PICNUM = 390
LANDING_FLOOR_PICNUM = 304


class SpiralError(VocabularyError):
    """A spiral the corpus does not support, named precisely enough to fix."""


@dataclass(frozen=True)
class SpiralPlan:
    """What the parameters worked out to, before any geometry exists."""

    steps: int
    turns: float
    swept_degrees: float
    step_rise: int
    step_angle: float
    total_rise: int
    inner_radius: int
    outer_radius: int
    clear_height: int
    handed: int
    entry_angle: float
    exit_angle: float
    why: str

    @property
    def inner_tread(self) -> float:
        return self.inner_radius * math.radians(self.step_angle)

    @property
    def outer_tread(self) -> float:
        return self.outer_radius * math.radians(self.step_angle)

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": self.steps, "turns": round(self.turns, 3),
            "swept_degrees": round(self.swept_degrees, 2),
            "step_rise": self.step_rise, "step_angle": round(self.step_angle, 3),
            "total_rise": self.total_rise,
            "rise_bodies": round(abs(self.total_rise) / PLAYER_HEIGHT, 2),
            "inner_radius": self.inner_radius, "outer_radius": self.outer_radius,
            "inner_tread": round(self.inner_tread),
            "outer_tread": round(self.outer_tread),
            "clear_height": self.clear_height, "handed": self.handed,
            "entry_angle": self.entry_angle, "exit_angle": self.exit_angle,
            "why": self.why,
        }


def minimum_radius(step_angle: float = STEP_ANGLE,
                   body: int = PLAYER_WIDTH) -> int:
    """The smallest outer radius whose tread a body can stand on.

    ``tread = radius * step_angle`` in radians, so this inverts it. At E3M1's
    22.5 degrees a 384-unit body needs 978 units of radius; below that the outer
    tread is narrower than the player and the stair is a ladder with a curve.
    """
    return int(math.ceil(body / math.radians(step_angle)))


def plan_spiral(*, rise: int, exit_angle: float, radius: int = OUTER_RADIUS,
                step_angle: float = STEP_ANGLE, handed: str = "right",
                entry_angle: float = 0.0,
                clear_height: int = CLEAR_HEIGHT) -> SpiralPlan:
    """Work out the turns, steps and step rise from what the design actually knows.

    `rise` is positive downward, in Blood's sense, so a climb from a cellar to a
    loft is negative. `exit_angle` is where the player is facing when they step
    off, relative to the entry.
    """
    if rise == 0:
        raise SpiralError("a spiral has to change height")
    if clear_height <= PLAYER_HEIGHT:
        raise SpiralError(
            f"a clear height of {clear_height} is under one standing body "
            f"({PLAYER_HEIGHT}); nothing could walk the stair")
    smallest = minimum_radius(step_angle)
    if radius < smallest:
        raise SpiralError(
            f"an outer radius of {radius} gives a tread of "
            f"{radius * math.radians(step_angle):.0f} units at {step_angle} "
            f"degrees a step, and a body is {PLAYER_WIDTH} across. Either widen "
            f"the radius to at least {smallest}, or narrow the step angle -- "
            "those two and the rise cannot all be honoured as given")

    wanted = float(exit_angle) % 360.0
    per_turn_steps = 360.0 / step_angle
    best: tuple[float, int, float, int] | None = None
    too_shallow = False
    for turns in range(0, 9):
        swept = 360.0 * turns + wanted
        if swept <= 0:
            continue
        # The landings take an angular slot each, so the author's exit angle is
        # where the *top landing's* far edge lands -- otherwise asking for 180
        # quietly delivered 225 and the parameter meant nothing.
        slots = int(round(swept / step_angle))
        steps = slots - 2
        if steps < 2:
            continue
        step_rise = int(round(rise / steps))
        if abs(step_rise) > MAX_STEP:
            continue
        # A spiral is only safe if it climbs more in a turn than it is tall.
        #
        # This is the law the sweep found and the one instance hid. Once a
        # spiral passes a full turn, step `i` sits directly under step `i+16`,
        # and their bands are disjoint only when the rise per turn clears the
        # clear height. E3M1 makes 32,768 a turn against a 24,576 stair -- 8,192
        # of slab, the same figure BB4 puts between its storeys. Shallower than
        # that and the turns interpenetrate: a wide, lazy spiral is not a gentler
        # version of a steep one, it is a broken one.
        rise_per_turn = abs(step_rise) * per_turn_steps
        if swept > 360.0 and rise_per_turn <= clear_height:
            too_shallow = True
            continue
        # Nearest to the corpus's own spiral rise, not to the player's limit.
        score = abs(abs(step_rise) - TARGET_STEP_RISE)
        if best is None or score < best[0]:
            best = (score, steps, swept, step_rise)
    if best is None:
        needed = math.ceil(abs(rise) / MAX_STEP)
        if too_shallow:
            raise SpiralError(
                f"a rise of {rise} to an exit angle of {exit_angle} degrees only "
                f"comes out at more than one turn, and at that pitch a turn "
                f"climbs less than the stair is tall ({clear_height}), so each "
                "turn would sit inside the one above it. Climb further, come out "
                "at a nearer angle, or lower the clear height -- those three and "
                "the turn count cannot all be honoured as given")
        raise SpiralError(
            f"a rise of {rise} to an exit angle of {exit_angle} degrees needs at "
            f"least {needed} steps to stay inside the player's {MAX_STEP} step, "
            f"and no whole number of extra turns at {step_angle} degrees gives "
            "that many. Change the rise, the exit angle, or the step angle")

    _score, steps, swept, step_rise = best
    turns = swept / 360.0
    slab = int(abs(step_rise) * per_turn_steps - clear_height)
    why = (
        f"{steps} steps of {step_rise} over {swept:.1f} degrees "
        f"({turns:.2f} turns): the whole number of extra turns whose step rise "
        f"lands nearest the corpus's {TARGET_STEP_RISE}, with "
        f"{MAX_STEP} as the refusal threshold rather than the target"
        + (f"; a turn climbs {int(abs(step_rise) * per_turn_steps)} against a "
           f"{clear_height} stair, leaving {slab} of slab between turns"
           if swept > 360.0 else "; under one turn, so nothing is over anything")
    )
    return SpiralPlan(
        steps=steps, turns=turns, swept_degrees=swept, step_rise=step_rise,
        step_angle=step_angle, total_rise=int(step_rise * steps),
        inner_radius=INNER_RADIUS, outer_radius=int(radius),
        clear_height=int(clear_height),
        handed=-1 if str(handed).startswith("l") else 1,
        entry_angle=float(entry_angle), exit_angle=wanted, why=why,
    )


def _at(axis: tuple[int, int], radius: float, degrees: float) -> tuple[int, int]:
    radians = math.radians(degrees)
    return (int(round(axis[0] + radius * math.cos(radians))),
            int(round(axis[1] + radius * math.sin(radians))))


def _step_outline(axis: tuple[int, int], inner: int, outer: int,
                  start: float, end: float) -> list[tuple[int, int]]:
    """One step: four corners, two radial edges and two chords.

    Four walls, which is what every one of E3M1's twenty-six spiral sectors has.
    The newel is simply not covered by any sector, so it comes out solid.
    """
    points = [_at(axis, inner, start), _at(axis, outer, start),
              _at(axis, outer, end), _at(axis, inner, end)]
    if area2(tuple(points)) < 0:
        points.reverse()
    return points


def spiral_stair(layout: Any, structure_id: str, *, axis: tuple[int, int],
                 base_floor_z: int, rise: int, exit_angle: float,
                 radius: int = OUTER_RADIUS, entry_angle: float = 0.0,
                 handed: str = "right", step_angle: float = STEP_ANGLE,
                 clear_height: int = CLEAR_HEIGHT, landings: bool = True,
                 arrive_at: str | None = None, role: str = "stair",
                 connection: dict[str, Any] | None = None,
                 **surface: Any) -> Structure:
    """Build a spiral about `axis`, climbing `rise` and coming out facing `exit_angle`.

    Everything else is derived: the turns, the step count, the step rise, the
    step angle and the landings at both ends. The author never states a turn.

    Each step records the turn it belongs to as intent. That is where the
    description lives; the safety lives in `overlap_visibility`, which finds the
    one-turn-apart overlaps and sees them as ordinary band-separated pairs.
    """
    plan = plan_spiral(rise=rise, exit_angle=exit_angle, radius=radius,
                       step_angle=step_angle, handed=handed,
                       entry_angle=entry_angle, clear_height=clear_height)
    options = dict(connection or {})
    options.setdefault("min_width", max(512, int(plan.outer_tread)))

    fields = dict(surface)
    fields.setdefault("floor_picnum", STEP_FLOOR_PICNUM)

    regions: list[str] = []
    previous: str | None = None
    previous_anchor: Anchor | None = None
    sweep = plan.step_angle * plan.handed

    total = plan.steps + (2 if landings else 1)
    for index in range(total):
        # A landing is a step with no rise, at each end -- E3M1 has three flat
        # sectors at its head, wearing a different floor from the run. It gets
        # its own angular slot: sharing one with the first step gave the two
        # identical footprints, which the layout refuses and rightly so.
        is_landing = landings and index in (0, total - 1)
        climbed = min(index, plan.steps)
        floor_z = int(base_floor_z + plan.step_rise * climbed)
        start = plan.entry_angle + sweep * index
        end = start + sweep
        outline = _step_outline(axis, plan.inner_radius, plan.outer_radius,
                                min(start, end), max(start, end))
        region_id = f"region:{structure_id}:{'landing' if is_landing else 'step'}_{index:02d}"
        step_fields = dict(fields)
        if is_landing:
            step_fields["floor_picnum"] = LANDING_FLOOR_PICNUM
        layout.add_region(
            region_id, outline, role=role,
            floor_z=floor_z, ceiling_z=floor_z - plan.clear_height,
            intent={
                "purpose": f"{structure_id} "
                           f"{'landing' if is_landing else f'step {climbed} of {plan.steps}'}",
                "turn": int(abs(climbed * plan.step_angle) // 360),
                "angle": round(start % 360, 1),
            },
            **step_fields,
        )
        if previous is not None and previous_anchor is not None:
            layout.add_connection(
                f"connection:{structure_id}:{index:02d}", previous, region_id,
                a1=previous_anchor.a, a2=previous_anchor.b, **options)
        regions.append(region_id)
        if index == 0:
            # The free start/end edges are radial and therefore as long as the
            # usable stair width.  An outer chord is only one tread deep
            # (about 393 units at a 1000-unit radius): using it as a doorway
            # made an approach from a room look like a sideways slit and could
            # be narrower than the requested portal width.  A spiral must open
            # through its long side, just like a straight stair flight.
            entry_flank = Anchor(
                region_id, _at(axis, plan.inner_radius, start),
                _at(axis, plan.outer_radius, start))
        # The edge the next step shares with this one, computed from the angle
        # rather than read off the outline: `_step_outline` may reverse its
        # points to wind correctly, which scrambles any index-based guess.
        previous = region_id
        previous_anchor = Anchor(
            region_id,
            _at(axis, plan.inner_radius, end), _at(axis, plan.outer_radius, end))

    # The form declares its own overlap. A true 22.5-degree helix brings step
    # `i+16` back to exactly step `i`'s footprint -- E3M1's hand-drawn 22.2 to
    # 22.9 never quite repeats, but a derived one does -- and the layout refuses
    # identical footprints unless something says they are meant. This is the
    # constructor carrying its own safety rather than the author arguing for it:
    # `plan_spiral` has already refused any pitch whose turns would not clear
    # each other, so by the time these are declared the bands are disjoint.
    # Which pairs a helix actually brings back onto each other, derived rather
    # than guessed. Step `k` occupies the wedge from `k*a` to `(k+1)*a`, so two
    # steps meet again when their slots are congruent modulo a turn -- the same
    # footprint -- or one slot apart, where the radial edge one closes on is the
    # one the other opens on. Declaring only whole turns left step 15 and step 0
    # sharing the 360/0 edge with nothing to say they were meant to.
    #
    # Nothing wider is declared. `plan_spiral` has already refused any pitch
    # whose turns would not clear each other, so by the time these are named the
    # bands are disjoint and the declaration records that rather than excusing it.
    per_turn = int(round(360.0 / plan.step_angle))
    for index in range(len(regions)):
        for other in range(index + per_turn - 1, len(regions)):
            if (other - index) % per_turn in (0, 1, per_turn - 1):
                layout.declare_special(regions[index], regions[other], "helix")

    # The first start-radial and last end-radial edges are the two free, long
    # sides of the staircase.  Internal radial edges join adjacent treads;
    # only these two touch the shaft's rooms.
    structure = Structure(
        structure_id=structure_id, kind="spiral_stair", layout=layout,
        regions=tuple(regions), far=previous_anchor,
        flanks=(entry_flank, previous_anchor),
        provenance={
            "vocabulary": "bloodmap.spiral.spiral_stair",
            "precedent": "E3M1 sectors 15-40: 23 steps of 2048 at 22.5 degrees, "
                         "clear 24576, radius 248 to 1375, solid newel",
            **plan.to_dict(),
        },
    )
    if arrive_at:
        structure.arrive_at(arrive_at, **options)
    return structure
