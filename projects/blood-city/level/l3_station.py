"""Gravesend Station: the first building BEHIND the city's edge.

The owner, 2026-11-18: "Buildings that makes city edges are now empty, but
because they are outside we have almost unlimited space to create something
nice we want there ... we can do something like train station for
example". And of the first version: "looks like something where you need a
lot of imagination and it is partially ripoff of E1M2 without deeper
context knowledge, try to make it better, iterate on it".

The first version was E1M2's hall with nothing in it and a block in train
livery. Round 1 of `tools.critique` (three readers, 2 out of 5 each):
with the words hidden it was "an underground platform with a parked
carriage", sure 2 of 5; the train "reads as a giant billiard-table felt";
no track or platform edge in sight; a ticket counter no clerk could stand
behind; an unmarked slot for a street door; an empty hall; nothing to do
and no way on.

This version is laid out from what a station is FOR, a passenger's steps
in order, and each step has a thing:

``find it``    STATION lettered on the street wall beside the door.
``buy``        a booking OFFICE behind a barred window, with a clerk in
               it, a TICKETS board over it, and a door round the side.
``wait``       benches down the hall, a clock, the arrivals board, bills.
``pass``       iron gates between the columns (E1M2 sprites 473-477),
               a revolving fare gate, and two open bays.
``board``      a carriage with a DOOR and glazed WINDOWS, standing under
               a train-shed roof. (A free-standing car under the sky can
               have neither in this engine: the wall over an opening runs
               to the sector's ceiling, and the sky has none. Under a
               roof at the car's own height, the car is the solid between
               its windows.) Its floor is the platform's, so one steps in.
               Inside it is E1M3's: a carpet, tables, a way through.
``the train``  a locomotive ahead of it under the open sky: a boiler, a
               cab in the livery, driving wheels (E1M3 sprites 418-421).
``the line``   two tracks, the far one empty so rails are SEEN (and
               running ALONG the train: see `dress`); a buffer
               stop behind; ahead a tunnel that darkens, barred.
``go on``      a ramp at the platform's west end down to the track.

And something to do: the carriage door is shut. The lever that opens it
is on the hall's column beside the door's bay (it was in the booking
office until two rounds of readers said pulling it "appears to do
nothing"); what is in the carriage is worth the walk.

The seventh version (after three blind readers named 3 to 5 of its 11
things): the train stands under the open sky, not in a brick bay; a
signal box with a balcony overlooks it, and its lever raises a roll-up
gate in the tunnel's mouth; the tunnel leads to a goods store; there is
a waiting room off the hall.

Round 6 (recognition 3, comparison 3, use 3, sense 4): still NOT passed;
the carriage gained a red door, four windows a side and a bill, the
locomotive its recipe. Round 5 (3 of 5 each, up from 2) left open:
from the platform the carriage is one long striped slab with two windows
and no ends, roof edge or couplings; the doorway on the street has no
frame or canopy of its own; the red sky over the track trench reads as a
lid; lettering floats where its wall is dark; the line goes nowhere.

Sizes are a person's (`scale.py`): the carriage is 2,048 over all (3.4 m;
the first was 6.8 m, the third 5.1 m and as tall as the shed: "reads as
buildings") and 2.4 bodies over the rail, its door 1,024, its windows
half a body up.

Still owed, and said so: the tunnel leads nowhere (it should reach the
quay); no guard's van, luggage or water tower. Tiles with no owner name:
1665 (train livery), 174, 414, 2320
(locomotive wheels), 431 and 943 (the boards).
"""

from __future__ import annotations

import wires
from bloodmap import wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, Style
from bloodmap.mechanism import DISTINCT_ANGLES, turnstile_spec
from bloodmap.slope import SlopeSpec

from materials import FACADES
from resolution import GRADE, PU, STREET_SKY

COMPASS = {"north": 0, "east": 1, "south": 2, "west": 3}
BODY = 16960

#: levels (z grows downward)
HALL_UP = 20480                    # 1.21 bodies: E1M2 s207 -> s271
HALL_Z = GRADE - HALL_UP
PLATFORM_DROP = 14336              # 0.85 body: E1M2 s272 over s34
BED_Z = HALL_Z + PLATFORM_DROP
HALL_CLEAR = 50176                 # 2.96 bodies: E1M2 s271
#: Round 3, every reader: "the carriage is a solid 5.1 m wide running from
#: track bed to roof, 6.7 m ... the train reads as buildings". A car in
#: this engine is the solid between its windows and so reaches its
#: sector's ceiling; the answer is to bring THAT ceiling down to a car's
#: roof (2.4 bodies over the rail, 4.1 m) and let the platform canopy's
#: higher edge hang over it as a timber valance.
CAR_TOP = 40960
SHED_CLEAR = CAR_TOP
OPEN_CLEAR = STREET_SKY - HALL_UP

#: plan, in world units; north of the city is negative y
DOOR = (12 * PU, -256, 14 * PU, 0)
PASSAGE = (int(11.5 * PU), -256 - 4096, int(14.5 * PU), -256)
RAMP = (12 * PU, -256 - 8192, 14 * PU, -256 - 4096)
HALL = (8 * PU, -14592, 18 * PU, -8448)
OFFICE = (6144, -13568, 7936, -10496)
OFFICE_DOOR = (7936, -11264, 8192, -10496)
OFFICE_WINDOW = (7936, -13056, 8192, -12032)      # two halves, bars between
PY0, PY1 = -16640, -14592
#: (x0, x1, roofed, the bay the carriage door is in)
#: THE TRAIN STANDS UNDER THE SKY. Three readers, blind, on the fifth
#: version: the carriage's side is "a building facade with two windows",
#: its door "a door in a brick corridor". It stood in a brick bay under
#: the hall's roof with brick over its roof line. Two sectors whose
#: ceilings are BOTH parallax draw no wall between them above the lower
#: one, so the platform is open to the sky now and the sliver the car
#: stands in has a parallax ceiling at the car's roof: over the car is
#: sky. (I had written that a wall under a parallax sky runs "to the
#: sky". It runs to its sector's ceiling; the sky is drawn above that.)
#: ... AND THEN BACK UNDER A ROOF. The owner, 2026-11-19, of the open-sky
#: car: "You will probably need to keep that wagon under roof if you want
#: to have an interior." A car with an inside is a void that reaches its
#: sector's ceiling; with a sky for that ceiling there is no roof to see
#: from the signal box's balcony, which looks down on it. What was wrong
#: with the first roofed car was not the roof but the BAND OVER IT: the
#: platform's ceiling stood a body higher than the car's, and that band
#: wore the hall's brick. So the platform beside the car has an AWNING at
#: the car's own roof height (1.57 bodies over the platform, 2.7 m): the
#: car's side runs from the platform to the awning and nothing is above it.
#: (the awning is gone again: see THE CARRIAGE IS BUILT OF SECTORS)
PLATFORM = ((6144, 8192, False, False), (8192, 9984, False, False),
            (9984, 14848, False, False), (14848, 15872, False, True),
            (15872, 18432, False, False), (18432, 21248, False, False),
            (21248, 22528, False, False),
            #: ... and on beside the locomotive, so it is SEEN (round 3:
            #: "no locomotive" -- it stood past the platform's end wall)
            (22528, 29696, False, False))
DOWN_RAMP = (4096, PY0, 6144, PY1)                # platform's west end
BED_Y = (PY0 - 8192, PY0)                         # two tracks
BED_X = (2048, 6144, 22528, 30720)                # sky | shed | sky
#: The far bore was shade 60, near black, from when the tunnel was a dead
#: end that faded out. It now holds the switch that ends the level, and the
#: owner, playing it on 2026-11-19: "that exit switch is in the very dark
#: corridor, not sure why we made that one strip that dark when other rooms
#: around it are lit." It keeps a step of fade and no more.
TUNNEL = ((30976, 34816, 24), (34816, 38912, 30))
#: THE LINE GOES SOMEWHERE. Every round: "the tunnel is barred, the
#: station is a dead end". A roll-up gate stands in the tunnel's mouth
#: (tile 9, the owner's "metal roll-up gate": on 40 of the campaign's
#: type-600 doors, E3M3 s279); the lever that raises it is in the signal
#: box, whose balcony looks straight at it. Beyond the tunnel, the goods
#: store the line serves.
GATE_X = (30720, 30976)
GATE_CHANNEL = wires.channel("station:gate")
#: where the exit switch hangs: set when the tunnel's last bore is built
WAY_OUT: dict = {}
STORE = (38912, -25856, 44032, -15616)
#: The avenue front and the rooms behind it (`avenue_front`): the avenue's
#: mouth is x 32,768 to 39,936 on the city's north edge (y 0). The hall
#: starts behind the forecourt (3,072) and the arches (1,536); the
#: concourse stops short of the goods store (x 38,912) and 512 clear of
#: the track bed's edge (y -16,640), which is the platform's.
EAST_HALL = (32768, -8704, 39936, -4608)
EAST_STAIR = (34816, -12800, 37888, -8704)
CONCOURSE = (30976, -16128, 38400, -12800)
EAST_LINK = (29696, -16128, 30976, -14592)
#: the owner's "grey ashlar stone blocks", 13 maps; jambs his "stone column"
FRONT_STONE, FRONT_JAMB = 427, 479
#: (rectangle, how high it stands)
CRATES = (((42240, -25344, 43520, -24064), 16384),
          ((40704, -25344, 41984, -24320), 10240),
          ((42496, -17408, 43520, -16128), 16384),
          ((42496, -22528, 43520, -21248), 12288))
#: THE SIGNAL BOX: height. The owner, 2026-11-19: "you might add some
#: more places, rooms, balcony (some height to it)". A stair from the
#: platform's east end up 1.2 bodies to a cabin with the gate's lever,
#: and an open balcony over the platform, level with the engine's dome.
SIGNAL_UP = 20480
LANDING = (22528, -14592, 23552, -12800)
SIGNAL_RAMP = (23552, -13824, 26624, -12800)
SIGNAL_BOX = (26624, -13824, 29696, -11776)
BALCONY = (26624, -14592, 29696, -13824)
#: THE WAITING ROOM, off the hall's east wall: carpet, plaster, benches
#: round the walls, a longcase clock (720, the owner's "grandfather
#: clock, front face"), a table with chairs.
WAITING_DOOR = (18432, -12544, 18688, -11520)
WAITING = (18688, -13568, 22272, -10496)
WAIT_BENCHES = ((19200, -13440, 21760, -13056), (19200, -11008, 21760, -10624))
WAIT_TABLE = (20224, -12288, 20992, -11776)
CAR = (10240, PY0 - 128 - 2048, 20992, PY0 - 128)      # 3.4 m over all
#: the strip the car stands in: 128 along its sides, 16 at its ends
RING = (CAR[0] - 256, CAR[1] - 128, CAR[2] + 256, PY0)
#: THE CARRIAGE IS BUILT OF SECTORS. The owner, 2026-11-19: "Carriage can
#: be made out of red sectors and ceiling can be made out of floor
#: aligned solid sprites, this will make it working without lowering sky
#: which looks bad from the outside ... try to solve it to keep interior
#: and make it looking good from outside."
#: So the car is no longer a hole in the map with an inside cut into it.
#: Its WALLS are sectors a hull thick whose floors stand at the roof's
#: height; a WINDOW is a stretch of that wall whose floor is only sill
#: high; the DOOR is a stretch whose floor sinks to the platform's when
#: the lever is pulled; the INSIDE is a room under the same sky as the
#: platform; and the ROOF is solid floor-aligned sprites laid over the
#: inside at the walls' top. Nothing lowers the sky, and from the signal
#: box's balcony there is a roof to look down on.
CAR_H = 26624                       # the roof over the platform: 1.57 bodies
ROOF = 438                          # the owner's "embossed metal floor", as a top
#: where the side walls change kind, west to east: wall, window, wall ...
SIDE_X = (CAR[0] + 256, 11008, 12032, 12800, 13824, 14848, 15872, 16896,
          17920, 18688, 19712, CAR[2] - 256)
