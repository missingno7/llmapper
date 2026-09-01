"""Measure a built construct with the miners that produced its template.

The owner walked zoo v3 and found the turnstile's four blades sitting in a
SQUARE where they had previously formed a cross radiating from the axis. That
regression passed every gate the project had: structural validation, the
usage laws, the self-reading gate, byte-exact round trip, an NBlood load
smoke and thirty-one renders. All of them ask whether the map is well formed.
None asks whether the construct still looks like the thing it was mined from.

So each constructor promoted from a mined template gets a **conformance
check**: build it, measure the built geometry with the same relational miners
that produced the template, and diff the measurements against it. The
measurement is relational on purpose -- angular spacing about an axis, radial
stand-off, span as a fraction of clear height -- because those are the
relations that survive a change of size, and a template that only fixed
absolute numbers would fail on every legitimate rescale while missing exactly
this bug.

The direction matters and is a hard rule: conformance parses a BUILT map
against a template mined from originals. It never mines a built map into a
template. Generated maps are never evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, degrees, hypot
from typing import Any, Sequence

#: Build's angle unit: 2048 to the turn.
BUILD_TURN = 2048

#: What the campaign's rotors do, from reports/blood-turnstile-build.md.
#: Sixteen blades across four mined rotors, every one of them 384 from its
#: axis, in two vanes at right angles. The offset is a CONSTANT -- it does
#: not scale with the rotor or with the blade's own width -- which is itself
#: part of the template.
TURNSTILE_TEMPLATE = {
    "blades": 4,
    "radial_stand_off": 384,
    "angular_spacing_degrees": 90.0,
    "span_fraction_of_clear": 1.0,
    #: The axis marker's ANGLE is the turn the rotor makes per period, not a
    #: facing -- E1M4's two rotors and DWE1M9's both use -8192, four whole
    #: turns. It is a motion parameter, so anything that treats it as a
    #: direction and rotates it changes how fast the rotor spins.
    "axis_turn": -8192,
    "source": "E1M4 151/314, DWE1M9 61/64; reports/blood-turnstile-build.md",
}


class ConformanceError(ValueError):
    """A construct that cannot be measured at all."""


@dataclass
class Deviation:
    """One relation that came out other than the template says."""

    relation: str
    wanted: Any
    found: Any
    detail: str = ""

    def __str__(self) -> str:
        return (f"{self.relation}: wanted {self.wanted}, found {self.found}"
                + (f" ({self.detail})" if self.detail else ""))


@dataclass
class Conformance:
    """What a built construct measured, and where it left its template."""

    construct: str
    measured: dict[str, Any] = field(default_factory=dict)
    deviations: list[Deviation] = field(default_factory=list)

    @property
    def conforms(self) -> bool:
        return not self.deviations

    def report(self) -> str:
        if self.conforms:
            return f"{self.construct}: conforms"
        return (f"{self.construct}: {len(self.deviations)} deviation(s)\n  "
                + "\n  ".join(str(d) for d in self.deviations))


def _sector_sprites(disk: Any, sector_id: int, picnum: int) -> list[Any]:
    return [s for s in disk.sprites
            if int(s.fields["sector"]) == sector_id
            and int(s.fields["picnum"]) == picnum
            and int(s.fields["status"]) != 10]


def _axis_sprite(disk: Any, sector_id: int):
    for sprite in disk.sprites:
        fields = sprite.fields
        if (int(fields["sector"]) == sector_id
                and int(fields["status"]) == 10
                and int(fields["type"]) == 5):
            return sprite
    return None


def _axis_marker(disk: Any, sector_id: int) -> tuple[int, int] | None:
    """The kMarkerAxis a rotate sector turns about, on statnum 10."""
    for sprite in disk.sprites:
        fields = sprite.fields
        if int(fields["sector"]) != sector_id:
            continue
        if int(fields["status"]) != 10:
            continue
        if int(fields["type"]) != 5:
            continue
        return (int(fields["x"]), int(fields["y"]))
    return None


def measure_turnstile(disk: Any, sector_id: int, *, blade_picnum: int = 332,
                      template: dict[str, Any] | None = None) -> Conformance:
    """Measure one rotor against the campaign's blade arrangement.

    Four relations, each of which the owner could see and no existing gate
    could:

    * **blade count** -- four, in two double-sided vanes;
    * **radial stand-off** -- every blade 384 from the axis. Blades stacked
      ON the axis was the first regression this caught, in an earlier run;
    * **angular spacing** -- the distinct bearings from the axis, 90 degrees
      apart. Four blades in a SQUARE have the same four bearings as a cross
      rotated 45 degrees, so bearing alone is not enough: the check also asks
      that each blade's OWN angle is perpendicular to its bearing, which is
      what makes a vane a vane rather than a fence panel;
    * **span** -- drawn height equal to the clear height, top on the ceiling
      and bottom on the floor.
    """
    wanted = dict(template or TURNSTILE_TEMPLATE)
    out = Conformance(construct=f"turnstile sector {sector_id}")
    sector = disk.sectors[sector_id]
    floor_z = int(sector.fields["floor_z"])
    ceiling_z = int(sector.fields["ceiling_z"])
    clear = abs(floor_z - ceiling_z)

    axis = _axis_marker(disk, sector_id)
    if axis is None:
        raise ConformanceError(
            f"sector {sector_id} has no kMarkerAxis; it is not a rotor")
    blades = _sector_sprites(disk, sector_id, blade_picnum)
    out.measured["blades"] = len(blades)
    out.measured["axis"] = axis
    if len(blades) != wanted["blades"]:
        out.deviations.append(Deviation("blade count", wanted["blades"],
                                        len(blades)))
    if not blades:
        return out

    offsets, bearings, spans, squareness = [], [], [], []
    for sprite in blades:
        fields = sprite.fields
        dx = int(fields["x"]) - axis[0]
        dy = int(fields["y"]) - axis[1]
        offsets.append(int(round(hypot(dx, dy))))
        bearing = (degrees(atan2(dy, dx))) % 360.0
        bearings.append(round(bearing, 1))
        spans.append(int(fields["y_repeat"]) * 4
                     * _tile_height(blade_picnum))
        #: A vane extends PERPENDICULAR to its own face normal. `ang` is that
        #: normal, so the bearing from the axis should be a quarter turn from
        #: it. Four blades arranged in a square have the right bearings and
        #: the wrong relationship to their own angles.
        own = (int(fields["angle"]) % BUILD_TURN) * 360.0 / BUILD_TURN
        squareness.append(round(abs((bearing - own) % 180.0), 1))

    out.measured["radial_stand_off"] = sorted(set(offsets))
    out.measured["bearings"] = sorted(set(bearings))
    out.measured["span"] = sorted(set(spans))
    out.measured["clear"] = clear
    out.measured["bearing_minus_own_angle"] = sorted(set(squareness))

    if set(offsets) != {wanted["radial_stand_off"]}:
        out.deviations.append(Deviation(
            "radial stand-off", wanted["radial_stand_off"],
            sorted(set(offsets)),
            "every blade in the four mined rotors is exactly this far out"))

    distinct = sorted(set(bearings))
    gaps = _gaps(distinct)
    if gaps and any(abs(g - wanted["angular_spacing_degrees"]) > 1.0
                    for g in gaps):
        out.deviations.append(Deviation(
            "angular spacing", f"{wanted['angular_spacing_degrees']} degrees",
            gaps))

    if set(squareness) != {90.0}:
        out.deviations.append(Deviation(
            "vane orientation", "90.0 (bearing perpendicular to face normal)",
            sorted(set(squareness)),
            "a vane extends across its own face; blades whose bearing is not "
            "perpendicular to their angle form a square, not a cross"))

    axis_sprite = _axis_sprite(disk, sector_id)
    if axis_sprite is not None and "axis_turn" in wanted:
        turn = int(axis_sprite.fields["angle"])
        out.measured["axis_turn"] = turn
        if turn != wanted["axis_turn"]:
            out.deviations.append(Deviation(
                "axis turn", wanted["axis_turn"], turn,
                "the axis marker's angle is how far the rotor turns per "
                "period, not a direction it faces"))

    if clear and set(spans) != {clear}:
        out.deviations.append(Deviation(
            "span", clear, sorted(set(spans)),
            "a blade spans its rotor exactly, top on the ceiling and bottom "
            "on the floor"))
    return out


def _gaps(bearings: list[float]) -> list[float]:
    if len(bearings) < 2:
        return []
    ordered = sorted(bearings)
    out = [round(b - a, 1) for a, b in zip(ordered, ordered[1:])]
    out.append(round(360.0 - ordered[-1] + ordered[0], 1))
    return sorted(set(out))


def _tile_height(picnum: int, default: int = 128) -> int:
    try:
        from .usage_kinds import tile_size

        size = tile_size(picnum)
        return int(size[1]) if size else default
    except Exception:
        return default


#: E1M1 s125: a thin sector whose two end caps carry OPPOSITE flags, so its
#: own length changes and the texture between them deforms.
#: The curtain family, as the ORIGINALS build it -- four dialects, not one.
#:
#: An earlier template described a pair of opposed caps and was routed on the
#: payload shape that produces, so rebuilding the constructor to the fin made
#: the check stop running. This one is routed on the fabric TILE and accepts
#: both leaf counts and both slot dialects, because a template that rejects
#: the tutorial is worse than no template.
CURTAIN_TEMPLATE = {
    "leaves": (1, 2),
    "shape": "part of the sector travels",
    "picnum": 146,
    "fabric_per_leaf": 3,
    #: The closed-span texel scale, measured over 355 fabric walls in the
    #: originals (43 campaign maps + the DOOR-CURTAIN tutorials, autosave
    #: debris excluded). 2.0 is the MODE and by a distance -- 171 of 355 --
    #: and it is what the constructor authors to. It is not a law: the
    #: attested envelope runs 1.0 to 8.0 (311 of 355), with a long tail to
    #: 0.05 and 10.0.
    #:
    #: An earlier version of this template demanded 2.0 +/- 0.35 and rejected
    #: DOOR-CURTAINSD s2 (1.33) and E1M1 s125 (2.83 and 4.0). A template that
    #: rejects the tutorial is worse than no template, so the gate flags the
    #: ENVELOPE and the constructor keeps the preference. The defect this was
    #: written for measured 96 -- twelve times outside the envelope.
    "closed_texel_scale": 2.0,
    "texel_envelope": (1.0, 8.0),
    "source": ("maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map s3 (one leaf, "
               "void); DOOR-CURTAINSD.map s2 (two leaves, void) and s4 (two "
               "leaves, POCKET); E1M1 s125 (two leaves, void, pelmet, Link)"),
}

#: `engine.cpp:4938-4940`: the middle band of a wall is drawn from `picnum`
#: only when the wall is ONE-SIDED, and from `overpicnum` only when it is
#: two-sided AND one-way (cstat 32); the masked path (cstat 16) is what
#: reaches a two-sided wall's middle otherwise. So a two-sided, unmasked wall
#: shows its fabric on the STEP bands and nowhere a body walks.
MASKED, ONE_WAY = 16, 32


def fabric_is_visible(disk: Any, wall_id: int, sector_id: int) -> bool:
    """Does this fabric wall draw in the band a body walks through?

    The relation the project had no way to ask. A curtain whose fabric sits
    on a two-sided unmasked wall passes every other gate and shows nothing:
    the tile is right, the cstat is legal, and the engine draws it only above
    the head or below the feet.
    """
    fields = disk.walls[wall_id].fields
    if int(fields["next_sector"]) < 0:
        return True                       # one-sided: the wall IS the fabric
    cstat = int(fields["cstat"])
    return bool(cstat & MASKED) or bool(cstat & ONE_WAY)


def curtain_dialect(disk: Any, sector_id: int,
                    tile: int = 146) -> dict[str, Any]:
    """Name which of the family's dialects this curtain is.

    Four are attested and they differ in ways that change how the thing is
    built, not just how it looks:

    * **leaves** -- one flagged tip, or two carrying opposite flags.
    * **slot** -- `void` when the fabric walls are one-sided (the leaf
      retracts into solid geometry) or `pocket` when they are two-sided into
      a real sector, which then has to be MASKED to draw at all.
    * **pelmet** -- fabric on a two-sided wall with a genuine step, which
      draws above the opening. E1M1 s125's five 1203-1207 walls are this: a
      valance, not the curtain body.
    * **link** -- command 5, which couples a light to the curtain's busy
      instead of switching it at the end of the travel.
    """
    from .curriculum import _extra
    from .motion import flagged_walls

    sector = disk.sectors[sector_id]
    start = int(sector.fields["wall_ptr"])
    count = int(sector.fields["wall_count"])
    extra = _extra(sector)
    fabric = [i for i in range(start, start + count)
              if int(disk.walls[i].fields["picnum"]) == tile
              or int(disk.walls[i].fields.get("over_picnum", 0)) == tile]
    one_sided = [i for i in fabric
                 if int(disk.walls[i].fields["next_sector"]) < 0]
    masked = [i for i in fabric if int(disk.walls[i].fields["cstat"]) & MASKED]
    pelmet = []
    for index in fabric:
        fields = disk.walls[index].fields
        other = int(fields["next_sector"])
        if other < 0 or int(fields["cstat"]) & (MASKED | ONE_WAY):
            continue
        neighbour = disk.sectors[other].fields
        if (int(sector.fields["floor_z"]) != int(neighbour["floor_z"])
                or int(sector.fields["ceiling_z"]) != int(neighbour["ceiling_z"])):
            pelmet.append(index)
    return {
        "leaves": len(flagged_walls(disk, sector_id)),
        "slot": "void" if one_sided else ("pocket" if masked else "flush"),
        "fabric_walls": len(fabric), "one_sided": len(one_sided),
        "masked": len(masked), "pelmet": len(pelmet),
        "link": int(extra.get("command", 0)) == 5,
        "push": any(_extra(disk.walls[i]).get("trigger_push") for i in fabric),
    }


def measure_curtain(disk: Any, sector_id: int,
                    template: dict[str, Any] | None = None,
                    declared: Sequence[int] | None = None) -> Conformance:
    """Measure a curtain against the originals, in whichever dialect it is.

    Four relations, and the fourth is the one nothing could previously ask.

    * **leaves**: one flagged wall or two carrying OPPOSITE flags. Two leaves
      that both move `with` do not converge, they travel together.
    * **members**: the motion set is what the construct DECLARED. For a void
      slot that is the fin alone; for a pocket it is the fin plus its
      pockets. `DragPoint` walks `nextwall` (triggers.cpp:817-854) and a
      flagged wall also drags its `point2` when that wall is unflagged
      (:897-910), so anything sharing a moved vertex moves too.
    * **fabric is visible**: at least one fabric wall PER LEAF draws in the
      walkable band. Not every wall -- DOOR-CURTAINSD s4 has six fabric walls
      and only two of them are visible, the masked pocket-side pair, and a
      rule demanding all six would reject the tutorial.
    * **closed-span repeat**: the geometry is saved at the ON pose, so the
      fabric in the file is the gathered bundle. Natural is
      `length / x_repeat == 2 * tile_width`; s3 and s53 hold it to the unit
      and s24 sits at twice it, which is why the tolerance is a band.
    """
    import math

    from .motion import flagged_walls, motion_set
    from .motion_sim import blood_poses
    from .texture_align import texel_scale

    wanted = dict(template or CURTAIN_TEMPLATE)
    out = Conformance(construct=f"curtain sector {sector_id}")

    flags = flagged_walls(disk, sector_id)
    leaves = len(flags)
    out.measured["leaves"] = leaves
    out.measured["flag_directions"] = sorted(set(flags.values()))
    if leaves not in tuple(wanted["leaves"]):
        out.deviations.append(Deviation(
            "leaves", wanted["leaves"], leaves,
            "a curtain has one flagged tip, or two carrying opposite flags"))
    if leaves == 2 and len(set(flags.values())) != 2:
        out.deviations.append(Deviation(
            "opposite flags", "one with and one against",
            sorted(set(flags.values())),
            "two leaves that move the same way travel together instead of "
            "converging"))

    try:
        moves = motion_set(disk, sector_id)["sectors"]
    except Exception:
        moves = []
    out.measured["motion_set"] = moves
    #: The relation is "the motion set is what the construct DECLARED", so
    #: it can only be checked when something declared. Flagging an
    #: undeclared curtain as deviant would reject three of the four
    #: originals: DOOR-CURTAINSD s4 legitimately moves its two POCKETS, and
    #: E1M1 s125 moves the room its pelmet walls are shared with. What is
    #: wrong is not that a neighbour moves -- `DragPoint` walks `nextwall`
    #: and neighbours always can -- but that one moves nobody declared.
    if declared is not None:
        members = sorted(set(declared) | {sector_id})
        if moves != members:
            out.deviations.append(Deviation(
                "members", members, moves,
                "the motion set is what the construct declared; DragPoint "
                "walks nextwall (triggers.cpp:817-854), so anything sharing "
                "a moved vertex moves too"))
    else:
        out.measured["undeclared_neighbours"] = [
            index for index in moves if index != sector_id]

    sector = disk.sectors[sector_id]
    start = int(sector.fields["wall_ptr"])
    count = int(sector.fields["wall_count"])
    fabric_walls = [i for i in range(start, start + count)
                    if int(disk.walls[i].fields["picnum"]) == wanted["picnum"]
                    or int(disk.walls[i].fields.get("over_picnum", 0))
                    == wanted["picnum"]]
    out.measured["fabric_walls"] = len(fabric_walls)
    if not fabric_walls:
        out.deviations.append(Deviation(
            "fabric", wanted["picnum"], sorted(
                {int(disk.walls[i].fields["picnum"])
                 for i in range(start, start + count)}),
            "the deformation is only visible on the curtain texture"))
        return out

    visible = [i for i in fabric_walls
               if fabric_is_visible(disk, i, sector_id)]
    out.measured["fabric_visible"] = len(visible)
    if len(visible) < max(1, leaves):
        out.deviations.append(Deviation(
            "fabric is visible", f"at least {max(1, leaves)} (one per leaf)",
            len(visible),
            "engine.cpp:4938-4940 draws a two-sided wall's middle band only "
            "when it is masked or one-way; unmasked, the fabric shows on the "
            "step bands and nowhere a body walks"))

    try:
        closed, _drawn = blood_poses(disk, sector_id)
    except Exception as exc:
        out.measured["closed_pose"] = f"unavailable: {exc}"
        return out
    width = int(wanted.get("tile_width", 32))
    scales = []
    for index in fabric_walls:
        k = index - start
        a, b = closed[k], closed[(k + 1) % count]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 0:
            continue
        scales.append(round(texel_scale(
            length, width, int(disk.walls[index].fields["x_repeat"])), 2))
    out.measured["closed_texel_scale"] = scales
    low, high = wanted["texel_envelope"]
    stretched = [value for value in scales if not low <= value <= high]
    if stretched:
        out.deviations.append(Deviation(
            "closed-span texel scale", f"within [{low}, {high}] (mode 2.0)",
            stretched,
            "the fabric is sized for the span it HANGS ACROSS, not for the "
            "gathered bundle the file is saved at"))
    return out


#: E1M1 s28/s30: one flagged wall, and it is the shared boundary.
PLANAR_DOOR_TEMPLATE = {
    "flagged_walls": 1,
    "boundary_is_a_portal": True,
    "source": "E1M1 s27-s30",
}


def measure_planar_door(disk: Any, sector_id: int,
                        template: dict[str, Any] | None = None) -> Conformance:
    """Measure a planar door against the owner-authored oracle.

    `maps/blood/mechanism/casket.map` is the definition: ONE footprint split
    by a sliding boundary into a LID and a HOLE, the lid sliding to cover or
    reveal the hole that carries the link. Two dialects are legal and this
    accepts both -- the motor may sit on either side of the boundary (the
    oracle drives the lid, E1M1 drives the hole) and either one or both
    records of the boundary pair may carry the flag (the oracle flags both,
    E1M1 one). What it does NOT accept is a travel the receiving side cannot
    take, which is what the zoo shipped: a boundary sweeping 2304 units past
    the far wall of a 768-deep cover, inverting it.

    The invariant is checked by SWEEPING, not by reading the rest pose, since
    the rest pose is exactly where the defect is invisible.
    """
    from .effects import payload
    from .swept_state import sweep_sector

    out = Conformance(construct=f"planar door sector {sector_id}")
    shape = payload(disk, sector_id)["shape"]
    out.measured["shape"] = shape.get("shape")
    out.measured["flagged"] = shape.get("flagged")
    if shape.get("shape") != "boundary re-partition":
        out.deviations.append(Deviation(
            "payload shape", "boundary re-partition", shape.get("shape"),
            "exactly one flagged wall on the motor, and it must be the "
            "portal to the other half of the footprint"))
        return out
    partner = shape.get("re_partitions_with")
    out.measured["re_partitions_with"] = partner

    #: Which dialect. Both are legal; the measurement records which.
    #: The step is on whichever surface the two halves differ in. The
    #: oracle's upper plane is a lid in the FLOOR -- s2 33792, s3 34816 --
    #: and its lower plane the mirror of that in the CEILING, s5 -33792
    #: against s6 -34816. Reading only floors calls the lower lid a hole.
    motor = disk.sectors[sector_id].fields
    other = disk.sectors[partner].fields
    floor_step = int(motor["floor_z"]) - int(other["floor_z"])
    ceiling_step = int(other["ceiling_z"]) - int(motor["ceiling_z"])
    if abs(ceiling_step) > abs(floor_step):
        step, plane = ceiling_step, "ceiling"
    else:
        step, plane = floor_step, "floor"
    out.measured["step_plane"] = plane
    out.measured["lid_step"] = abs(step)
    #: The lid is the side that stands PROUD of the hole: its floor is
    #: higher, or in the mirrored plane its ceiling is lower.
    out.measured["dialect_motor"] = "lid" if step < 0 else "hole"
    if abs(step) == 0:
        out.measured["dialect_motor"] = "flush"
        out.deviations.append(Deviation(
            "lid step", "a step between the two halves",
            "the halves are flush",
            "the oracle's lid is a tray one 1024 step above the hole it "
            "covers, which is what makes the open hole read as somewhere to "
            "drop into rather than a change of floor colour"))
    boundary = int(shape["boundary_wall"])
    twin = int(disk.walls[boundary].fields["next_wall"])
    both = (twin >= 0
            and int(disk.walls[twin].fields["cstat"]) & (16384 | 32768) != 0)
    out.measured["dialect_flags"] = "both" if both else "one"

    #: The invariant the rest pose cannot show.
    swept = sweep_sector(disk, sector_id)
    out.measured["swept_areas"] = [swept.areas[0], swept.areas[-1]]         if swept.areas else []
    for line in swept.problems:
        out.deviations.append(Deviation(
            "the motion stays inside the footprint", "no inversion, no "
            "collapse, no crossing", line,
            "the travel has to leave a usable sector on BOTH sides at BOTH "
            "ends; the oracle's 1920 into a 2176 footprint leaves 128"))
    return out


def travel_of(disk: Any, sector_id: int) -> tuple[int, int] | None:
    """The vector between a Marked sector's two markers, or None."""
    from .effects import motion_markers

    markers = motion_markers(disk, sector_id)
    if not markers:
        return None
    off = markers.get("marker_0")
    on = markers.get("marker_1")
    if not off or not on:
        return None
    return (int(on["x"]) - int(off["x"]), int(on["y"]) - int(off["y"]))


