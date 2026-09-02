"""Street anatomy: a run is a roadway, two sidewalks, and the kerb between.

Promotes queue ranks 3 and 6 into one constructor. Until now a district's
street was a single flat region -- the whole open space at one level wearing
one tile -- which is why the city reads as empty even where it is dense: there
is no difference between the part you walk on and the part carts use, so the
eye has nothing to follow.

**Measured, not assumed.** E3M1 is the campaign's own city street and it
answers every number here:

* the split is tile **4** for the sidewalk and **352** for the roadway. They
  meet on 22 shared walls, the second-commonest heterogeneous adjacency in
  the map;
* the kerb is **2048**, and it is not a range -- all 22 shared walls give
  exactly 2048, with the sidewalk ABOVE. (The brief for this work said 1024;
  that is the rise of this project's existing grate kerb, which is a ring
  around a drain and a different object.)
* the sidewalk BAND is **2048** wide: the modal narrow dimension of the nine
  tile-4 sectors that touch a roadway, 5 of 9 exactly there.

So the sidewalk stays at grade with the buildings and the plazas, and the
ROADWAY drops away from it. That direction matters: raising the pavement
instead would put a step down into every shop door in the city.

The kerb itself is not a sector. It is the JUNCTION mediation at the sidewalk
/ roadway boundary -- a 2048 step, well inside Blood's climbable 4096 -- and
it exists as the height difference across that shared wall, the same way a
threshold does.

A run narrower than `MIN_CARRIAGEWAY + 2 * SIDEWALK` has no roadway at all
and stays pavement end to end. That is not a failure to build one: a
3072-wide lane between two blocks is a pedestrian lane, and the campaign's
own lanes are the same.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

#: E3M1, measured.
SIDEWALK_TILE = 4
ROADWAY_TILE = 352
#: The step from pavement down to carriageway. 22 of 22 shared walls.
KERB_RISE = 2048
#: The pavement band either side. Modal narrow dimension, 5 of 9 -- but the
#: nine are not all 2048: 1024 and 2560 are in the set too, so the band is a
#: choice within a measured range rather than a constant. A wide run affords
#: the modal 2048; a narrow one takes 1024 and still has a road, which is
#: better than a main street with no carriageway at all.
SIDEWALK = 2048
SIDEWALK_NARROW = 1024
#: Above this a run affords the full band.
WIDE_RUN = 6144
#: Below this a run is all pavement. E3M1's own roadways are 4096 and wider,
#: so a carriageway narrower than one player-and-a-half of clear road is not
#: a road, it is a gap between two kerbs.
MIN_CARRIAGEWAY = 2048


class StreetError(ValueError):
    """A run that cannot be given an anatomy."""


@dataclass(frozen=True)
class Run:
    """One node-to-node stretch of street, with its width class."""

    name: str
    a: tuple[float, float]
    b: tuple[float, float]
    width: int
    district: str = ""

    @property
    def horizontal(self) -> bool:
        return abs(self.b[0] - self.a[0]) >= abs(self.b[1] - self.a[1])

    @property
    def length(self) -> float:
        return (abs(self.b[0] - self.a[0]) if self.horizontal
                else abs(self.b[1] - self.a[1]))


def sidewalk_for(width: int) -> int:
    """How wide a pavement this run can afford, from the measured pair."""
    return SIDEWALK if int(width) >= WIDE_RUN else SIDEWALK_NARROW


def carriageway(run: Run, *, sidewalk: int | None = None,
                minimum: int = MIN_CARRIAGEWAY) -> tuple[int, int, int, int] | None:
    """The roadway rectangle of a run, or None when the run is all pavement.

    The roadway is the run's centre with a `sidewalk` band taken off each
    side. Returned in world units as (x0, y0, x1, y1).
    """
    if run.width <= 0:
        raise StreetError(f"{run.name}: width {run.width} is not a width")
    if sidewalk is None:
        sidewalk = sidewalk_for(run.width)
    inner = run.width - 2 * int(sidewalk)
    if inner < int(minimum):
        return None
    (ax, ay), (bx, by) = run.a, run.b
    if run.horizontal:
        centre = (ay + by) / 2.0
        low, high = min(ax, bx), max(ax, bx)
        return (int(low), int(centre - inner / 2),
                int(high), int(centre + inner / 2))
    centre = (ax + bx) / 2.0
    low, high = min(ay, by), max(ay, by)
    return (int(centre - inner / 2), int(low),
            int(centre + inner / 2), int(high))


def kerb_junction(run: Run) -> dict[str, Any]:
    """What the sidewalk/roadway boundary IS, as a declared mediation.

    A construct member with the `junction` role: the place two things meet
    and neither owns. Named so a reading can find it, and so the step is a
    stated intent rather than an accident of two floor heights.
    """
    return {
        "kind": "kerb", "role": "junction", "run": run.name,
        "rise": KERB_RISE, "above": SIDEWALK_TILE, "below": ROADWAY_TILE,
        "why": ("E3M1's sidewalk stands 2048 over its roadway on all 22 "
                "shared walls; a body steps up it, well inside the 4096 "
                "Blood will climb"),
    }


# ---------------------------------------------------------------------------
# prefab slots
# ---------------------------------------------------------------------------

#: What the campaign spaces along a street, measured as an interval rather
#: than a count so a longer run simply gets more. The city's own service
#: reading put lamps at roughly nine plan units; this keeps that and states
#: it as the authoring preference it is.
LAMP_INTERVAL = 9 * 1024
#: A lamp stands ON the pavement, so it is inset from the kerb by half a
#: sidewalk band -- never overhanging the drop.
LAMP_INSET = SIDEWALK // 2


@dataclass(frozen=True)
class Slot:
    """A place something may stand, derived rather than placed by hand.

    The PREFAB SLOT idea, adopted here because this is the case that asked
    for it: how many street lamps a run wants is a function of how long it
    is, and writing them out one by one is how a city ends up with lamps in
    three districts and none in the fourth.
    """

    slot_id: str
    kind: str
    x: int
    y: int
    side: str = ""

    def as_json(self) -> dict[str, Any]:
        return {"id": self.slot_id, "kind": self.kind,
                "x": self.x, "y": self.y, "side": self.side}


def lamp_slots(run: Run, *, interval: int = LAMP_INTERVAL,
               inset: int | None = None, sidewalk: int | None = None
               ) -> list[Slot]:
    """Lamp positions along both pavements of a run.

    Spaced from the middle outwards so a run always has a lamp near its
    centre and the ends stay clear for whatever meets them -- a junction, a
    gate, a doorway.
    """
    if interval <= 0:
        raise StreetError("interval must be positive")
    if sidewalk is None:
        sidewalk = sidewalk_for(run.width)
    if inset is None:
        inset = sidewalk // 2
    length = run.length
    count = max(1, int(length // interval))
    out: list[Slot] = []
    for index in range(count):
        t = (index + 0.5) / count
        for side, sign in (("low", -1), ("high", 1)):
            offset = sign * (run.width / 2.0 - sidewalk + inset)
            if run.horizontal:
                x = run.a[0] + (run.b[0] - run.a[0]) * t
                y = (run.a[1] + run.b[1]) / 2.0 + offset
            else:
                x = (run.a[0] + run.b[0]) / 2.0 + offset
                y = run.a[1] + (run.b[1] - run.a[1]) * t
            out.append(Slot(f"{run.name}:lamp:{index}:{side}", "lamp",
                            int(x), int(y), side))
    return out


#: A porch is as deep as the step it shelters plus a body's shoulder, and it
#: exists where a door meets a facade tall enough to want one. Below this the
#: facade is a shopfront and a porch on it reads as a mistake.
PORCH_MIN_FACADE = 3 * 16960
PORCH_DEPTH = 1536


def wants_porch(facade_height: int, *, minimum: int = PORCH_MIN_FACADE) -> bool:
    """The porch rule: a tall facade's door is recessed, a low one's is not.

    Stated as a threshold so it is arguable. Three player heights is where
    the campaign's own doorways start carrying a hood rather than sitting
    flush.
    """
    return int(facade_height) >= int(minimum)


def porch_slots(runs: Iterable[Run], doors: Sequence[dict[str, Any]],
                *, minimum: int = PORCH_MIN_FACADE) -> list[Slot]:
    """Which of a street's doors want a porch, by the rule above."""
    out = []
    for door in doors:
        if not wants_porch(int(door.get("facade_height", 0)), minimum=minimum):
            continue
        out.append(Slot(f"{door['id']}:porch", "porch",
                        int(door["x"]), int(door["y"]),
                        str(door.get("facing", ""))))
    return out


