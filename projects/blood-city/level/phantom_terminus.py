"""Build the Phantom Terminus, its train and the pump landing's concealed approach."""

from itertools import pairwise

from bloodmap import mechanism, motion, wiring
from bloodmap.levelprog import RECT_FACES, Style
from bloodmap.model import record_fields
from bloodmap.player_space import PLAYER_PROFILES

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

TRACK = (46592, -17152, 70656, -12544)
CAR = (48640, -16384, 56832, -13312)
TRACK_FLOOR = GHOST_FLOOR + 1536
TRACK_ROOF = TRACK_FLOOR - 26624
TRAVEL = 11264
DEPART = "phantom:departure"
RUN = "phantom:car"
DOOR = (50240, 51264)
WINDOWS = ((49024, 49920), (51648, 52672), (53056, 54080), (54656, 55680))
GREEN = 4
WINDOW_MASK = 1099
PRIZE = "phantom:prize"
ARM = "phantom:arm"
COACH = "phantom:coach-state"
BOARDING = "phantom:boarding"
LAMP_PULSE = "phantom:lamp-pulse"
PLATFORM_ENTRY = "phantom:first-platform"
SPILL_OFF = "phantom:spill-off"
SEAT_Z = TRACK_FLOOR - 6656
#: the one empty seat, facing the open door: it is seen from the platform
PRIZE_AT = (50752, -15456)
SEATED = (2330, 2333, 2334)
PANEL_MASK = 255
BLOCK = 1 | 16 | 64


def _car_edges():
    """The full car loop, with its windows and doorway as atomic redwalls."""
    west, north, east, south = CAR
    windows = {span: WINDOW_MASK for span in WINDOWS}
    sections = (*WINDOWS, DOOR)
    cuts = sorted({west, east, *(x for span in sections for x in span)})
    for a, b in pairwise(cuts):
        yield (a, north), (b, north), windows.get((a, b), PANEL_MASK)
    yield (east, north), (east, south), PANEL_MASK
    for b, a in pairwise(reversed(cuts)):
        mask = None if (a, b) == DOOR else windows.get((a, b), PANEL_MASK)
        yield (b, south), (a, south), mask
    yield (west, south), (west, north), PANEL_MASK


