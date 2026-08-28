"""Light pools: the only way a district-sized sector can have lighting.

Blood lights a street by *subdividing* it -- E3M1's street network is 20
sectors for a T of streets, and shade varies between them.  Gravesend's
massing is one region per district (the E2M6 form), so shade is uniform
across a whole district and every street frame reads flat no matter how
good the tiles are.

A light pool is the campaign's answer at the smallest possible cost: a
small sector cut into the street floor under a lamp, a few shade points
lighter than the street around it, animating if the lamp is a flame.  One
sector and four walls buys a pool of light, and the geometry is otherwise
inert -- the floor is flush, so nothing changes underfoot.

Pools are placed from the street-furniture rate (E3M1 runs a light prop per
4-5k units of street frontage) at the places a city actually lights: venue
mouths, gates, stair heads, and junctions.
"""

from __future__ import annotations

from bloodmap.levelprog import Frame, RECT_FACES, Style

COMPASS = dict(zip(RECT_FACES, range(4)))

#: A pool is two player-widths across: big enough to read as light on the
#: ground, small enough that ten of them cost 40 walls.
POOL = 1536

#: Shade step into the pool.  The campaign's lit sectors sit 8-16 points
#: brighter than the field around them; -12 read too faintly in the quay
#: frame against a street at +32, so the pool takes -18 and carries a fire.
POOL_SHADE_STEP = -18

#: Flicker, on the campaign's commonest wave (flicker2).
FLICKER = {"amplitude": -8, "shade_wave": 7, "shade_frequency": 6}