def measure_planar_pair(disk: Any, upper: int, lower: int) -> Conformance:
    """Both halves of a stack-linked planar door travel the same way.

    E1M1's casket is four sectors in two pairs, one above the other, and the
    same travel vector runs on both sides of the room-over-room plane --
    markers 42->43 and 44->45, minus 1916 and minus 1912. If the two halves
    disagreed the revealed holes would not meet through the link.
    """
    out = Conformance(construct=f"planar door pair {upper}/{lower}")
    a, b = travel_of(disk, upper), travel_of(disk, lower)
    out.measured["travel"] = {"upper": a, "lower": b}
    if a is None or b is None:
        out.deviations.append(Deviation("travel", "two marker pairs", (a, b)))
        return out
    #: Within one player width: E1M1's own two differ by 4 units.
    if hypot(a[0] - b[0], a[1] - b[1]) > 384:
        out.deviations.append(Deviation(
            "same travel on both sides of the plane", a, b,
            "the revealed holes have to meet through the link"))
    return out


#: Measured over twelve campaign maps, 1495 wall-aligned sprites: 92.4% sit
#: at 90 degrees to their wall's direction and 5.2% at 270 -- the same
#: relation, facing the other way -- for 97.6% perpendicular. 1.6% lie
#: PARALLEL to their wall, which is a sprite edge-on to the room and is what
#: this catches.
WALL_SPRITE_TEMPLATE = {
    "perpendicular_share": 0.976,
    "source": "12 campaign maps, 1495 wall-aligned sprites",
}