def _make_car(layout, track):
    """Translate one flush slab with a supported rider and an open side door.

    Like Stockyard's full-wall shuttle, the car is saved at ON and only its
    host shares drag points. A flush deck makes all the hull masks equilevel.
    The slab goes east on OFF. Both ends and both flanks leave a standing lane.
    """
    host = layout.regions[track]
    car = track + "_car"
    edges = list(_car_edges())
    outline = [a for a, _, _ in edges]
    layout.add_region(
        car, outline, type=616, floor_z=host.floor_z, ceiling_z=host.ceiling_z,
        wall_picnum=109, portal_wall_picnum=109, floor_picnum=1717, ceiling_picnum=454,
        floor_shade=0, wall_shade=0, ceiling_shade=0, relative_alignment="floor",
        layer=host.layer, intent={"kind": "furnished"},
        sector_behavior={"state": 1, "busy": 65536, "drag": 1, "busy_wave_a": 1,
                         "busy_wave_b": 1, "busy_time_a": 55, "busy_time_b": 55})
    layout.carve_hole(track, outline)
    for index, (a, b, mask) in enumerate(edges):
        layout.add_connection(f"{car}:edge:{index}", car, track, a1=a, a2=b,
                              min_width=1, min_opening=BODY.standing_height)
        if mask is not None:
            length = abs(b[0] - a[0]) + abs(b[1] - a[1])
            _mask(layout, car, track, a, b, mask,
                  x_repeat=8 if mask == WINDOW_MASK else max(1, length // 128),
                  y_repeat=3 if mask == WINDOW_MASK else 8,
                  shade=0 if mask == WINDOW_MASK else 3, pal=GREEN)
    layout.declare_motion(car, [track, car])
    x0, y0, x1, y1 = CAR
    on = ((x0 + x1) // 2, (y0 + y1) // 2)
    motion.place_markers(layout, "phantom_car", driven_region=car, on_at=on,
                         off_at=(on[0] + TRAVEL, on[1]), off_region=track, z=host.floor_z)
    wires.wire(RUN).then(wiring.region(car))
    return car



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
WATER_FLOOR = GHOST_FLOOR + 5632
SOUTH_EDGE = -12544
EDGE_BACK = -11904
PLATFORM_BACK = -10496
PLATFORM_LEFT, PLATFORM_RIGHT = 46848, 58624
BOOKING = (46592, -9984, 52224, -7936)
PLATFORM = (PLATFORM_LEFT, EDGE_BACK, PLATFORM_RIGHT, PLATFORM_BACK)
BAY_CLEAR = 24576
WATCHERS = (57984, 60928, 63872, 66816)


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
    edge = _room(part, "edge", (PLATFORM_LEFT, SOUTH_EDGE, PLATFORM_RIGHT, EDGE_BACK),
                 EDGE, GHOST_FLOOR + 768, clear=GHOST_CLEAR + 768, shades=(45, 35, 49))
    track = _room(part, "track", TRACK, BORE, TRACK_FLOOR, TRACK_FLOOR - TRACK_ROOF,
                  shades=(41, 40, 42))
    _connect(part, edge, "south", platform, "north", skin=386)
    _connect(part, edge, "north", track, "south", skin=205)
    booking_pool = _booking_hall(part, booking, platform)
    pools = _platform_rooms(part, platform, edge)
    stop = _service_line(part, platform, track)
    _drowned_siding(part, track)
    lamps = [*booking_pool, edge, *pools]
    track.raw("the last car and its pickup circuit",
              lambda layout, room: _run_car(layout, room, platform, stop, lamps))
    platform.raw("the first distant whistle and the lamps along the edge", _platform_entry)
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
    # Leave a full body of the original secret sector at the stair mouth.
    pool = _light_pool(part, booking, "booking_ticket",
                       (47040, -9680, 48992, -8448), (47360, -9440, 48640, -8656),
                       48000, -8912, clear=28672)
    # Three narrow beams with dark gaps left by the folded gate.
    for index, x in enumerate((49520, 49856, 50192)):
        _spill(part, booking, f"gate_{index}", (x, -9952, x + 160, -8768),
               GHOST_FLOOR, 28672)
    return pool


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


def _light_pool(part, host, name, outer, inner, x, y, *, clear=GHOST_CLEAR):
    ring = _inset(part, host, f"{name}_penumbra", _rect_outline(outer, 160), HALL,
                  GHOST_FLOOR, clear, (12, 14, 18))
    # The inner cut uses the ring's true edge names rather than a compass face.
    lit = _inset(part, ring, f"{name}_pool", _rect_outline(inner, 112), HALL,
                 GHOST_FLOOR, clear, (2, 5, 8))
    lit.raw("a round lamp casting a defined pool",
            lambda layout, room: _round_lamp(
                layout, room.region_id, f"{name}_lamp", x, y, shade=-24, size=52))
    return [ring, lit]


def _spill(part, host, name, rect, floor, clear, *, far=False):
    patch = _inset(part, host, f"spill_{name}", _rect_outline(rect),
                   Material(386, 1717, 379, 386), floor, clear, (2, 12, 30),
                   kind="phantom_green_spill")
    # The far pool is saved dark in the car's ON state. The OFF stop leaves
    # just its authored base shade, and the returning car closes the pool.
    if far:
        wires.wire(COACH).then(wiring.region(patch.region_id), state=1, busy=65536,
                              amplitude=54, shade_floor=1)
    else:
        wires.wire(DEPART).then(wiring.region(patch.region_id),
                               amplitude=57, shade_floor=1)
    return patch


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
                  Material(255, 1717, 174, 386), GHOST_FLOOR - 5120,
                  clear=22528, role="detail", shades=(1, 4, 8),
                  declared_zero_exit=True)
    _connect(part, board, "north", waiting, "south", skin=386, clear=0)
    board.raw("green enamel station name and its own lamp", _platform_name)
    beam = _inset(part, waiting, "stationmaster_beam",
                  _rect_outline((55744, -9856, 56640, -9200)), TIMBER,
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
    pools = []
    for name, x in (("platform_gate", 50240), ("platform_last", 55296)):
        pools.extend(_light_pool(
            part, platform, name, (x - 1056, -11856, x + 1056, -10544),
            (x - 704, -11648, x + 704, -10752), x, -11168))
    ring, flicker = _light_pool(
        part, platform, "platform_failing", (52672, -11856, 54176, -10544),
        (53024, -11648, 53824, -10752), 53424, -11168)
    wires.wire(SPILL_OFF).then(
        wiring.region(flicker.region_id), state=1, busy=65536,
        amplitude=43, shade_wave=6, shade_frequency=13, shade_phase=4,
        shade_floor=1, shade_ceiling=1, shade_walls=1)
    pools.append(ring)
    near = _room(part, "first_edge_pool", (47968, -12392, 48736, -11976),
                 EDGE, GHOST_FLOOR + 768, GHOST_CLEAR + 768, shades=(3, 8, 11))
    edge.carve(near.outline)
    for side in COMPASS:
        part.connect(near.face(side), edge.face("north"), min_width=1,
                     connection_id=f"connection:phantom_first_light:{side}")
    wires.wire(PLATFORM_ENTRY).then(wiring.region(near.region_id),
                                   amplitude=48, shade_floor=1, shade_ceiling=1)
    _platform_barrier(part, platform)
    for i, (left, right) in enumerate(WINDOWS):
        _spill(part, edge, f"window_{i}", (left, -12512, right, -12344),
               GHOST_FLOOR + 768, GHOST_CLEAR + 768)

    porch = _room(part, "signal_step", (57152, PLATFORM_BACK, 58368, -10048),
                  EDGE, GHOST_FLOOR - 2048, BAY_CLEAR, shades=(31, 30, 39))
    cabin = _room(part, "signal_cabin", (57088, -10048, 58560, -8192),
                  SERVICE, GHOST_FLOOR - 4096, BAY_CLEAR, shades=(22, 23, 30))
    _connect(part, porch, "north", platform, "south", skin=386)
    _connect(part, porch, "south", cabin, "north", skin=386)
    cabin.raw("the station side of the rail recall circuit", _signal_dress)
    return [waiting, *pools]


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
    for i, (left, right) in enumerate(WINDOWS):
        _spill(part, catwalk, f"berth_{i}", (left + TRAVEL, SOUTH_EDGE + 48,
               right + TRAVEL, SOUTH_EDGE + 336), GHOST_FLOOR + 3072,
               BAY_CLEAR + 2048, far=True)
    stop = _room(part, "brick_stop", (66560, -10368, 69632, -8704),
                 BRICK, GHOST_FLOOR + 2048, BAY_CLEAR, shades=(24, 26, 33))
    _connect(part, stop, "north", catwalk, "south", skin=386)
    bench = setpieces.raised_solid(
        part, "phantom_mortar_bench", stop, (66752, -9584, 67696, -8984),
        TIMBER, grade=GHOST_FLOOR + 2048, rise=6144, host_clear=BAY_CLEAR, shade=20)
    bench.raw("stacked bricks left by the men who closed the line", _mortar_table)
    stop.raw("the bricking gang left their tools by the return switch", _stop_dress)
    catwalk.raw("bulkhead lamps and directions for the return walk", _walk_dress)

    end = _room(part, "blind_tunnel", (TRACK[2], TRACK[1], 72192, SOUTH_EDGE),
                BORE, GHOST_FLOOR + 2048, BAY_CLEAR, shades=(39, 32, 43))
    _connect(part, end, "west", track, "east", skin=358)
    end.raw("a brick plug across the old running tunnel", _buffers)
    for index, x in enumerate(WATCHERS):
        mouth = _room(part, f"watch_mouth_{index}", (x, -17472, x + 1152, TRACK[1]),
                      EDGE, TRACK_FLOOR, BAY_CLEAR, shades=(37, 33, 41))
        niche = _room(part, f"watch_niche_{index}", (x, -18496, x + 1152, -17472),
                      SERVICE, TRACK_FLOOR, BAY_CLEAR, shades=(3, 2, 6),
                      declared_zero_exit=True)
        _connect(part, mouth, "south", track, "north", skin=358)
        _connect(part, mouth, "north", niche, "south")
        niche.raw("a watcher and a masked iron screen at equal height",
                  lambda layout, room, front=mouth, left=x, i=index:
                  _watcher(layout, room, front, left, i))
    return stop


#: The drowned car's end wall, along y: two windows and the gangway door between.
SUNK_FACE = 39936
SUNK_WINDOWS = ((-16320, -15424), (-14272, -13376))
SUNK_DOOR = (-15232, -14464)
SUNK_CLEAR = 26624


def _drowned_siding(part, track):
    """The line falls under black water; the next car stands in it, still lit and still full."""
    sill = _room(part, "siding", (45056, TRACK[1], TRACK[0], SOUTH_EDGE),
                 BORE, GHOST_FLOOR + 2048, BAY_CLEAR + 2048, shades=(38, 33, 40))
    water_motion = {"depth": 1, "pan_always": 1, "pan_floor": 1,
                    "pan_angle": 1024, "pan_velocity": 2}
    flood = _room(part, "drowned", (SUNK_FACE, TRACK[1], 45056, SOUTH_EDGE), WATER,
                  WATER_FLOOR, SUNK_CLEAR, shades=(40, 36, 44), sector_behavior=water_motion)
    _connect(part, sill, "east", track, "west", skin=358)
    _connect(part, flood, "east", sill, "west", skin=386)
    saloon = _room(part, "sunk_car", (36864, -16448, SUNK_FACE - 192, -13248),
                   Material(109, 2915, 454, 109), WATER_FLOOR, SUNK_CLEAR,
                   shades=(6, 0, 0), declared_zero_exit=True)
    saloon.intent = {"kind": "phantom_cab_green"}
    for index, (low, high) in enumerate(SUNK_WINDOWS):
        bay = _room(part, f"sunk_window_{index}", (SUNK_FACE - 192, low, SUNK_FACE, high),
                    Material(109, 2915, 454, 109), WATER_FLOOR, SUNK_CLEAR,
                    shades=(6, 0, 0), declared_zero_exit=True)
        bay.intent = {"kind": "phantom_cab_green"}
        _connect(part, bay, "west", saloon, "east")
        _connect(part, bay, "east", flood, "west")
        bay.raw("a carriage window the tide has reached", lambda layout, room, y0=low, y1=high:
                _sunk_window(layout, room, flood.region_id, y0, y1))
        _inset(part, flood, f"sunk_glow_{index}",
               ((SUNK_FACE + 64, low + 96), (SUNK_FACE + 1792, low - 160 + 320 * index),
                (SUNK_FACE + 1792, high - 160 + 320 * index), (SUNK_FACE + 64, high - 96)),
               WATER, WATER_FLOOR, SUNK_CLEAR, (2, 36, 44), kind="phantom_green_spill",
               declared_zero_exit=True, sector_behavior=water_motion)
    saloon.raw("the second car's passengers, sitting in the water", _sunk_passengers)
    flood.raw("the second car's end wall and its one headlamp", _sunk_end)


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
    base = region.rsplit("/", 1)[0]
    lamp = _round_lamp(layout, base + "/first_edge_pool", "first_edge_lamp",
                       48128, -12176, shade=-24, type=456, cstat=161, behavior={"state": 1})
    wires.wire(PLATFORM_ENTRY).then(wiring.placement(lamp))
    for index, x in enumerate((51456, 55360, 57728)):
        _round_lamp(layout, region, f"edge_lamp_{index}", x, -12176,
                    shade=55 if index == 1 else 9)
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
        x = 57088
        y = round(sum(point[1] for point in outline) / 4)
        piece.raw("the courses' faces, in the gang's lantern light",
                  lambda layout, room, loop=outline: [layout.paint_wall(
                      platform.region_id, a, b, picnum=383, shade=3)
                      for a, b in pairwise((*loop, loop[0]))])
        piece.raw("a broken brick on its unfinished course",
                  lambda layout, room, index=i, cx=x, cy=y: _prop(
                      layout, room.region_id, f"brick_top_{index}", cx, cy,
                      51 + index % 2, 13, 16, shade=3))
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
    ring, pool = _light_pool(
        part, platform, "gang_lantern", (57360, -11632, 58544, -10568),
        (57552, -11488, 58448, -10728), 58112, -10976)
    for piece in (ring, pool):
        wires.wire(DEPART).then(wiring.region(piece.region_id),
                               amplitude=36, shade_floor=1, shade_ceiling=1)


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
        (58240, -11372, 51, 22, 21), (57472, -10832, 52, 20, 22),
        (57696, -11680, 51, 25, 18),
    )):
        space = _phantom_floor(layout, x, y, GHOST_FLOOR)
        _prop(layout, space, f"bricking_gang_{i}", x, y, tile, width, height, shade=-13)
    # The lit undercoat and pale frieze get separate wall records at the
    # ends of the pool. The opposite corner remains black.
    _split_lit_wall(layout, station, (51968, PLATFORM_BACK), (52608, PLATFORM_BACK),
                    shade=12, tile=369)


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
    _round_lamp(layout, region, "signal_lamp", 57856, -9296, size=36, shade=1)
    _call(layout, region, "signal", (58560, -9840), (58560, -8512))
    _bill(layout, region, "signal_clock", (58432, -8192), (57216, -8192),
          1165, 32, 1.01)


