"""Light pools: the only way a district-sized sector can have lighting.

Blood lights a street by *subdividing* it -- E3M1's street network is 20
sectors for a T of streets, and shade varies between them.  Gravesend's
massing is one region per district (the E2M6 form), so shade is uniform
across a whole district and every street frame reads flat no matter how
good the tiles are.

A light pool is the campaign's answer at the smallest possible cost: a
small sector cut into the street floor under a lamp.  Its brightness is now
derived by LightBomb from the declared lamp source rather than stored as a
second shade number.  One sector and a short faceted rim buys a pool of light,
and the geometry is otherwise inert -- the floor is flush, so nothing changes
underfoot.

Pools are placed from the street-furniture rate (E3M1 runs a light prop per
4-5k units of street frontage) at the places a city actually lights: venue
mouths, gates, stair heads, and junctions.
"""

from __future__ import annotations

import math

from bloodmap.levelprog import Frame, RECT_FACES, Style

COMPASS = dict(zip(RECT_FACES, range(4)))

#: A pool is two player-widths across: big enough to read as light on the
#: ground, small enough that ten of them cost 40 walls.  The footprint is a
#: four-sided diamond approximation of a circle: its edges remain wide enough
#: for Build's walkable portal rule while the angled rim reads as a pool of
#: light instead of a square patch.
POOL = 1536
POOL_SIDES = 4

#: Outdoor lamps need a stronger source than an indoor bracket: the open sky
#: absorbs the upward half of the rays and the road sector is large.  This is
#: a source property, not a hand-tuned floor shade; LightBomb turns it into
#: the actual generated surface values.
LAMP_INTENSITY = 2.0

#: Flicker, on the campaign's commonest wave (flicker2).
FLICKER = {"amplitude": -8, "shade_wave": 7, "shade_frequency": 6}


def _pool_outline(size: int) -> list[tuple[int, int]]:
    """Return an integer, counter-clockwise circular pool footprint."""
    center = size / 2.0
    radius = size / 2.0
    return [
        (int(round(center + math.cos(2.0 * math.pi * index / POOL_SIDES) * radius)),
         int(round(center + math.sin(2.0 * math.pi * index / POOL_SIDES) * radius)))
        for index in range(POOL_SIDES)
    ]


#: What a pool's floor is before the lamp lights it.  It has to be the same
#: in every district: LightBomb adds to the base, so a pool inheriting its
#: street's pavement shade would make one identical lamp read four different
#: brightnesses across the city.  This is the value all nine had while they
#: hung off the root, and now it is stated rather than inherited by accident.
BASE_SHADE = 32


def pool(district, street_room, name: str, *, x: int, y: int, floor_z: int,
         clear_height: int, floor_picnum: int, wall_picnum: int,
         ceiling_picnum: int, sky: bool,
         flicker: bool = True, size: int = POOL) -> object:
    """Cut one light-receiving sector into `street_room` at (x, y).

    Its shade is intentionally absent.  The lamp standing in this sector is a
    declared LightBomb source, so the emitted geometry receives generated light
    instead of carrying a second hand-tuned shade number.
    """
    half = size // 2
    origin_x, origin_y = int(x - half), int(y - half)
    outline = _pool_outline(size)
    frame = street_room.world_frame()
    street_room.carve([(origin_x - frame.dx + px, origin_y - frame.dy + py)
                       for px, py in outline])
    behavior = dict(FLICKER) if flicker else {}
    # A light pool belongs to the street it lights.  Eleven of them used to
    # sit at the top of the city, one room each, as siblings of the
    # districts -- a singleton assembly for a patch of brighter paving.
    # `citytree.sub` puts it inside the street; the district still declares
    # the portals, because a room may not.
    import citytree
    room = citytree.make_room(
        street_room, f"lightpool_{name}", outline,
        role="detail", faces={f"edge{index}": index
                               for index in range(POOL_SIDES)},
        # Relative to the street it now sits in, not to the city: a frame
        # is stated in its parent's coordinates.
        frame=Frame(origin_x - frame.dx, origin_y - frame.dy, -frame.dz),
        intent={"light_pool": name, "generated_surfaces": ["floor"]},
        region_kwargs={"sector_behavior": behavior} if behavior else {},
        note=f"light pool: {name}",
    )
    room.surfaces(floor_picnum=floor_picnum, wall_picnum=wall_picnum,
                  ceiling_picnum=ceiling_picnum, parallax_ceiling=sky,
                  floor_z=floor_z, clear_height=clear_height,
                  floor_shade=BASE_SHADE)
    for index in range(POOL_SIDES):
        district.connect(room.face(f"edge{index}"), street_room.face("north"),
                         connection_id=f"connection:pool_{name}_{index}")
    return room

