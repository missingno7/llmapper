"""Build the Phantom Terminus, its train and the pump landing's concealed approach."""

from itertools import pairwise

from bloodmap import mechanism, motion, wiring
from bloodmap.levelprog import RECT_FACES, Style
from bloodmap.model import record_fields
from bloodmap.player_space import PLAYER_PROFILES

import carriage
import setpieces
import wallplane
import wires
from materials import SEWER, Material
from resolution import SEWER_FLOOR

COMPASS = dict(zip(RECT_FACES, range(4)))
BODY = PLAYER_PROFILES["blood"]
GHOST_FLOOR = 118784
GHOST_STEPS = 28
GHOST_TREAD = 320
GHOST_CLEAR = 32768
GHOST_DIALS = (("A", 49664, 1), ("B", 50176, 3), ("C", 50688, 2))

#: the platform's edge and the carriage's deck are one level; the rails lie 0.36 of a body under it
DECK = GHOST_FLOOR + 768
TRACK = (46592, -17152, 70656, -12544)
#: past the platform's end the bore widens, so nothing scrapes a rider off the running board
PASSING = (58624, 60032, -12160)
TRACK_FLOOR = DECK + 6144
TRACK_ROOF = DECK - carriage.TOP
#: five windows along the saloon, the second of them the open door, then the driver's cab
COACH_PLAN = carriage.Plan(128, ((8, 24), (27, 43), (46, 62), (65, 81), (84, 100)), door=1, cab=17,
                           broken=frozenset({"north_window_3", "south_window_3"}))
COACH = carriage.Axes((48640, -12608 - 64 * carriage.WIDTH))
CAR = (*COACH(0, 0), *COACH(COACH_PLAN.length, carriage.WIDTH))
TRAVEL = 11264
DEPART = "phantom:departure"
RUN = "phantom:car"
DOOR = tuple(COACH(u, 0)[0] for u in COACH_PLAN.slots[COACH_PLAN.door])
GREEN = 4
PRIZE = "phantom:prize"
STATION = "region:gravesend/sewer/ghost_station"
PRIZE_REGION = f"{STATION}/track_coach:north_seat_1"
ARM = "phantom:arm"
COACH_STATE = "phantom:coach-state"
CAR_LIGHT = "phantom:car-light"
PLATFORM_ENTRY = "phantom:first-platform"
SEAT_Z = DECK - carriage.SEAT
#: the one empty seat, facing the open door: it is seen from the platform
PRIZE_AT = COACH((COACH_PLAN.slots[1][0] + COACH_PLAN.slots[1][1]) / 2, 9)
SEATED = (2330, 2333, 2334)
PANEL_MASK = 255
BLOCK = 1 | 16 | 64


def build(sewer, silt_trap):
    """Keep the maintenance entrance and build the railway below it."""
    part = sewer.assembly("ghost_station", style=Style(layer="ghost_station"),
                          note="Phantom Terminus under the pump landing")
    clear = 20480
    # The narrow lips at either end screen the extended pocket. The plug is
    # saved inside that pocket, the ON pose used to initialise a type 616.
    housing = part.room(
        "hatch", [(47808, 1024), (49088, 1024), (49088, 1152), (50944, 1152),
                  (50944, 1920), (49088, 1920), (49088, 2048), (47808, 2048),
                  (47808, 1920), (47616, 1920), (47616, 1152), (47808, 1152)],
        faces={"north": 0, "south": 6}, role="gateway",
        style=Style(**SEWER.style_kwargs(floor_z=SEWER_FLOOR, clear_height=clear)),
        note="the pump hatch's fixed reveal and sideways pocket")
    part.connect(housing.face("south"), silt_trap.face("north"),
                 connection_id="connection:ghost_hatch")
    housing.raw("a whole service panel slides into the blind pocket", _ghost_hatch)

    plate = _room(part, "inspection_plate", (51200, 2368, 51328, 4672), IRON,
                 SEWER_FLOOR - 6400, 11776, role="detail",
                 declared_zero_exit=True)
    part.connect(plate.face("west"), silt_trap.face("east"),
                 connection_id="connection:ghost_inspection_plate",
                 role="window", min_opening=1024)

    foot = 1024 - GHOST_STEPS * GHOST_TREAD

    booking = _station_rooms(part, foot)
    housing.staircase(
        "ghost_service_stair", "north", total_rise=GHOST_FLOOR - SEWER_FLOOR,
        tread=GHOST_TREAD, step_rise=2048, clear_height=24576,
        arrive_at=booking.region_id, shade_ramp=(22, 31))

    plate.raw("the last inspection's settings", _ghost_inspection)
    silt_trap.raw("the lower landing's three maintenance dials", _ghost_controls)


def _ghost_hatch(layout, housing):
    """A four-wall type-616 plug moves bodily within the fixed hatch surround."""
    from bloodmap import motion, wiring
    import wires

    host = housing.region_id
    panel = f"{host}:panel"
    travel = 1600
    outline = [(49280, 1280), (50816, 1280), (50816, 1792), (49280, 1792)]
    layout.carve_hole(host, outline)
    roof = layout.regions[host].ceiling_z
    layout.add_region(
        panel, outline, role="detail", layer="ghost_station", type=616,
        ceiling_z=roof - 4096, floor_z=roof, wall_picnum=490,
        floor_picnum=255, ceiling_picnum=255, declared_zero_exit=True,
        intent={"kind": "machine"},
        sector_behavior={"state": 0, "busy_time_a": 15})
    for index, a in enumerate(outline):
        layout.add_connection(
            f"connection:ghost_panel_{index}", panel, host,
            a1=a, a2=outline[(index + 1) % len(outline)], role="doorway",
            gated=True, face_picnum=490)
    on = (50048, 1536)
    motion.place_markers(layout, "ghost_hatch", driven_region=panel,
                         off_at=(on[0] - travel, on[1]), on_at=on,
                         off_region=host, z=roof)
    layout.declare_motion(panel, [host])
    wires.wire("ghost:hatch-open").then(wiring.region(panel))


