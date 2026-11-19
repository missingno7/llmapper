"""The pumping station: a road-level way into the sewer, with stairs.

The grate is a one-way drop -- 3.14 player heights, which the engine
forgives (kFallDamageFloor covers anything under 3.70) but which nobody can
climb back up.  The works stair is the way out, and it is tucked inside a
superblock where a player will not find it.

So this is the entrance the owner asked for and the one Blood itself
builds: a small technical building standing on the street, a door, and
stairs going down.  It is a lean-to on the works' east wall rather than a
free-standing hut, because a free-standing mass in the street would add a
tenth walk-around loop and the loop census is at its contract ceiling of
nine.

The descent is real geometry all the way: a straight flight reaches a short
cellar corridor, then a spiral falls 20,480 units into the sewer directly
below it.  The stair owns its annulus and leaves its newel solid; the corridor
meets only the long radial side of its first tread.  It is not a room wrapped
round a hole in the stair.
"""

from __future__ import annotations

import wires
from bloodmap import wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.spiral import INNER_RADIUS

from materials import FACADES, INTERIORS, MASONRY
from resolution import (GRADE, PU, STATION_STACK_LANDING_DEPTH,
                        STATION_STACK_PLANE, STREET_SKY)

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The station sits INSIDE the works mass with its door on the rail spur.
#: A lean-to bumped out of the works was tried first: `carve` adds a second
#: hole rather than unioning with the works hole, so the two holes ended up
#: sharing an edge, which is not a legal boundary.  Inside the mass the
#: rooms live in void that is already there, and the door on the spur reads
#: the same from the street.
SHED = (50 * PU, 5 * PU, 53 * PU, 8 * PU)   # x1 is the works' east face

#: One bay wide, on the bay grid, like every other opening in the city.
MOUTH_Y0, MOUTH_H = 6 * PU, 1024
DOOR_D, PORCH_D = 512, 512
#: A door-height porch so the facade owns the wall above the opening.
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_HEIGHT = 31744

#: Eight risers of one max step land exactly on the spiral's cellar plane.
STEP, TREAD = 4096, 512
FLIGHT = 8           # one straight run; the works void is long enough
STAIR_W = 1024
CELLAR_FLOOR_Z = STATION_STACK_PLANE
assert CELLAR_FLOOR_Z == GRADE + FLIGHT * STEP