def _stop_dress(layout, room):
    region = room.region_id
    _round_lamp(layout, region, "stop_lamp", 68224, -9728, shade=-5)
    _call(layout, region, "brick", (69568, -8704), (66624, -8704))
    _sign(layout, region, "way_back", (66560, -8832), (66560, -10240),
          "STAIRS", size=45, height=0.98)
    _prop(layout, region, "scattered_brick", 67136, -9824, 51, 29, 25, shade=11)
    _prop(layout, region, "sweeper", 69248, -9280, 2333, 44, 46, shade=0)
    _prop(layout, region, "cloak", 68000, -9250, 896, 40, 40, type=113, status=3, shade=-8)


def _mortar_table(layout, room):
    region = room.region_id
    _prop(layout, region, "brick_offcut", 67008, -9272, 52, 23, 20, shade=4)
    _prop(layout, region, "brick_stack", 67456, -9248, 51, 25, 25, shade=5)


def _walk_dress(layout, room):
    region = room.region_id
    for i, x in enumerate((61056, 63616, 66944, 68736)):
        _round_lamp(layout, region, f"return_lamp_{i}", x, -11616, size=31, shade=17)
    _sign(layout, region, "return", (62528, -10368), (60416, -10368),
          "TO STAIRS", size=49, height=0.97)


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
    _prop(layout, region, "watcher", x + 576, -18016, 799, 52, 51, shade=40)
    _round_lamp(layout, region, f"watcher_lamp_{index}", x + 576, -18016,
                size=24, shade=-19)


