"""Build The Signal Box: a lane to a level crossing at night, the box beside it, and the gate its lever opens.

    python projects/signal-box/level/build.py

The plan, west to east and north (low y) to south (high y), in plan units of 1,024:

    far road   x 0..8,   y -8..3.5   beyond the crossing gate; the way out at its north end
    gate       x 1..7,   y 3.5..4    the crossing gate, shut; the lever upstairs lifts it
    track      x -12..32, y 4..8     the railway, east-west under the night sky
    lane       x 0..8,   y 8..24     where the player starts, open to the sky
    the box    x 9..30,  y 9..14     locking room (ground), a stair east, the lever room up it,
                                     whose north wall has three windows on the track

The shape every build has: program (rooms in a tree) -> layout -> circuit -> finish.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import finish, glass, keys, supplies, switches, wiring
from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, LevelProgram, Style, floor_detail, wall_detail
from bloodmap.light_stage import Rule
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.rules import art_sizes
from bloodmap.texture_align import sprite_tile_extents

BODY = PLAYER_PROFILES["blood"]
U, PH = BODY.body_width, BODY.standing_height
P = 1024  # one plan unit: the grid the rooms are laid on
MAP = PROJECT / "level" / "signal-box.MAP"
FLOOR = 0

RISE = 5 * BODY.max_step     # the lever room is a storey up: 20,480, 1.21 bodies

# tiles, each chosen by what the owner or the catalog says it is
SKY = 2500          # owner: sky parallax segment
COBBLE = 110        # owner: cobblestone
TRACK = 1129        # owner: railway track with sleepers, floor texture (rails run along the tile's x)
BRICK = 421         # owner: wall of grey bricks (E1M2's track cutting)
PLANKS = 67         # owner: dark horizontal planks (E1M2's waiting-hall ceiling)
BOARDS = 49         # weathered red and grey boards with cross rails (E1M2's station)
WOOD_FLOOR = 250    # light wooden planks
STONE = 281         # owner: irregular grey stone masonry
GATE = 170          # owner: wooden boarding: the crossing gate's leaf
LAMP_POST = 640     # black street lamp post (light_kinds: standing)
CHAIN_LAMP = 641    # owner: lamp hanging on a chain
LEVER_DOWN = 1075   # lever switch in rusty frame, down: the frame's other levers

OUTDOOR = Style(wall_picnum=BRICK, floor_picnum=COBBLE, ceiling_picnum=SKY, wall_shade=24, floor_shade=26,
                ceiling_shade=30, parallax_ceiling=True, floor_z=FLOOR, clear_height=RISE + int(1.7 * PH))
INSIDE = Style(wall_picnum=BOARDS, floor_picnum=WOOD_FLOOR, ceiling_picnum=PLANKS, wall_shade=16, floor_shade=16,
               ceiling_shade=24, parallax_ceiling=False, clear_height=int(1.4 * PH))

TREAD = 3 * U // 2 * 2       # 1,152 per step
SILL, HEAD = int(0.55 * PH), int(1.3 * PH)
BASE = int(1.4 * PH)         # the brick plinth: as high as the locking room
TOP = RISE + int(1.7 * PH)   # the roof line: over the lever room's ceiling
LIP = 0.125                  # the lip's depth, in plan units (128)


def light(region: str) -> Rule:
    if "lane" in region or "far_road" in region:
        return Rule("pairs", LAMP_POST, 6 * P)
    if "lever_room" in region or "locking" in region:
        return Rule("hanging", CHAIN_LAMP, 4 * P)
    return Rule("none", 0, 0)


def program() -> tuple[LevelProgram, dict]:
    level = LevelProgram("signal-box", name="The Signal Box", style=OUTDOOR, art_sizes=art_sizes(),
                         tile_extents=sprite_tile_extents())
    rooms: dict = {}

    def at(room, face, x, y):
        """Where the plan point (x, y) falls along a face, as a share of it: faces run round the room, so south runs east to west."""
        (ax, ay), (bx, by) = [room.world_frame().apply(p) for p in room.local_edge(face)]
        length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        return ((x * P - ax) * (bx - ax) + (y * P - ay) * (by - ay)) / length ** 2

    def rect(name, x0, y0, x1, y1, note, parent=level, **surfaces):
        room = parent.rect_room(name, origin=(x0 * P, y0 * P), size=((x1 - x0) * P, (y1 - y0) * P), note=note)
        if surfaces:
            room.surfaces(**surfaces)
        rooms[name] = room
        return room

    lane = rect("lane", 0, 8, 8, 24, "the lane the player walks up to the crossing, between brick walls")
    track = rect("track", -12, 4, 36, 8, "the railway, east-west, open to the night sky",
                 floor_picnum=TRACK, floor_shade=28)
    far = rect("far_road", 0, -8, 8, 3.5, "the road on beyond the crossing gate: the way out")
    far.region_kwargs = {"declared_zero_exit": True}  # its only way in is the gate, shut at rest
    gate = rect("gate", 1, 3.5, 7, 4, "the crossing gate: shut until the signalman's lever lifts it",
                wall_picnum=GATE, parallax_ceiling=False, ceiling_picnum=GATE, clear_height=0)
    gate.role = "doorway"
    gate.region_kwargs = {"type": 600,
                          "sector_behavior": z_motion_door(FLOOR, FLOOR - int(1.6 * PH), interaction="remote",
                                                           rx_id=0, open_time=20)}

    box = level.assembly("box", style=INSIDE.override(floor_z=FLOOR), note="the signal box")
    door = rect("doorway", 8, 11, 9, 12.5, "the box's door from the lane", parent=box,
                clear_height=int(1.15 * PH), wall_picnum=STONE)
    door.role = "doorway"
    locking = rect("locking_room", 9, 9, 15, 14, "the locking room: the interlocking under the levers, a stair up",
                   parent=box, floor_picnum=STONE, wall_picnum=STONE)
    lever = rect("lever_room", 15 + 5 * TREAD / P, 9, 30, 14, "the lever room: a frame of levers, windows on the track",
                 parent=box, clear_height=int(1.6 * PH))
    lever.frame = Frame(lever.frame.dx, lever.frame.dy, -RISE)
    locking.staircase("stairs:up", "east", at=0.5, width=4 * U, total_rise=-RISE, step_rise=-BODY.max_step,
                      tread=TREAD, arrive_at=lever.region_id, wall_picnum=STONE)

    # the box seen from outside: a brick plinth a storey high, the timber upper storey on a thin lip above it,
    # under a lower sky, so the box ends in a roof line with the night over it
    def lip(name, x0, y0, x1, y1):
        room = rect(name, x0, y0, x1, y1, "the box's front above its brick plinth: a thin lip, looked at, never walked",
                    floor_z=FLOOR - BASE, clear_height=TOP - BASE, wall_picnum=BOARDS, floor_picnum=BOARDS,
                    ceiling_picnum=SKY, parallax_ceiling=True, wall_shade=20)
        room.role = "exterior"
        return room

    lip_track = lip("lip_track", 8, 8, 30, 8 + LIP)
    lip_north = lip("lip_lane_n", 8, 8 + LIP, 8 + LIP, 11 - LIP)
    lip_south = lip("lip_lane_s", 8, 12.5 + LIP, 8 + LIP, 14)
    level.connect(track.face("south", at=at(track, "south", 19, 8), width=22 * P), lip_track.face("north"))
    level.connect(lip_track.face("south", at=at(lip_track, "south", 8 + LIP / 2, 8 + LIP), width=LIP * P),
                  lip_north.face("north"))
    level.connect(lane.face("east", at=at(lane, "east", 8, 9.5), width=(3 - 2 * LIP) * P), lip_north.face("west"))
    level.connect(lane.face("east", at=at(lane, "east", 8, 13.25 + LIP / 2), width=(1.5 - LIP) * P),
                  lip_south.face("west"))
    level.connect(lane.face("east", at=at(lane, "east", 8, 8 + LIP / 2), width=LIP * P), lip_track.face("west"))

    # three windows in the lever room's north wall, each a reveal and a sill sector with the pane between
    windows = []
    for k, x in enumerate((21.5, 24.5, 27.5)):
        sill = -RISE - SILL
        inner = rect(f"window_{k}_in", x, 8.625, x + 2, 9, "a window's inner reveal", parent=box,
                     floor_z=sill, clear_height=HEAD - SILL, wall_picnum=BOARDS)
        outer = rect(f"window_{k}_out", x, 8 + LIP, x + 2, 8.625, "a window's outer reveal", parent=box,
                     floor_z=sill, clear_height=HEAD - SILL, wall_picnum=BRICK)
        level.connect(lever.face("north", at=at(lever, "north", x + 1, 9), width=2 * P), inner.face("south"))
        level.connect(inner.face("north"), outer.face("south"))
        level.connect(outer.face("north"), lip_track.face("south", at=at(lip_track, "south", x + 1, 8 + LIP),
                                                           width=2 * P))
        windows.append((int(x * P), int(8.625 * P)))

    level.connect(lane.face("north"), track.face("south", at=at(track, "south", 4, 8), width=8 * P))
    level.connect(track.face("north", at=at(track, "north", 4, 4), width=6 * P), gate.face("south"), gated=True)
    level.connect(gate.face("north"), far.face("south", at=0.5, width=6 * P), gated=True)
    level.connect(lane.face("east", at=at(lane, "east", 8, 11.75), width=1.5 * P), door.face("west"))
    level.connect(door.face("east"), locking.face("west", at=at(locking, "west", 9, 11.75), width=1.5 * P))

    # the lever frame along the lever room's south wall: six levers back, one forward (the one that works)
    for k, at in enumerate((0.2, 0.3, 0.4, 0.6, 0.7, 0.8)):
        lever.decorate(wall_detail(f"frame_lever_{k}", LEVER_DOWN, 0.45, face="south", at=at, height=0.45,
                                   cstat=80))
    # lamp posts: the light-stage lights roofed rooms only, so the open air's lamps are set down here
    for name, room, local in (("lamp_lane_1", lane, (0.08, 0.35)), ("lamp_lane_2", lane, (0.92, 0.8)),
                              ("lamp_far", far, (0.9, 0.3))):
        room.decorate(floor_detail(name, LAMP_POST, 2.2, local=local, cstat=128, shade=-8, emits_light=True))
    # supplies: what the player is given, near where it is needed
    lane.decorate(floor_detail("barrel", 925, 0.75, local=(0.15, 0.8), cstat=129))
    level.set_start(lane, local=(0.5, 0.92), angle=1536)
    return level, rooms, windows


def place_things(layout, rooms):
    """Enemies and pickups, as Blood sets them down (`bloodmap.supplies`)."""
    put = [
        ("shotgun", "lane", (0.7, 0.7), supplies.item(41)),
        ("shells", "locking_room", (0.2, 0.8), supplies.item(67)),
        ("pouch", "lever_room", (0.9, 0.8), supplies.item(108)),
        ("cultist_lane", "lane", (0.3, 0.25), supplies.dude(202, angle=512)),
        ("cultist_track", "track", (0.6, 0.5), supplies.dude(201, angle=1024)),
        ("zombie_box", "locking_room", (0.7, 0.3), supplies.dude(203, angle=1024)),
        ("cultist_lever", "lever_room", (0.5, 0.5), supplies.dude(202, angle=1024)),
    ]
    for name, room, local, fields in put:
        layout.place_on_floor(name, rooms[room].region_id, local=local, **fields)


def build() -> finish.Finished:
    level, rooms, windows = program()
    layout = level.compile()
    place_things(layout, rooms)
    circuit = wiring.Circuit(layout)
    # a shut door shows the walls of the sectors either side of it: they wear the gate's boards
    gate = rooms["gate"]
    for side, (a, b) in (("track", ((1 * P, 4 * P), (7 * P, 4 * P))), ("far_road", ((7 * P, int(3.5 * P)), (1 * P, int(3.5 * P))))):
        layout.paint_wall(rooms[side].region_id, a, b, picnum=GATE)
    # over the box's door the lane's wall is drawn up to the lip: it wears the upper storey's boards
    layout.paint_wall(rooms["lane"].region_id, (8 * P, 11 * P), (8 * P, int(12.5 * P)), picnum=BOARDS)

    # the working lever: in the middle of the frame, pulled to lift the crossing gate
    lever = rooms["lever_room"]
    (x0, y0), (x1, y1) = [lever.world_frame().apply(p) for p in lever.local_edge("south")]
    pull = dict(switches.pressed_switch(tile=1074, tx_id=0))
    pull.pop("behavior")
    layout.place_on_wall("signal_lever", lever.region_id, a1=(x0, y0), a2=(x1, y1), t=0.5, status=0,
                         height_player_heights=pull.pop("height_player_heights"), **pull)
    circuit.wire("gate", "pulling the signal lever lifts the crossing gate", ).when(
        wiring.placement("signal_lever"), "push", command=1).then(wiring.region(rooms["gate"].region_id))

    # the way out: a switch on the far road's end wall
    far = rooms["far_road"]
    (x0, y0), (x1, y1) = [far.world_frame().apply(p) for p in far.local_edge("north")]
    way_out = dict(switches.exit_switch())
    way_out.pop("behavior")
    layout.place_on_wall("exit_switch", far.region_id, a1=(x0, y0), a2=(x1, y1), t=0.5, status=0,
                         height_player_heights=way_out.pop("height_player_heights"), **way_out)
    circuit.wire("way-out", "pushing the switch at the far road's end ends the level",
                 engine="kChannelLevelExitNormal").when(wiring.placement("exit_switch"), "push", command=1)

    def panes(compiled):
        spans = [(x - 8, y - 8, x + 2 * P + 8, y + 8) for x, y in windows]
        return glass.glaze(compiled.level, spans, fit=True)

    made = finish.finish(layout, MAP, circuit=circuit, light=light, on_level=panes)
    finish.write_manifest(made, PROJECT / "reports" / "build-manifest.json")
    return made


def main() -> int:
    made = build()
    if not made.ok:
        print("the map was not written")
        return 1
    from tools import project

    return project.main(["status", PROJECT.name])


if __name__ == "__main__":
    raise SystemExit(main())