SOUTH_KINDS = "SWSWSDSWSWS"
NORTH_KINDS = "SWSWSSSWSWS"
HULL_SOLID: list = []
HULL_OPEN: list = []
LATE_TYPES: dict = {}
HULL = 256
CAR_DOOR_X = (14848, 15872)
#: round 5: "one 17.8 m slab, two windows a side, one door" -- four
#: windows a side now, a body wide each, and a door that looks like one
CAR_WINDOWS_X = ((11008, 12032), (12800, 13824), (16896, 17920),
                 (18688, 19712))
CAR_CLEAR, WINDOW_SILL, WINDOW_HEAD = 24576, 8192, 20480
#: tables against the far side, seats either side of each, an aisle left
TABLES = ((12288, CAR[1] + 384, 12800, CAR[1] + 896),
          (17408, CAR[1] + 384, 17920, CAR[1] + 896))
SEATS = tuple((x, CAR[1] + 384, x + 384, CAR[1] + 896)
              for x in (11776, 12928, 16896, 18048))
AXIS = (CAR[1] + CAR[3]) // 2
#: the locomotive: a cab the car's width, a boiler narrower and lower, a
#: dome and a chimney standing on it, a buffer beam at its nose
CAB = (22784, CAR[1], 24320, CAR[3])
#: round 4: "a diamond-plate box with a stepped top ... nothing shows
#: which end leads". A low FRAME the wheels hang on; on it a boiler
#: narrower than the frame (the nearest a sector gets to round); on that
#: a dome and, at the nose, a thin tall chimney, darker than the rest.
FRAME = (24448, AXIS - 896, 28160, AXIS + 896)
BOILER = (24576, AXIS - 512, 28032, AXIS + 512)
DOME = (25728, AXIS - 192, 26112, AXIS + 192)
CHIMNEY = (27392, AXIS - 192, 27776, AXIS + 192)
BEAM = (28288, CAR[1], 28544, CAR[3])
BUFFER = (2560, CAR[1] + 256, 3584, CAR[3] - 256)
#: pools of light under the hall's lamps: (x0, y0, x1, y1)
POOLS = ((9216, -10752, 10752, -9216), (12544, -10240, 14080, -8704),
         (15872, -10752, 17408, -9216))
LAMP, WALL_LAMP, CURTAIN = 945, 2183, 147
STREET_TORCH = 506
COLUMNS = tuple(HALL[0] + 1024 + k * 2560 for k in range(4))
#: Replace the fenced bay between the first two columns with a roofed rotor.
FARE_JAMBS = (COLUMNS[0], COLUMNS[1] + 512)
FARE_ROTOR = (COLUMNS[0] + 512, HALL[1], COLUMNS[1], HALL[1] + 2048)
FARE_CLEAR = 32768
BENCHES = ((10240, -11392), (14848, -12032))      # clear landing in front of the fare gate
CAR_DOOR_CHANNEL = wires.channel("station:car-door")

#: tiles (the owner's names in quotes)
FLOOR = 281                        # "irregular grey stone masonry"
HALL_WALL, PLANKS = 90, 67         # "worn large bricks with moss"
PASSAGE_WALL, PASSAGE_CEILING = 414, 120
TRACK = 1129                       # "railway track with sleepers"
FAR_WALL, TUNNEL_WALL, TUNNEL_VAULT = 421, 80, 253
PLATFORM_FACE, LIVERY = 174, 1665
COLUMN, WOOD, PLATING = 115, 34, 470
#: the locomotive's plate. 470 at this size read as red brick (my own
#: frames of the fourth version); 438 is the owner's "embossed metal
#: floor", worn here on a boiler's side -- a use he has not named.
IRON = 438
#: THE LOCOMOTIVE'S RECIPE, from walking round Blood's own with
#: `tools.look_at` (knowledge/blood/studies/locomotive). The owner, of the
#: fourth: "made from one texture and there is grave on it. You should
#: study more textures, decals combinations and locomotives in other
#: levels." E1M4's engine is FOUR surfaces and three sprites: rusted
#: plate 255 for the body, riveted plates 470 under it where the wheels
#: hang, the riveted barrel 2453 where it is round, diamond plate 438 on
#: top, a flame, and two smokes (754, 672) over the chimney. The Death
#: Wish trains add a barred vent (794) in the side and a horned face
#: (634) on the front. None of these is an owner-named use on a train.
BODY_PLATE, UNDERFRAME, BARREL, CAB_PANEL = 255, 470, 2453, 490
VENT, HORNED_FACE, SMOKE_THIN, SMOKE_PLUME = 794, 634, 754, 672
#: round 5, two readers: "the carriage has no doors on the platform
#: side". It had one, shut, in the livery. 56 is a red door with a small
#: window (unnamed by the owner); it rides up with the leaf.
CAR_DOOR_TILE = 56
BILL = 356
ROLLUP, CRATE, BALUSTRADE, LONGCASE, CAB_WINDOW = 9, 95, 588, 720, 389                         # E1M3 hangs a bill on its carriage side
CARPET, PANELLING = 300, 105       # "carpet", "coffered wood panelling"
#: round 4, two readers: "the carriage windows are wooden door panels
#: pasted into the green band" -- they were looking THROUGH the glass at
#: brown panelling. The car is lined in the owner's "plaster wall with top
#: beam and carved base", pale behind the glass; its seats are his chairs.
CAR_LINING, CHAIR = 109, 758
BARS = 58                          # "iron bars (jail)"
#: (E1M2's is 8413; bit 64, one-sided, is dropped: the hall's gates are
#: seen from the platform too)
GATE = {"type": 0, "picnum": 1044, "cstat": 8413 & ~64, "x_repeat": 64,
        "y_repeat": 96, "shade": 32, "status": 0}       # E1M2 sprite 473
WHEELS = {"type": 0, "picnum": 2320, "cstat": 464, "x_repeat": 88,
          "y_repeat": 104, "shade": 22, "status": 0}     # E1M3 sprite 419
CLOCK = {"tile": 1165, "x_repeat": 55, "y_repeat": 55}  # MISKSTAT sprite 143
BOARDS = {"tickets": 943, "arrivals": 431, "telephone": 645}
POSTERS = (440, 453, 981, 225)     # the last is the Pandemonium Show's bill

FACES: dict = {}       # region id -> tile its raised faces wear
TRACKS: list = []      # regions floored in track
EDGE: list = []        # platform parts a body may not step off
OPENINGS: list = []    # the carriage's door and windows, seen from the shed
COLUMN_BOXES: list = []
PANES: list = []       # (x0, y0, x1, y1): lines that are glazed
GRILLES: list = []     # lines that are barred
ROOMS: dict = {}


