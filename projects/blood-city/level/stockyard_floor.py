"""The bleeding floor: the stockyard drain's middle, opened into one vaulted room where the slaughterhouse washes down into the race.

The owner's brief, 2026-11-25: the stockyard branch is "the most cramped part of
the sewers and not one enemy in it ... widen or raise one stretch". The drain was
one corridor 37 metres long. Now it comes along the wall of a hall seven units wide:
half a vault, flat over the water and falling to the east wall. (It lay both sides
of the race until 2026-11-25, and the arcade's sunk court is over the west side.)
Blood comes out of a pipe in the east wall, down a gutter across the floor and
into the race, which is the ring's green water above that and blood below it.
Carcasses hang over the gutter and the dry floor; a dock a step up along the east
wall, which the gutter cuts, is the one other level. Nothing else is in it.

Built of `bloodmap.arrangement`; the corridors either side are the sewer's.
"""

from __future__ import annotations

from bloodmap import arrangement as A
from bloodmap.slope import SlopeSpec

PU = 1024
LAYER = "stockyard_floor"
KEY = "region:gravesend/sewer/stockyard_floor:hall"
X0, X1, Y0, Y1 = 48.75, 55.75, 39.5, 44.5
RACE = (49.25, 50.25)
GUTTER = (41.75, 42.25)
DOCK = 53.75
FLOOR, WATER, GUTTER_Z, DOCK_Z = 61440, 63488, 62464, 57344
CROWN, FALL = 20480, 3072                                  # the roof falls this much a plan unit, from the race to the east wall
#: where the blood has come right across the race: from the gutter's mouth, slantwise down the current
PLUME = ((50.25, 41.75), (50.25, 44.5), (49.25, 44.5), (49.25, 43.75))
TILE, PAVING, ROOF, BLOOD = 296, 291, 1030, 1120            # the drain's own


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def plan() -> list:
    place = A.Arrangement()
    place.add("west", _rect(X0, Y0, RACE[0], Y1))
    place.add("race", _rect(RACE[0], Y0, RACE[1], Y1))
    place.add("east", _rect(RACE[1], Y0, DOCK, Y1))
    place.add("dock", _rect(DOCK, Y0, X1, Y1))
    place.add("gutter", _rect(RACE[1], GUTTER[0], X1, GUTTER[1]))
    return place.resolve()


def roof(x: float) -> int:
    """How high the roof is over a point across the hall (plan units)."""
    return round(CROWN + FALL * max(x - RACE[1], 0))


def build(layout, strips: dict) -> dict[str, str]:
    """Lay the hall between two lengths of corridor; `strips` is {(y, x0, x1): region id} of their ends."""
    from l3_sewer import FLOW, WATER_DEPTH, flow_behavior
    from settling_hall import _edge_on
    cells = plan()
    by_name = {c.name: c for c in cells}

    def surface(name):
        kind = name.rstrip("_01")
        wet = kind in ("race", "gutter")
        floor = {"race": WATER, "gutter": GUTTER_Z, "dock": DOCK_Z}.get(kind, FLOOR)
        more = {}
        if kind not in ("race", "west"):
            near, far = {"east": (RACE[1], DOCK), "dock": (DOCK, X1), "gutter": (RACE[1], X1)}[kind]
            more["ceiling_slope"] = SlopeSpec(hinge=_edge_on(by_name[name], x=_q(near)), rise_z=roof(far) - roof(near))
            ceiling = roof(near)
        else:
            ceiling = CROWN
        if wet:
            run = FLOW["stockyard_drain"] if kind == "race" else (1024, 24, False)
            more["sector_behavior"] = {"amplitude": -4, "shade_frequency": 4, "depth": WATER_DEPTH if kind == "race" else 1,
                                       **flow_behavior(*run)}
        return dict(floor_z=floor, ceiling_z=ceiling, wall_picnum=TILE, floor_picnum=BLOOD if wet else PAVING,
                    ceiling_picnum=ROOF, floor_shade=38, wall_shade=24, ceiling_shade=28, layer=LAYER, role="interior",
                    declared_zero_exit=True, intent={"kind": "furnished"}, **more)

    regions = A.lay(layout, KEY, cells, surface)
    for (y, x0, x1), strip in strips.items():
        middle = (x0 + x1) / 2
        cell = "race" if RACE[0] < middle < RACE[1] else "west" if middle < RACE[0] else ("east_0" if y == Y0 else "east_1")
        a, b = ((_q(x0), _q(y)), (_q(x1), _q(y))) if y == Y0 else ((_q(x1), _q(y)), (_q(x0), _q(y)))
        layout.add_connection(f"connection:stockyard_floor:{y}:{x0}", strip, regions[cell], a1=b, a2=a,
                              min_width=1, min_opening=0)
    layout.add_overlay("blood:stockyard_gutter", regions["gutter"], list(by_name["gutter"].outer), floor_pal=7)
    layout.add_overlay("blood:stockyard_race", regions["race"], [(_q(x), _q(y)) for x, y in PLUME], floor_pal=7)
    _furnish(layout, regions)
    return regions


#: the carcasses on their hooks (E3M2's): (cell, x, y, repeat)
CARCASSES = (("east_0", 52.6, 40.4, 46), ("east_0", 51.6, 41.2, 42), ("gutter", 52.3, 42.0, 48), ("east_1", 52.9, 43.1, 44),
             ("east_1", 51.7, 43.7, 42))
#: an empty hook, over the way in and over the far floor
HOOKS = (("east_0", 51.0, 40.2, 42), ("dock_1", 54.6, 43.6, 40))
#: what has run off them
STAINS = (("east_0", 52.6, 40.4, 44, 512), ("east_0", 51.6, 41.2, 36, 0), ("east_1", 52.9, 43.1, 48, 1024), ("east_1", 51.7, 43.7, 30, 300))


def _furnish(layout, regions) -> None:
    from bloodmap.placement import drawn_extent
    from bloodmap.shade_table import _art
    from l3_foundry import _attested

    def put(name, cell, source, x, y, *, hang=False, over=0, **fields):
        spec = _attested(source[0], source[1], picnum=source[2])
        fields = {**spec["fields"], **fields}
        art = _art()[source[2]]
        top, bottom = drawn_extent(art.height, art.animation["yofs"], fields["y_repeat"], fields["cstat"])
        z = roof(x) + 256 - top if hang else layout.regions[regions[cell]].floor_z - 16 - over - (0 if fields["cstat"] & 32 else bottom)
        layout.add_sprite(f"sewer:bleeding_{name}", regions[cell], x=_q(x), y=_q(y), z=z, behavior=dict(spec["behavior"]), **fields)

    for k, (cell, x, y, size) in enumerate(CARCASSES):
        put(f"carcass_{k}", cell, ("E3M2", 416, 1351), x, y, hang=True, x_repeat=size, y_repeat=size)
    for k, (cell, x, y, size) in enumerate(HOOKS):
        put(f"hook_{k}", cell, ("E1M8", 417, 692), x, y, hang=True, x_repeat=size, y_repeat=size)
    for k, (cell, x, y, size, angle) in enumerate(STAINS):
        put(f"stain_{k}", cell, ("E2M4", 0, 713), x, y, x_repeat=size, y_repeat=size, cstat=32, shade=8, angle=angle)
    # the slaughterhouse's pipe, dripping into the gutter's head
    put("pipe", "gutter", ("E1M8", 0, 977), X1 - 8 / PU, 42.0, over=9000, angle=1024, x_repeat=66, y_repeat=58, shade=-8)
