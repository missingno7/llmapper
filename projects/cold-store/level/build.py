"""Build The Cold Store: a cellar of four rooms behind a locked door, taken to a map by the shared finishing sequence.

    python projects/cold-store/level/build.py

Begun from the starter (`python -m tools.project new`) on 2026-11-26, as the proof
that a level is built, looked at and tested by the shared tools alone: nothing
here is imported from another level. It is small on purpose, and it uses one of
each thing a level is made of:

    rooms      an entry with a side store, a low passage, a hall with a stair, a landing (`bloodmap.levelprog`)
    a lock     the passage ends at a rising door that wants the skull key (`bloodmap.doors.z_motion_door`);
               the key lies in the side store (`bloodmap.keys.pickup`), and the lock is signed (`keys.sign_the_locks`)
    foes       two cultists in the hall and one on the landing (`bloodmap.supplies.dude`)
    supplies   a shotgun where the level starts, shells and a pouch on the way (`bloodmap.supplies.item`)
    a wire     the switch on the landing ends the level (`bloodmap.wiring.Circuit`)
    light      a rule a kind of place (`bloodmap.light_stage.Rule`)

What was looked up to build it is on the shelves (`python -m tools.findings find door`:
a rising door is closed at rest and 256 thick; `find partial edge`: rooms that share an
edge are joined along all of it).
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import doors, finish, keys, supplies, switches, wiring
from bloodmap.levelprog import LevelProgram, Style, floor_detail
from bloodmap.light_stage import Rule
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.rules import art_sizes
from bloodmap.texture_align import sprite_tile_extents

BODY = PLAYER_PROFILES["blood"]
#: one body's width and height: sizes are written in these, never in bare numbers
U, PH = BODY.body_width, BODY.standing_height
MAP = PROJECT / "level" / "cold-store.MAP"
FLOOR = 0
SKULL = 1
#: the door is as high as the passage it shuts
PASSAGE_HIGH = int(1.4 * PH)
#: panelled metal, as the campaign's ceiling doors wear it (`python -m tools.findings find door leaf`)
LEAF_TILE = 495

#: what the place is made of; a child room overrides only what differs
BRICK = Style(wall_picnum=180, floor_picnum=292, ceiling_picnum=385, wall_shade=8, floor_shade=12, ceiling_shade=10,
              floor_z=FLOOR, clear_height=2 * PH)

#: which kind of light each place is lit by: the first key found in a region's path wins
LIGHTS = (
    ("door", Rule("none", 0, 0, cut=False)),
    ("passage", Rule("none", 0, 0)),            # too low for a lamp of its own: it is lit from both ends
    ("hall", Rule("hanging", 641, 4096)),
    ("", Rule("ceiling", 795, 3072)),
)


def light(region: str) -> Rule:
    return next(rule for key, rule in LIGHTS if key in region)


def program() -> tuple[LevelProgram, dict]:
    level = LevelProgram("cold-store", name="The Cold Store", style=BRICK, art_sizes=art_sizes(),
                         tile_extents=sprite_tile_extents())
    entry = level.rect_room("entry", size=(8 * U, 8 * U), note="where the level starts")
    store = level.rect_room("store", size=(6 * U, 5 * U), note="a side store off the entry: the key is kept here")
    store.surfaces(clear_height=int(1.6 * PH), floor_picnum=294)
    store.place_against("south", entry.face("north", at=0.5, width=6 * U))
    passage = level.rect_room("passage", size=(10 * U, 3 * U), note="a low way through, shut at its far end")
    passage.surfaces(clear_height=PASSAGE_HIGH)
    passage.place_against("west", entry.face("east", at=0.5, width=3 * U))
    # the leaf is its own room: down on its floor at rest, and it rises into the lintel when the skull key is shown
    door = doors.rising_door(level, "door", wide=3 * U, floor_z=FLOOR, opening=PASSAGE_HIGH, key=SKULL,
                             note="the cold store's door: wants the skull key")
    door.place_against("west", passage.face("east"))
    hall = level.rect_room("hall", size=(16 * U, 14 * U), note="the cold store itself: a stair up its east side")
    hall.surfaces(clear_height=4 * PH, wall_picnum=5)
    hall.place_against("west", door.face("east"))
    landing = level.rect_room("landing", size=(6 * U, 8 * U), note="up the stair: the way out")
    rise = 5 * BODY.max_step
    landing.place_against("west", hall.face("east", at=0.5, width=6 * U)).move(dx=5 * 2 * U, dz=-rise)
    level.connect(entry.face("north", at=0.5, width=6 * U), store.face("south"))
    level.connect(entry.face("east", at=0.5, width=3 * U), passage.face("west"))
    level.connect(passage.face("east"), door.face("west"))
    level.connect(door.face("east"), hall.face("west", at=0.5, width=3 * U))
    hall.staircase("stairs:up", "east", at=0.5, width=6 * U, total_rise=-rise, step_rise=-BODY.max_step, tread=2 * U,
                   arrive_at=landing.region_id)
    hall.decorate(floor_detail("barrel_a", 925, 0.75, local=(0.2, 0.15), cstat=129),
                  floor_detail("barrel_b", 925, 0.75, local=(0.28, 0.12), cstat=129))
    store.decorate(floor_detail("barrel", 925, 0.75, local=(0.85, 0.2), cstat=129))
    level.set_start(entry, local=(0.25, 0.7), angle=0)
    return level, {"entry": entry, "store": store, "passage": passage, "door": door, "hall": hall, "landing": landing}


def build(write: bool = True) -> finish.Finished:
    """Build the level; `write=False` builds and holds it to the gates without touching the files (a test)."""
    level, rooms = program()
    layout = level.compile()
    counts = {}
    # the key, and what the player starts with and finds on the way
    layout.place_on_floor("key_skull", rooms["store"].region_id, local=(0.3, 0.35), **keys.pickup(SKULL))
    for name, room, local, kind in (("shotgun", "entry", (0.6, 0.3), 41), ("shells_a", "store", (0.6, 0.6), 67),
                                    ("shells_b", "hall", (0.15, 0.8), 68), ("pouch", "landing", (0.3, 0.8), 108)):
        layout.place_on_floor(f"supply_{name}", rooms[room].region_id, local=local, **supplies.item(kind))
    # who is in the way: Tommy-gun cultists in the hall, one with a shotgun by the way out
    for name, room, local, kind, angle in (("hall_a", "hall", (0.55, 0.25), 201, 1024), ("hall_b", "hall", (0.4, 0.8), 201, 1024),
                                           ("landing", "landing", (0.6, 0.4), 202, 1024)):
        layout.place_on_floor(f"foe_{name}", rooms[room].region_id, local=local, angle=angle, **supplies.dude(kind))
    # the leaf a player sees is the band of the NEIGHBOUR's wall over the shut door (a rising door's own walls have no
    # height at rest): the passage's and the hall's side of it wear the panelled metal, and the door's own stay brick
    doors.hang_leaf(layout, rooms["door"], LEAF_TILE, ("west", rooms["passage"]), ("east", rooms["hall"]))
    counts["locks_signed"] = keys.sign_the_locks(layout)
    circuit = wiring.Circuit(layout)
    # the way out: a switch on the landing's far wall, wearing the tile that says so
    landing = rooms["landing"]
    (x0, y0), (x1, y1) = [landing.world_frame().apply(p) for p in landing.local_edge("east")]
    way_out = dict(switches.exit_switch())
    way_out.pop("behavior")
    layout.place_on_wall("exit_switch", landing.region_id, a1=(x0, y0), a2=(x1, y1), t=0.5, status=0,
                         height_player_heights=way_out.pop("height_player_heights"), **way_out)
    circuit.wire("way-out", "pushing the switch on the landing ends the level", engine="kChannelLevelExitNormal").when(
        wiring.placement("exit_switch"), "push", command=1)
    made = finish.finish(layout, MAP if write else None, circuit=circuit, light=light, manifest=counts)
    if write and made.ok:
        # only for a map that was written: a manifest beside an older map would describe a level that is not there
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