def build(city, street):
    """The station behind the north wall, joined to `street` by one door."""
    sky = FACADES["theatre_row"].ceiling
    station = city.assembly(
        "gravesend_station",
        style=Style(floor_picnum=FLOOR, wall_picnum=HALL_WALL,
                    ceiling_picnum=PLANKS, floor_z=GRADE,
                    clear_height=HALL_CLEAR, layer="street"),
        note="Gravesend Station: office, hall, platform, train, tunnel")
    import citytree
    import detailing
    citytree.declare_venue(station, "station", "landmark",
                           built_by="l3_station")

    def room(name, rect, *, floor_z, clear, note, role="interior",
             sky_open=False, rk=None, intent=None, outline=None, faces=COMPASS,
             **surfaces):
        x0, y0, x1, y1 = (int(v) for v in rect)
        made = station.room(
            name, outline or [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(faces), frame=Frame(x0, y0),
            region_kwargs=dict(rk or {}), note=note,
            #: every room here is furnished by `furnish`, not by the
            #: city's generic dressing (see `dressing.dress`)
            intent=intent or {"kind": "furnished"})
        made.surfaces(floor_z=floor_z, clear_height=clear,
                      parallax_ceiling=sky_open,
                      **({"ceiling_picnum": sky} if sky_open else {}),
                      **surfaces)
        ROOMS[name] = made
        return made

    def inside(host, host_rect, name, rect, rise, top, face, note,
               shade=18):
        """A solid thing standing in `host`: a hole and a floor at its top."""
        x0, y0, x1, y1 = rect
        hx0, hy0 = host_rect[0], host_rect[1]
        host.carve([(x0 - hx0, y0 - hy0), (x1 - hx0, y0 - hy0),
                    (x1 - hx0, y1 - hy0), (x0 - hx0, y1 - hy0)])
        floor = int(host.style.floor_z) - rise
        clear = int(host.style.clear_height) - rise
        made = room(name, rect, floor_z=floor, clear=clear,
                    sky_open=bool(host.style.parallax_ceiling),
                    role="detail", note=note,
                    #: a thing in a room, not a room: the generic dressing
                    #: stood a gravestone on the locomotive's cab
                    intent={"kind": "light_pool" if not rise else "machine"},
                    rk={"declared_zero_exit": True},
                    floor_picnum=top, wall_picnum=face, floor_shade=shade)
        FACES[made.region_id] = face
        for side in COMPASS:
            station.connect(made.face(side), host.face("north"),
                            connection_id=f"connection:station_{name}_{side}")
        return made

    # ---- in from the street, and up -------------------------------------
    door = room("door", DOOR, floor_z=GRADE, clear=32768, role="gateway",
                note="the way through the city's north wall",
                #: its jambs wear the hall's iron column, lit: a doorway
                #: with a frame (round 5: "an unmarked, unframed slot")
                wall_picnum=COLUMN, ceiling_picnum=WOOD,
                floor_shade=10, wall_shade=4, ceiling_shade=12)
    passage = room("passage", PASSAGE, floor_z=GRADE, clear=65536,
                   note="the entrance passage",
                   wall_picnum=PASSAGE_WALL, ceiling_picnum=PASSAGE_CEILING,
                   #: round 6, two readers: "the station entrance doorway
                   #: renders as a flat black void" from the street
                   floor_shade=16, ceiling_shade=30, wall_shade=20)
    rx0, ry0, rx1, ry1 = RAMP
    ramp = room("ramp", RAMP, floor_z=GRADE, clear=HALL_UP + HALL_CLEAR,
                role="gateway",
                note="the stair up to the hall (E1M2 s105: one sloped floor)",
                rk={"floor_slope": SlopeSpec(
                    hinge=((rx1, ry1), (rx0, ry1)), rise_z=-HALL_UP)},
                wall_picnum=PASSAGE_WALL, floor_shade=14, wall_shade=26)
    hx0, hy0, hx1, hy1 = HALL
    rx0, _, rx1, ry1 = FARE_ROTOR
    jx0, jx1 = FARE_JAMBS
    hall_outline = [(x - hx0, y - hy0) for x, y in (
        (hx0, hy0), (jx0, hy0), (jx0, ry1), (jx1, ry1), (jx1, hy0),
        (hx1, hy0), (hx1, hy1), (hx0, hy1))]
    hall = room("hall", HALL, floor_z=HALL_Z, clear=HALL_CLEAR,
                outline=hall_outline, faces={"north_west": 0, "fare_gate": 2,
                "north": 4, "east": 5, "south": 6, "west": 7},
                note="the booking hall: mossy brick under dark planks",
                floor_shade=26, ceiling_shade=44, wall_shade=34)
    city.connect(door.face("south"), street.face("north"),
                 connection_id="connection:station_door")
    station.connect(door.face("north"), passage.face("south"),
                    connection_id="connection:station_passage")
    station.connect(ramp.face("south"), passage.face("north"),
                    connection_id="connection:station_ramp_foot")
    station.connect(ramp.face("north"), hall.face("south"),
                    connection_id="connection:station_ramp_head")

    # ---- the booking office: a clerk behind bars, a door round the side --
    office = room("office", OFFICE, floor_z=HALL_Z, clear=32768,
                  note="the booking office", wall_picnum=PASSAGE_WALL,
                  floor_picnum=WOOD, ceiling_picnum=PLANKS,
                  floor_shade=16, ceiling_shade=30, wall_shade=22)
    way = room("office_door", OFFICE_DOOR, floor_z=HALL_Z, clear=28672,
               role="gateway", note="the office's side door",
               wall_picnum=WOOD, ceiling_picnum=WOOD, floor_shade=20)
    station.connect(way.face("east"), hall.face("west"),
                    connection_id="connection:station_office_door_hall")
    station.connect(way.face("west"), office.face("east"),
                    connection_id="connection:station_office_door_in")
    wx0, wy0, wx1, wy1 = OFFICE_WINDOW
    mid = (wx0 + wx1) // 2
    pocket = room("office_window_in", (wx0, wy0, mid, wy1),
                  floor_z=HALL_Z - WINDOW_SILL, clear=16384, role="detail",
                  note="the booking window, the clerk's side",
                  rk={"declared_zero_exit": True}, wall_picnum=WOOD,
                  floor_picnum=WOOD, ceiling_picnum=WOOD, floor_shade=10)
    reveal = room("office_window_out", (mid, wy0, wx1, wy1),
                  floor_z=HALL_Z - WINDOW_SILL, clear=16384, role="detail",
                  note="the booking window, the passenger's side",
                  rk={"declared_zero_exit": True}, wall_picnum=WOOD,
                  floor_picnum=WOOD, ceiling_picnum=WOOD, floor_shade=10)
    station.connect(pocket.face("west"), office.face("east"),
                    connection_id="connection:station_window_office")
    station.connect(pocket.face("east"), reveal.face("west"),
                    connection_id="connection:station_window_pane")
    station.connect(reveal.face("east"), hall.face("west"),
                    connection_id="connection:station_window_hall")
    GRILLES.append((mid - 16, wy0, mid + 16, wy1))

    # ---- the hall: columns on the platform line, benches to wait on -----
    for cx in COLUMNS[2:]:
        box = (cx, HALL[1] + 128, cx + 512, HALL[1] + 640)
        hall.carve([(box[0] - HALL[0], box[1] - HALL[1]),
                    (box[2] - HALL[0], box[1] - HALL[1]),
                    (box[2] - HALL[0], box[3] - HALL[1]),
                    (box[0] - HALL[0], box[3] - HALL[1])])
        COLUMN_BOXES.append(box)
    COLUMN_BOXES.extend(((jx0, hy0, rx0, ry1), (rx1, hy0, jx1, ry1)))

    # DOOR-ROTATING s4: four carried vanes, a fixed outline and a central axis.
    # The campaign rotor's iron lattice matches the hall's fixed grilles.
    # At its stock size each vane reaches 768, leaving 256 to either jamb.
    fare = turnstile_spec(period=255, floor_z=HALL_Z, ceiling_z=HALL_Z - FARE_CLEAR,
                          arrangement=DISTINCT_ANGLES)
    fare["behavior"].pop("rx_id")  # the city's named engine wire supplies RX
    rotor = room("fare_turnstile", FARE_ROTOR, floor_z=HALL_Z, clear=FARE_CLEAR,
                 role="gateway", note="the four-vane fare gate beside the open bays",
                 rk={"type": fare["sector_type"], "sector_behavior": fare["behavior"]},
                 wall_picnum=COLUMN, ceiling_picnum=PLANKS,
                 floor_shade=8, ceiling_shade=18, wall_shade=8)
    station.connect(rotor.face("south"), hall.face("fare_gate"),
                    connection_id="connection:station_fare_hall")
    wires.wire("station:fare-turnstile").then(wiring.region(rotor.region_id))
    pivot = ((rx0 + rx1) // 2, (hy0 + ry1) // 2)

    def place_fare_rotor(layout, room):
        px, py = pivot
        layout.add_sprite("placement:station:fare_turnstile:axis", room.region_id,
                          x=px, y=py, **fare["axis"])
        for index, blade in enumerate(fare["blades"]):
            fields = dict(blade)
            dx, dy = fields.pop("dx"), fields.pop("dy")
            layout.add_sprite(f"placement:station:fare_turnstile:vane:{index}",
                              room.region_id, x=px + dx, y=py + dy, shade=8, **fields)

    rotor.raw("Fit the campaign axis marker and four floor-to-roof grates.",
              place_fare_rotor)
    for index, (bx, by) in enumerate(BENCHES):
        #: round 3: "bench seats are 1.06 m deep (real: about 0.45 m) and
        #: read as crates". A seat 0.6 m deep and knee high, a thin back.
        inside(hall, HALL, f"bench_{index}", (bx, by, bx + 2048, by + 384),
               4608, WOOD, WOOD, "a bench: the seat")
        inside(hall, HALL, f"bench_{index}_back",
               (bx, by + 448, bx + 2048, by + 576), 10240, WOOD, WOOD,
               "a bench: its back")
    #: LIGHT. Three rounds running: "uniform lighting everywhere; no
    #: darkness or pools of light". The hall is dark now, and what light
    #: there is lies under its lamps.
    for index, rect in enumerate(POOLS):
        inside(hall, HALL, f"pool_{index}", rect, 0, FLOOR, HALL_WALL,
               "light under a hall lamp", shade=0)

    # ---- the platform ---------------------------------------------------
    parts = []
    for index, (x0, x1, roofed, bay) in enumerate(PLATFORM):
        part = room(
            f"platform_{index}", (x0, PY0, x1, PY1), floor_z=HALL_Z,
            clear=(CAR_TOP - PLATFORM_DROP) if roofed else OPEN_CLEAR,
            sky_open=not roofed,
            role="interior" if roofed else "exterior",
            note="the platform under its canopy" if roofed
            else "the platform, open to the sky",
            floor_shade=14 if roofed else 10,
            **({"ceiling_shade": 36} if roofed else {}))
        FACES[part.region_id] = PLATFORM_FACE
        if not bay:
            EDGE.append(part.region_id)
        if parts:
            station.connect(parts[-1].face("east"), part.face("west"),
                            connection_id=f"connection:station_platform_{index}")
        if hx0 <= x0 and x1 <= hx1:
            face = "north_west" if x0 < jx0 else "north"
            span = min(x1, jx0) - x0 if face == "north_west" else x1 - max(x0, jx1)
            station.connect(part.face("south"), hall.face(face), min_width=span,
                            connection_id=f"connection:station_hall_platform_{index}")
        fare_span = min(x1, rx1) - max(x0, rx0)
        if fare_span > 0:
            station.connect(part.face("south"), rotor.face("north"), min_width=fare_span,
                            connection_id=f"connection:station_fare_platform_{index}")
        parts.append(part)
    dx0, dy0, dx1, dy1 = DOWN_RAMP
    down = room("platform_ramp", DOWN_RAMP, floor_z=HALL_Z, clear=OPEN_CLEAR,
                sky_open=True, role="exterior",
                note="the ramp from the platform's end down to the track",
                rk={"floor_slope": SlopeSpec(
                    hinge=((dx1, dy0), (dx1, dy1)), rise_z=PLATFORM_DROP)},
                floor_shade=24, wall_picnum=FAR_WALL)
    FACES[down.region_id] = PLATFORM_FACE
    station.connect(down.face("east"), parts[0].face("west"),
                    connection_id="connection:station_ramp_platform")

    # ---- the track: sky, shed, sky --------------------------------------
    # Round 2 of the critique: "a solid plank ceiling covers the tracks and
    # train ... no sky or open air" and "flat light". The shed roofs the
    # NEAR track only (the carriage needs it); the far track lies open to
    # the sky beside it, so the carriage's far windows look out on light.
    by0, by1 = BED_Y
    near_y0 = CAR[1] - 128

    def bed(name, rect, clear, note, roofed=False):
        made = room(name, rect, floor_z=BED_Z, clear=clear,
                    sky_open=not roofed,
                    role="interior" if roofed else "exterior", note=note,
                    rk={"declared_zero_exit": True}, floor_picnum=TRACK,
                    wall_picnum=FAR_WALL, floor_shade=20, wall_shade=14,
                    **({"ceiling_picnum": PLANKS, "ceiling_shade": 30}
                       if roofed else {}))
        TRACKS.append(made.region_id)
        return made

    open_clear = OPEN_CLEAR + PLATFORM_DROP
    west = bed("track_west", (BED_X[0], by0, BED_X[1], by1), open_clear,
               "the track under the sky")
    east = bed("track_east", (BED_X[2], by0, BED_X[3], by1), open_clear,
               "the track under the sky")
    far = bed("track_far", (BED_X[1], by0, BED_X[2], near_y0), open_clear,
              "the far track, open to the sky")
    near_w = bed("near_west", (BED_X[1], near_y0, RING[0], by1), open_clear,
                 "the near track behind the train")
    near_e = bed("near_east", (RING[2], near_y0, BED_X[2], by1), open_clear,
                 "the near track between carriage and engine")
    shed = bed("shed", RING, open_clear,
               "the track the carriage stands on")
    for a, b, name in (
            (near_w.face("west"), west.face("east"), "near_west"),
            (near_w.face("east"), shed.face("west"), "ring_west"),
            (near_e.face("west"), shed.face("east"), "ring_east"),
            (near_e.face("east"), east.face("west"), "near_east"),
            (far.face("west"), west.face("east"), "far_west"),
            (far.face("east"), east.face("west"), "far_east"),
            (near_w.face("north"), far.face("south"), "far_near_w"),
            (shed.face("north"), far.face("south"), "far_ring"),
            (near_e.face("north"), far.face("south"), "far_near_e")):
        station.connect(a, b, connection_id=f"connection:station_{name}")
    for index, part in enumerate(parts):
        x0, x1 = PLATFORM[index][:2]
        beside = (east if x0 >= BED_X[2] else near_w if x1 <= RING[0]
                  else near_e if x0 >= RING[2] else shed)
        station.connect(part.face("north"), beside.face("south"),
                        connection_id=f"connection:station_edge_{index}")
    station.connect(down.face("north"), west.face("south"),
                    connection_id="connection:station_ramp_track")

    # ---- the signal box: a stair, a cabin, a balcony over the platform --
    landing = room("signal_landing", LANDING, floor_z=HALL_Z, clear=OPEN_CLEAR,
                   sky_open=True, role="exterior",
                   note="the foot of the signal box's stair",
                   floor_shade=14, wall_picnum=HALL_WALL, wall_shade=18)
    sx0, sy0, sx1, sy1 = SIGNAL_RAMP
    stair = room("signal_stair", SIGNAL_RAMP, floor_z=HALL_Z,
                 clear=OPEN_CLEAR, sky_open=True, role="gateway",
                 note="the stair up to the signal box (one sloped floor)",
                 rk={"floor_slope": SlopeSpec(
                     hinge=((sx0, sy1), (sx0, sy0)), rise_z=-SIGNAL_UP)},
                 floor_picnum=WOOD, floor_shade=12, wall_picnum=HALL_WALL,
                 wall_shade=18)
    box = room("signal_box", SIGNAL_BOX, floor_z=HALL_Z - SIGNAL_UP,
               clear=28672, note="the signal box: the gate's lever",
               floor_picnum=WOOD, wall_picnum=WOOD, ceiling_picnum=PLANKS,
               floor_shade=6, ceiling_shade=24, wall_shade=12)
    balcony = room("signal_balcony", BALCONY, floor_z=HALL_Z - SIGNAL_UP,
                   clear=OPEN_CLEAR - SIGNAL_UP, sky_open=True,
                   role="exterior",
                   note="the signal box's balcony over the platform",
                   floor_picnum=WOOD, floor_shade=8, wall_picnum=HALL_WALL,
                   wall_shade=16)
    FACES[balcony.region_id] = HALL_WALL
    station.connect(landing.face("north"), parts[-1].face("south"),
                    connection_id="connection:station_signal_landing")
    station.connect(stair.face("west"), landing.face("east"),
                    connection_id="connection:station_signal_foot")
    station.connect(stair.face("east"), box.face("west"),
                    connection_id="connection:station_signal_head")
    station.connect(box.face("north"), balcony.face("south"),
                    connection_id="connection:station_signal_balcony")
    station.connect(balcony.face("north"), parts[-1].face("south"),
                    connection_id="connection:station_balcony_edge")

    # ---- the waiting room ------------------------------------------------
    wdoor = room("waiting_door", WAITING_DOOR, floor_z=HALL_Z, clear=28672,
                 role="gateway", note="the waiting room's door",
                 wall_picnum=WOOD, ceiling_picnum=WOOD, floor_shade=12)
    waiting = room("waiting_room", WAITING, floor_z=HALL_Z, clear=36864,
                   note="the waiting room: carpet, benches, a clock",
                   floor_picnum=CARPET, wall_picnum=CAR_LINING,
                   ceiling_picnum=PLANKS, floor_shade=2, ceiling_shade=22,
                   wall_shade=4)
    station.connect(wdoor.face("west"), hall.face("east"),
                    connection_id="connection:station_waiting_door_hall")
    station.connect(wdoor.face("east"), waiting.face("west"),
                    connection_id="connection:station_waiting_door_in")
    for index, rect in enumerate(WAIT_BENCHES):
        inside(waiting, WAITING, f"wait_bench_{index}", rect, 4608, WOOD,
               WOOD, "a bench in the waiting room", shade=8)
    inside(waiting, WAITING, "wait_table", WAIT_TABLE, 7168, WOOD, WOOD,
           "the waiting room's table", shade=6)

    # ---- the carriage: walls that are sectors, a roof that is sprites ---
    from bloodmap.doors import xsector_remote_rx

    cx0, cy0, cx1, cy1 = CAR
    shed_rect = RING
    shed.carve([(cx0 - shed_rect[0], cy0 - near_y0),
                (cx1 - shed_rect[0], cy0 - near_y0),
                (cx1 - shed_rect[0], cy1 - near_y0),
                (cx0 - shed_rect[0], cy1 - near_y0)])
    sky_z = HALL_Z - OPEN_CLEAR
    roof_z = HALL_Z - CAR_H
    sill_z = HALL_Z - WINDOW_SILL

    def hull(name, rect, floor, note, **more):
        made = room(name, rect, floor_z=floor, clear=floor - sky_z,
                    sky_open=True, role="detail", note=note,
                    rk={"declared_zero_exit": True, **more.pop("rk", {})},
                    **{"floor_picnum": ROOF, "wall_picnum": CAR_LINING,
                       "floor_shade": 20, **more})
        return made

    car = room("carriage", (cx0 + HULL, cy0 + HULL, cx1 - HULL, cy1 - HULL),
               floor_z=HALL_Z, clear=OPEN_CLEAR, sky_open=True,
               note="the carriage: a carpet, tables, a way through "
                    "(E1M3's lounge car)",
               rk={"declared_zero_exit": True},
               floor_picnum=CARPET, wall_picnum=CAR_LINING, floor_shade=0,
               wall_shade=0)
    ends = {}
    for side, x0, x1 in (("west", cx0, cx0 + HULL), ("east", cx1 - HULL, cx1)):
        end = hull(f"hull_{side}", (x0, cy0, x1, cy1), roof_z,
                   "the carriage's end wall")
        HULL_SOLID.append(end.region_id)
        ends[side] = end
        for face in ("north", "south", side):
            station.connect(end.face(face), shed.face("north"),
                            connection_id=f"connection:station_hull_{side}_{face}")
        inner = "east" if side == "west" else "west"
        station.connect(car.face(side), end.face(inner),
                        connection_id=f"connection:station_hull_{side}_in")
    for row, kinds, y0, y1, out_face, in_face in (
            ("s", SOUTH_KINDS, cy1 - HULL, cy1, "south", "north"),
            ("n", NORTH_KINDS, cy0, cy0 + HULL, "north", "south")):
        previous = ends["west"]
        for k, kind in enumerate(kinds):
            rect = (SIDE_X[k], y0, SIDE_X[k + 1], y1)
            if kind == "S":
                piece = hull(f"hull_{row}{k}", rect, roof_z,
                             "the carriage's side wall")
                HULL_SOLID.append(piece.region_id)
            elif kind == "W":
                piece = hull(f"window_{row}{k}", rect, sill_z,
                             "a carriage window: the wall, sill high",
                             floor_picnum=WOOD)
                HULL_OPEN.append(piece.region_id)
            else:
                #: THE DOOR: a stretch of wall that sinks into the floor.
                #: Typed after the door pass, which takes a type-600
                #: region for a leaf whose CEILING rises.
                piece = hull(
                    "carriage_door", rect, roof_z,
                    "the carriage door: the lever sinks it",
                    rk={"sector_behavior": {
                        **xsector_remote_rx(CAR_DOOR_CHANNEL),
                        "off_floor_z": roof_z, "on_floor_z": HALL_Z,
                        "off_ceiling_z": sky_z, "on_ceiling_z": sky_z,
                        "busy_time_a": 8, "busy_time_b": 8}},
                    floor_picnum=WOOD)
                LATE_TYPES[piece.region_id] = 600
                wires.wire("station:car-door").then(wiring.region(piece.region_id))
            station.connect(piece.face(out_face), shed.face("north"),
                            connection_id=f"connection:station_{row}{k}_out")
            station.connect(piece.face(in_face), car.face(out_face),
                            connection_id=f"connection:station_{row}{k}_in")
            station.connect(piece.face("west"), previous.face("east"),
                            connection_id=f"connection:station_{row}{k}_west")
            previous = piece
        station.connect(previous.face("east"), ends["east"].face("west"),
                        connection_id=f"connection:station_{row}_last")
    car_rect = (cx0 + HULL, cy0 + HULL, cx1 - HULL, cy1 - HULL)
    for index, rect in enumerate(TABLES):
        inside(car, car_rect, f"carriage_table_{index}", rect, 7168, WOOD,
               WOOD, "a table in the carriage")

    # ---- the locomotive, the buffer, the tunnel -------------------------
    east_rect = (BED_X[2], by0, BED_X[3], by1)
    #: round 3: "a box 4.25 m wide and 9 m long, with a cab in the
    #: carriage's livery ... reads as a second carriage". A cab the car's
    #: width and height in black plate; a boiler narrower and lower; on it
    #: a dome and a chimney; a buffer beam at the nose.
    frame = inside(east, east_rect, "loco_frame", FRAME, 13312, IRON,
                   UNDERFRAME, "the locomotive's frame and running board",
                   shade=18)
    boiler = inside(frame, FRAME, "boiler", BOILER, 17408, BODY_PLATE,
                    BARREL, "the locomotive's boiler", shade=10)
    inside(boiler, BOILER, "dome", DOME, 4096, IRON, BODY_PLATE,
           "the steam dome", shade=8)
    inside(boiler, BOILER, "chimney", CHIMNEY, 18432, BODY_PLATE, BARREL,
           "the chimney", shade=28)
    inside(east, east_rect, "cab", CAB, CAR_TOP, IRON, CAB_PANEL,
           "the locomotive's cab", shade=16)
    inside(east, east_rect, "beam", BEAM, 9216, WOOD, WOOD,
           "the buffer beam", shade=16)
    inside(west, (BED_X[0], by0, BED_X[1], by1), "buffer", BUFFER, 8192,
           PLATING, PLATING, "the buffer stop (an invention)")
    tunnel_clear = int(3.9 * BODY) // 256 * 256
    gate = room("tunnel_gate", (GATE_X[0], by0 + 512, GATE_X[1], by1 - 512),
                floor_z=BED_Z, clear=0, role="doorway",
                note="the roll-up gate in the tunnel's mouth: the signal "
                     "box's lever raises it",
                rk={"type": 600, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(
                        BED_Z, BED_Z - tunnel_clear, interaction="remote",
                        rx_id=GATE_CHANNEL, open_time=20)},
                wall_picnum=ROLLUP, floor_picnum=TRACK,
                ceiling_picnum=TUNNEL_VAULT)
    station.connect(gate.face("west"), east.face("east"),
                    connection_id="connection:station_gate_out")
    wires.wire("station:gate").then(wiring.region(gate.region_id))
    previous = gate
    for index, (x0, x1, shade) in enumerate(TUNNEL):
        bore = room(f"tunnel_{index}", (x0, by0 + 512, x1, by1 - 512),
                    floor_z=BED_Z, clear=int(3.9 * BODY) // 256 * 256,
                    note="the tunnel the line leaves by",
                    rk={"declared_zero_exit": True},
                    floor_picnum=TRACK,
                    wall_picnum=TUNNEL_WALL, ceiling_picnum=TUNNEL_VAULT,
                    floor_shade=shade, ceiling_shade=shade, wall_shade=shade)
        TRACKS.append(bore.region_id)
        station.connect(bore.face("west"), previous.face("east"),
                        connection_id=f"connection:station_tunnel_{index}")
        if index == len(TUNNEL) - 1:
            # THE WAY OUT. The city had none: the reader that marks the
            # campaign said so on 2026-11-19. The line leaves by this tunnel
            # and so does the player; the switch that ends the level hangs
            # on the bore's side wall near its far end (placed with the
            # levers, below). The end wall itself is an opening onto the
            # dark beyond, and the build refuses a switch hung on air.
            WAY_OUT.update(region=bore.region_id, a1=(x0, by0 + 512),
                           a2=(x1, by0 + 512))
        previous = bore
    #: the tunnel mouth is barred: the line goes on, the player does not
    store = room("goods_store", STORE, floor_z=BED_Z, clear=49152,
                 note="the goods store the line serves: crates for the quay",
                 rk={"declared_zero_exit": True},
                 floor_picnum=FLOOR, wall_picnum=TUNNEL_WALL,
                 ceiling_picnum=PLANKS, floor_shade=12, ceiling_shade=34,
                 wall_shade=20)
    station.connect(previous.face("east"), store.face("west"),
                    connection_id="connection:station_store")
    for index, (rect, rise) in enumerate(CRATES):
        inside(store, STORE, f"crate_{index}", rect, rise, CRATE, CRATE,
               "a crate for the quay", shade=8)

    # ---- THE AVENUE FRONT: the station seen from the city's main street --
    # The showcase's blind reader, round 2, of the north-lane door: "a brick
    # building entrance ... the recessed passage looks like another gap in
    # the wall". It is a slot in a long wall on a lane where no view shows a
    # front. The avenue, the city's long axis, ended in a blank end wall a
    # few units south of the platform's east end. The station is fronted
    # there now (`avenue_front`, built with the streets), and these are the
    # rooms behind that front: an entrance hall at street level, a stair up
    # the station's own 1.21 bodies (E1M2 s105, as the north-lane ramp), and
    # a concourse at platform level that walks out onto the platform's east
    # end beside the locomotive.
    ex0, ey0, ex1, ey1 = EAST_HALL
    east_hall = room("east_hall", EAST_HALL, floor_z=GRADE, clear=HALL_CLEAR,
                     note="the station's avenue entrance hall",
                     wall_picnum=FRONT_STONE, floor_shade=4,
                     ceiling_shade=16, wall_shade=8)
    east_hall.light_source("east_hall_lamp", local=(0.5, 0.5),
                           height_player_heights=2.2)
    sx0, sy0, sx1, sy1 = EAST_STAIR
    east_stair = room("east_stair", EAST_STAIR, floor_z=GRADE,
                      clear=HALL_UP + HALL_CLEAR, role="gateway",
                      note="the stair up from the avenue hall to the concourse",
                      rk={"floor_slope": SlopeSpec(
                          hinge=((sx1, sy1), (sx0, sy1)), rise_z=-HALL_UP)},
                      wall_picnum=FRONT_STONE, floor_shade=14, wall_shade=22)
    concourse = room("concourse", CONCOURSE, floor_z=HALL_Z, clear=HALL_CLEAR,
                     note="the concourse: the avenue's way onto the platform",
                     floor_shade=16, ceiling_shade=40, wall_shade=30)
    concourse.light_source("concourse_lamp", local=(0.3, 0.5),
                           height_player_heights=2.2)
    link = room("concourse_link", EAST_LINK, floor_z=HALL_Z, clear=32768,
                role="gateway", note="from the concourse onto the platform",
                wall_picnum=COLUMN, ceiling_picnum=WOOD, floor_shade=12)
    station.connect(east_stair.face("south"), east_hall.face("north"),
                    connection_id="connection:station_east_stair_foot")
    station.connect(east_stair.face("north"), concourse.face("south"),
                    connection_id="connection:station_east_stair_head")
    station.connect(link.face("east"), concourse.face("west"),
                    connection_id="connection:station_concourse_link")
    station.connect(link.face("west"), parts[-1].face("east"),
                    connection_id="connection:station_link_platform")
    return ROOMS


def furnish(layout, street_region_id: str, attested=None) -> dict:
    """Signs, boards, gates, wheels, the lever, and who is here."""
    import doorswitch
    import wallplane

    report = {"signs": 0, "boards": 0, "gates": 0, "wheels": 0, "folk": 0}
    hall, office = ROOMS["hall"], ROOMS["office"]
    hx0, hy0, hx1, hy1 = HALL

    def words(text, region_id, a1, a2, style, height):
        if wallplane.text(layout, f"sign:station_{text.lower().replace(' ', '_')}",
                          region_id, a1, a2, words=text, style=style,
                          height_player_heights=height):
            report["signs"] += 1

    #: on the street, beside the door: so a station is FOUND
    #: round 3: "the street door is an unmarked slot, and STATION is
    #: lettered on the neighbouring wall above eye level". The name goes
    #: right beside the door at a reader's height, a clock over it, and a
    #: lit lamp either side of the doorway.
    #: (round 4: at eye height the letters lay across the neighbour's
    #: window mullions; they sit in the band over that row)
    words("STATION", street_region_id, (DOOR[2] + 256, 0),
          (DOOR[2] + 4352, 0), "fascia", 2.2)
    for name, a1, a2, tile, t_at, height, repeat in (
            #: the campaign's wall torch (506, 186 uses at 1.03 bodies): the
            #: recessed lamp 2183 is a recorded MISFIT outdoors, "small eye
            #: symbols" to a blind reader (`tools.tile_contexts show 2183`)
            ("street_lamp_e", (DOOR[2] + 64, 0), (DOOR[2] + 704, 0),
             STREET_TORCH, 0.5, 1.03, 64),
            ("street_lamp_w", (DOOR[0] - 704, 0), (DOOR[0] - 64, 0),
             STREET_TORCH, 0.5, 1.03, 64),
            ("street_clock", (DOOR[0] - 2304, 0), (DOOR[0] - 768, 0),
             CLOCK["tile"], 0.5, 1.6, CLOCK["x_repeat"])):
        got = wallplane.sprite(
            layout, f"station:{name}", street_region_id, a1, a2, tile=tile,
            x_repeat=repeat, y_repeat=repeat, cstat=16 | 64 | 128, t=t_at,
            height_player_heights=height, offset_player_widths=0.04, shade=-8)
        report["boards"] += bool(got)
    #: THE AVENUE FRONT, from the forecourt: GRAVESEND over the west arch
    #: and STATION over the east, over the arches' crowns; the station clock
    #: high on the pier between them; lamp posts (the avenue's own,
    #: `props.STREET_LAMP`) before each jamb.
    import props
    report["front"] = 0
    fy0 = -FORECOURT_D
    courts = AVENUE_FRONT.get("courts", [])
    for court in courts:
        region = court["region"]
        floor_z = layout.regions[region].floor_z
        for a, b in ARCHES:
            if court["a"] <= a and b <= court["b"]:
                word = "GRAVESEND" if a < 36352 else "STATION"
                if wallplane.text(layout, f"sign:station_front_{word.lower()}", region,
                                  (a - 256, fy0), (b + 256, fy0), words=word,
                                  style="fascia",
                                  height_player_heights=ARCH_APEX / 16960 + 0.55):
                    report["front"] += 1
        for x in (33024, 35840, 36864, 39680):
            if not court["a"] < x < court["b"]:
                continue
            layout.add_sprite(f"station:front_post_{x}", region, x=x, y=fy0 + 1024,
                              z=int(floor_z), **props.fields(
                                  props.STREET_LAMP, x_repeat=props.STREET_LAMP_REPEAT,
                                  y_repeat=props.STREET_LAMP_REPEAT))
            layout.add_light_source(
                f"light:station_front_{x}", region, x=x, y=fy0 + 1024,
                z=int(floor_z - props.STREET_LAMP_LIGHT * 16960), intensity=2.0)
            report["front"] += 1
        if court["a"] < FRONT_PIER[0] < court["b"]:
            # centred on the pier, which the seam halves: hung on the west
            # court's wall at its east end (no one wall has room for it)
            layout.place_on_wall(
                "station:front_clock", region, a1=(FRONT_PIER[0], fy0),
                a2=(court["b"], fy0), t=0.97, height_player_heights=5.6,
                offset_player_widths=0.04, picnum=CLOCK["tile"], x_repeat=72,
                y_repeat=72, cstat=16 | 64 | 128, shade=-8, type=0, status=0)
            report["front"] += 1
    #: the town's name where a passenger on the platform reads it: the
    #: hall's own north wall is open, so it hangs over the ramp's head
    words("GRAVESEND", hall.region_id, (hx1 - 512, hy1), (RAMP[2] + 256, hy1),
          "fascia", 2.2)
    words("TO THE QUAY", ROOMS["track_east"].region_id,
          (BED_X[2] + 1024, BED_Y[0]), (BED_X[3] - 1024, BED_Y[0]),
          "notice", 2.0)

    def board(name, tile, region, a1, a2, t, height, repeat=64):
        got = wallplane.sprite(
            layout, f"station:{name}", region.region_id, a1, a2, tile=tile,
            x_repeat=repeat, y_repeat=repeat, cstat=16 | 64 | 128, t=t,
            height_player_heights=height, offset_player_widths=0.04, shade=2)
        report["boards"] += bool(got)

    #: ...and inside: the avenue hall says what it is, the concourse when
    #: the trains go. (`wallplane` takes a wall's ends with the room on the
    #: right, +Y down: west to east on a north wall, north to south on an
    #: east wall.)
    if "east_hall" in ROOMS:
        eh = ROOMS["east_hall"]
        ex0, ey0, ex1, ey1 = EAST_HALL
        board("east_tickets", BOARDS["tickets"], eh, (ex0, ey1 - 512), (ex0, ey0 + 512),
              0.5, 1.9)
        board("east_arrivals", BOARDS["arrivals"], eh, (ex0 + 512, ey0),
              (EAST_STAIR[0] - 256, ey0), 0.5, 1.5, 80)
        # the owner's "lamp hanging on a chain" (641) from the hall's
        # ceiling, seated half its drawn height down (no hang point in its
        # art); not the wall lamp 2183, which reads as an eye from the street
        for index, local in enumerate(((0.25, 0.5), (0.75, 0.5))):
            layout.place_on_ceiling(
                f"station:east_hall_lamp_{index}", eh.region_id, local=local,
                height_player_heights=12288 / 16960, picnum=641, cstat=0,
                x_repeat=48, y_repeat=48, shade=-16, pal=0, type=0, status=0)
        cc = ROOMS["concourse"]
        cx0, cy0, cx1, cy1 = CONCOURSE
        board("concourse_clock", CLOCK["tile"], cc, (cx1, cy0 + 512), (cx1, cy1 - 512),
              0.5, 1.9, CLOCK["x_repeat"])
        board("concourse_arrivals", BOARDS["arrivals"], cc, (cx0 + 512, cy0),
              (cx1 - 512, cy0), 0.3, 1.5, 80)
        words("GRAVESEND STATION", cc.region_id, (cx0 + 512, cy0), (cx1 - 512, cy0),
              "fascia", 2.2)

    #: TICKETS over the booking window; arrivals and the clock where the
    #: stair arrives; the telephone and the bills along the east wall
    board("tickets", BOARDS["tickets"], hall, (hx0, OFFICE_WINDOW[3]),
          (hx0, OFFICE_WINDOW[1]), 0.5, 1.9)
    board("arrivals", BOARDS["arrivals"], hall, (RAMP[0] - 256, hy1),
          (hx0 + 512, hy1), 0.5, 1.5, 80)
    board("clock", CLOCK["tile"], hall, (hx1, hy1), (RAMP[2] + 256, hy1),
          0.15, 2.9, CLOCK["x_repeat"])
    board("telephone", BOARDS["telephone"], hall, (hx1, hy0 + 1024),
          (hx1, hy1 - 512), 0.92, 1.0)
    for index, tile in enumerate(POSTERS):
        board(f"poster_{index}", tile, hall, (hx1, hy0 + 1024),
              (hx1, hy1 - 512), 0.1 + 0.2 * index, 1.55, 88)

    #: lamps: lit ones in the wall over each pool of light, and on the
    #: office's wall; curtains drawn back in the carriage's windows
    report["lamps"] = report["curtains"] = 0
    for index, (x0, _y0, x1, _y1) in enumerate(POOLS):
        got = wallplane.sprite(
            layout, f"station:hall_lamp_{index}", hall.region_id,
            (x1 + 256, hy1), (x0 - 256, hy1), tile=WALL_LAMP, x_repeat=48,
            y_repeat=48, cstat=16 | 64 | 128, t=0.5,
            height_player_heights=2.1, offset_player_widths=0.04, shade=-8)
        report["lamps"] += bool(got)
    car = ROOMS["carriage"]
    cy_n, cy_s = CAR[1] + HULL, CAR[3] - HULL
    for side, y in (("n", cy_n), ("s", cy_s)):
        for k, (x0, x1) in enumerate(CAR_WINDOWS_X):
            for end, (a, b) in (("a", (x0 - 64, x0 + 448)),
                                ("b", (x1 - 448, x1 + 64))):
                try:
                    layout.place_on_wall(
                        f"station:curtain_{side}{k}{end}", car.region_id,
                        a1=(a, y) if side == "n" else (b, y),
                        a2=(b, y) if side == "n" else (a, y), t=0.5,
                        height_player_heights=0.92,
                        offset_player_widths=0.03, spans_opening=True,
                        type=0, picnum=CURTAIN, cstat=16 | 128,
                        x_repeat=56, y_repeat=28, shade=4, status=0)
                    report["curtains"] += 1
                except Exception:                           # noqa: BLE001
                    pass

    #: iron gates between the columns, with the rotor and two open bays
    edges = [hx0] + [x for c in COLUMNS for x in (c, c + 512)] + [hx1]
    bays = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    for index, (x0, x1) in enumerate(bays):
        if (x0, x1) == (FARE_ROTOR[0], FARE_ROTOR[2]) or index in (2, 3) or x1 - x0 < 768:
            continue
        layout.place_on_wall(
            f"station:gate_{index}", hall.region_id, a1=(x0, hy0),
            a2=(x1, hy0), t=0.5, height_player_heights=1.45,
            offset_player_widths=0.04, spans_opening=True, **GATE)
        report["gates"] += 1

    #: the locomotive's driving wheels, on the side the platform sees
    east = ROOMS["track_east"]
    #: ONE sprite: tile 2320 is three coupled wheels already, and three
    #: of them lay over each other (the sprite lint's overlapping pairs)
    #: ...and on the side it does not. The owner, in the game, having
    #: stepped down onto the track: "locomotive is missing wheels on the
    #: other side". One sprite to a side, each facing out.
    for k, (a1, a2) in enumerate((
            ((FRAME[0], FRAME[3]), (FRAME[2], FRAME[3])),
            ((FRAME[2], FRAME[1]), (FRAME[0], FRAME[1])))):
        for first, second in ((a1, a2), (a2, a1)):
            try:
                layout.place_on_wall(
                    f"station:wheels_{k}", east.region_id, a1=first,
                    a2=second, t=0.5, height_player_heights=0.61,
                    offset_player_widths=0.03, spans_opening=True, **WHEELS)
                report["wheels"] += 1
                break
            except Exception:                               # noqa: BLE001
                continue

    #: THE ROOF: solid floor-aligned sprites over the inside, at the
    #: walls' top (the walls' own tops are the roof's edge). Laid by
    #: `bloodmap.flatsprite.cover`, which knows where a flat sprite's
    #: rectangle really lies: the first roof was written by hand at angle
    #: 0, where a tile's width runs along the map's y, and every piece
    #: lay a quarter turn round -- 256 gaps along the car, 128 hanging
    #: over each wall (the owner, in the game: "sprite roof on carriage
    #: doesn't align").
    from bloodmap import flatsprite
    import wallplane as _art

    report["roof"] = 0
    car_room = ROOMS["carriage"]
    inner = (CAR[0] + HULL, CAR[1] + HULL, CAR[2] - HULL, CAR[3] - HULL)
    size = _art.art()[ROOF]
    for index, piece in enumerate(flatsprite.cover(
            inner, size[:2])):
        layout.place_on_floor(
            f"station:roof_{index}", car_room.region_id,
            local=((piece["x"] - inner[0]) / (inner[2] - inner[0]),
                   (piece["y"] - inner[1]) / (inner[3] - inner[1])),
            height_player_heights=CAR_H / BODY, type=0, picnum=ROOF,
            cstat=32 | 1 | 256, x_repeat=piece["x_repeat"],
            y_repeat=piece["y_repeat"], angle=piece["angle"], shade=20,
            status=0)
        report["roof"] += 1
    #: the locomotive's decals: a barred vent in each side of the cab, the
    #: horned face on the smokebox, smoke standing over the chimney
    report["engine"] = 0
    frame_room, chimney = ROOMS["loco_frame"], ROOMS["chimney"]
    for name, region, a1, a2, tile, height, repeat in (
            #: the cab's side has a WINDOW (E1M4's engine has a
            #: wood-framed opening there); blind, the cab's side was "an
            #: industrial rail loading bay"
            ("cab_window_s", east, (CAB[0], CAB[3]), (CAB[2], CAB[3]),
             CAB_WINDOW, 1.75, (48, 40)),
            ("cab_window_n", east, (CAB[2], CAB[1]), (CAB[0], CAB[1]),
             CAB_WINDOW, 1.75, (48, 40)),
            ("smokebox_face", frame_room, (BOILER[2], BOILER[3]),
             (BOILER[2], BOILER[1]), HORNED_FACE, 0.55, (48, 52))):
        for first, second in ((a1, a2), (a2, a1)):
            try:
                layout.place_on_wall(
                    f"station:{name}", region.region_id, a1=first, a2=second,
                    t=0.5, height_player_heights=height,
                    offset_player_widths=0.03, spans_opening=True, type=0,
                    #: the face stands PROUD of the smokebox and is seen
                    #: from behind as one walks past: two-sided (the owner:
                    #: "looks cool how it reaches outside, but because of
                    #: that it should be two sided")
                    picnum=tile,
                    cstat=(16 | 128) if tile == HORNED_FACE
                    else (16 | 64 | 128),
                    x_repeat=repeat[0],
                    y_repeat=repeat[1], shade=6, status=0)
                report["engine"] += 1
                break
            except Exception:                               # noqa: BLE001
                continue
    #: Both stand on the chimney's top, centred (cstat 128), as the campaign
    #: writes every one of its 31 thin smokes and 20 plumes: their art is
    #: offset by half its height to be drawn centred, and without the bit the
    #: renderer lifts them by that (`tools.sprite_fit` "lifted"); the plume
    #: was also stacked 0.9 bodies up, and the taller of the two rises over
    #: the thin one from the chimney anyway.
    for name, tile, repeat, lift in (("smoke_thin", SMOKE_THIN, (56, 40), 0.0),
                                     ("smoke_plume", SMOKE_PLUME, (48, 80), 0.0)):
        layout.place_on_floor(
            f"station:{name}", chimney.region_id, local=(0.5, 0.5),
            height_player_heights=lift, type=0, picnum=tile, cstat=2 | 128,
            x_repeat=repeat[0], y_repeat=repeat[1], shade=0, status=0)
        report["engine"] += 1
    #: and a bill on the carriage's side, as E1M3's wears JO-JO's
    try:
        layout.place_on_wall(
            "station:car_bill", ROOMS["shed"].region_id,
            a1=(CAR_WINDOWS_X[1][1] + 128, CAR[3]),
            a2=(CAR_DOOR_X[0] - 128, CAR[3]), t=0.5,
            height_player_heights=1.75, offset_player_widths=0.03,
            spans_opening=True, type=0, picnum=BILL, cstat=16 | 64 | 128,
            x_repeat=40, y_repeat=40, shade=4, status=0)
        report["engine"] += 1
    except Exception as error:                              # noqa: BLE001
        report["bill"] = str(error)[:80]

    #: the signal box: the gate's lever on its back wall, a balustrade
    #: along the balcony's edge (588, the turned wooden railing E1M2's
    #: carriage wears)
    box, balcony = ROOMS["signal_box"], ROOMS["signal_balcony"]
    mid = (SIGNAL_BOX[0] + SIGNAL_BOX[2]) // 2
    doorswitch.place(layout, "station:gate_lever", box.region_id,
                     ((mid + 512, SIGNAL_BOX[3]), (mid - 512, SIGNAL_BOX[3])),
                     GATE_CHANNEL)
    wires.wire("station:gate").when(wiring.placement("station:gate_lever"), "push")
    # The exit, as the campaign ends a level: a pushed switch wearing the
    # tile that says so, 42 of its 43 maps. It was first made a sector that
    # ends the level when walked into; shown beside the campaign's wiring
    # (`catalog map`), that shape occurs in it nowhere.
    from bloodmap.switches import exit_switch

    way_out = dict(exit_switch())
    layout.place_on_wall(
        "station:exit_switch", WAY_OUT["region"], a1=WAY_OUT["a1"],
        a2=WAY_OUT["a2"], t=0.85,
        height_player_heights=way_out.pop("height_player_heights"),
        offset_player_widths=0.06, status=0, **way_out)
    wires.wire("station:way-out").when(
        wiring.placement("station:exit_switch"), "push", command=1)
    report["rail"] = 0
    #: two lengths: the tile is 128 texels, 1,536 wide at this repeat
    #: (four of them lay over each other: the sprite lint's pairs)
    for k in range(2):
        x0 = BALCONY[0] + k * 1536
        layout.place_on_wall(
            f"station:balustrade_{k}", balcony.region_id,
            a1=(x0, BALCONY[1]), a2=(x0 + 1536, BALCONY[1]), t=0.5,
            height_player_heights=0.3, offset_player_widths=0.03,
            #: TWO-SIDED (no bit 64): the owner, in the game: "that
            #: balcony at station is not 2 sided sprite, so it is
            #: invisible from the other side ... Two sided wall sprite can
            #: be used for balcony railing"
            #: and SOLID (bit 1): "that balcony railing is not solid" --
            #: one walked through it and off the balcony
            spans_opening=True, type=0, picnum=BALUSTRADE,
            cstat=16 | 128 | 1, x_repeat=48, y_repeat=40, shade=6, status=0)
        report["rail"] += 1
    #: the waiting room: a clock on the far wall, a lit lamp
    wx0, wy0, wx1, wy1 = WAITING
    waiting = ROOMS["waiting_room"]
    for name, a1, a2, tile, height, repeat in (
            ("wait_clock", (wx1, wy0 + 768), (wx1, wy1 - 768), LONGCASE,
             0.75, 56),
            ("wait_lamp", (wx1, wy0 + 256), (wx1, wy0 + 1024), WALL_LAMP,
             1.6, 40),
            ("ticket_lamp", (hx0, OFFICE_WINDOW[1] - 896),
             (hx0, OFFICE_WINDOW[1] - 128), WALL_LAMP, 1.5, 40)):
        region = hall if name == "ticket_lamp" else waiting
        if name == "ticket_lamp":
            a1, a2 = a2, a1
        got = wallplane.sprite(
            layout, f"station:{name}", region.region_id, a1, a2, tile=tile,
            x_repeat=repeat, y_repeat=repeat, cstat=16 | 64 | 128, t=0.5,
            height_player_heights=height, offset_player_widths=0.04, shade=-4)
        report["boards"] += bool(got)

    #: the lever that opens the carriage, in the office
    #: round 3 and round 4's one blocker from the passenger: "the office
    #: lever opens a carriage door about 14 m away and out of sight ...
    #: pulling it appears to do nothing". It is on the column beside the
    #: door's bay now, facing the platform: lever and door in one look.
    lx = max(c for c in COLUMNS if c + 512 <= CAR_DOOR_X[0])
    doorswitch.place(layout, "station:car_lever", hall.region_id,
                     ((lx + 512, HALL[1] + 128), (lx, HALL[1] + 128)),
                     CAR_DOOR_CHANNEL)
    wires.wire("station:car-door").when(wiring.placement("station:car_lever"), "push")
    import props

    def free(room_name, local):
        region = layout.regions[ROOMS[room_name].region_id]
        return props.free_local(region, local)

    if attested is not None:
        for name, room_name, type_id, local in (
                ("clerk", "office", 203, (0.6, 0.35)),
                ("office_loot", "office", 67, (0.3, 0.8)),
                ("guard", "carriage", 202, (0.9, 0.7)),
                ("porter", "carriage", 203, (0.3, 0.75)),
                ("prize", "carriage", 109, (0.97, 0.75)),
                ("loiterer", "hall", 202, (0.7, 0.4)),
                ("waiter", "waiting_room", 203, (0.7, 0.5)),
                ("signalman", "signal_box", 202, (0.75, 0.6)),
                ("store_guard_0", "goods_store", 202, (0.45, 0.3)),
                ("store_guard_1", "goods_store", 203, (0.5, 0.75)),
                ("store_prize", "goods_store", 109, (0.6, 0.5)),
                ("store_loot", "goods_store", 67, (0.3, 0.15))):
            spec = attested(type_id)
            where = free(room_name, local)
            if spec is not None and where is not None:
                layout.place_on_floor(f"station:{name}",
                                      ROOMS[room_name].region_id,
                                      local=where, **spec["fields"])
                report["folk"] += 1
    # SIGNS OF USE. Round 2: "no signs of use: no bodies, debris or
    # litter", "the halls have almost no props". What a harbour town's
    # station has lying about: sacks and barrels for the quay, somebody's
    # paper, somebody dead, and a drink on the carriage's tables.
    report["things"] = 0
    cx0, cy0 = CAR[0] + HULL, CAR[1] + HULL
    cw, cd = CAR[2] - CAR[0] - 2 * HULL, CAR[3] - CAR[1] - 2 * HULL
    for index, (x0, y0, x1, y1) in enumerate(SEATS):
        where = free("carriage", (((x0 + x1) / 2 - cx0) / cw,
                                  ((y0 + y1) / 2 - cy0) / cd))
        if where is not None:
            #: The chair is a VOXEL in the game and has a facing; my
            #: renderer draws its flat sprite, so a frame shows neither
            #: its facing nor quite its bulk (the owner, 2026-11-18, when
            #: I called these "far too big" from a frame: "maybe little
            #: bigger"). They are at Blood's own repeat, 40 (12 of the
            #: campaign's 24; the rest 48): 1.06 bodies to the top of the
            #: back. Each pair is turned to face its table across it.
            table = min(TABLES, key=lambda r: abs((r[0] + r[2]) / 2
                                                  - (x0 + x1) / 2))
            faces_east = (x0 + x1) / 2 < (table[0] + table[2]) / 2
            props.stand_on_floor(layout, f"station:chair_{index}",
                                 ROOMS["carriage"].region_id, local=where,
                                 tile=CHAIR, angle=0 if faces_east else 1024)
            report["things"] += 1
    for name, room_name, tile, local in (
            ("sack_0", "platform_2", 822, (0.12, 0.25)),
            ("sack_1", "platform_2", 822, (0.2, 0.3)),
            ("sack_2", "platform_5", 822, (0.3, 0.3)),
            ("barrel_0", "platform_1", 925, (0.3, 0.3)),
            ("barrel_1", "platform_5", 925, (0.55, 0.25)),
            ("barrel_2", "platform_0", 925, (0.5, 0.3)),
            ("barrel_3", "platform_7", 925, (0.25, 0.75)),
            ("sack_3", "platform_7", 822, (0.32, 0.8)),
            ("sack_4", "platform_7", 822, (0.8, 0.7)),
            ("dead_0", "hall", 2333, (0.55, 0.7)),
            ("dead_1", "platform_4", 2334, (0.5, 0.6)),
            ("lantern_0", "office", 693, (0.8, 0.5)),
            ("bottle_0", "carriage_table_0", 759, (0.4, 0.5)),
            ("bottle_1", "carriage_table_0", 606, (0.65, 0.4)),
            ("bottle_2", "carriage_table_1", 605, (0.5, 0.5)),
            ("wait_chair_0", "waiting_room", CHAIR, (0.36, 0.5)),
            ("wait_chair_1", "waiting_room", CHAIR, (0.7, 0.5)),
            ("wait_bottle", "wait_table", 759, (0.5, 0.5)),
            ("store_barrel_0", "goods_store", 925, (0.3, 0.85)),
            ("store_barrel_1", "goods_store", 925, (0.38, 0.9)),
            ("store_sack_0", "goods_store", 822, (0.2, 0.8)),
            ("store_sack_1", "goods_store", 822, (0.7, 0.2)),
            ("box_lantern", "signal_box", 693, (0.2, 0.7))):
        where = free(room_name, local)
        if where is None:
            continue
        try:
            props.stand_on_floor(layout, f"station:{name}",
                                 ROOMS[room_name].region_id, local=where,
                                 tile=tile)
            report["things"] += 1
        except Exception:                                   # noqa: BLE001
            pass
    return report


#: what the carriage's walls wear is DRAWN TO FIT -- a door one tile wide,
#: a livery whose bands must run level through door and windows -- and the
#: city's texture-framing pass, which gives every wall the campaign's texel
#: density, would redraw it (the first sector-built door came out as four
#: narrow doors side by side). `dress` notes each such record and `keep`
#: puts it back after the framing.
KEPT: dict = {}
FRAME_FIELDS = ("picnum", "x_repeat", "y_repeat", "x_panning", "y_panning",
                "cstat", "shade")


def keep(level) -> int:
    for wall_id, fields in KEPT.items():
        wall = level.walls[wall_id]
        (wall.get("fields", wall) if isinstance(wall, dict)
         else wall.fields).update(fields)
    return len(KEPT)


#: THE FRONT (second version, the owner's word on the first, 2026-11-20:
#: "Train station facade looks bad, there are building textures with
#: windows and they are even cutoff ... maybe you can even do some arcs").
#: The windows were the bands over the two doors: a roofed doorway opening
#: onto a street draws the wall over it from its head to the STREET'S sky,
#: in the street's own facade tile (Theatre Row's 400, the foundry's 393),
#: a slab of windows standing over a front of 6.8 bodies. A sector cannot
#: wear another tile above a door; the band only reaches the sky of the
#: sector in front of it. So the station has a FORECOURT: an open sector
#: across the avenue's mouth whose sky stands at the front's height, and
#: the front is the forecourt's far wall, one plane of stone. The doors are
#: ARCHES, as E1M2's station entrance (s207 into s103) is a pointed one: two
#: half-sectors whose ceilings slope from the spring to the apex, so the
#: stone over each arch is the front's own and draws an arch.
#:
#: The forecourt is two rooms, one in each district the mouth crosses,
#: joined at the seam (x 36,352).
FORECOURT = ((32768, 36352), (36352, 39936))
FORECOURT_D = 3072
#: the front's height: the forecourt's sky (6.8 bodies; the end walls stand
#: 5.8, E3M1 s0/s343), out of a body's reach as a lower sky must be
FRONT_H = 114688
#: the arches: (x0, x1) each, 2,048 wide; spring 2.4 bodies (a public
#: door's head), apex 4.2; as deep as a jamb is thick
ARCHES = ((33280, 35328), (37376, 39424))
ARCH_SPRING, ARCH_APEX, ARCH_D = 40960, 71680, 1536
#: the stone the front is: the owner's "grey ashlar stone blocks" (427), the
#: pier between the arches his "grey stone wall with meander ornament"
#: (409), the arches' soffits his "dressed/worked stone" (253)
FRONT_PIER = (35328, 37376)
PIER_STONE, SOFFIT = 409, 253
#: what `furnish` reads to letter and light the front
AVENUE_FRONT: dict = {}


def avenue_front(city, streets, district_of, district_bounds, gates, *,
                 grade: int, street_sky: int, sky_tile: int) -> dict:
    """The station's forecourt and arched front across the avenue's mouth.

    The forecourt rooms stand on the city's edge in the districts the mouth
    crosses (as `streets.end_walls` builds its masses), each joined to its
    street by a gate along y 0 whose ends are made vertices of the street's
    outline. Their sky is the front's height, so every band over an arch
    ends at the front's top.
    """
    from bloodmap.levelprog import _compass_edges
    import streets as street_anatomy

    hall = ROOMS["east_hall"]
    fy0 = -FORECOURT_D
    courts = []
    for index, (a, b) in enumerate(FORECOURT):
        district = next(d for d, bounds in district_bounds.items()
                        if streets.get(d) is not None and bounds[1] == 0
                        and bounds[0] <= a and b <= bounds[2])
        owner = district_of[district]
        court = owner.room(
            f"station_forecourt_{index}",
            [(0, 0), (b - a, 0), (b - a, FORECOURT_D), (0, FORECOURT_D)],
            role="exterior", faces=dict(COMPASS), frame=Frame(a, fy0),
            note="the station forecourt: its sky is the front's top",
            intent={"kind": "station_front", "street": "the_avenue"})
        court.surfaces(floor_z=grade, clear_height=FRONT_H, floor_picnum=FLOOR,
                       wall_picnum=FRONT_STONE, ceiling_picnum=int(sky_tile),
                       parallax_ceiling=True, floor_shade=10, wall_shade=10)
        street = streets[district]
        origin = (int(district_bounds[district][0]), int(district_bounds[district][1]))
        street.outline = street_anatomy._with_vertices(
            street.outline, [(a - origin[0], -origin[1]), (b - origin[0], -origin[1])])
        street.faces = {**{k: v for k, v in street.faces.items()
                           if k in street._hole_faces},
                        **_compass_edges(street.outline)}
        gates.append((f"connection:station_forecourt_{index}_mouth",
                      court.region_id, street.region_id, (a, 0), (b, 0), 0))
        courts.append((court, owner, district, street, a, b))
        AVENUE_FRONT.setdefault("courts", []).append(
            {"region": court.region_id, "street": street.region_id, "a": a, "b": b})
    city.connect(courts[1][0].face("west"), courts[0][0].face("east"),
                 connection_id="connection:station_forecourt_seam")

    arches = 0
    for index, (a, b) in enumerate(ARCHES):
        court, owner = next((c, o) for c, o, _d, _s, ca, cb in courts if ca <= a and b <= cb)
        mid = (a + b) // 2
        halves = []
        for side, (x0, x1) in enumerate(((a, mid), (mid, b))):
            half = owner.room(
                f"station_arch_{index}_{side}",
                [(0, 0), (x1 - x0, 0), (x1 - x0, ARCH_D), (0, ARCH_D)],
                role="gateway", faces=dict(COMPASS),
                frame=Frame(x0, fy0 - ARCH_D),
                note="half of a pointed arch: its ceiling rises to the apex",
                region_kwargs={"ceiling_slope": SlopeSpec(
                    # each half pivots on its OUTER jamb (the sector's first
                    # wall) and rises to the apex over the arch's middle
                    hinge=(((x0, fy0), (x0, fy0 - ARCH_D)) if side == 0
                           else ((x1, fy0 - ARCH_D), (x1, fy0))),
                    rise_z=-(ARCH_APEX - ARCH_SPRING))},
                intent={"kind": "station_front", "street": "the_avenue"})
            half.surfaces(floor_z=grade, clear_height=ARCH_SPRING,
                          parallax_ceiling=False, floor_picnum=FLOOR,
                          wall_picnum=FRONT_STONE, ceiling_picnum=SOFFIT,
                          floor_shade=-6, ceiling_shade=-4, wall_shade=-2)
            half.light_source(f"arch_lamp_{index}_{side}", local=(0.5, 0.5),
                              height_player_heights=1.8)
            city.connect(half.face("south"), court.face("north"),
                         connection_id=f"connection:station_arch_{index}_{side}_out")
            city.connect(half.face("north"), hall.face("south"),
                         connection_id=f"connection:station_arch_{index}_{side}_in")
            halves.append(half)
        city.connect(halves[1].face("west"), halves[0].face("east"),
                     connection_id=f"connection:station_arch_{index}_crown")
        # Round 15: "the archways look like dark recesses ... light the
        # arch from within so a warm pool spills onto the cobbles". The
        # passages are lit (above) and a pool of lit floor lies before each
        # arch: a flush sector of its own, the forecourt being one sector
        # and one shade (`lightpools`' reason).
        import setpieces
        from materials import INTERIORS
        pool = setpieces.raised_solid(
            owner, f"station_arch_{index}_pool", court,
            (a - 256, fy0 + 256, b + 256, fy0 + 2048), INTERIORS["common"],
            grade=grade, rise=0, host_clear=FRONT_H, connector=owner,
            note="the light the arch spills onto the forecourt")
        pool.surfaces(floor_picnum=FLOOR, floor_shade=0, ceiling_picnum=int(sky_tile),
                      parallax_ceiling=True, clear_height=FRONT_H)
        arches += 1
    return {"forecourt": len(courts), "arches": arches}


def front_stone(level) -> int:
    """The pier between the arches wears the owner's meander-ornament stone.

    A room has one wall tile; the forecourt's far wall is the front, and
    the stretch of it between the arches is the pier. Kept (`KEPT`) so the
    texture-framing pass does not repaint it.
    """
    count = 0
    for w_id, wall in enumerate(level.walls):
        w = wall.get("fields", wall) if isinstance(wall, dict) else wall.fields
        n = level.walls[int(w["point2"])]
        n = n.get("fields", n) if isinstance(n, dict) else n.fields
        if (int(w["y"]) == int(n["y"]) == -FORECOURT_D and int(w["next_sector"]) < 0
                and FRONT_PIER[0] <= min(int(w["x"]), int(n["x"]))
                and max(int(w["x"]), int(n["x"])) <= FRONT_PIER[1]):
            w["picnum"] = PIER_STONE
            KEPT[w_id] = {k: w[k] for k in FRAME_FIELDS}
            count += 1
    return count


def dress(level, compiled) -> dict:
    """Faces, columns, sleepers, glass and bars, and the platform's edge."""
    from bloodmap import glass

    def f(item):
        return item.get("fields", item) if isinstance(item, dict) else item.fields

    def sectors(regions):
        return {compiled.allocations[r].sector_id for r in regions
                if r in compiled.allocations}

    report = {"columns": 0, "edge": 0, "track": 0, "openings": 0}
    for wall in level.walls:
        w = f(wall)
        if int(w["next_sector"]) >= 0:
            continue
        n = f(level.walls[int(w["point2"])])
        for x0, y0, x1, y1 in COLUMN_BOXES:
            if (x0 <= int(w["x"]) <= x1 and y0 <= int(w["y"]) <= y1
                    and x0 <= int(n["x"]) <= x1 and y0 <= int(n["y"]) <= y1):
                w["picnum"], w["x_repeat"], w["y_repeat"] = COLUMN, 4, 8
                w["shade"] = 26
                report["columns"] += 1
    tracks, edge, openings = sectors(TRACKS), sectors(EDGE), sectors(OPENINGS)
    #: The door pass splits the doorway into a thin type-600 leaf with a
    #: reveal either side, so the leaf is found by type and place, and the
    #: door's FACE is the reveals' wall toward it.
    leaf = set()
    for index, sector in enumerate(level.sectors):
        s = f(sector)
        if int(s.get("type", 0)) != 600:
            continue
        first = f(level.walls[int(s["wall_ptr"])])
        if (CAR_DOOR_X[0] <= int(first["x"]) <= CAR_DOOR_X[1]
                and CAR[1] <= int(first["y"]) <= CAR[3]):
            leaf.add(index)
    solid, opening = sectors(HULL_SOLID), sectors(HULL_OPEN)
    inside_car = sectors([ROOMS["carriage"].region_id])
    report["hull"] = 0
    gate_leaf = set()
    for index, sector in enumerate(level.sectors):
        s = f(sector)
        if int(s.get("type", 0)) != 600:
            continue
        first = f(level.walls[int(s["wall_ptr"])])
        if GATE_X[0] <= int(first["x"]) <= GATE_X[1]:
            gate_leaf.add(index)
    bores = sectors([made.region_id for name, made in ROOMS.items()
                     if name.startswith("tunnel_")])
    #: the pools are lit; nothing else in the hall is
    for name, made in ROOMS.items():
        if name.startswith("pool_") and made.region_id in compiled.allocations:
            s = f(level.sectors[compiled.allocations[made.region_id].sector_id])
            s["floor_shade"], s["ceiling_shade"] = -2, 30
    for index, sector in enumerate(level.sectors):
        s = f(sector)
        if index in tracks:
            #: THE RAILS RUN ALONG THE TRAIN. The owner, on the second
            #: version: "You didn't spot that rails are going 90 degrees
            #: from train than they should really go?" I had copied E1M2
            #: s34's `floor_stat` 4 (x and y swapped) without asking which
            #: way ITS track runs: north-south, 61,952 long. Tile 1129's
            #: rails run along the tile's x, so E1M2 must swap and a track
            #: that runs east-west, as this one does, must NOT. Neither I
            #: nor three readers over two rounds named it.
            s["floor_stat"] = int(s["floor_stat"]) & ~4
            s["floor_x_panning"] = s["floor_y_panning"] = 0
            report["track"] += 1
        for w_id in range(int(s["wall_ptr"]),
                          int(s["wall_ptr"]) + int(s["wall_count"])):
            w = f(level.walls[w_id])
            other = int(w["next_sector"])
            #: nobody steps off the platform's edge (the ramp at its west
            #: end is the way down); the carriage's bay is left open
            #: (The platform's edge was blocked, with a ramp at its west
            #: end for the way down. The owner, in the game: "I would also
            #: remove that invisible wall to be able to get into railway."
            #: It is open: one steps off the platform onto the track.)
            if (index in tracks and other in edge) or (index in edge
                                                       and other in tracks):
                w["cstat"] = int(w["cstat"]) & ~1
                report["edge"] += 1
            if index in tracks and other in bores and index not in bores:
                #: the tunnel's mouth is a hole in a LIT wall (rounds 2
                #: and 3: "the track ends in a black void under a red sky")
                w["picnum"], w["shade"] = FAR_WALL, 8
            if other in leaf and index not in leaf:
                #: THE DOOR. A two-sided wall's tile is its upper band,
                #: hung from the leaf's ceiling: the door rises with it.
                w["picnum"], w["x_repeat"] = CAR_DOOR_TILE, 8
                w["y_repeat"] = round(8 * 32768 / (CAR_TOP - PLATFORM_DROP))
                w["x_panning"], w["y_panning"] = 0, 0
                w["cstat"] = int(w["cstat"]) & ~4
                w["shade"] = 4
                report["door"] = report.get("door", 0) + 1
                KEPT[w_id] = {k: w[k] for k in FRAME_FIELDS}
            if other in solid | opening and index not in leaf:
                n = f(level.walls[int(w["point2"])])
                length = (abs(int(n["x"]) - int(w["x"]))
                          + abs(int(n["y"]) - int(w["y"])))
                if index in inside_car | solid | opening:
                    #: seen from inside: the lining
                    w["picnum"], w["shade"] = CAR_LINING, 0
                    w["x_repeat"] = max(1, min(255, round(length / 128)))
                    w["y_repeat"] = 8
                else:
                    #: seen from outside: the livery, its 256 texels over
                    #: the car's height, its top at the roof. A step's
                    #: wall hangs from the NEXT sector's floor, so under
                    #: a window (whose floor is the sill) the tile is
                    #: panned down by what stands between sill and roof.
                    w["picnum"], w["shade"] = LIVERY, 10
                    w["x_repeat"] = max(1, min(255, round(length / 128)))
                    w["y_repeat"] = round(2048 * 256 / CAR_TOP)
                    w["x_panning"] = 0
                    w["y_panning"] = 0 if other in solid else round(
                        256 * (CAR_H - WINDOW_SILL) / CAR_TOP) % 256
                w["cstat"] = int(w["cstat"]) & ~4
                report["hull"] += 1
                KEPT[w_id] = {k: w[k] for k in FRAME_FIELDS}
            if other in gate_leaf and index not in gate_leaf:
                n = f(level.walls[int(w["point2"])])
                length = (abs(int(n["x"]) - int(w["x"]))
                          + abs(int(n["y"]) - int(w["y"])))
                w["picnum"] = ROLLUP
                w["x_repeat"] = max(1, min(255, round(length / 128)))
                w["y_repeat"], w["x_panning"], w["y_panning"] = 8, 0, 0
                w["cstat"] = int(w["cstat"]) & ~4
                w["shade"] = 6
                report["gate"] = report.get("gate", 0) + 1
            if index in tracks and other in openings:
                #: the wall over and under a window is the carriage's side:
                #: the livery, hung from the shed's roof like the solid
                #: stretches beside it
                n = f(level.walls[int(w["point2"])])
                length = (abs(int(n["x"]) - int(w["x"]))
                          + abs(int(n["y"]) - int(w["y"])))
                w["picnum"] = LIVERY
                w["x_repeat"] = max(1, min(255, round(length / 128)))
                #: the same scale the solid stretches wear (`storeys` 1:
                #: the tile's 256 texels over the car's height), hung from
                #: the same roof
                w["y_repeat"] = round(2048 * 256 / CAR_TOP)
                w["x_panning"], w["y_panning"] = 0, 0
                #: bit 4 on a TWO-sided wall pegs both its bands to this
                #: sector's ceiling -- where the solid stretches, which
                #: are one-sided and unpegged, already hang from. (Without
                #: it the band under a window started again at the sill:
                #: green where the skirt should be.)
                w["cstat"] = int(w["cstat"]) | 4
                w["shade"] = 10
                report["openings"] += 1
    for sector in level.sectors:
        s = f(sector)
        #: the carriage door's reveals took the shed's floor: sleepers on
        #: a doorstep
        if (int(s["floor_picnum"]) == TRACK
                and int(s["floor_z"]) != BED_Z):
            s["floor_picnum"] = WOOD
            s["floor_stat"] = int(s["floor_stat"]) & ~4
            s["floor_y_panning"] = 0
    report["glass"] = glass.glaze(level, PANES, fit=True)["panes"]
    report["bars"] = len(glass.grille(level, GRILLES, tile=BARS)["barred"])
    report["front_pier"] = front_stone(level)
    return report