def _sector_walls(disk: Any, sector_id: int):
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    for index in range(start, start + int(fields["wall_count"])):
        wall = disk.walls[index].fields
        end = disk.walls[int(wall["point2"])].fields
        yield index, ((int(wall["x"]), int(wall["y"])),
                      (int(end["x"]), int(end["y"])))


def _point_to_segment(point, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(
        1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / length))
    near = (ax + t * dx, ay + t * dy)
    return hypot(point[0] - near[0], point[1] - near[1]), (dx, dy)


def measure_wall_sprites(disk: Any, *, tolerance: int = 200,
                         skip: set[int] | None = None) -> Conformance:
    """Every wall-aligned sprite should face out of the wall it is on.

    The broadest oddity-catcher here, and the one that generalises the
    turnstile bug: a sprite whose POSITION was transformed and whose ANGLE
    was not ends up edge-on to the room. The campaign is 97.6% perpendicular
    over 1495 wall sprites, so a build that is not is doing something the
    campaign does roughly one time in sixty.

    Letters are skipped: a word is a row of wall sprites laid ALONG the wall
    by design, and `lettering` owns that arrangement.
    """
    out = Conformance(construct="wall sprites")
    skipped = skip if skip is not None else set(range(3808, 3834))
    total = 0
    offenders = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["cstat"]) & 0x30 != 16:
            continue
        if int(fields["status"]) == 10:
            continue
        if int(fields["picnum"]) in skipped:
            continue
        sector_id = int(fields["sector"])
        walls = list(_sector_walls(disk, sector_id))
        if not walls:
            continue
        point = (int(fields["x"]), int(fields["y"]))
        best = min(walls, key=lambda w: _point_to_segment(point, *w[1])[0])
        distance, direction = _point_to_segment(point, *best[1])
        if distance > tolerance:
            continue
        total += 1
        wall_angle = degrees(atan2(direction[1], direction[0])) % 360.0
        own = (int(fields["angle"]) % BUILD_TURN) * 360.0 / BUILD_TURN
        delta = round((own - wall_angle) % 180.0)
        if not (80 <= delta <= 100):
            offenders.append(
                f"sprite {index} (tile {fields['picnum']}) on wall "
                f"{best[0]} of sector {sector_id} is {delta} degrees off "
                f"its wall, not 90")
    out.measured["wall_sprites"] = total
    out.measured["edge_on"] = len(offenders)
    if offenders:
        out.deviations.append(Deviation(
            "wall sprites face out of their wall", "90 degrees",
            f"{len(offenders)} of {total} are not",
            "; ".join(offenders[:6])))
    return out