def _ghost_controls(layout, landing):
    """Report both match edges to a tally, then latch its first ON signal."""
    from bloodmap import motion, wiring
    from bloodmap.placement import drawn_extent
    import l3_foundry
    import wallplane
    import wires

    region = landing.region_id
    matches = wires.wire("ghost:dial-matches")
    done = wires.wire("ghost:all-matched")
    opened = wires.wire("ghost:hatch-open")
    dial = l3_foundry._attested("E3M2", 22, 1161)
    width, height, _, offset = wallplane.art()[1161]
    fields = {**dial["fields"], "x_repeat": 48, "y_repeat": 48}
    top, bottom = drawn_extent(height, offset, fields["y_repeat"], fields["cstat"])
    for letter, x, setting in GHOST_DIALS:
        name = layout.add_sprite(
            f"ghost:dial_{letter}", region,
            x=x, y=2080, z=SEWER_FLOOR - 12800 - (top + bottom) // 2,
            angle=512, shade=-8, **fields,
            behavior={"data_1": 0, "data_2": setting, "data_3": 4,
                      "data_4": 203})  # E3M2 sprite 669: the dial click
        matches.when(wiring.placement(name), "push", command=motion.CMD_STATE,
                     on=True, off=True)
        half = width * fields["x_repeat"] // 8 + 64
        wallplane.text(layout, f"ghost:label_{letter}", region,
                       (x - half, 2048), (x + half, 2048), words=letter,
                       height_player_heights=1.08, size=48, required=True)

    tally = layout.add_sprite(
        "ghost:tally", region, x=48448, y=2240, z=SEWER_FLOOR - 12800,
        **{**l3_foundry._attested("E1M1", 22, 0)["fields"], "cstat": 32896},
        behavior={"data_1": 0, "data_2": len(GHOST_DIALS)})
    matches.then(wiring.placement(tally))
    done.when(wiring.placement(tally), "relay", command=motion.CMD_ON)

    # An RX message bypasses a sprite's Trigger Once flag. A toggle switch
    # operated by explicit ON instead reports only its first state change.
    latch = layout.add_sprite(
        "ghost:latch", region, x=48448, y=2272, z=SEWER_FLOOR - 12800,
        **{**l3_foundry._attested("E1M1", 20, 0)["fields"], "cstat": 32896})
    done.then(wiring.placement(latch))
    opened.when(wiring.placement(latch), "relay", command=motion.CMD_ON)
    sound = layout.add_sprite(
        "ghost:latch_sound", region, x=48448, y=2304, z=SEWER_FLOOR - 12800,
        **l3_foundry._attested("E1M1", 708)["fields"], behavior={"data_2": 360})  # PADLOCK
    opened.then(wiring.placement(sound))


def _ghost_inspection(layout, plate):
    """Write the settings as one-based positions, in panel order."""
    import wallplane

    a, b = (51328, 2368), (51328, 4672)
    wallplane.text(layout, "ghost:inspection", plate.region_id, a, b,
                   words="INSPECTION", size=64, palette="rust", shade=-8,
                   height_player_heights=0.50, required=True)
    for index, (letter, _, value) in enumerate(GHOST_DIALS):
        start = (a[0], a[1] + index * 768)
        end = (a[0], start[1] + 768)
        marks = ("I", "II", "III", "IV")[value]
        wallplane.text(layout, f"ghost:setting_{letter}", plate.region_id,
                       start, end, words=f"{letter} {marks}", size=45,
                       height_player_heights=0.24, required=True)



# DWE3M2 s481/s246: pale banded cement, large floor slabs, rusted edges.
HALL = Material(369, 374, 379, 386)
IRON = Material(248, 255, 255, 248)
EDGE = Material(386, 386, 211, 386)
BORE = Material(421, 1129, 211, 386)
SERVICE = Material(421, 379, 358, 248)
TIMBER = Material(67, 67, 379, 67)
BRICK = Material(383, 383, 358, 383)
WATER = Material(275, 2915, 275, 386)
#: the flood lies a step under the rails
WATER_FLOOR = TRACK_FLOOR + 3584
SOUTH_EDGE = -12544
EDGE_BACK = -11904
PLATFORM_BACK = -10496
PLATFORM_LEFT, PLATFORM_RIGHT = 46848, 58624
EDGE_LEFT = 47360
BOOKING = (46592, -9984, 52224, -7936)
PLATFORM = (PLATFORM_LEFT, EDGE_BACK, PLATFORM_RIGHT, PLATFORM_BACK)
BAY_CLEAR = 24576
WATCHERS = (57984, 60928, 63872, 66816)
WATCH_FLOOR = DECK + 1024


def _room(part, name, rect, material, floor=GHOST_FLOOR, clear=GHOST_CLEAR,
          *, role="interior", shades=(29, 26, 36), **region):
    x0, y0, x1, y1 = rect
    flat, wall, ceiling = shades
    return part.room(
        name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        faces=COMPASS, role=role,
        style=Style(**material.style_kwargs(
            floor_z=floor, clear_height=clear, floor_shade=flat,
            wall_shade=wall, ceiling_shade=ceiling)),
        region_kwargs={**material.region_kwargs(), **region},
        intent={"kind": "furnished"})


def _connect(part, small, side, big, face, *, skin=None, clear=BODY.standing_height):
    return part.connect(small.face(side), big.face(face),
                        connection_id=f"connection:{small.node_id}:{side}:{big.node_id}",
                        min_opening=clear, min_width=BODY.body_width, face_picnum=skin)


def _station_rooms(part, foot):
    booking = _room(part, "booking", (*BOOKING[:3], foot), HALL,
                    clear=28672, role="secret", secret=True, shades=(42, 34, 44))
    platform = _room(part, "platform", PLATFORM, HALL, shades=(50, 47, 51))
    edge = _room(part, "edge", (EDGE_LEFT, SOUTH_EDGE, PLATFORM_RIGHT, EDGE_BACK),
                 EDGE, DECK, clear=GHOST_CLEAR + 768, shades=(45, 35, 49))
    x0, y0, x1, y1 = TRACK
    p0, p1, deep = PASSING
    track = part.room(
        "track", [(x0, y0), (x1, y0), (x1, y1), (p1, y1), (p1, deep), (p0, deep), (p0, y1), (x0, y1)],
        faces={"north": 0, "east": 1, "south": 2, "passing_east": 3, "passing_west": 5, "south_west": 6, "west": 7}, role="interior",
        style=Style(**BORE.style_kwargs(floor_z=TRACK_FLOOR, clear_height=TRACK_FLOOR - TRACK_ROOF,
                                        floor_shade=41, wall_shade=40, ceiling_shade=42)),
        region_kwargs=BORE.region_kwargs(), intent={"kind": "furnished"})
    _connect(part, edge, "east", track, "passing_west", skin=205)
    # two steps at the platform's west end: whoever falls on the rails walks out
    last = edge
    for index, (a, b) in enumerate(((46976, EDGE_LEFT), (46592, 46976))):
        step = _room(part, f"pit_step_{index}", (a, SOUTH_EDGE, b, EDGE_BACK), EDGE,
                     DECK + 2048 * (index + 1), GHOST_CLEAR + 768 + 2048 * (index + 1), shades=(40, 35, 45))
        _connect(part, step, "east", last, "west", skin=205)
        _connect(part, step, "north", track, "south_west", skin=205)
        _connect(part, step, "south", platform, "north", skin=386)
        last = step
    _connect(part, edge, "south", platform, "north", skin=386)
    _connect(part, edge, "north", track, "south_west", skin=205)
    _booking_hall(part, booking, platform)
    _platform_rooms(part, platform, edge)
    stop = _service_line(part, platform, track)
    _drowned_siding(part, track)
    track.raw("the last car and its pickup circuit",
              lambda layout, room: _run_car(layout, room, platform, stop))
    platform.raw("the first distant whistle", _platform_entry)
    return booking


