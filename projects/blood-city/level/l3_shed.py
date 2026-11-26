"""The pumping station: a road-level way into the sewer, with stairs.

The grate is a one-way drop -- 3.14 player heights, which the engine
forgives (kFallDamageFloor covers anything under 3.98) but which nobody can
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

import house_letters
import wires
from bloodmap import motion, wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec
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
# Blood's ceiling-lifting doors (594 in the campaign) open to a median of
# 28,672 -- 1.69 player heights -- and 87% are taller than a body.  The
# 31,744 used here is the median over all 1,231 type-600 sectors, lifts
# included, not a door height; it is kept because changing it moves every
# door in Gravesend.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_HEIGHT = 31744

STAIR_W = 1024
CELLAR_FLOOR_Z = STATION_STACK_PLANE

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
#: The way down to it is E2M1's way below (s2 over s20): the passage off the hall is one flat sector whose floor is a link, and
#: under it one sector of the same plan slopes from a hand under the plane at the hall's end to a step over the cellar's floor at
#: the other. A body sinks through a linked floor onto what is under it and is carried over as its middle passes the plane, down
#: and up alike. (Eight treads until 2026-11-25; `references/sewers-outside.md` for why.) 28 degrees; E2M1's is 34.
RAMP = (47104 + 1024, 4096, 51712, 5120)
RAMP_HIGH, RAMP_LOW, RAMP_LINK = GRADE + 1024, CELLAR_FLOOR_Z - 1024, 21
RAMP_LAYER = "pump_ramp"
CELLAR = (SPIRAL_INNER_X, 4096, RAMP[0], 5120)
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
#: bodies. The settling basin stands in the north bay, the deck by
#: the gallery, the belt between; the south bay is left open floor.
#: (bbox; the outline is `HALL_OUTLINE`)
MACHINE_HALL = (40 * PU, int(3.5 * PU), int(47.5 * PU), 14 * PU)
HALL_OUTLINE = ((40, 3.5), (44, 3.5), (44, 7), (47.5, 7), (47.5, 14),
                (44.5, 14), (44.5, 11.5), (40, 11.5))
HALL_FACES = {"north": 0, "bay_e": 1, "deck_s": 2, "east": 3, "bay_s": 4,
              "bay_w": 5, "south": 6, "west": 7}
#: THE WAY IN, 2026-11-25 (`references/pump-hall-design.md`): the gallery
#: climbs a body from the lobby and comes out on a deck over the floor, as E3M6's
#: key is seen across its tanks from the walk above them (s414) before anyone can
#: reach it. Treads, then the landing, in the gallery; the deck and its treads down.
DECK_RISE = 16384
GALLERY = (int(47.5 * PU), int(5.5 * PU), 49 * PU, 7 * PU)
GALLERY_TREADS = 3                 # 512 each, from the landing to the lobby
DECK = (int(45.5 * PU), int(5.25 * PU), int(47.5 * PU), 7 * PU)
DECK_TREADS = 3                    # 512 each, west from the deck to x 44
HALL_CLEAR = 98304                 # 5.8 bodies: E3M5's foundry hall
GALLERY_CLEAR = 32768
#: the belt runs the hall's long way, west to east
BELT_X = (int(41.5 * PU), 46 * PU)
BELT_Y = (int(8.75 * PU), int(10.25 * PU))     # 1,536 wide: it was 1,024
BELT_RISE = 4096                   # one step: it can be boarded
BELT_VELOCITY, BELT_ANGLE = 48, 0      # E3M5's crusher line; toward +x
PRESS_CLEAR = 18432                # 1.09 bodies: E3M5 s44-52
#: (length, is a press): open, press, open, press, open. The middle stretch
#: is where the key lies (`gameplay.KEYS`): the widest, under its own light.
BELT_SECTIONS = ((768, False), (768, True), (1536, False), (768, True),
                 (768, False))
#: the hood over the middle stretch, between the presses: 2.2 bodies up, and
#: its underside is the light the key lies in
HOOD_CLEAR = 36864
#: the machine at each end of the belt: a solid block, wider than the belt
#: (across the belt, and along it: thin, for the ways past them)
MACHINE_HALF, MACHINE_DEPTH = 1024, (512, 512)
#: one open basin. There was a filter drum too, 1.5 units before the way in:
#: it was all a player saw of the hall
TANKS = ((int(42.1 * PU), int(5.1 * PU)),)
TANK_RADIUS = 1024
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
ALCOVE = (40 * PU - 256, 5 * PU, 40 * PU, 8 * PU)
ALCOVE_SILL, ALCOVE_CLEAR = 8192, 16384
POOL_SHADE, HALL_SHADE = 4, 22
#: The hall as a PROCESS. The owner, 2026-11-18: "Maybe we can think about
#: stuff in relations, like this machine connects to this, there is a
#: control panel here, there is a dirty water tank, the water goes there".
#: So the tank is an open SETTLING basin of sewage, a rim 0.6 body high with
#: the water moving inside it. The sludge goes down the belt through the presses, and the
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
BASIN_RIM, BASIN_WATER = 10240, 8192       # a swimmer climbs 2,048 (`underwater`)
SEWAGE = 1120
#: (from, to, how): written to the build manifest, and a test holds each
RELATIONS: list = []
#: E3M3's generator pulse, on the presses
PULSE = {"shade_wave": 5, "amplitude": -32, "shade_frequency": 5,
         "shade_floor": 1, "shade_walls": 1}
PLINTH_RADIUS, TANK_SIDES = 1280, 10
#: girders, in bodies over the floor: 0.6 under the hall's roof
TRUSS_HEIGHT = 3.25
PLATING, THRESHOLD, HAZARD = 470, 200, 205
#: what is walked on over the floor: the owner's "embossed metal floor"
PLATE = 438
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
    deck_z = GRADE - DECK_RISE
    gallery = room("gallery", gx0, gy0, gx1, gy1, floor_z=deck_z, clear=GALLERY_CLEAR,
                   rk={"portal_wall_picnum": HALL_WALL},
                   note="the landing: the gallery climbs to it from the lobby, and it comes out on the deck")
    gallery.surfaces(wall_picnum=HALL_WALL, floor_picnum=PLATE, ceiling_picnum=HALL_CEILING)
    near, rise = gallery, DECK_RISE // (GALLERY_TREADS + 1)
    for k in range(GALLERY_TREADS):
        x = gx1 + 512 * k
        tread = room(f"gallery_tread_{k}", x, gy0, x + 512, gy1, floor_z=deck_z + rise * (k + 1), clear=GALLERY_CLEAR,
                     rk={"portal_wall_picnum": HALL_WALL}, note="a step of the gallery, up from the lobby")
        tread.surfaces(wall_picnum=HALL_WALL, floor_picnum=PLATE, ceiling_picnum=HALL_CEILING)
        MACHINE_FACES[near.region_id] = PLATING if near is gallery else THRESHOLD
        shed.connect(near.face("east"), tread.face("west"), connection_id=f"connection:pump_gallery_{k}")
        near = tread
    MACHINE_FACES[near.region_id] = THRESHOLD
    shed.connect(near.face("east"), lobby.face("west"),
                 connection_id="connection:pump_gallery_lobby")
    # The deck over the hall's floor, and its treads down to it, west. Each is a
    # solid block: what is under it is the hall's own wall.
    dx0, dy0, dx1, dy1 = DECK
    deck = room("deck", dx0, dy0, dx1, dy1, floor_z=deck_z, clear=HALL_CLEAR - DECK_RISE,
                rk={"portal_wall_picnum": HALL_WALL}, note="the deck the gallery comes out on, over the belt")
    deck.surfaces(wall_picnum=HALL_WALL, floor_picnum=PLATE, ceiling_picnum=HALL_CEILING)
    MACHINE_FACES[deck.region_id] = PLATING
    shed.connect(gallery.face("west"), deck.face("east"), connection_id="connection:pump_gallery_hall")
    shed.connect(deck.face("south"), hall.face("deck_s"), connection_id="connection:pump_deck_edge")
    near, rise = deck, DECK_RISE // (DECK_TREADS + 1)
    for k in range(DECK_TREADS):
        x = dx0 - 512 * (k + 1)
        down = rise * (k + 1)
        tread = room(f"deck_tread_{k}", x, dy0, x + 512, dy1, floor_z=deck_z + down, clear=HALL_CLEAR - DECK_RISE + down,
                     rk={"portal_wall_picnum": HALL_WALL}, note="a step down from the deck to the hall's floor")
        tread.surfaces(wall_picnum=HALL_WALL, floor_picnum=PLATE, ceiling_picnum=HALL_CEILING)
        MACHINE_FACES[tread.region_id] = THRESHOLD
        shed.connect(near.face("west"), tread.face("east"), connection_id=f"connection:pump_deck_{k}")
        shed.connect(tread.face("south"), hall.face("deck_s"), connection_id=f"connection:pump_deck_{k}_edge")
        near = tread
    shed.connect(near.face("west"), hall.face("bay_e"), connection_id="connection:pump_deck_foot")

    # The belt line: one hole in the hall's floor plan, an I -- a machine
    # block at each end and the belt between them.
    bx0, bx1 = BELT_X
    by0, by1 = BELT_Y
    my0 = (by0 + by1) // 2 - MACHINE_HALF
    my1 = (by0 + by1) // 2 + MACHINE_HALF
    west, east = MACHINE_DEPTH
    line = [(bx0 - west, my0), (bx0, my0), (bx0, by0), (bx1, by0),
            (bx1, my0), (bx1 + east, my0),
            (bx1 + east, my1), (bx1, my1), (bx1, by1), (bx0, by1),
            (bx0, my1), (bx0 - west, my1)]
    hall.carve([(x - hx0, y - hy0) for x, y in line])
    MACHINE_BLOCKS.append((bx0 - west, my0, bx0, my1, CABINET))
    MACHINE_BLOCKS.append((bx1, my0, bx1 + east, my1, CABINET))
    cursor, previous = bx0, None
    for index, (length, press) in enumerate(BELT_SECTIONS):
        hood = index == len(BELT_SECTIONS) // 2
        clear = PRESS_CLEAR if press else HOOD_CLEAR if hood else HALL_CLEAR - BELT_RISE
        piece = room(
            f"belt_{index}", cursor, by0, cursor + length, by1,
            floor_z=GRADE - BELT_RISE, clear=clear,
            rk={"portal_wall_picnum": PLATING, "sector_behavior": (
                #: a press: E3M5 s45/47/50, turned over. It slams shut in two
                #: tenths, rises in a second and a half, waits, and both
                #: re-triggers keep it going; `crush` kills what is under it.
                #: ON is UP: the belt under it runs while its state is on or it
                #: is moving, so a press stopped shut (OFF) is a belt stopped
                #: (the owner, 2026-11-25: "the lever ... won't stop belt under
                #: the crushers, it is fine if by that it would stop the
                #: crushers as well").
                {"pan_floor": 1, "pan_always": 0, "drag": 1, "state": 1, "busy": 65536,
                 "pan_velocity": BELT_VELOCITY, "pan_angle": BELT_ANGLE,
                 "rx_id": CRUSH_CHANNEL, "busy_wave_a": 3, "busy_wave_b": 1,
                 "busy_time_a": 15 - 3 * (index // 2), "busy_time_b": 2,
                 "wait_time_a": 10 - 3 * (index // 2),
                 "retrigger_a": 1, "retrigger_b": 1, "crush": 1,
                 "off_ceiling_z": GRADE - BELT_RISE,
                 "on_ceiling_z": GRADE - BELT_RISE - PRESS_CLEAR,
                 "off_floor_z": GRADE - BELT_RISE,
                 "on_floor_z": GRADE - BELT_RISE, **PULSE}
                if press else
                {"pan_floor": 1, "pan_always": 0, "drag": 1, "state": 1,
                 "rx_id": BELT_CHANNEL,
                 "pan_velocity": BELT_VELOCITY, "pan_angle": BELT_ANGLE})},
            note=("a press: the belt runs under it" if press
                  else "the belt, open"))
        piece.surfaces(wall_picnum=PLATING, floor_picnum=BELT_TILE,
                       ceiling_picnum=PLATING if press else STRIP_LIGHT if hood else HALL_CEILING,
                       **({"ceiling_shade": 0} if hood else {}))
        wires.wire("pump:presses" if press else "pump:belt").then(
            wiring.region(piece.region_id))
        #: the stripes go on the press, as E3M5 puts them on its jambs
        MACHINE_FACES[piece.region_id] = HAZARD if press else CLADDING if hood else THRESHOLD
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
        outer, inner = ring(cx, cy, PLINTH_RADIUS), ring(cx, cy, PLINTH_RADIUS - 192)
        hall.carve([(x - hx0, y - hy0) for x, y in outer])
        plinth, origin = solid(f"tank_{index}_plinth", outer, BASIN_RIM, "the settling basin's rim")
        plinth.carve([(x - origin[0], y - origin[1]) for x, y in inner])
        tank, _inner_origin = solid(
            f"tank_{index}", inner, BASIN_WATER,
            "the settling basin: sewage, moving", floor_picnum=SEWAGE,
            floor_shade=HALL_SHADE - 6)
        tank.region_kwargs["sector_behavior"] = {
            "pan_floor": 1, "pan_always": 1, "pan_velocity": 8,
            "pan_angle": 256}
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
        ("lobby", "deck", "the gallery climbs a body and comes out over the hall: the key is seen before it is reached"),
        ("settling basin", "belt", "the sludge line runs south of the basin; lettered INTAKE and SLUDGE"),
        ("console lever", "belt", f"channel {BELT_CHANNEL}: stops and starts the "
         "belt's three open stretches, which pan and drag only while on"),
        ("console lever", "presses", f"two relays: off, each press stops when next shut, and the belt under it; "
         "on, they rise again"),
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
    # the north bay's back wall, and its return as far as the deck's treads
    run(P[0], P[1], [(1920, PIPES[0]), pil, (1920, PIPES[1])])
    run(P[1], (P[1][0], DECK[1]), [(1792, CLADDING)])
    # the long east wall, and the south bay, plain at its back
    run(P[3], P[4],
        [(1536, CLADDING), pil, (1536, PIPES[1]), pil, (1536, CLADDING), pil, (1792, PIPES[0])])
    run(P[4], P[5], [(1408, PIPES[1]), pil, (1408, PIPES[2])])
    run(P[5], P[6], [(2560, CLADDING)])
    run(P[6], P[7], [(2176, PIPES[0]), pil, (2176, PIPES[2])])
    # west: pipes, the lever's panel between hazard strips, the alcove
    run(P[7], (hx0, ay1), [(2304, PIPES[0]), (256, HAZARD), (768, CLADDING), (256, HAZARD)])
    run((hx0, ay0), P[0], [(1536, PIPES[1])])

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
        from bloodmap import wallplane
        for k, (a1, a2) in enumerate((((hx0 + 640, hy0), (hx0 + 1280, hy0)),)):
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
        # It stands in its ON picture, says its state, and two relays tell the
        # presses: OFF is kCmdStopOff, so a press goes round to shut and stays
        # (triggers.cpp:154); ON waits two seconds, or a lever thrown off and on
        # again would find the stop still pending and leave the press shut.
        doorswitch.place(layout, "pump:belt_lever", hall.region_id,
                         ((hx0, ay1 + 1024), (hx0, ay1 + 256)), BELT_CHANNEL, command=motion.CMD_STATE)
        belt, presses = wires.wire("pump:belt"), wires.wire("pump:presses")
        belt.when(wiring.placement("pump:belt_lever"), "push", command=motion.CMD_STATE, on=True, off=True, state=1)
        for name, kind, fields in (
                ("stop", 20, dict(command=motion.CMD_STOP_OFF, on=False, off=True, state=1)),
                ("restart", 21, dict(command=motion.CMD_ON, on=False, off=True, wait_time=20))):
            relay = f"pump:press_{name}"
            layout.place_on_floor(relay, hall.region_id, local=(0.82, 0.95), type=kind, picnum=0, cstat=32768,
                                  x_repeat=64, y_repeat=64, status=0)
            belt.then(wiring.placement(relay))
            presses.when(wiring.placement(relay), wiring.RELAY, **fields)
        # Each stage says what it is, in stencil, on the wall behind it.
        for word, a1, a2 in (
                ("INTAKE", (hx0 + 1408, hy0), (hx0 + 2688, hy0)),
                ("BELT", (hx0, ay1 + 1024), (hx0, ay1 + 256)),
                ("SLUDGE", (int(44.2 * PU), int(11.5 * PU)),
                 (int(42.9 * PU), int(11.5 * PU)))):
            house_letters.text(layout, f"sign:pump_{word.lower()}",
                           hall.region_id, a1, a2, words=word,
                           style="department" if word == "BELT" else "works",
                           height_player_heights=1.2 if word == "BELT" else 1.7)
        # The lever's own light, over it, and one over the way in, where the treads come down: a fluorescent tube, stood up.
        # (They were 2183, read as a recessed lamp: it is the trap that fires out of a wall, 40 of the campaign's 40.)
        for k, (region, a1, a2) in enumerate((
                (hall.region_id, (hx0, ay1 + 1024), (hx0, ay1 + 256)),
                (deck.region_id, (DECK[0], DECK[1]), (DECK[2], DECK[1])),
                (hall.region_id, (hx1, 13 * PU), (hx1, 14 * PU)))):
            wallplane.sprite(layout, f"pump:lamp_{k}", region, a1, a2, tile=796, x_repeat=56, y_repeat=32,
                             cstat=16 | 64 | 128, t=0.5, height_player_heights=(2.15, 1.5, 1.7)[k],
                             offset_player_widths=0.04, shade=-64)
        # A round light over the landing, and one in the lobby (795, Blood's commonest).
        for name, region, x, y in (("landing", gallery.region_id, 48.25, 6.25), ("lobby", lobby.region_id, 51.25, 5.75)):
            layout.add_sprite(f"pump:light_{name}", region, x=int(x * PU), y=int(y * PU),
                              z=layout.regions[region].ceiling_z + 64, picnum=795,
                              x_repeat=48, y_repeat=48, cstat=32 | 128 | 8, shade=-16)
        # Which way is which, from the lobby.
        x0, y0 = SHED[0] + 512, SHED[1] - STAIR_W
        house_letters.text(layout, "sign:pump_sewer", lobby.region_id, (x0, y0), (x0 + 1536, y0), words="SEWER",
                       style="notice", height_player_heights=1.3)
        # An iron rail along the deck's edge (DWE2M10's 104): solid, and seen from both sides.
        for k in range(4):
            layout.add_sprite(f"pump:deck_rail_{k}", deck.region_id, x=DECK[0] + 512 * k + 256, y=DECK[3] - 24,
                              z=GRADE - DECK_RISE - 4096, picnum=104, x_repeat=32, y_repeat=32, angle=512,
                              cstat=16 | 128 | 1, shade=8)
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
    hall.surfaces(floor_picnum=PLATE)

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
    cellar = room("cellar", *CELLAR, floor_z=CELLAR_FLOOR_Z, clear=20480,
                  role="gateway",
                  note="the station cellar; its pit drops into the sewer")

    head = room("ramp_head", *RAMP, clear=28672, role="gateway",
                note="the passage off the station's floor: its own floor is the link")
    ramp = room("ramp", *RAMP, floor_z=RAMP_LOW, clear=RAMP_LOW - GRADE, role="gateway",
                note="the ramp under it, down to the cellar",
                rk={"floor_slope": SlopeSpec(hinge=((RAMP[0], RAMP[3]), (RAMP[0], RAMP[1])), rise_z=RAMP_HIGH - RAMP_LOW)})
    ramp.surfaces(layer=RAMP_LAYER, floor_picnum=PLATE, wall_shade=24, floor_shade=26)
    shed.connect(head.face("east"), hall.face("west"), connection_id="connection:pump_ramp_head")
    shed.connect(ramp.face("west"), cellar.face("east"), connection_id="connection:pump_ramp_foot")

    def link(layout, _room):
        from bloodmap.roomoverroom import room_over_room
        room_over_room(layout, "pump:ramp_link", head.region_id, ramp.region_id, link_id=RAMP_LINK,
                       at=((RAMP[0] + RAMP[2]) // 2, (RAMP[1] + RAMP[3]) // 2))

    hall.raw("the ramp's link", link)

    # `_assembly` lets the caller add the staircase against this corridor's
    # single radial face.  There is deliberately no curved carve: the newel
    # and the space around the remaining treads are solid masonry.
    machines = machine_hall(shed, hall, room)
    return {"hall": hall, "cellar": cellar, "_assembly": shed, **machines}