def runs_from_plan(nodes: dict[str, Sequence[float]],
                   edges: Iterable[Sequence[Any]],
                   widths: dict[str, int], *, unit: int = 1024) -> list[Run]:
    """Turn a plan's circulation graph into runs in world units."""
    out = []
    for edge in edges:
        a, b, kind, district = edge[0], edge[1], edge[2], edge[3]
        if a not in nodes or b not in nodes:
            raise StreetError(f"edge {a}->{b} names a node that does not exist")
        if kind not in widths:
            raise StreetError(f"edge {a}->{b} has width class {kind!r}")
        name = edge[4] if len(edge) > 4 else f"{a}_{b}"
        out.append(Run(
            name=str(name).replace(" ", "_"),
            a=(nodes[a][0] * unit, nodes[a][1] * unit),
            b=(nodes[b][0] * unit, nodes[b][1] * unit),
            width=int(widths[kind]), district=str(district)))
    return out


# ---------------------------------------------------------------------------
# where a road stops
# ---------------------------------------------------------------------------

#: **A road does not end at a building, and it does not end at a kerb.** E3M1
#: ends its streets against a raised mass whose floor IS the top of the wall
#: -- you see a stone face across the road and a strip of sky above it -- and
#: that mass is a sector, not a facade.
#:
#: Measured on its three (s0, s339, s343):
#:
#: ==== ===== ========= =========== ================= ==================
#: id   walls floor pic ceiling     above the road    under the sky line
#: ==== ===== ========= =========== ================= ==================
#: s0     9      379    3491 sky    5.80 bodies       5.80
#: s339  10      379    3491 sky    3.86              7.73
#: s343   8      379    3491 sky    5.80 / 9.60       5.80
#: ==== ===== ========= =========== ================= ==================
#:
#: Its faces to the road and to the pavements are two-sided, **blocking**
#: (cstat 1), at `y_repeat` 8, in the district's own facade stone -- 400 on
#: s0, 401 on s339, 108 on s343. Where a face meets a pedestrian path instead
#: of a road it is NOT blocking (s339's walls to s10/s11, picnum 181,
#: cstat 0): you may walk between the houses, you may not walk up the end of
#: the street.
#:
#: The floor tile is 379, which is also the answer to where E3M1's 379 lives:
#: it is the top of an end wall, not a plaza surface. That correction stands.
END_WALL_FLOOR_TILE = 379
END_WALL_CSTAT_BLOCKING = 1
END_WALL_Y_REPEAT = 8
#: E3M1's range, in player heights, as a band rather than a number: three of
#: three sit inside it and a termination outside it is not this dialect.
END_WALL_RISE_BODIES = (3.86, 5.80)
END_WALL_SKY_BODIES = (5.80, 7.73)