def _booking_hall(part, booking, platform):
    gate = _room(part, "gate_open", (49280, PLATFORM_BACK, 50688, BOOKING[1]),
                 EDGE, clear=BAY_CLEAR, shades=(28, 26, 35))
    _connect(part, gate, "north", platform, "south", skin=386)
    _connect(part, gate, "south", booking, "north", skin=386)
    for name, a, b in (("west", 47616, 49152), ("east", 50816, 51968)):
        middle = -10240
        front = _room(part, f"gate_{name}_front", (a, middle, b, BOOKING[1]),
                      EDGE, clear=BAY_CLEAR, shades=(33, 32, 41))
        rear = _room(part, f"gate_{name}_rear", (a, PLATFORM_BACK, b, middle),
                     EDGE, clear=BAY_CLEAR, shades=(32, 31, 41))
        _connect(part, front, "south", booking, "north", skin=386)
        _connect(part, rear, "north", platform, "south", skin=386)
        _connect(part, front, "north", rear, "south")
        front.raw("Death Wish's folding gate, between matching planes",
                  lambda layout, room, other=rear, x0=a, x1=b: _mask(
                      layout, room.region_id, other.region_id, (x0, middle), (x1, middle),
                      1060, shade=25, x_repeat=16, y_repeat=10))

    near = _room(part, "counter_reveal", (46272, -9472, 46592, -8448),
                 IRON, GHOST_FLOOR - 7168, clear=16384, role="detail",
                 shades=(19, 23, 28), declared_zero_exit=True)
    far = _room(part, "counter_pane", (46080, -9472, 46272, -8448),
                IRON, GHOST_FLOOR - 7168, clear=16384, role="detail",
                shades=(19, 21, 28), declared_zero_exit=True)
    clerk = _room(part, "clerk", (44672, -9856, 46080, -8128), HALL,
                  clear=BAY_CLEAR, shades=(20, 20, 28), declared_zero_exit=True)
    _connect(part, near, "east", booking, "west", skin=386, clear=0)
    _connect(part, near, "west", far, "east", clear=0)
    _connect(part, far, "west", clerk, "east", skin=386, clear=0)
    far.raw("a fixed grille above the ticket shelf", lambda layout, room: _mask(
        layout, near.region_id, room.region_id, (46272, -9472), (46272, -8448),
        58, shade=28, x_repeat=8, y_repeat=8))
    cabinet = _room(part, "line_cabinet", (49216, -7936, 51200, -7424),
                    TIMBER, GHOST_FLOOR - 9216, 13312, role="detail",
                    declared_zero_exit=True, shades=(21, 15, 30))
    _connect(part, cabinet, "north", booking, "south", skin=248, clear=0)
    cabinet.raw("a framed route map with the line struck off", _line_map)
    clerk.raw("the clerk has stopped stamping tickets", _clerk_dress)
    booking.raw("the clock, the crossed-off line and the booking sign", _booking_dress)


