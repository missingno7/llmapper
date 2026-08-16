"""Deterministic cross-engine semantic fixtures.

Each scenario is a SemanticLevel plus independent Doom and Blood encodings.
The progression solver is expected to reach the same conclusion on both.
"""

from __future__ import annotations

from .construction import LevelBuilder
from .doom import (
    ML_BLOCKING, ML_TWOSIDED, NO_SIDE, DoomDiskMap, DoomLinedef, DoomSector,
    DoomSidedef, DoomThing, DoomVertex, _tex8,
)
from .mechanisms import SemanticConnection, SemanticLevel, SemanticMechanism, SemanticRegion


def _side(sector: int, mid: bytes = b"-") -> DoomSidedef:
    return DoomSidedef(0, 0, _tex8("-"), _tex8("-"), _tex8(mid), sector)


def _sector(tag: int = 0, floor: int = 0, ceil: int = 128, special: int = 0, flat: bytes = b"FLOOR0_1") -> DoomSector:
    return DoomSector(floor, ceil, _tex8(flat), _tex8(b"CEIL1_1"), 192, special, tag)


def _line(v1: int, v2: int, front: int, back: int | None, special: int = 0, tag: int = 0, mid: bytes = b"STARTAN2") -> tuple[DoomLinedef, list[DoomSidedef]]:
    sides = [_side(front, mid)]
    back_id = NO_SIDE
    flags = ML_BLOCKING
    if back is not None:
        sides.append(_side(back, b"-"))
        back_id = 1  # placeholder; caller reindexes
        flags = ML_TWOSIDED
    line = DoomLinedef(v1, v2, flags, special, tag, 0, back_id)
    return line, sides


def assemble_doom(
    name: str,
    vertices: list[tuple[int, int]],
    raw_lines: list[tuple],
    sectors: list[DoomSector],
    things: list[DoomThing],
) -> DoomDiskMap:
    """raw_lines: (v1, v2, front, back|None, special=0, tag=0, mid=b'STARTAN2')"""
    linedefs: list[DoomLinedef] = []
    sidedefs: list[DoomSidedef] = []
    for item in raw_lines:
        v1, v2, front, back = item[:4]
        special = item[4] if len(item) > 4 else 0
        tag = item[5] if len(item) > 5 else 0
        mid = item[6] if len(item) > 6 else b"STARTAN2"
        front_id = len(sidedefs)
        sidedefs.append(_side(front, mid if back is None else b"-"))
        back_id = NO_SIDE
        flags = ML_BLOCKING
        if back is not None:
            back_id = len(sidedefs)
            sidedefs.append(_side(back, b"-"))
            flags = ML_TWOSIDED
        linedefs.append(DoomLinedef(v1, v2, flags, special, tag, front_id, back_id))
    return DoomDiskMap(
        name=name, format="doom",
        things=things,
        linedefs=linedefs,
        sidedefs=sidedefs,
        vertices=[DoomVertex(x, y) for x, y in vertices],
        sectors=sectors,
    )


def fixture_basic_room() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    """start → corridor → room → exit"""
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"], tags=["start"]),
            SemanticRegion("corridor", ["sector:1"]),
            SemanticRegion("room", ["sector:2"], tags=["exit"]),
        ],
        connections=[
            SemanticConnection("c1", "open", "start", "corridor"),
            SemanticConnection("c2", "open", "corridor", "room"),
        ],
        mechanisms=[
            SemanticMechanism("exit", "exit", "neutral", ["linedef:exit"], "use", False, "idle"),
        ],
        start_region="start",
        exit_regions=["room"],
    )
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (384, 0), (384, 192),
        (576, 0), (576, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            # start, clockwise, interior on the right; east wall portals to corridor
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1), (1, 0, 0, None),
            # corridor
            (4, 1, 1, None), (2, 5, 1, None), (5, 4, 1, 2),
            # room / exit
            (6, 4, 2, None), (5, 7, 2, None), (7, 6, 2, None, 11, 0, b"SW1COMM"),
        ],
        [_sector(), _sector(), _sector()],
        [DoomThing(96, 96, 0, 1, 7)],
    )
    blood = _blood_rooms(
        [
            [(0, 0), (6144, 0), (6144, 6144), (0, 6144)],
            [(6144, 0), (12288, 0), (12288, 6144), (6144, 6144)],
            [(12288, 0), (18432, 0), (18432, 6144), (12288, 6144)],
        ],
        portals=[(0, 1, 1, 3), (1, 1, 2, 3)],
        start=(3072, 3072, 0),
        exit_sector=2,
    )
    return semantic, doom, blood