def _sunk_window(layout, room, water, low, high):
    """The running car's own window frame, sill and head, hung on the drowned face."""
    region = room.region_id
    _mask(layout, region, water, (SUNK_FACE, low), (SUNK_FACE, high), WINDOW_MASK,
          shade=0, x_repeat=8, y_repeat=3, pal=GREEN)
    middle, width = (low + high) // 2, high - low - 8
    _panel(layout, region, f"sunk_sill_{low}", SUNK_FACE - 24, middle,
           WATER_FLOOR - 3400, 1665, width, 6784, shade=4, angle=0, pal=GREEN)
    _panel(layout, region, f"sunk_head_{low}", SUNK_FACE - 24, middle,
           WATER_FLOOR - SUNK_CLEAR + 2600, 386, width, 4800, shade=3, angle=0, pal=GREEN)


def _sunk_passengers(layout, room):
    region = room.region_id
    for i, (x, y, tile) in enumerate((
        (39168, -15996, 2330), (38720, -15568, 2333), (39232, -14020, 2330),
        (38656, -13600, 2334), (38336, -14848, 2330),
    )):
        _prop(layout, region, f"sunk_passenger_{i}", x, y, tile, 46, 50,
              cstat=144, angle=0, shade=-5, support=WATER_FLOOR - 3072)
    for i, x in enumerate((39232, 37888)):
        _round_lamp(layout, region, f"sunk_lamp_{i}", x, -14848, size=46, shade=-35, pal=GREEN)