#: E1M1 s65, the sprite-payload gate: two carried leaves, both perpendicular
#: to the travel. A leaf faces ACROSS the line it slides along -- that is
#: what makes it a barrier rather than a blade edge-on to the opening.
SPRITE_GATE_TEMPLATE = {
    "leaf_angle_to_travel_degrees": 90,
    "source": "E1M1 s65 (sprites 37/38, both angle 1792, travel -1024,-1024)",
}


def measure_sprite_payload(disk: Any, sector_id: int,
                           template: dict[str, Any] | None = None
                           ) -> Conformance:
    """A sector whose payload is sprites: do the leaves face across the slide?

    The same class of bug as the turnstile's, one construct along. A leaf
    whose position is transformed and whose angle is not slides edge-on and
    stops nothing.
    """
    from .effects import payload

    wanted = dict(template or SPRITE_GATE_TEMPLATE)
    out = Conformance(construct=f"sprite payload sector {sector_id}")
    carried = payload(disk, sector_id)
    leaves = list(carried["sprites_with"]) + list(carried["sprites_against"])
    out.measured["leaves"] = len(leaves)
    if not leaves:
        return out
    travel = travel_of(disk, sector_id)
    out.measured["travel"] = travel
    if not travel or travel == (0, 0):
        out.deviations.append(Deviation("travel", "a marker pair", travel))
        return out
    bearing = degrees(atan2(travel[1], travel[0])) % 360.0
    deltas = []
    for index in leaves:
        own = (int(disk.sprites[index].fields["angle"]) % BUILD_TURN)             * 360.0 / BUILD_TURN
        deltas.append(round((own - bearing) % 180.0))
    out.measured["leaf_angle_to_travel"] = sorted(set(deltas))
    wanted_delta = wanted["leaf_angle_to_travel_degrees"]
    if any(abs(d - wanted_delta) > 10 for d in deltas):
        out.deviations.append(Deviation(
            "leaf angle to travel", f"{wanted_delta} degrees",
            sorted(set(deltas)),
            "a leaf faces across the line it slides along"))
    return out