def fixture_switch_door() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"]),
            SemanticRegion("door", ["sector:1"]),
            SemanticRegion("exit", ["sector:2"], tags=["exit"]),
        ],
        connections=[
            SemanticConnection("d1", "door", "start", "door", mechanism_id="switch-door", initial="closed"),
            SemanticConnection("d2", "open", "door", "exit"),
        ],
        mechanisms=[
            SemanticMechanism(
                "switch-door", "door", "neutral", ["linedef:switch", "sector:1"],
                "switch", False, "closed", targets=["sector:1"],
            ),
            SemanticMechanism("exit", "exit", "neutral", ["linedef:exit"], "use", False, "idle"),
        ],
        start_region="start",
        exit_regions=["exit"],
    )
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (256, 0), (256, 192),
        (448, 0), (448, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1, 29, 1, b"SW1COMM"), (1, 0, 0, None),
            (4, 1, 1, None, 0, 0, b"BIGDOOR2"), (2, 5, 1, None, 0, 0, b"BIGDOOR2"), (5, 4, 1, 2),
            (6, 4, 2, None), (5, 7, 2, None), (7, 6, 2, None, 11),
        ],
        [_sector(), _sector(tag=1, ceil=0), _sector()],
        [DoomThing(96, 96, 0, 1, 7)],
    )
    blood = _blood_switch_door()
    return semantic, doom, blood


def fixture_keyed_door() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"]),
            SemanticRegion("key_room", ["sector:1"], items=["key:blue"]),
            SemanticRegion("door", ["sector:2"]),
            SemanticRegion("exit", ["sector:3"], tags=["exit"]),
        ],
        connections=[
            SemanticConnection("open1", "open", "start", "key_room"),
            SemanticConnection("gate", "key_gate", "start", "door", mechanism_id="blue-door", required_keys=["blue"], initial="closed"),
            SemanticConnection("open2", "open", "door", "exit"),
        ],
        mechanisms=[
            SemanticMechanism(
                "blue-door", "key_gate", "neutral", ["linedef:key", "sector:2"],
                "use", True, "closed", required_keys=["blue"], targets=["sector:2"],
            ),
        ],
        start_region="start",
        exit_regions=["exit"],
    )
    # start (0) west, key room (1) south, locked door (2) east, exit (3)
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (192, -192), (0, -192),
        (256, 0), (256, 192),
        (448, 0), (448, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            # start: south portal to key room, east keyed door
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 2, 26, 0, b"DOORBLU"), (1, 0, 0, 1),
            # key room south of start
            (5, 0, 1, None), (4, 5, 1, None), (1, 4, 1, None),
            # locked door
            (6, 1, 2, None, 0, 0, b"BIGDOOR2"), (2, 7, 2, None, 0, 0, b"BIGDOOR2"), (7, 6, 2, 3),
            # exit
            (8, 6, 3, None), (7, 9, 3, None), (9, 8, 3, None, 11),
        ],
        [_sector(), _sector(), _sector(ceil=0), _sector()],
        [DoomThing(96, 96, 0, 1, 7), DoomThing(96, -96, 0, 5, 7)],
    )
    blood = _blood_keyed()
    return semantic, doom, blood


