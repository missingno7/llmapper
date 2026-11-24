"""A railway carriage built of sectors: solid hull, glazed windows, upholstered benches, and a roof of its own, standing in one hole of its host.

The owner, 2026-11-24, of the one-sector train before it: "The whole train is
just single sector and everything inside are sprites, we should be able to
make it out of sectors ... This should make the train look better, more solid
and not feeling like cut out of paper."

How Blood builds one, measured (study `moving-bodies`):

* MACHINERY-1WAYVEHICLE s2-s10, the tutorial: zero-height sectors for the
  solid corners, side sectors with a sill and a head, one deck.
* DWE1M2 s225-s228, s418-s423: hull corners of floor = ceiling at the host's
  roof, so the host draws one whole wall from the ground up; the saloon under
  a ceiling of its own; a window in two half bays with the glass between.
* E1M3's cars (s2-s25): walls 109, ceiling 454/455, carpet 300-308, a bench is
  a strip raised 3,072 faced in its own cover, a window bay is lined with
  curtain 146 in wood 20.

Everything is laid out on a grid of units in the carriage's own axes: `u`
along it, `v` across it from the back to the platform side. `Axes` turns a
unit into world coordinates with two integer vectors, so a carriage may stand
square ((64, 0), (0, 64)) or askew on a lattice ((63, 16), (-16, 63), which is
14 degrees and keeps every point an integer).

The carriage does not know whether it moves: `bloodmap.mechanism.rigid_body`
makes its `members` one body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from bloodmap.planar_geom import collinear_overlap_interval
from bloodmap.planar_layout import PlanarLayout

#: across, in units: running board, hull, the room inside, hull, board
BOARD, HULL, INSIDE = 1, 3, 42
BENCH = 9
WIDTH = 2 * (BOARD + HULL) + INSIDE
#: along: the end platform, and the end wall
END = 3
ARM = 1

SILL, HEAD = 7168, 19456
DOOR_HEAD = 20480
ROOF, CLERESTORY, TOP = 21504, 25088, 25856
SEAT, ARM_REST, DESK = 5632, 8192, 7168
BOARD_DROP = 512
GANGWAY = (20, 30)
FRONT = (13, 37)
#: the two windows in an end wall, either side of its shut gangway door
END_WINDOWS = ((9, 17), (33, 41))
DESK_SPAN = (12, 38)

# surfaces (see the module note for where each is Blood's)
WAINSCOT, CARPET, CEILING, CUSHION, BENCH_WOOD, CURTAIN, WOOD = 109, 304, 454, 305, 67, 146, 20
PILLAR, HEADER, LIVERY, UNDERFRAME, STEEL = 2453, 255, 1665, 470, 255
TREAD = 438
DOOR_LEAF = 199
GLASS, BROKEN = 266, 1099
BLOCK = 1 | 16 | 64

ROOMS = {"aisle", "seat", "arm", "cab", "desk"}


@dataclass(frozen=True)
class Axes:
    """Where a carriage's units are in the world: an origin and the step of one unit along and across."""

    origin: tuple[int, int]
    along: tuple[int, int] = (64, 0)
    across: tuple[int, int] = (0, 64)

    def __call__(self, u: float, v: float) -> tuple[int, int]:
        x = self.origin[0] + u * self.along[0] + v * self.across[0]
        y = self.origin[1] + u * self.along[1] + v * self.across[1]
        return round(x), round(y)