def _sunk_end(layout, room):
    region = room.region_id
    # the rails go on under the water, seen through it
    for i, x in enumerate(range(44544, 40960, -1024)):
        _flat(layout, region, f"sunk_rails_{i}", x, -14848, WATER_FLOOR - 24, 1129,
              1024, 2048, shade=8 + 6 * i, cstat=162)
    for low, high in ((-16448, -16320), (-15424, -14272), (-13376, -13248)):
        _split_lit_wall(layout, region, (SUNK_FACE, high), (SUNK_FACE, low), shade=3,
                        tile=PANEL_MASK, pal=GREEN)
    middle = sum(SUNK_DOOR) // 2
    _panel(layout, region, "sunk_gangway", SUNK_FACE + 20, middle, WATER_FLOOR - 8704,
           199, SUNK_DOOR[1] - SUNK_DOOR[0], 17408, shade=8, angle=0, pal=GREEN)
    _panel(layout, region, "sunk_number", SUNK_FACE + 36, middle, WATER_FLOOR - 18900,
           1407, 400, 2880, shade=-10, angle=0, pal=GREEN)
    _panel(layout, region, "sunk_headlamp", SUNK_FACE + 40, middle, WATER_FLOOR - 23000,
           624, 310, 5224, shade=-45, angle=0, pal=9)


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