def fixture_lift() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"]),
            SemanticRegion("lift", ["sector:1"]),
            SemanticRegion("upper", ["sector:2"], tags=["exit"]),
        ],
        connections=[
            SemanticConnection("to-lift", "lift", "start", "lift", mechanism_id="lift", initial="closed"),
            SemanticConnection("to-upper", "open", "lift", "upper"),
        ],
        mechanisms=[
            SemanticMechanism("lift", "lift", "neutral", ["sector:1"], "use", True, "closed", targets=["sector:1"]),
        ],
        start_region="start",
        exit_regions=["upper"],
    )
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (256, 0), (256, 192),
        (448, 0), (448, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1, 62, 1), (1, 0, 0, None),
            (4, 1, 1, None), (2, 5, 1, None), (5, 4, 1, 2),
            (6, 4, 2, None), (5, 7, 2, None), (7, 6, 2, None, 11),
        ],
        [_sector(), _sector(tag=1, floor=0, ceil=192), _sector(floor=64, ceil=192)],
        [DoomThing(96, 96, 0, 1, 7)],
    )
    blood = _blood_lift()
    return semantic, doom, blood


def fixture_teleport() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"]),
            SemanticRegion("dest", ["sector:1"], tags=["exit"]),
        ],
        connections=[
            SemanticConnection("tp", "teleport", "start", "dest", mechanism_id="teleport"),
        ],
        mechanisms=[
            SemanticMechanism("teleport", "teleport", "neutral", ["linedef:39"], "walk", True, "idle"),
        ],
        start_region="start",
        exit_regions=["dest"],
    )
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (320, 0), (512, 0), (512, 192), (320, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, None, 97, 1), (1, 0, 0, None),
            (4, 7, 1, None), (7, 6, 1, None), (6, 5, 1, None, 11), (5, 4, 1, None),
        ],
        [_sector(), _sector(tag=1)],
        [DoomThing(64, 96, 0, 1, 7), DoomThing(416, 96, 0, 14, 7)],
    )
    blood = _blood_teleport()
    return semantic, doom, blood