def _rect_outline(rect, chamfer=0):
    x0, y0, x1, y1 = rect
    if chamfer:
        c = chamfer
        return ((x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
                (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c))
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def _inset(part, host, name, outline, material, floor, clear, shades, *, kind="furnished",
           face_picnum=None, **behavior):
    """Cut an independent floor or ceiling finish into a fixed room."""
    flat, wall, roof = shades
    faces = {f"edge_{i}": i for i in range(len(outline))}
    piece = part.room(
        name, outline, faces=faces, role="detail",
        style=Style(**material.style_kwargs(floor_z=floor, clear_height=clear,
                                           floor_shade=flat, wall_shade=wall, ceiling_shade=roof)),
        region_kwargs={**material.region_kwargs(), **behavior}, intent={"kind": kind})
    host.carve(outline)
    for face in faces:
        part.connect(piece.face(face), host.face(next(iter(host.faces))), min_width=1,
                     min_opening=0, face_picnum=face_picnum,
                     connection_id=f"connection:phantom:{name}:{face}")
    return piece


def _platform_rooms(part, platform, edge):
    waiting = _room(part, "waiting", (52736, PLATFORM_BACK, 56832, -7936), HALL,
                    shades=(49, 45, 48))
    _connect(part, waiting, "north", platform, "south", skin=386)
    for i, x in enumerate((53248, 55296)):
        seat = setpieces.raised_solid(
            part, f"phantom_bench_{i}", waiting, (x, -8960, x + 1280, -8384),
            TIMBER, grade=GHOST_FLOOR, rise=4608, host_clear=GHOST_CLEAR, shade=25)
        setpieces.raised_solid(
            part, f"phantom_bench_back_{i}", waiting, (x, -8344, x + 1280, -8152),
            Material(88, 67, 379, 88), grade=GHOST_FLOOR, rise=9728,
            host_clear=GHOST_CLEAR, shade=27)
        seat.raw("the waiting dead on the timber seat",
                 lambda layout, room, at=x: _prop(
                     layout, room.region_id, "waiting_body", at + 640, -8672,
                     2330 if at < 54000 else 2334, 46, 50, shade=-14))
    waiting.raw("lost baggage, the bills and the stationmaster's stopped clock", _waiting_dress)
    board = _room(part, "platform_nameboard", (52864, -7936, 55552, -7552),
                  Material(255, 255, 174, 386), GHOST_FLOOR - 5120,
                  clear=22528, role="detail", shades=(1, 4, 8),
                  declared_zero_exit=True)
    _connect(part, board, "north", waiting, "south", skin=386, clear=0)
    board.raw("green enamel station name and its own lamp", _platform_name)
    beam = _inset(part, waiting, "stationmaster_beam",
                  _rect_outline((55744, -9856, 56640, -9200)), Material(67, 374, 67, 67),
                  GHOST_FLOOR, GHOST_CLEAR - 4608, (7, 9, 14), face_picnum=88)
    beam.raw("the stationmaster hanging beside the stopped clock", _stationmaster)
    broken = _inset(part, waiting, "cracked_vault",
                    _rect_outline((54528, -9888, 55328, -9152), 128),
                    Material(368, 374, 369, 369), GHOST_FLOOR, GHOST_CLEAR + 2048,
                    (14, 17, 20), face_picnum=368)
    broken.raw("a broken vault panel with a lamp hanging loose", _broken_lamp)
    platform.raw("a blood trail, altar and the unfinished brick barrier", _platform_stories)

    for i, x in enumerate((47616, 51584, 55744, 57856)):
        col = _room(part, f"column_{i}", (x, -12320, x + 320, -12000),
                    EDGE, GHOST_FLOOR + 768, clear=0, role="detail",
                    declared_zero_exit=True)
        edge.carve(col.outline)
        for face in COMPASS:
            part.connect(col.face(face), edge.face("south"), min_width=1,
                         min_opening=0, face_picnum=386,
                         connection_id=f"connection:phantom_pier:{i}:{face}")
    edge.raw("flush platform lamps", _edge_dress)
    _platform_barrier(part, platform)

    porch = _room(part, "signal_step", (57152, PLATFORM_BACK, 58368, -10048),
                  EDGE, GHOST_FLOOR - 2048, BAY_CLEAR, shades=(31, 30, 39))
    cabin = _room(part, "signal_cabin", (57088, -10048, 58560, -8192),
                  SERVICE, GHOST_FLOOR - 4096, BAY_CLEAR, shades=(22, 23, 30))
    _connect(part, porch, "north", platform, "south", skin=386)
    _connect(part, porch, "south", cabin, "north", skin=386)
    cabin.raw("the station side of the rail recall circuit", _signal_dress)
    # the one listener laid before the light stage, which adds the rest (`lights.groups`)
    wires.wire(CAR_LIGHT).then(wiring.region(porch.region_id))


def _service_line(part, platform, track):
    last = platform
    for index, (x0, x1) in enumerate(pairwise((PLATFORM_RIGHT, 59072, 59584, 60032))):
        tread = _room(part, f"return_step_{index}", (x0, -11776, x1, -10752),
                      SERVICE, GHOST_FLOOR + index * 1024, BAY_CLEAR, shades=(35, 33, 39))
        _connect(part, tread, "west", last, "east", skin=386)
        last = tread
    catwalk = _room(part, "service_walk", (60032, SOUTH_EDGE, 69760, -10368),
                    SERVICE, GHOST_FLOOR + 3072, BAY_CLEAR + 2048, shades=(40, 35, 43))
    _connect(part, last, "east", catwalk, "west")
    _connect(part, catwalk, "north", track, "south", skin=386)
    _connect(part, catwalk, "west", track, "passing_east", skin=386)
    stop = _room(part, "brick_stop", (66560, -10368, 69632, -8704),
                 BRICK, GHOST_FLOOR + 2048, BAY_CLEAR, shades=(24, 26, 33))
    _connect(part, stop, "north", catwalk, "south", skin=386)
    bench = setpieces.raised_solid(
        part, "phantom_mortar_bench", stop, (66752, -9584, 67696, -8984),
        TIMBER, grade=GHOST_FLOOR + 2048, rise=6144, host_clear=BAY_CLEAR, shade=20)
    bench.raw("the lantern left by the men who closed the line", _mortar_table)
    for index, (rect, rise) in enumerate((((67904, -9472, 68416, -9216), 5120),
                                          ((67904, -9088, 68416, -8832), 2560))):
        setpieces.raised_solid(part, f"phantom_brick_stack_{index}", stop, rect, BRICK,
                               grade=GHOST_FLOOR + 2048, rise=rise, host_clear=BAY_CLEAR, shade=20)
    stop.raw("the bricking gang left their tools by the return switch", _stop_dress)
    catwalk.raw("bulkhead lamps and directions for the return walk", _walk_dress)

    end = _room(part, "blind_tunnel", (TRACK[2], TRACK[1], 72192, SOUTH_EDGE),
                BORE, TRACK_FLOOR, TRACK_FLOOR - TRACK_ROOF, shades=(39, 32, 43))
    _connect(part, end, "west", track, "east", skin=358)
    end.raw("a brick plug across the old running tunnel", _buffers)
    for index, x in enumerate(WATCHERS):
        mouth = _room(part, f"watch_mouth_{index}", (x, -17472, x + 1152, TRACK[1]),
                      EDGE, WATCH_FLOOR, BAY_CLEAR, shades=(37, 33, 41))
        niche = _room(part, f"watch_niche_{index}", (x, -18496, x + 1152, -17472),
                      SERVICE, WATCH_FLOOR, BAY_CLEAR, shades=(3, 2, 6),
                      declared_zero_exit=True)
        _connect(part, mouth, "south", track, "north", skin=358)
        _connect(part, mouth, "north", niche, "south")
        niche.raw("a watcher and a masked iron screen at equal height",
                  lambda layout, room, front=mouth, left=x, i=index:
                  _watcher(layout, room, front, left, i))
    return stop


#: The drowned carriage: four windows long, off the rails and askew (14 degrees, on an integer lattice).
WRECK_PLAN = carriage.Plan(89, ((8, 24), (27, 43), (46, 62), (65, 81)),
                           broken=frozenset({"south_window_0", "north_window_2"}))
WRECK = carriage.Axes((38272, -17088), (63, 16), (-16, 63))
#: its deck is this far under the water: the benches just clear it
WRECK_DECK = WATER_FLOOR + 5120
CAVERN = ((36608, -17152), (37632, -18944), (41472, -19456), (44032, -18432), (45056, -17152),
          (45056, -12544), (44288, -11264), (41600, -10752), (37888, -11392), (36608, -12928))
#: the slab of the old roof that came down on the carriage and rests along its top
SLAB = ((37696, -17664), (43456, -17408), (44416, -16256), (44416, -12928), (43456, -12096),
        (38400, -12096), (37056, -13376), (37056, -16768))
WATER_MOTION = {"depth": 1, "pan_always": 1, "pan_floor": 1, "pan_angle": 1024, "pan_velocity": 2}


def _drowned_siding(part, track):
    """The line falls into a flooded cavern; the next carriage stands in it with water all round."""
    sill = _room(part, "siding", (45056, TRACK[1], TRACK[0], SOUTH_EDGE),
                 BORE, TRACK_FLOOR + 1792, BAY_CLEAR + 1792, shades=(38, 33, 40))
    _connect(part, sill, "east", track, "west", skin=358)
    flood = part.room(
        "drowned", CAVERN, faces={f"edge_{i}": i for i in range(len(CAVERN))}, role="interior",
        style=Style(**WATER.style_kwargs(floor_z=WATER_FLOOR, clear_height=30720,
                                         floor_shade=40, wall_shade=36, ceiling_shade=44)),
        region_kwargs={**WATER.region_kwargs(), "sector_behavior": dict(WATER_MOTION)},
        intent={"kind": "furnished"})
    part.connect(sill.face("west"), flood.face("edge_4"), min_width=BODY.body_width,
                 min_opening=BODY.standing_height, face_picnum=386,
                 connection_id="connection:phantom_drowned_throat")
    slab = _inset(part, flood, "fallen_roof", SLAB, WATER, WATER_FLOOR,
                  WATER_FLOOR - (WRECK_DECK - carriage.TOP), (40, 36, 44), face_picnum=383,
                  sector_behavior=dict(WATER_MOTION))
    slab.raw("the next carriage, standing in the water", _drowned_carriage)
    flood.raw("what came down with the roof", _cavern_dress)


def _drowned_carriage(layout, slab):
    wreck = carriage.build(
        layout, f"{slab.region_id}_wreck", slab.region_id, WRECK, WRECK_DECK, WRECK_PLAN,
        pal=GREEN, shade=24, water=WATER_FLOOR, water_tile=2915, water_behavior=WATER_MOTION,
        kind="phantom_cab_green")
    for index, (name, u, tile) in enumerate((
            ("north_seat_0", 14, 2330), ("north_seat_1", 33, 2333), ("north_seat_2", 56, 2330),
            ("south_seat_0", 17, 2334), ("south_seat_1", 36, 2330), ("south_seat_2", 52, 2333),
            ("north_seat_3", 74, 2334), ("south_seat_3", 70, 2330))):
        x, y = WRECK(u, 8 if name.startswith("north") else 42)
        _prop(layout, wreck.at(name), f"drowned_passenger_{index}", x, y, tile, 42, 48, shade=-5)
    for index, u in enumerate((16, 35, 54, 73)):
        x, y = WRECK(u, 25)
        _round_lamp(layout, wreck.at("aisle"), f"drowned_lamp_{index}", x, y, size=46, shade=-35, pal=GREEN)
    # the line's name on the side that faces the way in
    _outside_lettering(layout, wreck, wreck.at("board"), WRECK_PLAN.slots[1], carry=0)


def _cavern_dress(layout, flood):
    region = flood.region_id
    for index, (x, y, tile, size) in enumerate(((44416, -16384, 2621, 60), (44288, -12032, 2622, 64),
                                               (36832, -14592, 2623, 70), (38784, -11648, 2621, 52),
                                               (37888, -18048, 2622, 60))):
        _prop(layout, region, f"drowned_rubble_{index}", x, y, tile, size, size, shade=-4)


def _mask(layout, first, second, a, b, tile, *, shade, x_repeat, y_repeat,
          translucent=False, pal=0):
    """Hang a blocking mask on a reciprocal wall with no floor or roof band."""
    left, right = layout.regions[first], layout.regions[second]
    if (left.floor_z, left.ceiling_z) != (right.floor_z, right.ceiling_z):
        raise ValueError(f"{first} and {second} cannot share a mask across a step")
    for region in (first, second):
        layout.paint_wall(region, a, b, fixed_frame=True, over_picnum=tile,
                          cstat=BLOCK | (128 if translucent else 0), pal=pal,
                          x_repeat=x_repeat, y_repeat=y_repeat, shade=shade)


def _prop(layout, region, name, x, y, tile, xr, yr, *, seat="floor",
          shade=12, cstat=128, support=None, **fields):
    from bloodmap.placement import seated_z

    room = layout.regions[region]
    _, height, _, offset = wallplane.art()[tile]
    z = seated_z(seat=seat, floor_z=room.floor_z if support is None else support,
                 ceiling_z=room.ceiling_z,
                 tile_height=height, y_repeat=yr, y_offset=offset, cstat=cstat,
                 clearance=16)
    return layout.add_sprite(f"phantom:{name}:{region}", region, x=x, y=y, z=z,
                             picnum=tile, x_repeat=xr, y_repeat=yr, cstat=cstat,
                             shade=shade, **fields)


def _round_lamp(layout, room, name, x, y, size=42, shade=-10, *, cstat=160, carry=0, **fields):
    roof = layout.regions[room].ceiling_z
    return layout.add_sprite(f"phantom:{name}", room, x=x, y=y, z=roof + 64,
                             picnum=795, cstat=cstat | carry,
                             x_repeat=size, y_repeat=size, shade=shade, **fields)


def _bill(layout, room, name, a, b, tile, repeat, height, *, shade=7, **options):
    return wallplane.sprite(layout, f"phantom:{name}", room, a, b, tile=tile,
                            x_repeat=repeat, y_repeat=repeat, cstat=208,
                            height_player_heights=height,
                            shade=shade, required=True, **options)


def _sign(layout, room, name, a, b, words, *, size=62, height=0.95):
    return wallplane.text(layout, f"phantom:{name}", room, a, b,
                          words=words, size=size, shade=-30, palette=5,
                          required=True, height_player_heights=height)


def _nameboard(layout, region, suffix, a, b, *, repeat, height):
    _bill(layout, region, f"name_{suffix}", a, b, 1667, repeat, height, shade=-32)
    wallplane.text(layout, f"phantom:terminus_{suffix}", region, a, b,
                   words="TERMINUS", size=100 if suffix == "platform" else 62,
                   shade=-37, palette=5, required=True, height_player_heights=height - 0.50)


def _booking_dress(layout, room):
    region = room.region_id
    east = ((52224, -9856), (52224, -8064))
    _split_lit_wall(layout, region, *east, shade=22, tile=255)
    _nameboard(layout, region, "booking", *east, repeat=48, height=1.37)
    _round_lamp(layout, region, "booking_sign_light", 51776, -9096, shade=-54, size=36)
    _round_lamp(layout, region, "booking_ticket_lamp", 48000, -8912, shade=-45, size=52)
    _bill(layout, region, "clock", (52224, -7936), (51232, -7936),
          1166, 34, 1.21)
    _sign(layout, region, "withdrawn", (52224, -7936), (51232, -7936),
          "CLOSED", size=44, height=0.70)
    _sign(layout, region, "tickets", (46592, -7992), (46592, -9864),
          "TICKETS", size=48, height=1.38)


def _line_map(layout, room):
    """An enamel branch diagram with crossed-out stops framed in timber."""
    region = room.region_id
    back = ((51200, -7424), (49216, -7424))
    for row, (words, gone) in enumerate((("GRAVESEND", True), ("GALLOWS", True), ("PHANTOM", False))):
        height = 0.60 - 0.20 * row
        wallplane.text(layout, f"phantom:line_stop_{row}", region, *back, words=words,
                       height_player_heights=height, size=44, shade=-30,
                       palette="rust" if gone else 5, required=True)


def _clerk_dress(layout, room):
    region = room.region_id
    _round_lamp(layout, region, "clerk_lamp", 45248, -9000)
    _prop(layout, region, "clerk_body", 45568, -8912, 1727, 40, 40,
          seat="ceiling", shade=12)
    _prop(layout, region, "ticket_crate", 45152, -8660, 95, 23, 25, shade=12)


def _split_lit_wall(layout, region, a, b, *, shade, tile, pal=0):
    """Give a light its own wall record on a fixed room's long straight face."""
    room = layout.regions[region]
    rebuilt = []
    for start, end in pairwise((*room.outer, room.outer[0])):
        rebuilt.append(start)
        ax = 0 if start[1] == end[1] else 1
        other = 1 - ax
        if start[other] != end[other] or not (a[other] == b[other] == start[other]):
            continue
        extra = [point for point in (a, b)
                 if min(start[ax], end[ax]) < point[ax] < max(start[ax], end[ax])]
        rebuilt.extend(sorted(extra, key=lambda point: point[ax], reverse=end[ax] < start[ax]))
    room.outer = tuple(rebuilt)
    layout.paint_wall(region, a, b, picnum=tile, shade=shade, pal=pal)


def _edge_dress(layout, room):
    region = room.region_id
    for index, x in enumerate((48448, 57728)):
        _round_lamp(layout, region, f"edge_lamp_{index}", x, -12176, shade=-40)
    floor, roof = GHOST_FLOOR + 768, GHOST_FLOOR - GHOST_CLEAR
    for i, x in enumerate((47776, 51744, 55904, 58016)):
        for side, y in (("track", -12340), ("hall", -11980)):
            _panel(layout, region, f"capital_{side}_{i}", x, y, roof + 1456,
                   174, 402, 2800, shade=-3, angle=512)
            _panel(layout, region, f"plinth_{side}_{i}", x, y, floor - 1184,
                   174, 416, 2150, shade=2, angle=512)


def _platform_name(layout, room):
    region = room.region_id
    _nameboard(layout, region, "platform", (55552, -7552), (52864, -7552),
               repeat=64, height=1.07)
    _round_lamp(layout, region, "enamel_board_lamp", 54208, -7776, size=32, shade=-31)


def _stationmaster(layout, room):
    _prop(layout, room.region_id, "stationmaster", 56256, -9552, 1727, 42, 42,
          seat="ceiling", shade=15)


def _broken_lamp(layout, room):
    _prop(layout, room.region_id, "loose_vault_lamp", 55168, -9488, 641, 32, 30,
          seat="ceiling", shade=-60)


def _waiting_dress(layout, room):
    region = room.region_id
    _split_lit_wall(layout, region, (56832, -10048), (56832, -8992), shade=14, tile=369)
    _bill(layout, region, "stationmaster_clock", (56832, -9984), (56832, -9088),
          1166, 42, 1.47, shade=-30)
    for i, (y, tile, repeat) in enumerate(((-10072, 356, 34), (-9536, 356, 34),
                                           (-8992, 356, 34), (-8480, 453, 31))):
        _bill(layout, region, f"bills_{i}", (52736, y + 270), (52736, y - 270),
              tile, repeat, 1.12, shade=-14)
    for i, (x, y, tile, width, height) in enumerate((
        (53504, -9832, 522, 50, 57), (53952, -9664, 523, 45, 42),
        (54192, -9896, 522, 27, 37),
    )):
        _prop(layout, region, f"abandoned_luggage_{i}", x, y, tile, width, height,
              shade=-32)
    _flat(layout, region, "fallen_newspaper", 53584, -10160, GHOST_FLOOR - 12,
          743, 240, 128, shade=4, cstat=160)
    _bill(layout, region, "gore", (56832, -8912), (56832, -8096), 713, 32, 0.44,
          shade=-11)


def _platform_barrier(part, platform):
    # On the south side of the east platform. A full-width route goes around
    # its north end to the return stairs. The ragged top is three courses.
    outlines = (
        (((56864, -11328), (57312, -11392), (57312, -11168),
          (56864, -11168)), 8704),
        (((56864, -11144), (57312, -11144), (57312, -10896),
          (56864, -10896)), 12288),
        (((56864, -10872), (57312, -10872), (57312, -10560),
          (56864, -10560)), 15360),
    )
    for i, (outline, rise) in enumerate(outlines):
        piece = _inset(part, platform, f"unfinished_brick_{i}", outline, BRICK,
                       GHOST_FLOOR - rise, GHOST_CLEAR - rise, (2, 5, 41),
                       face_picnum=383, declared_zero_exit=True)
        piece.raw("the courses' faces",
                  lambda layout, room, loop=outline: [layout.paint_wall(
                      platform.region_id, a, b, picnum=383)
                      for a, b in pairwise((*loop, loop[0]))])
    shrine = _inset(part, platform, "column_shrine",
                    _rect_outline((51584, -11824, 52288, -11472), 72), IRON,
                    GHOST_FLOOR - 1152, GHOST_CLEAR - 1152, (8, 13, 28),
                    face_picnum=386)
    shrine.raw("candles left at the pier base", _shrine)
    pit = _inset(part, platform, "fallen_platform_tiles",
                 _rect_outline((48320, -11800, 49088, -11248), 82),
                 Material(279, 280, 379, 279), GHOST_FLOOR + 512, GHOST_CLEAR + 512,
                 (22, 30, 52), face_picnum=279)
    pit.raw("stone chips in a patch of lost tile", _lost_tiles)

def _lost_tiles(layout, room):
    for i, (x, y, size) in enumerate(((48640, -11624, 37), (48784, -11680, 26),
                                      (48908, -11520, 21))):
        _prop(layout, room.region_id, f"fallen_tile_{i}", x, y,
              2621 + i, size, size, shade=-5)


def _shrine(layout, room):
    for i, (x, y, size) in enumerate(((51738, -11624, 29), (51928, -11618, 37),
                                      (52032, -11673, 22))):
        _prop(layout, room.region_id, f"shrine_candle_{i}", x, y, 938, size, size,
              shade=-51, type=32)


def _phantom_floor(layout, x, y, floor):
    from bloodmap.planar_geom import point_in_loop

    return next(r.region_id for r in layout.regions.values()
                if r.layer == "ghost_station" and r.floor_z == floor
                and point_in_loop((x, y), r.outer) == 1
                and all(point_in_loop((x, y), hole) == 0 for hole in r.holes))


def _platform_stories(layout, room):
    station = room.region_id
    for i, (x, y, width, depth) in enumerate((
        (53568, -9184, 270, 200), (53392, -9664, 220, 250),
        (52928, -10304, 176, 220), (52000, -10784, 185, 240),
        (51264, -11360, 230, 300), (50744, -11824, 214, 224),
        (50688, -12176, 274, 208),
    )):
        floor = GHOST_FLOOR + (768 if y < EDGE_BACK else 0)
        space = _phantom_floor(layout, x, y, floor)
        _flat(layout, space, f"blood_trail_{i}", x, y, floor - 20, 956,
              width, depth, shade=-18, cstat=164 if i % 2 else 160)
    for i, (x, y, tile, width, height) in enumerate((
        (57812, -11292, 2333, 39, 41), (58064, -10816, 2334, 41, 43),
        (58240, -11372, 2621, 30, 30), (57472, -10832, 2622, 34, 34),
        (57696, -11680, 2623, 36, 36), (57984, -11168, 693, 34, 36),
    )):
        space = _phantom_floor(layout, x, y, GHOST_FLOOR)
        _prop(layout, space, f"bricking_gang_{i}", x, y, tile, width, height, shade=-13)
    # the hall's own lamps down its middle: the light stage traces what each one lights
    for name, x in (("gate", 50240), ("last", 56640)):
        _round_lamp(layout, station, f"platform_lamp_{name}", x, -11168, shade=-45, size=52)


def _call(layout, room, suffix, a, b):
    name = layout.place_on_wall(
        f"phantom:call_{suffix}", room, a1=a, a2=b, t=0.5,
        height_player_heights=0.78, type=20, picnum=1046, cstat=208,
        shade=-8, x_repeat=37, y_repeat=37, behavior={"data_1": 203})
    wires.wire(RUN).when(wiring.placement(name), "push", command=motion.CMD_ON,
                         wait_time=1, dude_lockout=1)
    _sign(layout, room, f"recall_{suffix}", a, b, "RECALL", size=40, height=1.10)


def _signal_dress(layout, room):
    region = room.region_id
    _round_lamp(layout, region, "signal_lamp", 57856, -9296, size=36, shade=-40)
    _call(layout, region, "signal", (58560, -9840), (58560, -8512))
    _bill(layout, region, "signal_clock", (58432, -8192), (57216, -8192),
          1165, 32, 1.01)


def _stop_dress(layout, room):
    region = room.region_id
    _round_lamp(layout, region, "stop_lamp", 68224, -9728, shade=-40)
    _call(layout, region, "brick", (69568, -8704), (66624, -8704))
    _sign(layout, region, "way_back", (66560, -8832), (66560, -10240),
          "STAIRS", size=45, height=0.98)
    _prop(layout, region, "mortar_chip", 67136, -9824, 2621, 34, 34, shade=0)
    _prop(layout, region, "sweeper", 69248, -9280, 2333, 44, 46, shade=0)
    _prop(layout, region, "cloak", 68736, -9250, 896, 40, 40, type=113, status=3, shade=-8)


def _mortar_table(layout, room):
    _prop(layout, room.region_id, "mortar_lantern", 67360, -9272, 693, 34, 36, shade=-20)


def _walk_dress(layout, room):
    region = room.region_id
    for i, x in enumerate((61056, 63616, 66944, 68736)):
        _round_lamp(layout, region, f"return_lamp_{i}", x, -11616, size=31, shade=-40)
    _sign(layout, region, "return", (62528, -10368), (60416, -10368),
          "TO STAIRS", size=49, height=0.97)
    # 51 and 52 are broken plaster with the brick showing: a wall's decal and nothing else
    # (the owner, 2026-11-24; 51 of 51 uses in the corpus hang flat on a wall)
    _bill(layout, region, "fallen_plaster_0", (64832, -10368), (63616, -10368), 51, 48, 0.86, shade=-6)


def _buffers(layout, room):
    region = room.region_id
    x, y0, y1 = 72192, TRACK[1], TRACK[3]
    layout.paint_wall(region, (x, y0), (x, y1), picnum=383, shade=32)
    _bill(layout, region, "buffing_beam", (x, y0 + 768), (x, y1 - 768),
          2229, 57, 0.24, shade=12)
    _prop(layout, region, "buffer_lantern", 71712, -14592, 693, 34, 36, shade=-9)


def _watcher(layout, room, mouth, x, index):
    region = room.region_id
    _mask(layout, region, mouth.region_id, (x, -17472), (x + 1152, -17472),
          58, shade=21, x_repeat=9, y_repeat=10)
    _prop(layout, region, "watcher", x + 576, -18016, 799, 52, 51, shade=30)
    _round_lamp(layout, region, f"watcher_lamp_{index}", x + 576, -18016,
                size=24, shade=-50)


def _panel(layout, region, name, x, y, z, tile, width, height, *, shade, angle,
           carry=0, pal=0):
    columns, rows, _, _ = wallplane.art()[tile]
    layout.add_sprite(f"phantom:{name}", region, x=x, y=y, z=z, picnum=tile,
                      x_repeat=min(255, round(width * 4 / columns)),
                      y_repeat=max(1, round(height / (4 * rows))), angle=angle,
                      cstat=144 | carry, shade=shade, pal=pal)


def _flat(layout, room, name, x, y, z, tile, width, depth, *, shade=0,
          carry=0, pal=0, cstat=160, **fields):
    columns, rows, _, _ = wallplane.art()[tile]
    return layout.add_sprite(
        f"phantom:{name}", room, x=x, y=y, z=z, picnum=tile,
        x_repeat=round(width * 4 / columns), y_repeat=round(depth * 4 / rows),
        angle=1536, shade=shade, pal=pal, cstat=cstat | carry, **fields)


def _facing(axes, along, across):
    """The angle a wall sprite faces when it looks this way in a carriage's own axes."""
    from math import atan2, pi

    x = along * axes.along[0] + across * axes.across[0]
    y = along * axes.along[1] + across * axes.across[1]
    return round(atan2(y, x) * 1024 / pi) & 2047


def _outside_lettering(layout, coach, region, slot, *, carry):
    """PHANTOM over one opening and the fleet's number beside it, on the skin of the platform side."""
    axes, deck = coach.axes, coach.deck
    facing = _facing(axes, 0, 1)
    middle, skin = (slot[0] + slot[1]) / 2, carriage.WIDTH - carriage.BOARD + 0.15
    for index, letter in enumerate("PHANTOM"):
        x, y = axes(middle + 2 * (index - 3), skin)
        _panel(layout, region, f"destination_{index}:{region}", x, y, deck - 23168,
               wallplane.tile_for(letter), 104, 3000, shade=-34, angle=facing, carry=carry, pal=5)
    x, y = axes(slot[1] + 1.5, skin)
    _panel(layout, region, f"fleet_number:{region}", x, y, deck - 15360, 1407, 150, 1500, shade=-24,
           angle=facing, carry=carry)


def _furnish_coach(layout, coach):
    """Passengers on their benches, lamps in the raised roof, the conductor in his cab.

    Returns the placements that hang in the host: the engine moves them with
    the body because the host is a mover of the same travel (E1M2 s34).
    """
    carry = mechanism.CARRY_WITH
    plan, axes, deck = coach.plan, coach.axes, coach.deck
    for index, (name, u, tile) in enumerate((
            ("north_seat_0", 12, 2330), ("north_seat_0", 20, 2334), ("north_seat_2", 50, 2330),
            ("north_seat_2", 58, 2333), ("north_seat_3", 72, 2330), ("north_seat_4", 88, 2334),
            ("north_seat_4", 97, 2330), ("south_seat_0", 13, 2333), ("south_seat_3", 68, 2330),
            ("south_seat_4", 92, 2334))):
        x, y = axes(u, 8 if name.startswith("north") else 42)
        _prop(layout, coach.at(name), f"passenger_{index}", x, y, tile, 42, 48, shade=-5)
    for index, (u0, u1) in enumerate(plan.slots):
        x, y = axes((u0 + u1) / 2, 25)
        _round_lamp(layout, coach.at("aisle"), f"car_lamp_{index}", x, y, shade=-35, pal=GREEN, size=48)
    x, y = PRIZE_AT
    _round_lamp(layout, coach.at("north_seat_1"), "car_lamp_seat", x, y, size=30, shade=-45, pal=GREEN)
    x, y = axes((plan.saloon[1] + 1 + plan.inside[1]) / 2, 25)
    _round_lamp(layout, coach.at("cab"), "car_lamp_cab", x, y + 320, size=36, shade=-30, pal=GREEN)
    _prop(layout, coach.at("cab"), "conductor", x + 192, y - 256, 1727, 43, 41, cstat=128, seat="ceiling", shade=1)
    for index in (2, 4):
        u0, u1 = plan.slots[index]
        x, y = axes((u0 + u1) / 2 + 3, 47.8)
        _panel(layout, coach.at(f"south_window_{index}_in"), f"bloodied_pane_{index}", x, y,
               deck - 13312, 713, 296, 4160, shade=6, angle=_facing(axes, 0, -1))
    x, y = axes(35, 36)
    _flat(layout, coach.at("aisle"), "aisle_blood", x, y, deck - 20, 956, 260, 300, shade=-10)
    x, y = axes(77, 34)
    _prop(layout, coach.at("aisle"), "aisle_case", x, y, 523, 40, 38, shade=-18)
    _outside_lettering(layout, coach, coach.at("board"), plan.slots[plan.door], carry=carry)
    # wheels under the running board, both flanks: they stand in the track's own space
    outside = []
    for side, v, way in (("south", carriage.WIDTH + 0.15, 1), ("north", -0.15, -1)):
        for index, u in enumerate((16, 40, 88, 112)):
            x, y = axes(u, v)
            name = f"wheels_{side}_{index}"
            _panel(layout, coach.host, name, x, y, TRACK_FLOOR - 2700, 2320, 900, 5000,
                   shade=6, angle=_facing(axes, 0, way), carry=carry)
            outside.append(f"phantom:{name}")
    return tuple(outside)


def light_groups(compiled):
    """The station's lamps that blink, go out or travel, and the wire each is on.

    What each one lights is traced (`bloodmap.light_stage.switch_lamps`): the
    owner, 2026-11-24, "when you made light blinking it should also affect
    neighbouring sectors that are lit by that light".
    """
    from bloodmap import posed
    from bloodmap.light_stage import LampGroup

    def lamps(*names):
        return frozenset(compiled.placement_sprites[f"phantom:{name}"] for name in names)

    def station(region):
        return "/ghost_station/" in region and "_coach:" not in region

    def coach(region):
        return "_coach:" in region

    def gone(disk):
        prize = compiled.placement_sprites[f"phantom:prize:{PRIZE_REGION}"]
        return posed.posed(disk, posed.chain_of(wiring.chains(disk), f"sprite {prize}"))[0]

    car = lamps(*(f"car_lamp_{i}" for i in range(len(COACH_PLAN.slots))), "car_lamp_seat", "car_lamp_cab")
    link, depart = wires.channel(CAR_LIGHT), wires.channel(DEPART)
    sick = {"wave": 8, "frequency": 4}                     # flicker3: lit, with dips
    groups = [
        LampGroup("the coach's own lamps", car, within=coach, **sick),
        LampGroup("what falls from its windows", car, "on", rx=link, within=station, **sick),
        LampGroup("what falls from them at the far berth", car, "on", rx=link, within=station, moved=gone),
        LampGroup("the platform's lamps", lamps("platform_lamp_gate", "platform_lamp_last", "edge_lamp_1",
                                                "booking_ticket_lamp",
                                                "booking_sign_light"), "out", rx=depart, within=station),
        LampGroup("the loose lamp", lamps(f"loose_vault_lamp:{STATION}/cracked_vault"), wave=7, frequency=3,
                  phase=40, within=station),
        LampGroup("the near lamp", lamps("edge_lamp_0"), "out", rx=wires.channel(PLATFORM_ENTRY), within=station),
        LampGroup("the clerk's lamp", lamps("clerk_lamp"), wave=6, frequency=4, phase=90, within=station),
        LampGroup("the drowned carriage", lamps(*(f"drowned_lamp_{i}" for i in range(len(WRECK_PLAN.slots)))),
                  wave=8, frequency=3, phase=60, within=station),
    ]
    # flicker4 (9) is dark with bursts, strobe (10) a flash that dies away
    for index, (wave, frequency) in enumerate(((7, 5), (9, 4), (10, 5), (9, 3))):
        groups.append(LampGroup(f"watcher {index}", lamps(f"watcher_lamp_{index}"), wave=wave,
                                frequency=frequency, phase=70 * index, within=station))
    return groups


def apply_surface_palette(layout, compiled):
    """Finish authored green and cold mounts after ordinary city materials."""
    for name, region in layout.regions.items():
        allocation = compiled.allocations.get(name)
        if allocation is None:
            continue
        fields = record_fields(compiled.level.sectors[allocation.sector_id])
        intent = region.intent or {}
        if "floor_pal" in intent:                          # a carriage's piece (`carriage.build`)
            fields["floor_pal"], fields["ceiling_pal"] = intent["floor_pal"], intent["ceiling_pal"]
        elif name.rsplit("/", 1)[-1].startswith("watch_niche_"):
            fields["floor_pal"] = fields["ceiling_pal"] = 10
            for index in allocation.wall_ids:
                record_fields(compiled.level.walls[index])["pal"] = 10


def _marker(layout, name, region, x, y, kind, tile=0, *, angle=0, **behavior):
    room = layout.regions[region]
    return layout.add_sprite(
        f"phantom:{name}", region, x=x, y=y, z=(room.floor_z + room.ceiling_z) // 2,
        type=kind, picnum=tile, angle=angle, shade=-128, cstat=32896,
        behavior=behavior)


def _platform_entry(layout, room):
    station = room.region_id
    base = station.rsplit("/", 1)[0]
    entry = wires.wire(PLATFORM_ENTRY)
    # The gate throat is a full 512 units deep. The first light ring begins
    # just beyond the threshold, so a running player can miss the main floor.
    entry.when(wiring.region(base + "/gate_open"), "enter", command=motion.CMD_TOGGLE,
               once=True, dude_lockout=1)
    whistle = _marker(layout, "distant_whistle", base + "/blind_tunnel",
                      71104, -14848, 708, 2521, data_2=276)
    entry.then(wiring.placement(whistle))


def _coach_controls(layout, coach, station, stop):
    """The handle and the loot start one show, with repeatable travel afterwards."""
    run = wires.wire(RUN)
    departure = wires.wire(DEPART)
    aisle = coach.at("aisle")
    guns = _prop(layout, coach.at("north_seat_1"), "prize", *PRIZE_AT, 558, 48, 48,
                 type=42, status=3, cstat=128, shade=-48)
    prize = wires.wire(PRIZE)
    prize.when(wiring.placement(guns), "pickup", command=motion.CMD_ON,
               once=True, dude_lockout=1)
    x, y = coach.axes(coach.plan.inside[1] - 0.15, 42)
    handle = layout.add_sprite(
        "phantom:driver_handle", coach.at("cab"), x=x, y=y, z=DECK - 9600,
        type=20, picnum=1070, angle=1024, cstat=208,
        x_repeat=50, y_repeat=54, shade=-15, behavior={"data_1": 203, "data_2": 203})
    run.when(wiring.placement(handle), "push", command=motion.CMD_TOGGLE, off=True)
    relay = _marker(layout, "prize_relay", station, 52336, -11600, 20)
    prize.then(wiring.placement(relay))
    run.when(wiring.placement(relay), "relay", command=motion.CMD_OFF)
    sense = _marker(layout, "run_sense", station, 52368, -11600, 20, state=1)
    run.then(wiring.placement(sense))
    arm = wires.wire(ARM)
    arm.when(wiring.placement(sense), "relay", command=motion.CMD_ON, on=False, off=True)
    latch = _marker(layout, "departure_latch", station, 52400, -11600, 20)
    arm.then(wiring.placement(latch))
    departure.when(wiring.placement(latch), "relay", command=motion.CMD_ON)

    # The body announces each berth it stops at; another of its members drives
    # the light that falls from its windows, as it goes (`lights.groups`).
    coach_state = wires.wire(COACH_STATE)
    coach_state.when(wiring.region(aisle), wiring.RELAY, command=motion.CMD_STATE, on=True, off=True)
    wires.wire(CAR_LIGHT).when(wiring.region(coach.at("cab")), wiring.RELAY,
                               command=motion.CMD_LINK, on=False)
    arrival = _marker(layout, "arrival_quote", stop.region_id, 68160, -9700, 20, state=1)
    coach_state.then(wiring.placement(arrival))

    from caleb import ghost_tunnel
    ghost_tunnel(layout, stop, arrival_switch=arrival)


def _run_car(layout, track, platform, stop):
    coach = carriage.build(layout, f"{track.region_id}_coach", track.region_id, COACH, DECK, COACH_PLAN,
                           pal=GREEN, shade=6, kind="phantom_cab_green")
    outside = _furnish_coach(layout, coach)
    station = platform.region_id
    _coach_controls(layout, coach, station, stop)
    body = mechanism.rigid_body(layout, "phantom_car", members=coach.members, host_region=coach.host,
                                travel=(-TRAVEL, 0), lead=coach.at("aisle"), busy_time=55, wave=1)
    for region in body["receivers"]:
        wires.wire(RUN).then(wiring.region(region))
    mechanism.carry_fittings(layout, coach.members, also=outside)
    departure = wires.wire(DEPART)
    horn = _marker(layout, "whistle", station, 52304, -11584, 711, 2519, data_1=276)
    quake = _marker(layout, "quake", station, 52544, -11300, 19, 2072, data_1=1200)
    for placement in (horn, quake):
        departure.then(wiring.placement(placement))
    for i, x in enumerate((59264, 63872)):
        spawn = _marker(layout, f"spawn_{i}", track.region_id, x, -16768, 18, 2077,
                        angle=1024, data_1=210)
        departure.then(wiring.placement(spawn))
    import ambience
    for suffix, space, x, y, context in (
        ("station", station, 47200, -11000, "interior"),
        ("siding", station.rsplit("/", 1)[0] + "/drowned", 44544, -14000, "sewer"),
    ):
        z = layout.regions[space].floor_z - 6144
        layout.add_sprite(f"phantom:ambience_{suffix}", space, x=x, y=y, z=z,
                          **ambience.fields(context))
