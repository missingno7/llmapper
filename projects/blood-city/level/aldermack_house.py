"""Build and dress the Aldermack house from the measured theatre exemplars."""

from itertools import pairwise

from bloodmap import wiring
from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.mechanism import CMD_OFF, CMD_ON, curtain_spec
from bloodmap.placement import seated_z
from bloodmap.switches import pressed_switch
from bloodmap.texture_align import sprite_tile_extents

import caleb
import citytree
import curtains
import doorswitch
import wires
import wallplane
from materials import INTERIORS
from resolution import GRADE

STAGE_RISE, FLIES = 11520, 115712
HOUSE_CEILING, CIRCLE_RISE = 96256, 24576
RUNNER, FRAME, PLANKS, DRAPE, WOOD = 306, 1004, 15, 159, 88
SEAT, BACK, BEAMS = 42, 68, 28
HOUSE_WEST, HOUSE_EAST = 20480, 25600
AISLE_WIDTH = 1024
TERRACE_WEST, TERRACE_EAST = HOUSE_WEST + AISLE_WIDTH, HOUSE_EAST - AISLE_WIDTH
CENTER = 23040
STAGE_FRONT, APRON_BACK = 6912, 7168
OPENING = (21376, STAGE_FRONT, 24704, APRON_BACK)
SHOW_WIRE = "theatre:show"
SHOW_LATCH = "theatre:show-latch"
PIANO_WIRE = "theatre:pit-piano"
PRIZE_WIRE = "theatre:prize"
BOX_WIRE = "theatre:box-curtain"
HEADER = STAGE_RISE + 61056
WING_ROOF = STAGE_RISE + 28672
MAIN_WIRE = "theatre:curtain"
STRIPED_RED = 1004
MATERIAL = INTERIORS["theatre"]
COMPASS = dict(zip(RECT_FACES, range(4)))


def _room(parent, name, rect, *, floor=0, roof=HOUSE_CEILING,
          tile=RUNNER, wall=STRIPED_RED, ceiling=BEAMS,
          shades=(49, 49, 49),
          role="interior", note=""):
    x0, y0, x1, y1 = rect
    frame = parent.world_frame()
    room = citytree.make_room(
        parent, name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
        role=role, faces=dict(COMPASS),
        frame=Frame(x0 - frame.dx, y0 - frame.dy, -frame.dz),
        region_kwargs=MATERIAL.region_kwargs(),
        note=note or name.replace("_", " ").capitalize() + ".")
    room.intent.update(kind=f"aldermack_{name}", furnished=True)
    floor_shade, ceiling_shade, wall_shade = shades
    return room.surfaces(
        floor_z=GRADE - floor, clear_height=roof - floor,
        floor_picnum=tile, ceiling_picnum=ceiling, wall_picnum=wall,
        floor_shade=floor_shade, ceiling_shade=ceiling_shade, wall_shade=wall_shade)


def _join(a, af, b, bf, **options):
    left = a.face(af) if isinstance(af, str) else af
    right = b.face(bf) if isinstance(bf, str) else bf
    return citytree.common(a, b).connect(left, right, **options)


def _span(room, face, start, stop):
    """A sub-face specified in world units along x or y."""
    anchor = room.face(face).anchor()
    axis = 0 if face in ("north", "south") else 1
    a, b = anchor.a[axis], anchor.b[axis]
    return room.face(face, at=((start + stop) / 2 - a) / (b - a), width=stop - start)