def end_wall(outline, *, road_floor_z: int, standing_height: int,
             facade_tile: int, rise_bodies: float = 5.80,
             sky_bodies: float = 5.80, sky_tile: int = 3491,
             name: str = "end_wall") -> dict:
    """A road's termination, in E3M1's dialect.

    Returns the raised sector to emit and the faces it presents. `rise_bodies`
    is how far its floor stands above the road and `sky_bodies` how far the
    sky line stands above that floor, both in player heights, because that is
    how the three originals actually vary -- 3.86 to 5.80 up, 5.80 to 7.73
    of sky.

    The faces are **inserts on the ground plane, not part of any facade run**:
    an end wall is a thing standing at the end of a street, and giving its
    faces to the street's run would make the road's material turn a corner
    and climb it.
    """
    rise = int(round(float(rise_bodies) * int(standing_height)))
    sky = int(round(float(sky_bodies) * int(standing_height)))
    floor_z = int(road_floor_z) - rise
    return {
        "name": str(name),
        "outline": [tuple(int(v) for v in point) for point in outline],
        #: Blood's z grows downward: standing up is a smaller z.
        "floor_z": floor_z,
        "ceiling_z": floor_z - sky,
        "floor_picnum": END_WALL_FLOOR_TILE,
        "ceiling_picnum": int(sky_tile),
        "parallax_ceiling": True,
        "face_picnum": int(facade_tile),
        "face_cstat": END_WALL_CSTAT_BLOCKING,
        "face_y_repeat": END_WALL_Y_REPEAT,
        "rise": rise,
        "sky": sky,
        "source": ("E3M1 s0/s339/s343: floor 379, ceiling 3491 parallax, "
                   "blocking two-sided faces in the district's facade stone "
                   "at y_repeat 8"),
    }


def termination_faults(disk, declared, *, standing_height: int) -> list[str]:
    """Every road end is a declared termination, and reads like one.

    The gate the model needs and Gravesend fails: a road that simply stops
    against a building face or a kerb has no end, and a body walking it sees
    the level run out.
    """
    out = []
    for record in declared:
        rise = int(record.get("rise", 0)) / float(standing_height)
        sky = int(record.get("sky", 0)) / float(standing_height)
        low, high = END_WALL_RISE_BODIES
        if not (low - 0.5 <= rise <= high + 0.5):
            out.append(f"{record['name']}: stands {rise:.2f} bodies above the "
                       f"road; E3M1's three are {low}-{high}")
        low, high = END_WALL_SKY_BODIES
        if not (low - 0.5 <= sky <= high + 0.5):
            out.append(f"{record['name']}: {sky:.2f} bodies of sky above it; "
                       f"E3M1's three are {low}-{high}")
        if int(record.get("floor_picnum", 0)) != END_WALL_FLOOR_TILE:
            out.append(f"{record['name']}: its top wears "
                       f"{record.get('floor_picnum')}, not {END_WALL_FLOOR_TILE}")
        if not int(record.get("face_cstat", 0)) & END_WALL_CSTAT_BLOCKING:
            out.append(f"{record['name']}: its faces do not block -- you may "
                       f"not walk up the end of a street")
    return out