def pool(city, street_room, name: str, *, x: int, y: int, floor_z: int,
         clear_height: int, floor_picnum: int, wall_picnum: int,
         ceiling_picnum: int, sky: bool, street_shade: int,
         flicker: bool = True, size: int = POOL) -> object:
    """Cut one light pool into `street_room` at (x, y) in world units."""
    half = size // 2
    origin_x, origin_y = int(x - half), int(y - half)
    frame = street_room.world_frame()
    street_room.carve([(origin_x - frame.dx + dx, origin_y - frame.dy + dy)
                       for dx, dy in ((0, 0), (size, 0), (size, size), (0, size))])
    behavior = dict(FLICKER) if flicker else {}
    room = city.assembly(
        f"lightpool_{name}",
        style=Style(floor_picnum=floor_picnum, wall_picnum=wall_picnum,
                    ceiling_picnum=ceiling_picnum, parallax_ceiling=sky,
                    floor_z=floor_z, clear_height=clear_height,
                    floor_shade=street_shade + POOL_SHADE_STEP,
                    wall_shade=street_shade + POOL_SHADE_STEP),
    ).room(
        "pool", [(0, 0), (size, 0), (size, size), (0, size)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(origin_x, origin_y),
        region_kwargs={"sector_behavior": behavior} if behavior else {},
        note=f"light pool: {name}",
    )
    for face in ("north", "east", "south", "west"):
        city.connect(room.face(face), street_room.face("north"),
                     connection_id=f"connection:pool_{name}_{face}")
    return room


#: Blood's z-motion door sector types: the ones whose ceiling comes down to
#: the floor, so that the whole visible band of the wall facing them is the
#: two-sided wall's upper step.
DOOR_TYPES = {600, 602, 604, 614, 616, 618}


def settle_door_shading(level) -> dict:
    """Bring every door-facing wall back to its room's median shade.

    `shade_walls_directionally` shades a wall by the cosine between its
    normal and the room's implied light, which is right for a room and wrong
    for a door: whichever wall happens to face away from the lamp goes dark,
    and if that wall is the one with the door in it, the way out of the room
    is the blackest thing in the frame.  The pawn shop's door came out at
    shade 52 against a room median of 37, and the frame shows a black
    rectangle where the door should be.

    The campaign never does this.  Across E3M1, E3M2, E1M1, E6M1 and E4M9 --
    720 walls facing a z-motion door -- the median shade delta against the
    owning room is exactly +0.0, with p10 -5 and p90 +7.  A door is lit like
    the room it is in.

    So this runs after the directional pass and undoes it on doors only,
    leaving the rest of the room's modelling alone.
    """
    doors = {i for i, sector in enumerate(level.sectors)
             if int(_f(sector).get("type", 0)) in DOOR_TYPES
             or int(_f(sector)["floor_z"]) == int(_f(sector)["ceiling_z"])}
    settled = 0
    moved: list[int] = []
    for index, sector in enumerate(level.sectors):
        fields = _f(sector)
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        walls = list(range(start, start + count))
        if len(walls) < 3:
            continue
        shades = sorted(int(_f(level.walls[w])["shade"]) for w in walls)
        median = shades[len(shades) // 2]
        for wall in walls:
            wf = _f(level.walls[wall])
            if int(wf.get("next_sector", -1)) not in doors:
                continue
            was = int(wf["shade"])
            if was == median:
                continue
            wf["shade"] = median
            moved.append(was - median)
            settled += 1
    moved.sort()
    return {"walls_settled": settled,
            "largest_correction": moved[-1] if moved else 0,
            "median_correction": moved[len(moved) // 2] if moved else 0}


def _f(item):
    """A level item is either a dict with a "fields" key or the fields."""
    return item["fields"] if isinstance(item, dict) and "fields" in item else item


#: The campaign's within-room wall-shade spread, by floor area.  Measured
#: over 1,393 rooms of E3M1/E3M2/E6M1/E1M1/E4M9 (medians; p75 in brackets):
#:
#:     tiny   < 2M units^2     7  [15]
#:     small  2-10M           12  [22]
#:     medium 10-40M          19  [32]
#:     large  > 40M           21  [32]
#:
#: A room's light modelling grows with the room, which is the opposite of
#: what we were producing: `room_amplitude` sizes a room by WALL COUNT, and
#: our furniture is geometry, so the pawn shop -- 3.5 x 2.5 plan units with
#: four display pedestals in it -- has 22 walls and was shaded like a hall.
#: Its whole east wall came out at shade 52 against a room median of 37, and
#: in the frame that wall, the one with the door in it, is simply black.
#: The cap is the band's p75, NOT its median.  Capping at the median first
#: -- and it is a tempting number -- flattened 102 of 135 rooms and dropped
#: the level's measured contrast from 49.5 (campaign) to 32, which is
#: bloodmap.lighting's own recorded lesson: the campaign's spread is a
#: distribution with a long tail, and applying its average everywhere
#: produces a level with no light in it.  A cap at p75 removes the extreme
#: without removing the tail.
SPREAD_BY_AREA = ((2e6, 15), (10e6, 22), (40e6, 32), (float("inf"), 32))


def _sector_area(level, index) -> float:
    fields = _f(level.sectors[index])
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    acc = 0.0
    for wall in range(start, start + count):
        a = _f(level.walls[wall])
        b = _f(level.walls[int(a["point2"])])
        acc += int(a["x"]) * int(b["y"]) - int(b["x"]) * int(a["y"])
    return abs(acc) / 2


def settle_room_spread(level) -> dict:
    """Compress each room's wall shades to the spread its area earns.

    Shades are pulled toward the room's own median, so the light DIRECTION
    the directional pass modelled survives -- only its amplitude changes,
    and it changes to a number measured off the campaign rather than
    inferred from how many walls the room's furniture added.
    """
    compressed = 0
    biggest = 0
    for index, sector in enumerate(level.sectors):
        fields = _f(sector)
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        walls = list(range(start, start + count))
        if len(walls) < 4:
            continue
        shades = [int(_f(level.walls[w])["shade"]) for w in walls]
        spread = max(shades) - min(shades)
        if spread <= 0:
            continue
        area = _sector_area(level, index)
        target = next(t for bound, t in SPREAD_BY_AREA if area < bound)
        if spread <= target:
            continue
        median = sorted(shades)[len(shades) // 2]
        scale = target / spread
        for wall in walls:
            wf = _f(level.walls[wall])
            wf["shade"] = int(round(median + (int(wf["shade"]) - median) * scale))
        compressed += 1
        biggest = max(biggest, spread - target)
    return {"rooms_compressed": compressed, "largest_reduction": biggest}