def _coach_seats(layout, car):
    body_flags = 144 | mechanism.CARRY_WITH
    width = 800
    # E1M2 sprites 95/98/101 show the seated and slumped poses together.
    seats = (49056, 49888, PRIZE_AT[0], 51616, 52480, 53344, 54208, 55072)
    for j, (x, front) in enumerate([(x, -15392) for x in seats] +
                                    [(49600, -14112), (55040, -14112)]):
        north = j < len(seats)
        back = front - 544 if north else front + 544
        _flat(layout, car, f"seat_top_{j}", x, (front + back) // 2,
              SEAT_Z, 67, width, 544, carry=mechanism.CARRY_WITH,
              shade=-40 if x == PRIZE_AT[0] else 10)
        _panel(layout, car, f"seat_front_{j}", x, front, TRACK_FLOOR - 3328,
               67, width, 6400, shade=-40 if x == PRIZE_AT[0] else 14, angle=512,
               carry=mechanism.CARRY_WITH)
        # a pale lit back behind the prize: a black gun on brown boards is not seen
        lit = x == PRIZE_AT[0]
        _panel(layout, car, f"seat_back_{j}", x, back, SEAT_Z - (4600 if lit else 2208),
               1717 if lit else 298, width, 9000 if lit else 4352,
               shade=-40 if lit else 6, pal=GREEN if lit else 0, angle=512,
               carry=mechanism.CARRY_WITH)
        if x == PRIZE_AT[0]:
            continue
        tile = SEATED[(2, 0, 0, 0, 1, 0, 0, 2, 0, 1)[j]]
        _prop(layout, car, f"passenger_{j}", x, front - 146 if north else front + 104,
              tile, 42, 48, cstat=body_flags, angle=512, shade=-5, support=SEAT_Z)
    x, y = PRIZE_AT
    _round_lamp(layout, car, "empty_seat_spot", x, y - 250, size=64,
                shade=-35, pal=GREEN, carry=mechanism.CARRY_WITH)
    _prop(layout, car, "conductor", CAR[2] - 544, -15744, 1727, 43, 41,
          cstat=128 | mechanism.CARRY_WITH, seat="ceiling", shade=1)
    _panel(layout, car, "conductor_door", CAR[2] - 38, -15720,
           TRACK_FLOOR - 11200, 199, 848, 21120, shade=13, angle=1024,
           pal=GREEN, carry=mechanism.CARRY_WITH)