@dataclass(frozen=True)
class Plan:
    """What a carriage holds along its length, in units.

    `slots` are the window places, (from, to) along; `door` is the slot that
    is an open doorway on the platform side (a window on the other). `cab` is
    the length of the driver's cab at the far end, none if 0. `broken` names
    the windows whose glass is a hole.
    """

    length: int
    slots: tuple[tuple[int, int], ...]
    door: int | None = None
    cab: int = 0
    broken: frozenset = frozenset()

    @property
    def inside(self) -> tuple[int, int]:
        return 2 * END, self.length - 2 * END

    @property
    def saloon(self) -> tuple[int, int]:
        a, b = self.inside
        return (a, b - self.cab - 1) if self.cab else (a, b)

    @property
    def cab_window(self) -> tuple[int, int]:
        a = self.saloon[1] + 1
        return a + 4, a + self.cab - 4

    def arms(self) -> list[int]:
        """The arm rests: one unit wide, on the pillar between two windows."""
        return [(a[1] + b[0]) // 2 for a, b in zip(self.slots, self.slots[1:])]

    def bays(self) -> list[tuple[int, int]]:
        a, b = self.saloon
        arms = self.arms()
        return list(zip([a, *(x + ARM for x in arms)], [*arms, b]))


@dataclass
class Carriage:
    plan: Plan
    axes: Axes
    deck: int
    host: str
    key: str
    regions: dict[str, str] = field(default_factory=dict)
    roles: dict[str, str] = field(default_factory=dict)

    @property
    def members(self) -> list[str]:
        return list(self.regions.values())

    def at(self, name: str) -> str:
        return self.regions[name]


def _rect(u0, u1, v0, v1):
    return ((u0, v0), (u1, v0), (u1, v1), (u0, v1))


def _area(loop):
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(loop, (*loop[1:], loop[0])))


