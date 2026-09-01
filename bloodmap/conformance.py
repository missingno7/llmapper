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
from typing import Any

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
CURTAIN_TEMPLATE = {
    "flagged_walls": 2,
    "opposite_flags": True,
    "picnum": 146,
    "source": "E1M1 s125; knowledge/blood/design/owner-anchors-v1.json 146",
}


def measure_curtain(disk: Any, sector_id: int,
                    template: dict[str, Any] | None = None) -> Conformance:
    """Measure a curtain: edge convergence, and the fabric it deforms.

    The relation that makes a curtain a curtain is that its two flagged walls
    move TOWARD each other -- one carried with the travel and one against it
    -- so the sector's extent shrinks. A pair flagged the same way is a
    sector that slides; a pair flagged opposite ways is one that gathers.
    """
    from .effects import payload

    wanted = dict(template or CURTAIN_TEMPLATE)
    out = Conformance(construct=f"curtain sector {sector_id}")
    shape = payload(disk, sector_id)["shape"]
    out.measured["shape"] = shape.get("shape")
    out.measured["advancing"] = shape.get("advancing", [])
    out.measured["retreating"] = shape.get("retreating", [])
    if shape.get("shape") != "the sector resizes itself":
        out.deviations.append(Deviation(
            "payload shape", "the sector resizes itself", shape.get("shape"),
            "the two caps must carry opposite flags or nothing gathers"))
        return out
    if not (shape.get("advancing") and shape.get("retreating")):
        out.deviations.append(Deviation(
            "opposite flags", "at least one of each",
            (shape.get("advancing"), shape.get("retreating"))))

    sector = disk.sectors[sector_id]
    start = int(sector.fields["wall_ptr"])
    count = int(sector.fields["wall_count"])
    fabric = {int(disk.walls[i].fields["picnum"])
              for i in range(start, start + count)}
    out.measured["picnums"] = sorted(fabric)
    if wanted["picnum"] not in fabric:
        out.deviations.append(Deviation(
            "fabric", wanted["picnum"], sorted(fabric),
            "the deformation is only visible on the curtain texture"))
    return out


#: E1M1 s28/s30: one flagged wall, and it is the shared boundary.
PLANAR_DOOR_TEMPLATE = {
    "flagged_walls": 1,
    "boundary_is_a_portal": True,
    "source": "E1M1 s27-s30",
}


def measure_planar_door(disk: Any, sector_id: int,
                        template: dict[str, Any] | None = None) -> Conformance:
    """Measure a planar door: one flagged wall, and it is the boundary.

    Plus the relation the roadmap's blueprint names and a single sector
    cannot show on its own -- the same travel on both sides of the plane --
    which `measure_planar_pair` checks when there are two.
    """
    from .effects import payload

    out = Conformance(construct=f"planar door sector {sector_id}")
    shape = payload(disk, sector_id)["shape"]
    out.measured["shape"] = shape.get("shape")
    out.measured["flagged"] = shape.get("flagged")
    if shape.get("shape") != "boundary re-partition":
        out.deviations.append(Deviation(
            "payload shape", "boundary re-partition", shape.get("shape"),
            "exactly one flagged wall, and it must be the portal to the "
            "cover: the travel moves the line between the two sectors"))
        return out
    out.measured["re_partitions_with"] = shape.get("re_partitions_with")
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