def _furnish_car(layout, car):
    carry = mechanism.CARRY_WITH
    for index, (left, right) in enumerate(WINDOWS):
        x, width = (left + right) // 2, right - left - 8
        for side, y, angle in (("north", CAR[1] + 64, 512),
                               ("south", CAR[3] - 64, 1536)):
            _panel(layout, car, f"window_sill_{side}_{index}", x, y,
                   TRACK_FLOOR - 7616, 1665, width, 6784,
                   shade=-2, angle=angle, carry=carry, pal=GREEN)
            _panel(layout, car, f"window_head_{side}_{index}", x, y,
                   TRACK_ROOF + 2600, 386, width, 4800,
                   shade=3, angle=angle, carry=carry, pal=GREEN)
            _panel(layout, car, f"underframe_{side}_{index}", x, y,
                   TRACK_FLOOR - 2048, 470, width, 3840,
                   shade=17, angle=angle, carry=carry)
        lamp = _round_lamp(layout, car, f"car_lamp_{index}", x, -14976,
                           shade=-35, pal=GREEN, carry=carry, type=456,
                           behavior={"state": 1})
        wires.wire(LAMP_PULSE).then(wiring.placement(lamp))
        if index in (1, 3):
            _panel(layout, car, f"bloodied_pane_{index}", x + 176, CAR[3] - 112,
                   TRACK_FLOOR - 15040, 713, 296, 4160,
                   shade=10, angle=1536, carry=carry)
    door = sum(DOOR) // 2
    # Seven folded steel plates form the carried destination fascia. Small
    # plates sort with their own lettering from either end of the platform.
    for index, letter in enumerate("PHANTOM"):
        x = door - 336 + 112 * index
        _panel(layout, car, f"door_cornice_{index}", x, CAR[3] - 96,
               TRACK_ROOF + 2992, 255, 112, 5632,
               shade=6, angle=1536, carry=carry)
        _panel(layout, car, f"destination_letter_{index}", x, CAR[3] - 32,
               TRACK_ROOF + 2992, wallplane.tile_for(letter), 84, 2432,
               shade=-27, angle=512, carry=carry, pal=5)
    # E1M2's green fleet numeral beside the destination board.
    _panel(layout, car, "fleet_number", door + 310, CAR[3] - 48,
           TRACK_ROOF + 6976, 1407, 248, 1380, shade=-17, angle=512, carry=carry)
    _flat(layout, car, "threshold_step", door, CAR[3] - 178,
          TRACK_FLOOR - 16, 438, 960, 240, carry=carry, shade=3)
    _panel(layout, car, "boarding_lamp", door + 387, CAR[3] - 88,
           TRACK_ROOF + 9744, 795, 167, 2368, shade=-22,
           angle=1536, carry=carry, pal=GREEN)
    _panel(layout, car, "rear_livery", CAR[0] + 36, -14848,
           TRACK_FLOOR - 7616, 1665, 2824, 6784, shade=9, angle=0,
           carry=carry, pal=GREEN)
    for i, x in enumerate((49472, 55168)):
        _panel(layout, car, f"car_wheelset_{i}", x, CAR[3] - 12,
               TRACK_FLOOR - 2050, 2320, 792, 3840,
               shade=15, angle=1536, carry=carry)
    _coach_seats(layout, car)


def apply_surface_palette(layout, compiled):
    """Finish authored green and cold mounts after ordinary city materials."""
    for name, region in layout.regions.items():
        allocation = compiled.allocations.get(name)
        if allocation is None:
            continue
        leaf = name.rsplit("/", 1)[-1]
        kind = (region.intent or {}).get("kind")
        if kind in {"phantom_green_spill", "phantom_cab_green"} or leaf == "track_car":
            palette = GREEN
        elif leaf.startswith("watch_niche_"):
            palette = 10
        else:
            continue
        fields = record_fields(compiled.level.sectors[allocation.sector_id])
        fields["floor_pal"] = palette
        if kind != "phantom_green_spill":
            fields["ceiling_pal"] = palette
        if kind == "phantom_cab_green" or leaf.startswith("watch_niche_"):
            for index in allocation.wall_ids:
                record_fields(compiled.level.walls[index])["pal"] = palette


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