def build(layout: PlanarLayout, key: str, host: str, axes: Axes, deck: int, plan: Plan, *,
          pal: int = 0, shade: int = 8, water: int | None = None, water_tile: int = 2915,
          water_behavior: dict | None = None, kind: str = "furnished") -> Carriage:
    """Stand a carriage in `host`, joined to it along its running board."""
    car = Carriage(plan, axes, deck, host, key)
    top = layout.regions[host].ceiling_z
    if top != deck - TOP:
        raise ValueError(f"{key}: the host's roof is {deck - top} over the deck, the body is {TOP} tall")
    length, width = plan.length, WIDTH
    south, north = width - BOARD - HULL, BOARD + HULL      # the inner faces of the two flanks

    def add(name, role, loop, floor, ceiling, floor_tile, ceiling_tile, *, holes=(), zero=False):
        region, behavior = f"{key}:{name}", {}
        if water is not None and floor > water and floor != ceiling:
            floor, floor_tile, behavior = water, water_tile, dict(water_behavior or {})
        solid_piece = role == "pillar"
        layout.add_region(
            region, [axes(u, v) for u, v in loop],
            holes=[[axes(u, v) for u, v in h] for h in holes],
            floor_z=floor, ceiling_z=min(ceiling, floor), floor_picnum=floor_tile,
            ceiling_picnum=ceiling_tile, wall_picnum=WAINSCOT, floor_shade=shade, wall_shade=shade,
            ceiling_shade=shade, layer=layout.regions[host].layer, role="detail",
            # a drowned carriage's windows are its only openings
            declared_zero_exit=zero or plan.door is None or role not in ("aisle", "door"),
            intent={"kind": "furnished" if solid_piece or role == "board" else kind,
                    "floor_pal": pal if floor_tile == CARPET else 0,
                    "ceiling_pal": pal if ceiling_tile == CEILING else 0},
            sector_behavior=behavior)
        car.regions[name], car.roles[region] = region, role

    def solid(name, loop):
        add(name, "pillar", loop, top, top, TREAD, STEEL, zero=True)

    # -- the running board: a ledge all round, and the couplings' platforms
    hull = _rect(END, length - END, BOARD, width - BOARD)
    add("board", "board", _rect(0, length, 0, width), deck + BOARD_DROP, top, TREAD, STEEL,
        holes=(tuple(reversed(hull)),), zero=True)

    # -- the flanks: pillars and windows, and one doorway
    a, b = plan.inside
    for side, (outer, inner) in (("north", (BOARD, north)), ("south", (width - BOARD, south))):
        glass = outer + (1 if side == "north" else -1)     # the pane, one unit in from the skin
        openings = sorted([*plan.slots, *([plan.cab_window] if plan.cab else [])])
        cursor = None
        for index, (u0, u1) in enumerate(openings):
            if index:
                solid(f"{side}_pillar_{index}", _rect(cursor, u0, *sorted((outer, inner))))
            cursor = u1
            if side == "south" and plan.door is not None and (u0, u1) == plan.slots[plan.door]:
                add("door", "door", _rect(u0, u1, *sorted((outer, inner))),
                    deck, deck - DOOR_HEAD, TREAD, STEEL)
                continue
            for part, span in (("out", (outer, glass)), ("in", (glass, inner))):
                add(f"{side}_window_{index}_{part}", f"window_{part}", _rect(u0, u1, *sorted(span)),
                    deck - SILL, deck - HEAD, WOOD, WOOD, zero=True)
        # the two corners run round into the end walls
        first, last = openings[0][0], openings[-1][1]
        far = END_WINDOWS[0][0] if side == "north" else END_WINDOWS[1][1]
        nose = (FRONT[0] if side == "north" else FRONT[1]) if plan.cab else far
        west = ((END, outer), (first, outer), (first, inner), (a, inner), (a, far), (END, far))
        east = ((length - END, outer), (last, outer), (last, inner), (b, inner), (b, nose), (length - END, nose))
        for name, loop in ((f"{side}_west_corner", west), (f"{side}_east_corner", east)):
            solid(name, loop if _area(loop) > 0 else tuple(reversed(loop)))

    # -- the end walls: a shut gangway door sunk in each, or the driver's window
    for name, skin, room, step in [("west", END, a, 1)] + ([] if plan.cab else [("east", length - END, b, -1)]):
        for part, span in (("out", (skin, skin + step)), ("in", (room - step, room))):
            add(f"{name}_gangway_{part}", "recess", _rect(*sorted(span), *GANGWAY),
                deck, deck - HEAD, TREAD, WOOD, zero=True)
        solid(f"{name}_gangway_leaf", _rect(*sorted((skin + step, room - step)), *GANGWAY))
        for index, ((v0, v1), post) in enumerate(zip(END_WINDOWS, ((END_WINDOWS[0][1], GANGWAY[0]),
                                                                  (GANGWAY[1], END_WINDOWS[1][0])))):
            solid(f"{name}_gangway_post_{index}", _rect(*sorted((skin, room)), *post))
            for part, span in (("out", (skin, skin + step)), ("in", (skin + step, room))):
                add(f"{name}_window_{index}_{part}", f"window_{part}", _rect(*sorted(span), v0, v1),
                    deck - SILL, deck - HEAD, WOOD, WOOD, zero=True)
    if plan.cab:
        pane = length - END - 1
        for part, span in (("out", (pane, length - END)), ("in", (b, pane))):
            add(f"front_window_{part}", f"window_{part}", _rect(*span, *FRONT),
                deck - SILL - 1024, deck - HEAD, STEEL, STEEL, zero=True)

    # -- inside: benches along both flanks, an aisle under a raised roof
    s0, s1 = plan.saloon
    n_in, s_in = north + BENCH, south - BENCH
    bays = plan.bays()
    for side, span in (("north", (north, n_in)), ("south", (s_in, south))):
        for index, (u0, u1) in enumerate(bays):
            if side == "south" and index == plan.door:
                continue
            add(f"{side}_seat_{index}", "seat", _rect(u0, u1, *span),
                deck - SEAT, deck - ROOF, CUSHION, WOOD, zero=True)
        for index, u in enumerate(plan.arms()):
            add(f"{side}_arm_{index}", "arm", _rect(u, u + ARM, *span),
                deck - ARM_REST, deck - ROOF, WOOD, WOOD, zero=True)
    aisle = [(s0, n_in), (s1, n_in), (s1, s_in)]
    if plan.door is not None:
        d0, d1 = bays[plan.door]
        aisle += [(d1, s_in), (d1, south), (d0, south), (d0, s_in)]
    aisle += [(s0, s_in)]
    add("aisle", "aisle", tuple(aisle), deck, deck - CLERESTORY, CARPET, CEILING)
    if plan.cab:
        c0 = s1 + 1
        solid("partition_north", _rect(s1, c0, north, GANGWAY[0]))
        solid("partition_south", _rect(s1, c0, GANGWAY[1], south))
        add("cab_door", "door", _rect(s1, c0, *GANGWAY), deck, deck - HEAD, TREAD, WOOD)
        d0, d1 = DESK_SPAN
        add("cab", "aisle", ((c0, north), (b, north), (b, d0), (b - 3, d0), (b - 3, d1), (b, d1),
                             (b, south), (c0, south)), deck, deck - ROOF, TREAD, CEILING)
        add("desk", "desk", _rect(b - 3, b, d0, d1), deck - DESK, deck - ROOF, STEEL, CEILING, zero=True)

    # -- the one hole in the host, and every joint
    layout.carve_hole(host, [axes(u, v) for u, v in _rect(0, length, 0, width)])
    _join(layout, car, pal)
    return car