#: The spiral's axis and the radial side of its first tread.  These values are
#: shared by the top approach and the prefab call in ``build_skeleton``.
PIT = (45056, 4608, 46080, 5632)
SPIRAL_AXIS = ((PIT[0] + PIT[2]) // 2, (PIT[1] + PIT[3]) // 2)
SPIRAL_RADIUS = 1000
SPIRAL_INNER_X = SPIRAL_AXIS[0] + INNER_RADIUS
SPIRAL_OUTER_X = SPIRAL_AXIS[0] + SPIRAL_RADIUS
# A one-bay-wide approach, perpendicular to the first tread.  Its south face
# is exactly the stair's long radial portal; the straight flight reaches its
# east end.  Keeping this a corridor rather than the former 3.5 x 2.5-bay
# cellar prevents a host sector from enclosing the spiral and making a
# zero-thickness C-shaped wall.
CELLAR = (SPIRAL_INNER_X, 4096, 47616, 5120)
PIT_LANDING = STATION_STACK_LANDING_DEPTH


# ---------------------------------------------------------------------------
# the machine hall
# ---------------------------------------------------------------------------
#: The owner, walking the build of 2026-11-18: "Pump station interior is a
#: bit small, we can make it as a big technical building with conveyor
#: belts and heavy machinery, you can look for places like this in game
#: corpus." The station was one room 1,536 by 3,584 with a stair in it.
#:
#: Measured over the 89 campaign and curated maps: E3M5's foundry hall is
#: ~10,752 square and 5.8 bodies high, E6M3's warehouse 8,192 x 8,448 and
#: 3.86. A belt is a floor that pans AND pushes: `pan_floor`, `drag`, a
#: velocity, and `pan_always` (E3M5 s44-52: velocity 48, angle 512; E6M3 and
#: E4M9 the same at 10 and 20). E6M3 sets its belts a step over the floor;
#: E3M5 runs its belt through presses that are low stretches of the same
#: belt (1.09 bodies clear) between open ones.
#:
#: The hall stands in the works block's unused west part, over the sewer
#: and clear of the flight; a gallery joins it to the old room, which is
#: now the station's lobby.
#: (South of the flight and the spiral, north of the works cellar: those
#: are in this arrangement, and two rooms of one arrangement may not share
#: plan.)
#: SIZES, redone. The owner, having walked it: "it looks quite good, but
#: it feels like a miniature". The hall was 7,680 by 6,400 -- 13 m by 11 m
#: -- and 3.86 bodies high; E3M5's foundry is 5.8, and Blood's halls of
#: 40M and over run a median 11,776 on their SHORT side. E3M6's tanks are
#: 1,440 in radius where these were 832, a man's arm-span.
#:
#: The street is 512 west of the hall, so it cannot simply be wider. The
#: works block has two bays nothing stood in -- north-west and south-east
#: of the old rectangle -- and the hall is now ONE room that takes both:
#: 7,680 by 10,752 overall (13 m by 18 m), 64M of floor, under E3M5's 5.8
#: bodies. The settling basin stands in the north bay, the filter drum by
#: the gallery, the belt between; the south bay is left open floor.
#: (bbox; the outline is `HALL_OUTLINE`)
MACHINE_HALL = (40 * PU, int(3.5 * PU), int(47.5 * PU), 14 * PU)
HALL_OUTLINE = ((40, 3.5), (44, 3.5), (44, 5.25), (47.5, 5.25), (47.5, 14),
                (44.5, 14), (44.5, 11.5), (40, 11.5))
HALL_FACES = {"north": 0, "bay_e": 1, "north_e": 2, "east": 3, "bay_s": 4,
              "bay_w": 5, "south": 6, "west": 7}
GALLERY = (int(47.5 * PU), int(5.5 * PU), int(50.5 * PU), 7 * PU)
HALL_CLEAR = 98304                 # 5.8 bodies: E3M5's foundry hall
GALLERY_CLEAR = 32768
#: the belt runs the hall's long way, west to east
BELT_X = (int(41.5 * PU), 46 * PU)
BELT_Y = (int(8.75 * PU), int(10.25 * PU))     # 1,536 wide: it was 1,024
BELT_RISE = 4096                   # one step: it can be boarded
BELT_VELOCITY, BELT_ANGLE = 48, 0      # E3M5's crusher line; toward +x
PRESS_CLEAR = 18432                # 1.09 bodies: E3M5 s44-52
#: (length, is a press): open, press, open, press, open
BELT_SECTIONS = ((1024, False), (768, True), (1024, False), (768, True),
                 (1024, False))
#: the machine at each end of the belt: a solid block, wider than the belt
MACHINE_HALF, MACHINE_DEPTH = 1024, 1024    # across the belt, along it
TANKS = ((42 * PU, 6 * PU), (int(45.25 * PU), int(7.1 * PU)))
TANK_RADIUS, TANK_RISE = 1024, 57344
#: Owner anchors, every one: 215 pressed metal, 255 rusted metal, 491 metal
#: plating, 470 riveted plating, 200 riveted threshold, 205 hazard stripes.
HALL_WALL, HALL_FLOOR, HALL_CEILING = 503, 255, 491
#: What the hall WEARS. The owner, 2026-11-18: "they don't look
#: sophisticated, there is no combination of decals and textures making it
#: to look like something, for example in that pump station". It was one
#: tile, 215 -- which is a tread-plate FLOOR pattern stood on the walls --
#: at one shade.
#:
#: Measured over the campaign's 900 metal-walled sectors: almost none of
#: their detail is wall sprites (0.21 per 10,000 of wall). It is (1) wall
#: tiles with the pipes and dials painted in, (2) walls cut into a rhythm
#: of panel and pilaster (E3M5 s138 `298:1536 115:256 298:1536`, s158
#: `495:1024 195:256 495:1024`), (3) hazard strips at every opening (E6M3
#: s150-157, E3M5 s6), (4) a console bank let into a wall on a raised sill
#: under a strip light (E3M3's generator, E3M6 s414-416), (5) faceted
#: solids shaded facet by facet (E3M5 s14: 4 -> 16 -> 4), (6) tanks as
#: stepped polygons (E3M6), and (7) light that is the sector's own: pools,
#: and a pulse on the machine (E3M3: wave 5, amplitude -32).
#:
#: Every tile is the owner's: 496-498 "technical wall with pipes", 2453
#: "technical riveted metal cladding", 489 "technical metal cladding", 503
#: "metal wall", 2462/2463/2477 "machinery", 500 "technical door", 2288
#: "fluorescent light", 205 hazard stripes.
PIPES = (496, 498, 497)
PILASTER, CLADDING, CABINET = 489, 2453, 500
CONSOLES = (2462, 2463, 2477)
STRIP_LIGHT = 2288
PANEL, PILASTER_W = 1280, 256
PANEL_LONG = 1792                  # the long walls: five bays in 10,240
#: The console alcove in the west wall: three consoles on a sill half a
#: body up, exactly one tile (16,384) high, 256 deep.
ALCOVE = (40 * PU - 256, 5888, 40 * PU, 8960)
ALCOVE_SILL, ALCOVE_CLEAR = 8192, 16384
#: (x0, y0, x1, y1): strip lights in the roof with their pool beneath
POOLS = ((int(46.5 * PU), int(5.75 * PU), int(47.25 * PU), int(6.25 * PU)),
         (int(45.5 * PU), int(12.5 * PU), int(46.5 * PU), 13 * PU),
         (int(42.25 * PU), int(10.6 * PU), int(43.75 * PU), int(11.1 * PU)),
         (int(45.0 * PU), int(10.6 * PU), int(46.5 * PU), int(11.1 * PU)))
POOL_SHADE, HALL_SHADE = 4, 22
#: The hall as a PROCESS. The owner, 2026-11-18: "Maybe we can think about
#: stuff in relations, like this machine connects to this, there is a
#: control panel here, there is a dirty water tank, the water goes there".
#: So the two tanks are no longer two of the same thing: the west one is an
#: open SETTLING basin of sewage, a rim 0.6 body high with the water moving
#: inside it; the east one is the closed FILTER drum. Each has a riser to
#: the roof. The sludge goes down the belt through the presses, and the
#: lever beside the console bank stops and starts that belt: the belt's
#: sectors pan only while their state is on (sectorfx.cpp: `panAlways ||
#: busy`) and the lever toggles it on one channel.
BELT_CHANNEL = wires.channel("pump:belt")
#: The presses move. E3M5's are started by a sprite that hears the level
#: begin (sprite 38: rx 7, tx 108, command 3, once) and never stop.
CRUSH_CHANNEL = wires.channel("pump:presses")
LEVEL_START = 7
#: region id -> sector type, set once the door pass has run (a press is
#: type 600 and is not a door)
LATE_TYPES: dict = {}
BASIN_RIM, BASIN_WATER = 10240, 6144
SEWAGE = 1120
RISER_RADIUS = 224
#: (from, to, how): written to the build manifest, and a test holds each
RELATIONS: list = []
#: E3M3's generator pulse, on the presses
PULSE = {"shade_wave": 5, "amplitude": -32, "shade_frequency": 5,
         "shade_always": 1, "shade_floor": 1, "shade_walls": 1}
PLINTH_RADIUS, PLINTH_RISE, TANK_SIDES = 1280, 8192, 12
#: girders, in bodies over the floor: 0.6 under the hall's roof
TRUSS_HEIGHT = 3.25
PLATING, THRESHOLD, HAZARD = 470, 200, 205
#: The belt's own tile is 376: E2M7's and E4M9's belts wear it and the
#: owner has not named it (it is on the list for the tile sheet).
BELT_TILE = 376
#: region id -> the tile every wall that LOOKS AT it wears
MACHINE_FACES: dict = {}
#: (x0, y0, x1, y1, tile): solid blocks standing in the hall
MACHINE_BLOCKS: list = []
#: region ids of the faceted solids: drums and plinths
FACETED: list = []


def machine_hall(shed, lobby, room):
    """The hall, its gallery, the belt, the presses and the tanks."""
    hx0, hy0, hx1, hy1 = MACHINE_HALL
    hall = room("machine_hall", hx0, hy0, hx1, hy1, clear=HALL_CLEAR,
                outline=[(int(x * PU) - hx0, int(y * PU) - hy0)
                         for x, y in HALL_OUTLINE],
                faces=HALL_FACES,
                rk={"portal_wall_picnum": HALL_WALL},
                note="the machine hall: a belt through two presses, and the "
                     "pump tanks")
    hall.surfaces(wall_picnum=HALL_WALL, floor_picnum=HALL_FLOOR,
                  ceiling_picnum=HALL_CEILING)
    gx0, gy0, gx1, gy1 = GALLERY
    gallery = room("gallery", gx0, gy0, gx1, gy1, clear=GALLERY_CLEAR,
                   rk={"portal_wall_picnum": HALL_WALL},
                   note="the gallery from the lobby to the machine hall")
    gallery.surfaces(wall_picnum=HALL_WALL, floor_picnum=HALL_FLOOR,
                     ceiling_picnum=HALL_CEILING)
    shed.connect(gallery.face("east"), lobby.face("west"),
                 connection_id="connection:pump_gallery_lobby")
    shed.connect(gallery.face("west"), hall.face("east"),
                 connection_id="connection:pump_gallery_hall")

    # The belt line: one hole in the hall's floor plan, an I -- a machine
    # block at each end and the belt between them.
    bx0, bx1 = BELT_X
    by0, by1 = BELT_Y
    my0 = (by0 + by1) // 2 - MACHINE_HALF
    my1 = (by0 + by1) // 2 + MACHINE_HALF
    line = [(bx0 - MACHINE_DEPTH, my0), (bx0, my0), (bx0, by0), (bx1, by0),
            (bx1, my0), (bx1 + MACHINE_DEPTH, my0),
            (bx1 + MACHINE_DEPTH, my1), (bx1, my1), (bx1, by1), (bx0, by1),
            (bx0, my1), (bx0 - MACHINE_DEPTH, my1)]
    hall.carve([(x - hx0, y - hy0) for x, y in line])
    MACHINE_BLOCKS.append((bx0 - MACHINE_DEPTH, my0, bx0, my1, CABINET))
    MACHINE_BLOCKS.append((bx1, my0, bx1 + MACHINE_DEPTH, my1, CABINET))
    cursor, previous = bx0, None
    for index, (length, press) in enumerate(BELT_SECTIONS):
        clear = PRESS_CLEAR if press else HALL_CLEAR - BELT_RISE
        piece = room(
            f"belt_{index}", cursor, by0, cursor + length, by1,
            floor_z=GRADE - BELT_RISE, clear=clear,
            rk={"portal_wall_picnum": PLATING, "sector_behavior": (
                #: a press: E3M5 s45/47/50, field for field. It slams shut
                #: in two tenths, waits, rises in a second and a half, and
                #: both re-triggers keep it going for ever; `crush` kills
                #: what is under it. Its belt never stops (`pan_always`).
                {"pan_floor": 1, "pan_always": 1, "drag": 1,
                 "pan_velocity": BELT_VELOCITY, "pan_angle": BELT_ANGLE,
                 "rx_id": CRUSH_CHANNEL, "busy_wave_a": 1, "busy_wave_b": 3,
                 "busy_time_a": 2, "busy_time_b": 15 - 3 * (index // 2),
                 "wait_time_b": 10 - 3 * (index // 2),
                 "retrigger_a": 1, "retrigger_b": 1, "crush": 1,
                 "off_ceiling_z": GRADE - BELT_RISE - PRESS_CLEAR,
                 "on_ceiling_z": GRADE - BELT_RISE,
                 "off_floor_z": GRADE - BELT_RISE,
                 "on_floor_z": GRADE - BELT_RISE, **PULSE}
                if press else
                {"pan_floor": 1, "pan_always": 0, "drag": 1, "state": 1,
                 "rx_id": BELT_CHANNEL,
                 "pan_velocity": BELT_VELOCITY, "pan_angle": BELT_ANGLE})},
            note=("a press: the belt runs under it" if press
                  else "the belt, open"))
        piece.surfaces(wall_picnum=PLATING, floor_picnum=BELT_TILE,
                       ceiling_picnum=PLATING if press else HALL_CEILING)
        wires.wire("pump:presses" if press else "pump:belt").then(
            wiring.region(piece.region_id))
        #: the stripes go on the press, as E3M5 puts them on its jambs
        MACHINE_FACES[piece.region_id] = HAZARD if press else THRESHOLD
        if press:
            LATE_TYPES[piece.region_id] = 600
        for face in ("north", "south"):
            shed.connect(piece.face(face), hall.face("north"),
                         connection_id=f"connection:belt_{index}_{face}")
        if previous is not None:
            shed.connect(previous.face("east"), piece.face("west"),
                         connection_id=f"connection:belt_{index}_run")
        previous = piece
        cursor += length
    assert cursor == bx1, (cursor, bx1)

    # The pump tanks: a twelve-sided drum on a wider plinth (E3M6's are a
    # ten-sided plinth under a sixteen-sided drum), faceted so `dress` can
    # shade them facet by facet.
    import math
    import detailing

    def ring(cx, cy, radius):
        return [(cx + round(radius * math.cos(2 * math.pi * (k + 0.5) / TANK_SIDES)),
                 cy + round(radius * math.sin(2 * math.pi * (k + 0.5) / TANK_SIDES)))
                for k in range(TANK_SIDES)]

    def solid(name, points, rise, note, kind="machine", **surfaces):
        x0 = min(x for x, _y in points)
        y0 = min(y for _x, y in points)
        made = shed.room(
            name, [(x - x0, y - y0) for x, y in points], role="detail",
            faces={f"e{k}": k for k in range(len(points))},
            frame=Frame(x0, y0),
            region_kwargs={"declared_zero_exit": True},
            intent={"kind": kind}, note=note)
        made.surfaces(**{"wall_picnum": PILASTER, "floor_picnum": HALL_FLOOR,
                         "ceiling_picnum": HALL_CEILING,
                         "parallax_ceiling": False,
                         "floor_z": GRADE - rise,
                         "clear_height": HALL_CLEAR - rise, **surfaces})
        return made, (x0, y0)

    for index, (cx, cy) in enumerate(TANKS):
        basin = index == 0
        outer = ring(cx, cy, PLINTH_RADIUS)
        inner = ring(cx, cy, TANK_RADIUS if not basin else PLINTH_RADIUS - 192)
        riser = [(cx + dx, cy + dy) for dx, dy in (
            (-RISER_RADIUS, -RISER_RADIUS), (RISER_RADIUS, -RISER_RADIUS),
            (RISER_RADIUS, RISER_RADIUS), (-RISER_RADIUS, RISER_RADIUS))]
        hall.carve([(x - hx0, y - hy0) for x, y in outer])
        plinth, origin = solid(
            f"tank_{index}_plinth", outer,
            BASIN_RIM if basin else PLINTH_RISE,
            "the settling basin's rim" if basin else "the filter's plinth")
        plinth.carve([(x - origin[0], y - origin[1]) for x, y in inner])
        if basin:
            tank, inner_origin = solid(
                f"tank_{index}", inner, BASIN_WATER,
                "the settling basin: sewage, moving", floor_picnum=SEWAGE,
                floor_shade=HALL_SHADE - 6)
            tank.region_kwargs["sector_behavior"] = {
                "pan_floor": 1, "pan_always": 1, "pan_velocity": 8,
                "pan_angle": 256}
        else:
            tank, inner_origin = solid(f"tank_{index}", inner, TANK_RISE,
                                       "the filter drum")
        tank.carve([(x - inner_origin[0], y - inner_origin[1])
                    for x, y in riser])
        MACHINE_BLOCKS.append((riser[0][0], riser[0][1], riser[2][0],
                               riser[2][1], PILASTER))
        MACHINE_FACES[plinth.region_id] = THRESHOLD
        MACHINE_FACES[tank.region_id] = PILASTER
        FACETED.extend((plinth.region_id, tank.region_id))
        for name in list(plinth.faces):
            shed.connect(plinth.face(name), hall.face("north"),
                         connection_id=f"connection:plinth_{index}_{name}")
        for name in list(tank.faces):
            shed.connect(tank.face(name), plinth.face("e0"),
                         connection_id=f"connection:tank_{index}_{name}")
    RELATIONS.extend([
        ("settling basin", "filter drum", "side by side on one line, each "
         "with a riser to the roof; lettered INTAKE and FILTER"),
        ("filter drum", "belt", "the sludge line runs south of both tanks; "
         "lettered SLUDGE"),
        ("console lever", "belt", f"channel {BELT_CHANNEL}: toggles the "
         "belt's three open stretches, which pan and drag only while on"),
        ("level start", "presses", f"channel {CRUSH_CHANNEL}: a starter "
         "sets both presses slamming for good, as E3M5's are"),
        ("console bank", "console lever", "the lever hangs on the hazard "
         "strip at the alcove's end"),
    ])

    # The console alcove, let into the west wall on its sill.
    ax0, ay0, ax1, ay1 = ALCOVE
    alcove = room("consoles", ax0, ay0, ax1, ay1,
                  floor_z=GRADE - ALCOVE_SILL, clear=ALCOVE_CLEAR,
                  role="detail",
                  rk={"declared_zero_exit": True,
                      "portal_wall_picnum": CLADDING},
                  note="the console bank: three machine fronts on a sill")
    alcove.surfaces(wall_picnum=CONSOLES[0], floor_picnum=HALL_CEILING,
                    ceiling_picnum=STRIP_LIGHT, floor_shade=POOL_SHADE,
                    ceiling_shade=0, wall_shade=POOL_SHADE)
    MACHINE_FACES[alcove.region_id] = CLADDING
    shed.connect(alcove.face("east"), hall.face("west"),
                 connection_id="connection:pump_consoles")
    span = (ay1 - ay0) // len(CONSOLES)
    for k, tile in enumerate(CONSOLES):
        detailing.panel(alcove.region_id, (ax0, ay0 + k * span),
                        (ax0, ay0 + (k + 1) * span), tile, shade=POOL_SHADE,
                        note=f"console {k}")

    # The walls, cut into panel and pilaster.
    def run(a, b, pieces, shades=(HALL_SHADE, HALL_SHADE - 8)):
        """Lay `pieces` -- (length, tile) -- from a toward b."""
        length = abs(b[0] - a[0]) + abs(b[1] - a[1])
        sx = (b[0] > a[0]) - (b[0] < a[0])
        sy = (b[1] > a[1]) - (b[1] < a[1])
        assert sum(n for n, _t in pieces) == length, (a, b, length)
        done = 0
        for k, (n, tile) in enumerate(pieces):
            detailing.panel(
                hall.region_id, (a[0] + sx * done, a[1] + sy * done),
                (a[0] + sx * (done + n), a[1] + sy * (done + n)), tile,
                storeys=3,
                shade=shades[0] if n > PILASTER_W else shades[1],
                note=f"hall {tile}")
            done += n

    P = [(int(x * PU), int(y * PU)) for x, y in HALL_OUTLINE]
    pil = (PILASTER_W, PILASTER)
    # the north bay's back wall, its return, and the wall on to the gallery
    run(P[0], P[1], [(1792, PIPES[0]), pil, (1792, PIPES[1]), pil])
    run(P[1], P[2], [(1792, CLADDING)])
    run(P[2], P[3], [pil, (1536, PIPES[2]), pil, (1536, PIPES[0])])
    # east: the gallery's mouth between hazard strips, then the long wall
    run(P[3], (hx1, gy0), [(gy0 - P[3][1], HAZARD)])
    run((hx1, gy1), P[4],
        [(512, HAZARD), (PANEL, CLADDING), pil, (1024, PIPES[1]), pil,
         (PANEL, CLADDING), pil, (1024, PIPES[0]), pil, (1024, PIPES[2])])
    # the south bay
    run(P[4], P[5], [(1408, PIPES[1]), pil, (1408, PIPES[2])])
    run(P[5], P[6], [(1152, CLADDING), pil, (1152, CLADDING)])
    run(P[6], P[7], [(PANEL, PIPES[0]), pil, (1536, PIPES[1]), pil,
                     (PANEL, PIPES[2])])
    # west: pipes, a hazard strip, the alcove, cladding
    run(P[7], (hx0, ay1),
        [(PANEL, PIPES[0]), pil, (1024, PIPES[2]), (PILASTER_W, HAZARD)])
    run((hx0, ay0), P[0], [(1024, CLADDING), pil, (1024, PIPES[1])])

    # Strip lights in the roof, each with its pool on the floor: the
    # hall's light is its sectors' (E3M3, E1M3), not a lamp sprite's.
    for index, (px0, py0, px1, py1) in enumerate(POOLS):
        box = [(px0, py0), (px1, py0), (px1, py1), (px0, py1)]
        hall.carve([(x - hx0, y - hy0) for x, y in box])
        pool, _o = solid(f"hall_pool_{index}", box, 0,
                         "a strip light in the roof and its pool",
                         kind="light_pool", ceiling_picnum=STRIP_LIGHT,
                         wall_picnum=HALL_WALL, floor_shade=POOL_SHADE,
                         ceiling_shade=0)
        for name in list(pool.faces):
            shed.connect(pool.face(name), hall.face("north"),
                         connection_id=f"connection:hall_pool_{index}_{name}")
    hall.surfaces(floor_shade=HALL_SHADE, ceiling_shade=HALL_SHADE + 6,
                  wall_shade=HALL_SHADE)
    gallery.light_source("gallery_lamp", local=(0.5, 0.5),
                         height_player_heights=1.5)

    def fittings(layout, _room):
        """The little that hangs on the walls, and the hall's hum.

        Blood's machine rooms carry a wall sprite per 50,000 of wall, so
        this is two grates at the height E3M5 hangs them and no more.
        """
        import ambience
        import props
        import wallplane
        for k, (a1, a2) in enumerate((((hx0 + 640, hy0), (hx0 + 1280, hy0)),
                                      ((int(46.2 * PU), int(5.25 * PU)),
                                       (int(46.8 * PU), int(5.25 * PU))))):
            spec = props.fields(1044)
            wallplane.sprite(
                layout, f"pump:grate_{k}", hall.region_id, a1, a2, tile=1044,
                x_repeat=spec["x_repeat"], y_repeat=spec["y_repeat"],
                cstat=spec["cstat"], t=0.5, height_player_heights=1.1,
                offset_player_widths=0.04)
        # What starts the presses: E3M5 sprite 38, field for field.
        layout.place_on_floor(
            "pump:press_starter", hall.region_id, local=(0.8, 0.95),
            type=0, picnum=0, cstat=32768, x_repeat=64, y_repeat=64,
            status=0, behavior={"tx_id": CRUSH_CHANNEL, "rx_id": LEVEL_START,
                                "command": 3, "trigger_on": 1,
                                "trigger_once": 1})
        wires.wire("pump:presses").when(
            wiring.placement("pump:press_starter"), wiring.LEVEL_START,
            command=3, once=True)
        # The lever that runs the belt, on the hazard strip by the consoles.
        import doorswitch
        doorswitch.place(layout, "pump:belt_lever", hall.region_id,
                         ((hx0, ay1 + PILASTER_W), (hx0, ay1)), BELT_CHANNEL)
        wires.wire("pump:belt").when(wiring.placement("pump:belt_lever"), "push")
        # Each stage says what it is, in stencil, on the wall behind it.
        for word, a1, a2 in (
                ("INTAKE", (hx0 + 1408, hy0), (hx0 + 2688, hy0)),
                ("FILTER", (int(44.6 * PU), int(5.25 * PU)),
                 (int(45.9 * PU), int(5.25 * PU))),
                ("SLUDGE", (int(44.2 * PU), int(11.5 * PU)),
                 (int(42.9 * PU), int(11.5 * PU)))):
            wallplane.text(layout, f"sign:pump_{word.lower()}",
                           hall.region_id, a1, a2, words=word,
                           style="works", height_player_heights=1.7)
        ambience.fill(layout, [(hall.region_id, "works", (0.5, 0.35)),
                               (hall.region_id, "works", (0.15, 0.72))])

    hall.raw("the machine hall's grates and its hum", fittings)
    return {"machine_hall": hall, "gallery": gallery}


def dress(level, compiled) -> dict:
    """Paint what the hall's machines show the hall.

    A raised or low-ceilinged sector's sides are drawn from the record on
    the side that sees them (`bloodmap.skyline.dress_steps` says why), and
    a solid block's are the hall's own walls.
    """
    painted = {"faces": 0, "blocks": 0}
    faceted = {compiled.allocations[r].sector_id for r in FACETED
               if r in compiled.allocations}
    turn: dict = {}
    faces = {compiled.allocations[region_id].sector_id: tile
             for region_id, tile in MACHINE_FACES.items()
             if region_id in compiled.allocations}
    for wall in level.walls:
        f = wall.get("fields", wall) if isinstance(wall, dict) else wall.fields
        other = int(f["next_sector"])
        if other in faces:
            f["picnum"] = faces[other]
            painted["faces"] += 1
            if other in faceted:
                #: E3M5 s14: neighbouring facets of one drum 12 apart
                turn[other] = turn.get(other, 0) + 1
                f["shade"] = HALL_SHADE - 10 + 12 * (turn[other] % 2)
            continue
        if other >= 0:
            continue
        nxt = level.walls[int(f["point2"])]
        n = nxt.get("fields", nxt) if isinstance(nxt, dict) else nxt.fields
        for x0, y0, x1, y1, tile in MACHINE_BLOCKS:
            if (x0 <= int(f["x"]) <= x1 and y0 <= int(f["y"]) <= y1
                    and x0 <= int(n["x"]) <= x1 and y0 <= int(n["y"]) <= y1):
                f["picnum"] = tile
                #: one cabinet front per 1,024, standing on the floor: the
                #: tile is 64 by 128, two of them to the roof
                length = (abs(int(n["x"]) - int(f["x"]))
                          + abs(int(n["y"]) - int(f["y"])))
                f["x_repeat"] = max(1, round(length / 1024)) * 8
                f["y_repeat"], f["x_panning"], f["y_panning"] = 8, 0, 0
                f["cstat"] = int(f["cstat"]) | 4
                painted["blocks"] += 1
    return painted


def build(district, foundry_st, foundry_origin):
    city = district
    """The shed, its stair, and the cellar that holds the pit."""
    fx0, fy0 = foundry_origin
    sx0, sy0, sx1, sy1 = SHED

    service = INTERIORS["service"]
    shed = city.assembly(
        "pump_station",
        # Lit like a room someone works in, not like the sewer.  The source
        # declarations below now provide that readability; keeping a blanket
        # manual shade here would prevent LightBomb from deriving falloff.
        style=Style(**service.style_kwargs(floor_z=GRADE,
                                           clear_height=32768)),
        note="the pumping station: the sewer's road-level entrance",
    )

    def room(name, x0, y0, x1, y1, *, floor_z=GRADE, role="interior",
             clear=32768, note="", rk=None, outline=None, faces=None):
        made = shed.room(
            name, outline or [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0),
                              (0, y1 - y0)],
            role=role, faces=dict(faces or COMPASS),
            frame=Frame(int(x0), int(y0)),
            region_kwargs={**service.region_kwargs(), **(rk or {})},
            note=note)
        # Keep these base surfaces unprotected so declared fixtures own the
        # illumination.  Use a direct shade only for a deliberate local
        # art-direction override.
        made.surfaces(**service.style_kwargs(floor_z=floor_z,
                                             clear_height=clear))
        return made

    # Street -> porch -> door -> hall.
    porch = room("porch", sx1 - PORCH_D, MOUTH_Y0, sx1, MOUTH_Y0 + MOUTH_H,
                 role="gateway", clear=DOOR_HEIGHT,
                 note="the station's reveal, so the facade owns the wall above")
    porch.surfaces(wall_picnum=MASONRY.wall, ceiling_picnum=MASONRY.wall,
                   floor_z=GRADE, clear_height=DOOR_HEIGHT)
    door = room("door", sx1 - PORCH_D - DOOR_D, MOUTH_Y0,
                sx1 - PORCH_D, MOUTH_Y0 + MOUTH_H, role="doorway", clear=0,
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - DOOR_HEIGHT)},
                note="the station door")
    door.surfaces(wall_picnum=MASONRY.wall, floor_z=GRADE, clear_height=0)
    hall = room("hall", sx0 + 512, sy0 - STAIR_W,
                sx1 - PORCH_D - DOOR_D, sy1 - 512,
                note="the station floor: the stair head is in here")

    city.connect(porch.face("east"), foundry_st.face("west"),
                 connection_id="connection:pump_station_street")
    shed.connect(door.face("east"), porch.face("west"),
                 connection_id="connection:pump_door_porch")
    shed.connect(door.face("west"), hall.face("east"),
                 connection_id="connection:pump_door_hall")

    # One straight flight west into the works void, then the cellar.
    # The stair uses the hall's southern bay, so it arrives entirely above the
    # shortened cellar rather than into the sewer walk beyond its north wall.
    # Approach the cellar from the north so its far end meets the first spiral
    # tread head-on.  The old southern bay fed a room which wrapped around the
    # stair and made the doorway look like a sideways slit.
    stair_y0 = sy0 - STAIR_W
    cellar = room("cellar", *CELLAR, floor_z=CELLAR_FLOOR_Z, clear=20480,
                  role="gateway",
                  note="the station cellar; its pit drops into the sewer")

    # The stair is one bay wide, taken from a sub-span of the hall's west
    # face: anchored to the whole face it would be three plan units wide and
    # would run straight through the rail-yard backdrop box.
    face_len = (sy1 - 512) - sy0
    # The west face is wound south-to-north, so its anchor fraction runs in
    # the opposite direction to the room's local y coordinate.
    at = 1.0 - ((stair_y0 + STAIR_W / 2) - sy0) / face_len
    hall.staircase(
        "pump_flight", "west", at=at, width=STAIR_W,
        total_rise=FLIGHT * STEP, tread=TREAD, step_rise=STEP,
        arrive_at=cellar.region_id, connection={"role": "portal"})

    # `_assembly` lets the caller add the staircase against this corridor's
    # single radial face.  There is deliberately no curved carve: the newel
    # and the space around the remaining treads are solid masonry.
    machines = machine_hall(shed, hall, room)
    return {"hall": hall, "cellar": cellar, "_assembly": shed, **machines}