def _coach_controls(layout, car, station, stop):
    """The handle and the loot start one show, with repeatable travel afterwards."""
    run = wires.wire(RUN)
    departure = wires.wire(DEPART)
    guns = _prop(layout, car, "prize", *PRIZE_AT, 558, 48, 48, support=SEAT_Z,
                 type=42, status=3, cstat=128 | mechanism.CARRY_WITH, shade=-48)
    prize = wires.wire(PRIZE)
    prize.when(wiring.placement(guns), "pickup", command=motion.CMD_ON,
               once=True, dude_lockout=1)
    handle = layout.add_sprite(
        "phantom:driver_handle", car, x=CAR[2] - 88, y=-14688, z=TRACK_FLOOR - 12672,
        type=20, picnum=1070, angle=1024, cstat=208 | mechanism.CARRY_WITH,
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

    # A decoupled Enter reports ON without changing the mover. Its OFF stop also
    # reports its own state, so the two commands reach different receivers.
    coach = wires.wire(COACH)
    coach.when(wiring.region(car), "enter", command=motion.CMD_STATE, once=True,
               on=True, off=True, decoupled=1, dude_lockout=1)
    board_gate = _marker(layout, "boarding_sense", station, 52432, -11600, 20)
    coach.then(wiring.placement(board_gate))
    gate = wires.wire("phantom:boarding-arm")
    gate.when(wiring.placement(board_gate), "relay", command=motion.CMD_ON)
    once = _marker(layout, "boarding_latch", station, 52464, -11600, 20)
    gate.then(wiring.placement(once))
    boarding = wires.wire(BOARDING)
    boarding.when(wiring.placement(once), "relay", command=motion.CMD_ON)
    pulse = _marker(layout, "boarding_pulse", station, 52496, -11600, 20)
    boarding.then(wiring.placement(pulse), wait_time=2)
    wires.wire(LAMP_PULSE).when(wiring.placement(pulse), "relay",
                               command=motion.CMD_NOT_STATE, off=True)
    arrival = _marker(layout, "arrival_quote", stop.region_id, 68160, -9700, 20, state=1)
    coach.then(wiring.placement(arrival))

    from caleb import ghost_tunnel
    ghost_tunnel(layout, stop, arrival_switch=arrival)


def _run_car(layout, track, platform, stop, lamps):
    car = _make_car(layout, track.region_id)
    _furnish_car(layout, car)
    station = platform.region_id
    _coach_controls(layout, car, station, stop)
    departure = wires.wire(DEPART)
    horn = _marker(layout, "whistle", station, 52304, -11584, 711, 2519, data_1=276)
    quake = _marker(layout, "quake", station, 52544, -11300, 19, 2072, data_1=1200)
    for placement in (horn, quake):
        departure.then(wiring.placement(placement))
    for i, x in enumerate((59264, 63872)):
        spawn = _marker(layout, f"spawn_{i}", track.region_id, x, -16768, 18, 2077,
                        angle=1024, data_1=210)
        departure.then(wiring.placement(spawn))
    relay = _marker(layout, "track_spill_dimmer", station, 52528, -11600, 20)
    departure.then(wiring.placement(relay))
    off = wires.wire(SPILL_OFF)
    off.when(wiring.placement(relay), "relay", command=motion.CMD_OFF)
    # The fixed track host cannot be cut. Its spill is nonblocking native
    # floor art. The Crate Face receiver removes it permanently on OFF.
    for index, (left, right) in enumerate(WINDOWS):
        spill = _flat(layout, track.region_id, f"track_spill_{index}",
                      (left + right) // 2, -12912, TRACK_FLOOR - 12, 455,
                      right - left - 32, 576, pal=GREEN, shade=-58, cstat=162,
                      type=405, behavior={"state": 1})
        off.then(wiring.placement(spill))

    import ambience
    for suffix, space, x, y, context in (
        ("station", station, 47200, -11000, "interior"),
        ("siding", station.rsplit("/", 1)[0] + "/drowned", 44000, -14000, "sewer"),
    ):
        z = layout.regions[space].floor_z - 6144
        layout.add_sprite(f"phantom:ambience_{suffix}", space, x=x, y=y, z=z,
                          **ambience.fields(context))
    shade = {"shade_floor": 1, "shade_ceiling": 1, "shade_walls": 1}
    for lamp in lamps:
        departure.then(wiring.region(lamp.region_id), amplitude=48, **shade)
    reveal = station.rsplit("/", 1)[0] + "/clerk"
    layout.regions[reveal].sector_behavior.update(
        shade_always=1, shade_wave=6, amplitude=-13, shade_frequency=10, **shade)