def _hole(host, rect):
    x0, y0, x1, y1 = rect
    frame = host.world_frame()
    index = len(host.holes)
    host.carve([(x - frame.dx, y - frame.dy)
                for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
    return index


def _inset(host, name, rect, *, reveal=None, **finish):
    hole = _hole(host, rect)
    room = _room(host, name, rect, role="detail", **finish)
    for face in RECT_FACES:
        _join(room, face, host, host.hole_face(hole, face),
              min_width=1, min_opening=0, face_picnum=reveal)
    return room


def _flight(parent, name, rect, floors, *, axis, roof, tile=300, reverse=False):
    """Rectangular treads ordered from the approach to the destination."""
    x0, y0, x1, y1 = rect
    start, end = (x0, x1) if axis == "x" else (y0, y1)
    edges = [start + (end - start) * i // len(floors) for i in range(len(floors) + 1)]
    if reverse:
        edges.reverse()
    near, far = (("west", "east") if axis == "x" else ("north", "south"))
    if reverse:
        near, far = far, near
    steps = []
    for index, (rise, (a, b)) in enumerate(zip(floors, pairwise(edges)), 1):
        low, high = sorted((a, b))
        tread = (low, y0, high, y1) if axis == "x" else (x0, low, x1, high)
        steps.append(_room(parent, f"{name}_{index}", tread, floor=rise,
                           roof=roof, tile=tile, wall=WOOD))
    for step, next_step in pairwise(steps):
        _join(step, far, next_step, near)
    return steps


def _z_cloth(room, roof, wire):
    """A closed ceiling plane is the cloth under the fixed pelmet."""
    floor = room.effective_style()["floor_z"]
    room.region_kwargs.update(type=600, sector_behavior=z_motion_door(
        floor, GRADE - roof, interaction="remote", rx_id=wires.channel(wire),
        open_time=10, close_time=10))
    return room


def _proscenium(parent, stage, apron):
    """SCHOOL_'s three bays around the DWE1M9 s276 rising curtain."""
    curtain = _room(parent, "main_curtain", OPENING, floor=STAGE_RISE,
                    roof=STAGE_RISE, tile=PLANKS, ceiling=DRAPE, wall=DRAPE,
                    shades=(48, 50, 48), role="doorway")
    _z_cloth(curtain, HEADER, MAIN_WIRE)
    jamb = _room(parent, "pelmet", (OPENING[0], APRON_BACK, OPENING[2], APRON_BACK + 96),
                 floor=STAGE_RISE, roof=HEADER, tile=PLANKS, ceiling=FRAME, wall=FRAME,
                 shades=(49, 50, 45), role="gateway")
    _join(jamb, "south", apron, "north", face_picnum=FRAME)
    _join(curtain, "north", stage, "south", min_opening=0, gated=True, face_picnum=DRAPE)
    # the cloth's face to the house, lit by the footlights at its hem: at the
    # wall's own 45 a shut curtain was as dark as the wall it hangs in
    _join(curtain, "south", jamb, "north", min_opening=0, gated=True, face_picnum=DRAPE, face_shade=8)
    masks = []
    for side, x0, x1 in (("west", 20736, 21248), ("east", 24832, 25344)):
        bays = [
            _room(parent, f"{side}_drape_{end}", (x0, y0, x1, y1),
                  floor=STAGE_RISE, roof=STAGE_RISE + 51200, tile=PLANKS,
                  wall=FRAME, shades=(48, 50, 42), role="detail")
            for end, (y0, y1) in zip(("back", "front"),
                                    pairwise((STAGE_FRONT, 7088, APRON_BACK + 96)))
        ]
        _join(bays[0], "north", stage, "south")
        _join(bays[1], "south", apron, "north", face_picnum=FRAME)
        _join(bays[0], "south", bays[1], "north")
        masks.append((bays, ((x0, 7088), (x1, 7088))))
    return curtain, jamb, masks


def _polygon(parent, name, points, faces, **finish):
    x0, y0 = min(x for x, _ in points), min(y for _, y in points)
    x1, y1 = max(x for x, _ in points), max(y for _, y in points)
    room = _room(parent, name, (x0, y0, x1, y1), **finish)
    room.outline[:] = [(x - x0, y - y0) for x, y in points]
    room.faces = faces
    return room


def _wing_doors(parent, stage):
    """Four sliding cloth heads on the angled walls, as s280/281/322/323."""
    doors, wings = [], []
    for i, edge in enumerate(("wing_e1", "wing_e2", "wing_w2", "wing_w1")):
        host = stage.face(edge)
        a, b = host.anchor().a, host.anchor().b
        # Four corners are cut from the straight chords. The shutters' short
        # returns and the stone between them never meet a moving neighbour.
        a, b = sorted((tuple(round((7 * p + q) / 8) for p, q in zip(a, b)),
                       tuple(round((p + 7 * q) / 8) for p, q in zip(a, b))))
        north_a, north_b = (a[0], a[1] - 144), (b[0], b[1] - 144)
        back_a, back_b = (a[0], a[1] - 720), (b[0], b[1] - 720)
        door = _polygon(parent, f"stage_wing_door_{i}",
                        (north_a, north_b, b, a), dict(COMPASS),
                        floor=STAGE_RISE, roof=STAGE_RISE, tile=PLANKS, wall=DRAPE,
                        ceiling=DRAPE, shades=(59, 63, 63), role="doorway")
        _z_cloth(door, WING_ROOF, PRIZE_WIRE)
        wing = _polygon(parent, f"stage_watchers_{i}",
                        (back_a, back_b, north_b, north_a), dict(COMPASS),
                        floor=STAGE_RISE, roof=WING_ROOF, tile=PLANKS, wall=DRAPE,
                        shades=(55, 55, 42), role="detail")
        wing.region_kwargs["declared_zero_exit"] = True  # sealed until the pickup
        _join(door, "south", stage, edge, min_opening=0, gated=True, face_picnum=DRAPE)
        _join(door, "north", wing, "south", min_opening=0, gated=True, face_picnum=DRAPE)
        doors.append(door)
        wings.append(wing)
    return doors, wings


def _stage(parent, backstage, apron):
    # An eleven-sided chamber before the painted slit, measured from s279.
    outline = [(22016, 3824), (24064, 3824), (24960, 3968), (25728, 4352),
               (26368, 4864), (26368, STAGE_FRONT), (19712, STAGE_FRONT),
               (19712, 4864), (20352, 4352), (21120, 3968), (21600, 3872)]
    # The west stair's north edge is exactly the start of the long west wall.
    stage = _polygon(parent, "stage", outline,
                     {"north": 0, "wing_e1": 2, "wing_e2": 3, "east": 4, "south": 5,
                      "west": 6, "wing_w2": 7, "wing_w1": 8},
                     floor=STAGE_RISE, roof=FLIES, tile=PLANKS,
                     ceiling=BEAMS, wall=DRAPE, shades=(59, 50, 61),
                     note="The planked apse and the four watchers' drape doors.")
    cloth = _room(parent, "backcloth", (22016, 3584, 24064, 3824),
                  floor=STAGE_RISE, roof=65024, tile=PLANKS,
                  ceiling=448, wall=DRAPE, shades=(56, 50, 38), role="detail")
    _join(cloth, "south", stage, "north", face_picnum=DRAPE, face_shade=62)
    steps = _flight(parent, "west_wing_step", (19328, 4864, 19712, 5888),
                    (3840, 7680, STAGE_RISE), axis="x", roof=32768, tile=PLANKS)
    # A lintel over the stair's mouth carries its sign (aldermack_backstage):
    # the use reader could not tell how the dressing room reaches the stage.
    steps[0].surfaces(floor_z=GRADE - 3840, clear_height=26624 - 3840)
    _join(steps[0], "west", backstage, "stage_stair", face_picnum=WOOD)
    _join(steps[-1], "east", stage, "west")
    flats = [
        _inset(stage, f"scenic_flat_{side}", rect, floor=STAGE_RISE + 3072, roof=FLIES,
               tile=PLANKS, wall=20, shades=(57, 55, 62), reveal=20)
        for side, rect in (("west", (21040, 4384, 21680, 4544)),
                           ("east", (24880, 4496, 25648, 4656)))
    ]
    trap = _inset(stage, "trap", (22592, 4976, 23488, 5712),
                  floor=STAGE_RISE - 512, roof=FLIES, tile=20,
                  wall=20, shades=(51, 59, 55), reveal=20)
    slit = _inset(stage, "light_slit", (22400, 4072, 23680, 4224),
                  floor=STAGE_RISE, roof=FLIES, tile=PLANKS, ceiling=448,
                  wall=448, shades=(46, 56, 42), reveal=448)
    doors, wings = _wing_doors(parent, stage)
    curtain, jamb, masks = _proscenium(parent, stage, apron)
    return {"stage": stage, "flats": flats, "trap": trap, "cloth": cloth, "light_slit": slit,
            "curtain": curtain, "jamb": jamb, "masks": masks, "wing_doors": doors, "wings": wings}


def _pit(parent, floor, apron):
    pit = _room(parent, "orchestra_pit", (21600, 7680, 24166, 8704),
                floor=-8192, tile=PLANKS, wall=WOOD, shades=(40, 47, 35))
    steps = _flight(parent, "pit_step", (24166, 7680, 24678, 8704),
                    (-8192, -4096, 0), axis="y", roof=HOUSE_CEILING, tile=PLANKS)
    _join(pit, "north", apron, "south", min_opening=0)
    _join(steps[0], "north", apron, "south", min_opening=0)
    _join(steps[-1], "south", floor, "north")
    _join(pit, "south", floor, "north", min_opening=0)
    for step in steps:
        _join(step, "west", pit, "east")
    # E1M1's upright shape in s66: case, key shelf and a separate stool.
    hole = _hole(pit, (21728, 7816, 22304, 8568))
    case = _room(pit, "piano_case", (21728, 7816, 22176, 8568),
                 floor=4096, tile=20, wall=WOOD, shades=(28, 47, 29), role="detail")
    keys = _room(pit, "piano_keys", (22176, 7816, 22304, 8568),
                 floor=0, tile=620, wall=20, shades=(14, 47, 29), role="detail")
    for piece, flank, tile in ((case, "west", WOOD), (keys, "east", 20)):
        for face in ("north", "south", flank):
            _join(piece, face, pit, pit.hole_face(hole, face), min_width=1,
                  min_opening=0, face_picnum=tile)
    _join(keys, "west", case, "east", min_width=1, min_opening=0, face_picnum=WOOD)
    _inset(pit, "conductor_stand", (23072, 7808, 23584, 8048),
           floor=8000, wall=20, tile=68, shades=(48, 49, 48), reveal=WOOD)
    sides = []
    for side, x0, x1 in (("west", 20480, 21600), ("east", 24678, 25600)):
        flight = _flight(parent, f"{side}_apron_step", (x0, 7680, x1, 8704),
                         (3840, 7680, STAGE_RISE), axis="y", roof=HOUSE_CEILING,
                         reverse=True, tile=PLANKS)
        _join(flight[0], "south", floor, "north")
        _join(flight[-1], _span(flight[-1], "north", max(x0, 20582), min(x1, 25498)),
              apron, "south")
        for index, step in enumerate(reversed(flight)):
            if side == "west":
                _join(step, "east", pit, "west", min_opening=0)
            else:
                _join(step, "west", steps[index], "east", min_opening=0)
        sides.append(flight)
    return pit, sides


def _stalls(parent, approach):
    """DWE1M9 s274/275/277 compressed to three terraces and two lit side stairs."""
    terraces, benches, aisles = [], [], []
    for i in range(3):
        y = 10240 + i * 1024
        rise = 3072 + i * 6144
        rect = (TERRACE_WEST, y, TERRACE_EAST, y + 448)
        # A low warm wash over the rows: at the house's 49 the dead, the benches
        # and the rails ran together (critique round 1, the recognition and
        # use readers both).
        front = _room(parent, f"terrace_{i + 1}", rect, floor=rise, shades=(34, 49, 38))
        rear = _room(parent, f"terrace_tier_{i + 1}",
                     (TERRACE_WEST, y + 448, TERRACE_EAST, y + 1024),
                     floor=rise + 3072, wall=WOOD, shades=(32, 49, 36))
        _join(front, "south", rear, "north", face_picnum=WOOD)
        if terraces:
            _join(front, "north", terraces[-1][1], "south", face_picnum=WOOD)
        else:
            _join(front, "north", approach, "south", face_picnum=WOOD)
        benches.append(_bench(rear, "bench", 21632, 24448, y + 480, rise + 3072))
        terraces.append((front, rear))
    for side, x0, x1, inside in (
            ("west", HOUSE_WEST, TERRACE_WEST, "east"),
            ("east", TERRACE_EAST, HOUSE_EAST, "west")):
        stairs = _flight(parent, f"{side}_aisle_step", (x0, 10240, x1, 13312),
                         (3072, 6144, 9216, 12288, 15360, 18432),
                         axis="y", roof=HOUSE_CEILING, tile=RUNNER)
        _join(stairs[0], "north", approach, "south", face_picnum=WOOD)
        far = "west" if side == "west" else "east"
        for i, step in enumerate(stairs):
            step.surfaces(wall_picnum=STRIPED_RED)
            for tier in terraces[i // 2]:
                _overlap(step, inside, tier, far, min_width=1, min_opening=0, face_picnum=WOOD)
        aisles.append(stairs)
    return terraces, aisles, benches


def _bench(block, name, x0, x1, y, rise):
    """DWE1M9 s245/246: 256-deep wood seat and 256-deep back, on pilaster faces."""
    hole = _hole(block, (x0, y, x1, y + 512))
    seat = _room(block, name + "_seat", (x0, y, x1, y + 256),
                 floor=rise + 3072, tile=SEAT, wall=WOOD,
                 shades=(20, 48, 34), role="detail")
    back = _room(block, name + "_back", (x0, y + 256, x1, y + 512),
                 floor=rise + 8192, tile=BACK, wall=WOOD,
                 shades=(26, 48, 34), role="detail")
    for piece, edge in ((seat, "north"), (back, "south")):
        for face in ("west", "east", edge):
            _join(piece, face, block, block.hole_face(hole, face),
                  min_width=1, min_opening=0, face_picnum=WOOD)
    _join(back, "north", seat, "south", min_width=1, min_opening=0, face_picnum=WOOD)
    return seat


def _overlap(a, af, b, bf, **options):
    """Join an intersecting span on the two parallel faces."""
    axis = 0 if af in ("north", "south") else 1
    left = a.face(af).anchor()
    right = b.face(bf).anchor()
    start = max(min(left.a[axis], left.b[axis]), min(right.a[axis], right.b[axis]))
    stop = min(max(left.a[axis], left.b[axis]), max(right.a[axis], right.b[axis]))
    if start < stop:
        _join(a, _span(a, af, start, stop), b, _span(b, bf, start, stop), **options)


def _circle(parent, terraces, aisles, vomitory):
    lip = _room(parent, "circle_parapet", (20480, 13312, 25600, 13440),
                floor=CIRCLE_RISE + 3072, tile=409, wall=WOOD, role="detail")
    for section in (terraces[-1][-1], aisles[0][-1], aisles[1][-1]):
        _join(section, "south", lip, "north", face_picnum=WOOD, min_opening=0)
    front = _room(parent, "circle_front", (20480, 13440, 25600, 14208),
                  floor=CIRCLE_RISE, tile=RUNNER, wall=WOOD, shades=(36, 49, 43))
    rear = _room(parent, "circle_rear", (20480, 14208, 25600, 14950),
                 floor=CIRCLE_RISE + 2048, tile=RUNNER, wall=WOOD, shades=(40, 49, 44))
    _join(lip, "south", front, "north", face_picnum=409)
    _join(front, "south", rear, "north", face_picnum=WOOD)
    for tier, y, rise in ((front, 13568, CIRCLE_RISE), (rear, 14336, CIRCLE_RISE + 2048)):
        for side, x0, x1 in (("west", 21120, 22272), ("east", 23808, 24960)):
            _bench(tier, side, x0, x1, y, rise)
    flight = _flight(parent, "circle_step", (25728, 10240, 26496, 13824),
                     range(0, CIRCLE_RISE + 1, 3072), axis="y", roof=62464, tile=RUNNER)
    _join(flight[0], "north", vomitory, "south")
    landing = _room(parent, "circle_east_landing", (25600, 13824, 26496, 14208),
                    floor=CIRCLE_RISE, roof=57344, tile=RUNNER, wall=WOOD)
    _join(flight[-1], "south", landing, "north")
    _join(landing, "west", front, "east")
    return front, lip


def _boxes(parent, aisles, circle, parapet, apron_steps, stage):
    boxes, closed = [], []
    fin = None
    for i, (y0, y1, neighbours) in enumerate(
            ((7782, 8602, apron_steps[0]), (10368, 11520, aisles[0]),
             (11648, 13056, aisles[0]))):
        threshold = 20304 if i == 2 else 20352
        box = _room(parent, f"west_box_{i}", (19584, y0, threshold, y1),
                    floor=CIRCLE_RISE, roof=CIRCLE_RISE + 21504,
                    tile=SEAT, wall=DRAPE, shades=(36, 44, 37))
        if i == 2:
            spec = curtain_spec(opening=(threshold, y0, 20480, y1),
                                axis="y", anchored="high")
            faces = {name: index for name, x in (("west", threshold), ("east", 20480))
                     for index, (a, b) in enumerate(pairwise(spec["outline"] + spec["outline"][:1]))
                     if a[0] == b[0] == x and abs(a[1] - b[1]) == y1 - y0}
            sill = _polygon(parent, "box_curtain", spec["outline"], faces,
                            floor=CIRCLE_RISE + 4096, roof=CIRCLE_RISE + 21504,
                            tile=68, wall=FRAME, role="doorway")
            sill.intent["kind"] = "curtain"
            sill.region_kwargs.update(type=614, sector_behavior={
                "busy_time_a": curtains.BUSY, "busy_time_b": curtains.BUSY,
                "rx_id": wires.channel(BOX_WIRE)})
            fin = {"spec": spec, "room": sill, "name": "box_curtain", "wire": BOX_WIRE}
        else:
            sill = _room(parent, f"west_box_sill_{i}", (threshold, y0, 20480, y1),
                         floor=CIRCLE_RISE + 4096, roof=CIRCLE_RISE + 21504,
                         tile=68, wall=FRAME, role="detail")
        _join(sill, "west", box, "east", min_opening=0, face_picnum=WOOD)
        for room in neighbours:
            _overlap(sill, "east", room, "west", min_width=1,
                     min_opening=0, face_picnum=WOOD)
        boxes.append((box, sill))
        niche = _room(parent, f"east_false_box_{i}", (25600, y0, 25712, y1),
                      floor=CIRCLE_RISE + 4096, roof=CIRCLE_RISE + 20480,
                      tile=409, wall=DRAPE, shades=(37, 43, 26), role="detail")
        niche.region_kwargs["declared_zero_exit"] = True
        neighbours = apron_steps[1] if i == 0 else aisles[1]
        for room in neighbours:
            _overlap(niche, "west", room, "east", min_width=1,
                     min_opening=0, face_picnum=WOOD)
        closed.append(niche)
    # The stage box has its own short stair behind the proscenium's west leg.
    stage_box_stair = _flight(
        parent, "stage_box_step", (19712, STAGE_FRONT, 20352, 7782),
        (14784, 18048, 21312, CIRCLE_RISE), axis="y", roof=51200, tile=RUNNER)
    _join(stage_box_stair[0], "north", stage, "south", face_picnum=WOOD)
    _join(stage_box_stair[-1], "south", boxes[0][0], "north", face_picnum=WOOD)
    crossover = _room(parent, "box_crossover", (19584, 11520, 20160, 11648),
                      floor=CIRCLE_RISE, roof=CIRCLE_RISE + 21504, tile=SEAT, wall=WOOD)
    _join(crossover, "north", boxes[1][0], "south")
    _join(crossover, "south", boxes[2][0], "north")
    passage = _polygon(parent, "circle_west_passage",
                       ((19584, 13056), (20304, 13056), (20304, 13184),
                        (20480, 13184), (20480, 14208), (19584, 14208)),
                       {"north": 0, "east": 3},
                       floor=CIRCLE_RISE, roof=CIRCLE_RISE + 24576, tile=RUNNER, wall=WOOD)
    _join(boxes[-1][0], "south", passage, "north")
    _join(circle, "west", passage, "east")
    _overlap(passage, "east", parapet, "west", min_width=1, min_opening=0)
    _overlap(passage, "east", aisles[0][-1], "west", min_width=1, min_opening=0)
    return boxes, closed, fin


def build(venue, rooms):
    """Add the house and preserve the three room joins across ownership."""
    parent = venue.assembly("house", style=Style(), note="Stage, stalls, boxes and dress circle.")
    floor = _room(parent, "auditorium", (20480, 8704, 25600, 10240),
                  note="Front floor and cross aisle beneath the dome.")
    west = _room(parent, "pass_door_passage", (19456, 8704, 20480, 10240),
                 roof=24576, wall=WOOD)
    east = _room(parent, "vomitory", (25600, 8704, 26624, 10240),
                 roof=24576, tile=RUNNER, wall=WOOD)
    _join(west, "east", floor, "west", face_picnum=FRAME)
    _join(east, "west", floor, "east", face_picnum=FRAME)
    _join(east, "east", rooms["aldermack_foyer"], "west")
    rooms.update(aldermack_auditorium=floor, aldermack_pass_door_passage=west,
                 aldermack_vomitory=east)
    apron = _room(parent, "apron", (20582, APRON_BACK + 96, 25498, 7680),
                  floor=STAGE_RISE, tile=PLANKS, wall=FRAME, shades=(49, 48, 44))
    stage = _stage(parent, rooms["aldermack_backstage"], apron)
    pit, apron_steps = _pit(parent, floor, apron)
    terraces, aisles, benches = _stalls(parent, floor)
    circle, parapet = _circle(parent, terraces, aisles, east)
    boxes, false_boxes, box_curtain = _boxes(parent, aisles, circle, parapet, apron_steps, stage["stage"])
    dome = _inset(floor, "dome_rim", (21760, 8896, 24320, 10048),
                  roof=101376, tile=RUNNER, ceiling=409, wall=FRAME,
                  shades=(29, 46, 31), reveal=FRAME)
    crown = _inset(dome, "dome_crown", (22144, 9090, 23936, 9854),
                   roof=108544, tile=RUNNER, ceiling=422, wall=FRAME,
                   shades=(29, 46, 34), reveal=409)
    rooms.update(aldermack_stage=stage["stage"], aldermack_circle=circle)
    return {**stage, "box_curtain": box_curtain,
            "apron": apron, "pit": pit, "floor": floor, "benches": benches,
            "terraces": terraces, "aisles": aisles, "apron_steps": apron_steps, "parapet": parapet, "circle": circle,
            "boxes": boxes, "false_boxes": false_boxes, "crown": crown,
            "passages": (west, east)}


def _sprite(layout, name, room, tile, x, y, height=0, *, xr=64, yr=64,
            cstat=128, seat="floor", shade=0, **fields):
    """Place by drawn bottom or top, or at a stated centre height."""
    region = layout.regions[room.region_id]
    tile_h, offset = sprite_tile_extents()[tile]
    if seat == "centre":
        z = GRADE - height
    else:
        z = seated_z(seat=seat, floor_z=region.floor_z, ceiling_z=region.ceiling_z,
                     tile_height=tile_h, y_offset=offset, y_repeat=yr, cstat=cstat,
                     clearance=height)
    return layout.add_sprite(
        f"aldermack:{name}", room.region_id, x=x, y=y, z=z,
        picnum=tile, x_repeat=xr, y_repeat=yr, cstat=cstat, shade=shade, **fields)


def _face(layout, room, face, **fields):
    edge = room.face(face).anchor()
    layout.paint_wall(room.region_id, edge.a, edge.b, **fields)


def _chain(layout, name, room, x, y, mount_z, from_z, *, tile=694):
    """Extend a lamp or body hanger to its support using whole drawn links."""
    length = mount_z - from_z
    if length <= 0:
        return
    tile_h, offset = sprite_tile_extents()[tile]
    repeats = round(length / (4 * tile_h))
    level = from_z
    for i, repeat in enumerate(range(0, repeats, 128)):
        yr = min(128, repeats - repeat)
        z = seated_z(seat="ceiling", floor_z=mount_z, ceiling_z=level,
                     tile_height=tile_h, y_offset=offset, y_repeat=yr, cstat=128)
        layout.add_sprite(f"aldermack:{name}_{i}", room.region_id, x=x, y=y, z=z,
                          picnum=tile, x_repeat=32, y_repeat=yr, cstat=128, shade=32)
        level += 4 * tile_h * yr


def _hanger(layout, name, room, tile, x, y, height, *, xr, yr, shade,
            cstat=128, chain_tile=694, **fields):
    placement = _sprite(layout, name, room, tile, x, y, height,
                        xr=xr, yr=yr, shade=shade, cstat=cstat, **fields)
    tile_h, _offset = sprite_tile_extents()[tile]
    top = layout.regions[room.region_id].floor_z - height - 4 * tile_h * yr
    _chain(layout, name + "_chain", room, x, y, top,
           layout.regions[room.region_id].ceiling_z, tile=chain_tile)
    return placement


def _dress_stage(layout, built):
    stage, trap, apron, cloth = (built[key] for key in ("stage", "trap", "apron", "cloth"))
    _face(layout, built["pit"], "north", picnum=84, shade=48)
    _stage_title(layout, apron)
    # theatre red (2, as REALM4's drapes), the shut cloth and its legs alike
    _face(layout, built["jamb"], "north", pal=2)

    # HUNT s674, sprites 1665/1669: a player in a pool, a black silhouette on cloth.
    # The hanging woman and her gib sound are E1M3 s155, sprite 168.
    _sprite(layout, "hanged_performer", trap, 698, CENTER, 5280, 2560,
            xr=64, yr=62, cstat=385, shade=-21, type=416, status=4,
            behavior={"data_1": 8, "data_2": 16, "data_3": 5,
                      "data_4": 2205, "drop_item": 109})
    hero_top = layout.regions[trap.region_id].floor_z - 2560 - 4 * 128 * 62
    _chain(layout, "performer_rope", trap, CENTER, 5280, hero_top, GRADE - FLIES)
    # whole on the cloth: 832 wide, its edge 8 inside the backcloth's
    _sprite(layout, "performer_shadow", cloth, 698, CENTER + 600, 3592, 6656,
            xr=52, yr=56, shade=63, cstat=208, angle=512)
    _sprite(layout, "bloody_trap", trap, 1417, CENTER, 5300, 4,
            xr=43, yr=36, cstat=674, shade=7, pal=2)
    # Painted moon and torn, panelled towers, supported on their own flat runs.
    _sprite(layout, "painted_moon", cloth, 624, 22448, 3592, 42944,
            xr=68, yr=48, shade=8, pal=5, cstat=144, seat="centre", angle=512)
    for flat, x, y, palette in zip(built["flats"], (21360, 25264), (4492, 4604), (0, 4)):
        _sprite(layout, flat.node_id, flat, 2453, x, y, xr=63, yr=60,
                cstat=144, angle=512, shade=9, pal=palette)
    for i, y in enumerate((4640, 6128)):
        _sprite(layout, f"batten_{i}", stage, 20, CENTER, y, 49152 + 6144 * i,
                xr=204, yr=7, seat="centre", cstat=144, angle=512, shade=40)
        _sprite(layout, f"strand_{i}", stage, 258, CENTER, y + 6, 50688 + 6144 * i,
                xr=208, yr=22, seat="centre", cstat=144, angle=512, shade=26)
        _sprite(layout, f"diagonal_rope_{i}", stage, 513, (20980, 25092)[i], y + 96,
                52608, xr=105, yr=51, seat="centre", cstat=144 | (4 * i),
                angle=512, shade=34)
        _hanger(layout, f"stage_lamp_{i}", stage, 945, (22440, 23640)[i], y,
                30848 + i * 4096, xr=42, yr=44, shade=-18)
    # The ghost light, left burning on a dark stage: what shows through the
    # stair's mouth (round 2: "the opening reads as a black rectangle").
    _hanger(layout, "ghost_light", stage, 641, 20224, 4672, 8192,
            xr=56, yr=44, shade=-90)
    for i, x in enumerate((20992, 22016, 23040, 24064, 25088)):
        # EU11_ sprites 519–528 at 1024 centres. The flames sit in small cups.
        _sprite(layout, f"footlight_cup_{i}", apron, 554, x, 7536,
                xr=23, yr=16, shade=5)
        _sprite(layout, f"footlight_{i}", apron, 3566, x, 7536, 224,
                xr=12, yr=12, shade=-24)


def _stage_title(layout, apron):
    # DWE1M9 953/958: lamps strike the lettering and their chains disappear
    # into the stage head. The word belongs to this house.
    a, b = (OPENING[0] + 64, APRON_BACK + 96), (OPENING[2] - 64, APRON_BACK + 96)
    wallplane.text(layout, "aldermack:stage_title", apron.region_id, a, b,
                   words="ALDERMACK", size=74, palette=0, shade=-56,
                   top_z=GRADE - HEADER - 13568, over_steps=True, required=True)
    for side, x in enumerate((21136, 24944)):
        _hanger(layout, f"pelmet_lamp_{side}", apron, 641, x, 7440,
                HEADER - STAGE_RISE + 7808, xr=32, yr=31, shade=-26, chain_tile=745)


def _dress_house(layout, built):
    # E2M4 s613 uses the broad iron ring. Keep the visible canopy and extend
    # its hanger through the two recesses to the centre of the dome.
    # Up in the dome: at 54,272 it stood before the name and the beam from
    # every seat in the house.
    _hanger(layout, "chandelier", built["crown"], 549, CENTER, 9472, 74496,
            xr=68, yr=44, shade=-29)
    for passage, x in zip(built["passages"], (20224, 25856)):
        _sprite(layout, f"{passage.node_id}_sconce", passage, 554,
                x, 8728, 13568, xr=48, yr=48, cstat=448, angle=512, shade=-14, type=30)
        _sprite(layout, f"{passage.node_id}_plank_panel", passage, 457,
                x, 8720, xr=32, yr=17, cstat=144, angle=512, shade=-16)
    _dress_terraces(layout, built)
    for i, x in enumerate((21952, 22656, 23360, 24064)):
        _sprite(layout, f"pit_balustrade_{i}", built["floor"], 588,
                x, 8716, xr=21, yr=30, cstat=145, angle=512, shade=16)
    for i, (x, repeat) in enumerate(((21120, 39), (22400, 24), (23680, 24), (24960, 39))):
        # The narrower inner runs leave a body-wide gap for a drop to the stalls.
        _sprite(layout, f"circle_balustrade_{i}", built["parapet"], 588,
                x, 13376, xr=repeat, yr=24, cstat=145, angle=1536, shade=24)
    for i, (box, sill) in enumerate(built["boxes"]):
        y = round(sum(p[1] for p in box.world_outline()) / 4)
        _sprite(layout, f"box_candelabrum_{i}", box, 580, 19816, y - 150,
                xr=42, yr=44, shade=-9)
        if i < 2:
            _sprite(layout, f"box_balustrade_{i}", sill, 588, 20412, y,
                    xr=24, yr=24, cstat=145, angle=1024, shade=22)
        if i:
            _patron(layout, f"box_patron_{i}", box, 19920, y + 220)


def _dress_terraces(layout, built):
    # DWE1M9 832/833 transcribed at each end of every retained tread.
    for run in (*built["aisles"], *built["apron_steps"]):
        for step in run:
            points = step.world_outline()
            x0, x1 = min(x for x, _ in points), max(x for x, _ in points)
            y = min(y for _, y in points) + 124
            for end, x in enumerate((x0 + 112, x1 - 112)):
                for repeat, cstat, angle in ((8, 8322, 1792), (4, 8320, 1280)):
                    _sprite(layout, f"{step.node_id}_flare_{end}_{repeat}", step, 624,
                            x, y, xr=repeat, yr=repeat, cstat=cstat,
                            angle=angle, shade=-30, pal=8)
    for front, rear in built["terraces"]:
        for tier in (front, rear):
            y = min(p[1] for p in tier.world_outline())
            for i, x in enumerate(range(TERRACE_WEST + 256, TERRACE_EAST, 512)):
                # DWE1M9 752: rail centre at 4096 above its own terrace.
                _, yoff = sprite_tile_extents()[104]
                z = layout.regions[tier.region_id].floor_z - 4096 + 128 * yoff
                layout.add_sprite(
                    f"aldermack:{tier.node_id}_rail_{i}", tier.region_id,
                    x=x, y=y + 16, z=z, picnum=104, cstat=401, angle=1536,
                    x_repeat=32, y_repeat=32, shade=0)
        for side, x in enumerate((TERRACE_WEST + 144, TERRACE_EAST - 144)):
            y = min(p[1] for p in front.world_outline()) + 236
            _sprite(layout, f"{front.node_id}_newel_{side}", front, WOOD, x, y,
                    xr=14, yr=14, shade=-10, cstat=144, angle=1536)
            _sprite(layout, f"{front.node_id}_newel_light_{side}", front, 676,
                    x, y, 4 * sprite_tile_extents()[WOOD][0] * 14,
                    xr=8, yr=8, shade=-34)


def _dress_pit(layout, pit):
    _sprite(layout, "piano_stool", pit, 284, 22512, 8192, xr=32, yr=24,
            cstat=385, shade=8, type=416, status=4,
            behavior={"data_1": 5, "data_2": 20, "data_4": 312})
    edge = ((22304, 7816), (22304, 8568))
    piano = wires.wire(PIANO_WIRE)
    piano.when(wiring.face(pit.region_id, *edge), "push", command=CMD_ON, off=True)
    sound = layout.add_sprite(
        "aldermack:piano_sound", pit.region_id, x=22400, y=8260, z=13312,
        picnum=2519, type=708, status=0, cstat=32896,
        behavior={"data_2": 279, "wait_time": 2})
    piano.then(wiring.placement(sound))


def _patron(layout, name, room, x, y, *, terrace=False):
    # THESLUMS sprites 771, 773, 775: bloodied seated man and its gib record.
    return _sprite(layout, name, room, 2330, x, y,
                   xr=40, yr=40, cstat=400 if terrace else 384, angle=1536,
                   shade=-6, type=416, status=4,
                   behavior={"data_1": 8, "data_2": 16, "data_4": 318})


def _wire_show(layout, built):
    stage, curtain, trap = (built[key] for key in ("stage", "curtain", "trap"))
    region = layout.regions[stage.region_id]
    main = wires.wire(MAIN_WIRE)
    main.then(wiring.region(curtain.region_id))
    result = curtains.link_stage_light(layout, curtain.region_id, stage_region=stage.region_id)
    for room in (*built["flats"], trap, built["cloth"], built["light_slit"]):
        xsector = layout.regions[room.region_id].sector_behavior
        xsector.update(amplitude=-33 if room == built["light_slit"] else -24,
                       shade_floor=1, shade_ceiling=1, shade_walls=1)
        wires.wire("theatre:stage-light").then(wiring.region(room.region_id))
    # LinkSector sends the stage's ON edge when the curtain reaches full
    # travel. The latch takes ON and holds it for the rest of the level.
    latch = layout.add_sprite("aldermack:show_latch", stage.region_id,
                              x=CENTER, y=6000, z=region.floor_z - 1024,
                              picnum=0, cstat=32896, type=0, status=0)
    wires.wire(SHOW_LATCH).when(wiring.region(stage.region_id), wiring.RELAY,
                                command=CMD_ON).then(wiring.placement(latch))
    show = wires.wire(SHOW_WIRE)
    show.when(wiring.placement(latch), wiring.RELAY, command=CMD_ON)
    caleb._line(layout, show, region, 3101, CENTER, 6160)

    for i, bench in enumerate(built["benches"]):
        y = round(sum(p[1] for p in bench.world_outline()) / 4)
        _patron(layout, f"patron_still_{i}", bench, CENTER - 896, y, terrace=True)
        _sprite(layout, f"patron_alive_{i}", bench, 3798, CENTER + 866, y,
                xr=40, yr=40, cstat=384, shade=0, type=245, status=6,
                angle=1536)
        if i == 1:
            continue
        patron = _patron(layout, f"patron_rousing_{i}", bench, CENTER - 24, y, terrace=True)
        show.then(wiring.placement(patron))
        # E3M2 sprite 872, with a normal axe zombie instead of the hand.
        marker = layout.add_sprite(f"aldermack:rouse_{i}", bench.region_id,
                                   x=CENTER - 24, y=y, z=layout.regions[bench.region_id].floor_z,
                                   type=18, picnum=2077, cstat=32896,
                                   x_repeat=64, y_repeat=64, angle=1536,
                                   behavior={"trigger_once": 1, "data_1": 203})
        show.then(wiring.placement(marker))

    wing_control = doorswitch.place(layout, "aldermack:fly_lever", stage.region_id,
                                    ((19712, 6660), (19712, 6056)), main.channel,
                                    command=CMD_ON)
    control = pressed_switch(tile=1070, tx_id=main.channel, command=CMD_ON)
    control["behavior"].update(data_1=203, data_2=203)
    stand_control = _sprite(layout, "conductor", built["pit"], 1070, 23328, 8064, 2200,
                            seat="centre", cstat=control["cstat"], xr=40, yr=40,
                            shade=-20, angle=512, type=control["type"],
                            behavior=control["behavior"])
    for lever in (wing_control, stand_control):
        main.when(wiring.placement(lever), "push", command=CMD_ON, on=True, off=True)
    return result


def _wire_trap(layout, built):
    """E1M6 sprite 685's fire armour sets DWE1M9's drop and wing reveal."""
    trap, stage = built["trap"], built["stage"]
    prize = _sprite(layout, "fire_armour", trap, 2578, CENTER + 100, 5536,
                    xr=44, yr=44, shade=-44, type=142, status=3)
    strike = wires.wire(PRIZE_WIRE)
    strike.when(wiring.placement(prize), "pickup", command=CMD_ON, once=True)
    relay = layout.add_sprite(
        "aldermack:curtain_drop", trap.region_id, x=CENTER, y=5596,
        z=layout.regions[trap.region_id].floor_z - 768, picnum=0, cstat=32896)
    strike.then(wiring.placement(relay))
    wires.wire(MAIN_WIRE).when(wiring.placement(relay), wiring.RELAY, command=CMD_OFF)
    for door in built["wing_doors"]:
        strike.then(wiring.region(door.region_id))
    for i, wing in enumerate(built["wings"]):
        if i == 1:
            continue
        outline = wing.world_outline()
        x = round(sum(p[0] for p in outline) / 4)
        y = round(sum(p[1] for p in outline) / 4)
        _sprite(layout, f"watcher_{i}", wing, 2825, x, y, xr=40, yr=40,
                cstat=384, type=202, shade=-27, status=6, angle=512)
    # DWE1M9 963/964: two opposing layers of 3129. Shorten the repeats to
    # seat their drawn boxes below this fly ceiling. The ON edge removes
    # both effect sprites permanently, matching the blackout in s279.
    for i, (x, y, cstat, angle, xr, yr) in enumerate((
            (CENTER + 80, 4584, 650, 1536, 70, 146),
            (CENTER - 80, 4584, 654, 512, 64, 150))):
        beam = _sprite(layout, f"beam_{i}", stage, 3129, x, y, 128,
                       xr=xr, yr=yr, cstat=cstat, shade=-62, angle=angle,
                       type=417, status=4)
        strike.then(wiring.placement(beam))
    # where the light lands; it goes out with the beam
    pool = _sprite(layout, "beam_pool", stage, 625, CENTER, 4640, 64, xr=64, yr=48,
                   cstat=32 | 2 | 128, shade=-64, pal=8, angle=512, type=417, status=4)
    strike.then(wiring.placement(pool))


def furnish(layout, built):
    """Fit the cloth, dress the auditorium, and wire the two acts."""
    fin = built["box_curtain"]
    report = curtains.furnish(layout, fin, grade=GRADE - CIRCLE_RISE - 4096)
    fin_id = fin["room"].region_id
    layout.declare_motion(fin_id, [fin_id])
    for edge in fin["spec"]["fabric"]:
        layout.paint_wall(fin_id, *edge, shade=30, y_repeat=6, fixed_frame=True)
    for bays, (a, b) in built["masks"]:
        for room in bays:
            layout.paint_wall(room.region_id, a, b, over_picnum=DRAPE,
                              cstat=1 | 16 | 64, x_repeat=8, y_repeat=10,
                              shade=20, pal=2, fixed_frame=True)
    _dress_stage(layout, built)
    _dress_house(layout, built)
    _dress_pit(layout, built["pit"])
    _wire_trap(layout, built)
    return {"box_curtain": report,
            "stage_curtain": {"type": 600, "region": built["curtain"].region_id},
            "stage_light": _wire_show(layout, built)}