def _edges(layout, region):
    spec = layout.regions[region]
    for loop in (spec.outer, *spec.holes):
        yield from zip(loop, (*loop[1:], loop[0]))


def joints(layout, left, right):
    """Every stretch of wall two regions share, whatever else touches it."""
    for p, q in _edges(layout, left):
        for r, s in _edges(layout, right):
            overlap = collinear_overlap_interval(p, q, r, s)
            if overlap and overlap[0] != overlap[1]:
                yield overlap


def _join(layout, car, pal):
    for left, right in [*combinations(car.members, 2), (car.at("board"), car.host)]:
        for index, (p, q) in enumerate(joints(layout, left, right)):
            layout.add_connection(f"{left}|{right}:{index}", left, right, a1=p, a2=q,
                                  min_width=1, min_opening=0)
            for seen, beyond in ((left, right), (right, left)):
                fields = _skin(car, seen, beyond, pal, abs(q[0] - p[0]) + abs(q[1] - p[1]))
                if fields:
                    layout.paint_wall(seen, p, q, fixed_frame="x_repeat" in fields, **fields)


def _skin(car: Carriage, seen: str, beyond: str, pal: int, length: int) -> dict:
    """What a space sees on the face of the next: the one table of the carriage's finish."""
    here, there = car.roles.get(seen, "host"), car.roles.get(beyond, "host")
    if {here, there} == {"window_out", "window_in"}:
        name = seen.rsplit(":", 1)[-1]
        broken = any(name.startswith(hole) for hole in car.plan.broken)
        return {"over_picnum": BROKEN if broken else GLASS, "cstat": BLOCK | (0 if broken else 128),
                "pal": 0, "shade": 0, "x_repeat": 8, "y_repeat": 8}
    fields = {
        ("host", "board"): {"picnum": UNDERFRAME},
        ("board", "host"): {"picnum": UNDERFRAME},
        ("board", "pillar"): {"picnum": PILLAR if length <= 5 * 65 else UNDERFRAME},
        # the line's livery above and below an opening, the whole of its 256 rows in each band
        ("board", "window_out"): {"picnum": LIVERY, "pal": pal, "x_repeat": max(1, length // 128), "y_repeat": 68},
        ("board", "door"): {"picnum": LIVERY, "pal": pal, "x_repeat": max(1, length // 128), "y_repeat": 68},
        ("board", "recess"): {"picnum": HEADER, "pal": pal},
        ("recess", "pillar"): {"picnum": DOOR_LEAF, "pal": pal},
        ("window_out", "pillar"): {"picnum": STEEL, "pal": pal},
        ("window_in", "pillar"): {"picnum": CURTAIN, "pal": pal},
        ("door", "pillar"): {"picnum": WOOD},
    }.get((here, there))
    if fields is not None or here not in ROOMS:
        return fields or {}
    if there in ("pillar", "window_in", "door", "recess"):
        # whole panelling from the room's own ceiling down, past every opening (bit 4)
        return {"picnum": WAINSCOT, "cstat": 4, "pal": pal}
    return {"picnum": {"seat": BENCH_WOOD, "desk": STEEL}.get(there, WOOD)}