def _blood_rooms(polygons, portals, start, exit_sector: int):
    builder = LevelBuilder()
    allocs = [
        builder.add_sector(poly, ceiling_z=-17536, floor_z=0)
        for poly in polygons
    ]
    for a, aw, b, bw in portals:
        builder.connect(allocs[a].wall_ids[aw], allocs[b].wall_ids[bw])
    builder.set_player_start(sector=0, x=start[0], y=start[1], z=start[2], angle=0)
    switch = builder.add_sprite(sector=exit_sector, x=polygons[exit_sector][0][0] + 1024, y=polygons[exit_sector][0][1] + 1024, z=0, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", switch, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    return builder.build()


def _blood_switch_door():
    builder = LevelBuilder()
    start = builder.add_sector([(0, 0), (6144, 0), (6144, 6144), (0, 6144)], ceiling_z=-17536, floor_z=0)
    door = builder.add_sector([(6144, 0), (8192, 0), (8192, 6144), (6144, 6144)], ceiling_z=0, floor_z=0, type=600)
    exit_room = builder.add_sector([(8192, 0), (14336, 0), (14336, 6144), (8192, 6144)], ceiling_z=-17536, floor_z=0)
    builder.connect(start.wall_ids[1], door.wall_ids[3])
    builder.connect(door.wall_ids[1], exit_room.wall_ids[3])
    builder.set_behavior(
        "sector", door.sector_id, rx_id=100, busy_time_a=20, busy_time_b=20,
        off_ceiling_z=0, on_ceiling_z=-17536, off_floor_z=0, on_floor_z=0,
        trigger_push=0, trigger_wall_push=0,
    )
    switch = builder.add_sprite(sector=0, x=5120, y=3072, z=-4096, type=21, picnum=1070, status=0, angle=1024, cstat=464, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", switch, tx_id=100, command=1, trigger_on=1, trigger_push=1)
    builder.add_sprite(sector=2, x=9216, y=3072, z=0, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", len(builder.level.sprites) - 1, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    builder.set_player_start(sector=0, x=3072, y=3072, z=0, angle=0)
    return builder.build()


def _blood_keyed():
    builder = LevelBuilder()
    start = builder.add_sector([(0, 0), (6144, 0), (6144, 6144), (0, 6144)], ceiling_z=-17536, floor_z=0)
    key_room = builder.add_sector([(0, -4096), (6144, -4096), (6144, 0), (0, 0)], ceiling_z=-17536, floor_z=0)
    door = builder.add_sector([(6144, 0), (8192, 0), (8192, 6144), (6144, 6144)], ceiling_z=0, floor_z=0, type=600)
    exit_room = builder.add_sector([(8192, 0), (14336, 0), (14336, 6144), (8192, 6144)], ceiling_z=-17536, floor_z=0)
    builder.connect(start.wall_ids[0], key_room.wall_ids[2])
    builder.connect(start.wall_ids[1], door.wall_ids[3])
    builder.connect(door.wall_ids[1], exit_room.wall_ids[3])
    builder.set_behavior(
        "sector", door.sector_id, busy_time_a=20, busy_time_b=20,
        off_ceiling_z=0, on_ceiling_z=-17536, off_floor_z=0, on_floor_z=0,
        trigger_push=1, trigger_wall_push=1, key=1,
    )
    builder.add_sprite(sector=1, x=3072, y=-2048, z=0, type=100, picnum=2552, status=3, cstat=128, x_repeat=32, y_repeat=32)
    builder.set_behavior("sprite", 0)
    builder.add_sprite(sector=3, x=9216, y=3072, z=0, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", 1, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    builder.set_player_start(sector=0, x=3072, y=3072, z=0, angle=0)
    return builder.build()


def _blood_lift():
    builder = LevelBuilder()
    start = builder.add_sector([(0, 0), (6144, 0), (6144, 6144), (0, 6144)], ceiling_z=-17536, floor_z=0)
    lift = builder.add_sector([(6144, 0), (8192, 0), (8192, 6144), (6144, 6144)], ceiling_z=-17536, floor_z=0, type=600)
    upper = builder.add_sector([(8192, 0), (14336, 0), (14336, 6144), (8192, 6144)], ceiling_z=-26368, floor_z=-8784)
    builder.connect(start.wall_ids[1], lift.wall_ids[3])
    builder.connect(lift.wall_ids[1], upper.wall_ids[3])
    builder.set_behavior(
        "sector", lift.sector_id, busy_time_a=16, busy_time_b=16,
        off_ceiling_z=-17536, on_ceiling_z=-17536, off_floor_z=0, on_floor_z=-8784,
        trigger_push=1, trigger_wall_push=1, trigger_enter=1, wait_time_a=10, retrigger_a=1,
    )
    builder.add_sprite(sector=2, x=9216, y=3072, z=-8784, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", 0, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    builder.set_player_start(sector=0, x=3072, y=3072, z=0, angle=0)
    return builder.build()


def _blood_teleport():
    builder = LevelBuilder()
    start = builder.add_sector([(0, 0), (6144, 0), (6144, 6144), (0, 6144)], ceiling_z=-17536, floor_z=0, type=604)
    dest = builder.add_sector([(10240, 0), (16384, 0), (16384, 6144), (10240, 6144)], ceiling_z=-17536, floor_z=0)
    marker = builder.add_sprite(sector=1, x=13312, y=3072, z=0, type=8, picnum=3193, status=0, x_repeat=64, y_repeat=64)
    builder.set_behavior("sector", 0, marker_0=marker, trigger_enter=1, dude_lockout=1, data=0)
    builder.add_sprite(sector=1, x=12288, y=3072, z=0, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", 1, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    builder.set_player_start(sector=0, x=2048, y=3072, z=0, angle=0)
    return builder.build()


def fixture_unreachable_remote_switch() -> tuple[SemanticLevel, DoomDiskMap, "object"]:
    """Reachable start, closed door to exit, switch in an unreachable island.

    The solver must not treat activation='switch' as sufficient merely because
    the door-adjacent region is reachable.
    """
    semantic = SemanticLevel(
        source_game="neutral",
        regions=[
            SemanticRegion("start", ["sector:0"]),
            SemanticRegion("door", ["sector:1"]),
            SemanticRegion("exit", ["sector:2"], tags=["exit"]),
            SemanticRegion("island", ["sector:3"]),
        ],
        connections=[
            SemanticConnection(
                "d1", "door", "start", "door",
                mechanism_id="remote-door", initial="closed",
            ),
            SemanticConnection("d2", "open", "door", "exit"),
        ],
        mechanisms=[
            SemanticMechanism(
                "remote-door", "door", "neutral",
                ["linedef:switch", "sector:1", "sector:3"],
                "switch", False, "closed", targets=["sector:1"],
            ),
            SemanticMechanism("exit", "exit", "neutral", ["linedef:exit"], "use", False, "idle"),
        ],
        start_region="start",
        exit_regions=["exit"],
    )
    vertices = [
        (0, 0), (192, 0), (192, 192), (0, 192),
        (256, 0), (256, 192),
        (448, 0), (448, 192),
        (640, 0), (832, 0), (832, 192), (640, 192),
    ]
    doom = assemble_doom(
        "MAP01",
        vertices,
        [
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1), (1, 0, 0, None),
            (4, 1, 1, None, 0, 0, b"BIGDOOR2"), (2, 5, 1, None, 0, 0, b"BIGDOOR2"), (5, 4, 1, 2),
            (6, 4, 2, None), (5, 7, 2, None), (7, 6, 2, None, 11),
            (8, 11, 3, None, 29, 1, b"SW1COMM"), (11, 10, 3, None), (10, 9, 3, None), (9, 8, 3, None),
        ],
        [_sector(), _sector(tag=1, ceil=0), _sector(), _sector()],
        [DoomThing(96, 96, 0, 1, 7)],
    )
    builder = LevelBuilder()
    start = builder.add_sector([(0, 0), (6144, 0), (6144, 6144), (0, 6144)], ceiling_z=-17536, floor_z=0)
    door = builder.add_sector([(6144, 0), (8192, 0), (8192, 6144), (6144, 6144)], ceiling_z=0, floor_z=0, type=600)
    exit_room = builder.add_sector([(8192, 0), (14336, 0), (14336, 6144), (8192, 6144)], ceiling_z=-17536, floor_z=0)
    island = builder.add_sector([(20480, 0), (26624, 0), (26624, 6144), (20480, 6144)], ceiling_z=-17536, floor_z=0)
    builder.connect(start.wall_ids[1], door.wall_ids[3])
    builder.connect(door.wall_ids[1], exit_room.wall_ids[3])
    builder.set_behavior(
        "sector", door.sector_id, rx_id=100, busy_time_a=20, busy_time_b=20,
        off_ceiling_z=0, on_ceiling_z=-17536, off_floor_z=0, on_floor_z=0,
        trigger_push=0, trigger_wall_push=0,
    )
    switch = builder.add_sprite(
        sector=island.sector_id, x=22528, y=3072, z=-4096,
        type=21, picnum=1070, status=0, angle=1024, cstat=464, x_repeat=40, y_repeat=40,
    )
    builder.set_behavior("sprite", switch, tx_id=100, command=1, trigger_on=1, trigger_push=1)
    builder.add_sprite(sector=2, x=9216, y=3072, z=0, type=20, picnum=318, status=0, x_repeat=40, y_repeat=40)
    builder.set_behavior("sprite", len(builder.level.sprites) - 1, tx_id=4, command=1, trigger_on=1, trigger_push=1)
    builder.set_player_start(sector=0, x=3072, y=3072, z=0, angle=0)
    return semantic, doom, builder.build()


ALL_FIXTURES = {
    "basic-room": fixture_basic_room,
    "switch-door": fixture_switch_door,
    "keyed-door": fixture_keyed_door,
    "lift": fixture_lift,
    "teleport": fixture_teleport,
}
