"""Build __TITLE__: the level's rooms as a program, taken to a map by the shared finishing sequence.

    python projects/__NAME__/level/build.py

This is a starter, and it is a whole level in the small: a room to start in, a
passage shut by a door, a hall with a stair up to a landing, a lamp rule, and a
switch that ends the level. Replace it room by room. What it shows is the
shape every build has:

    program   rooms in a tree, each in its own coordinates (`bloodmap.levelprog`)
    layout    `program.compile()`: flat, absolute; the level's own structures are added here
    circuit   every wire declared with what it is for (`bloodmap.wiring.Circuit`)
    finish    compile, align, gates, light, tidy, write (`bloodmap.finish`)

Before building a kind of place, look it up: `python -m tools.catalog find <words>`
(the findings come first), `python -m tools.study <slug> --want "..."` for how
Blood built one. After building: `python -m tools.look __NAME__ --set start -o work/__NAME__`.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROJECT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import doors, finish, switches, wiring
from bloodmap.levelprog import LevelProgram, Style, floor_detail
from bloodmap.light_stage import Rule
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.rules import art_sizes
from bloodmap.texture_align import sprite_tile_extents

BODY = PLAYER_PROFILES["blood"]
#: one body's width and height: sizes are written in these, never in bare numbers
U, PH = BODY.body_width, BODY.standing_height
MAP = PROJECT / "level" / "__NAME__.MAP"
FLOOR = 0

#: what the place is made of; a child room overrides only what differs
STONE = Style(wall_picnum=180, floor_picnum=292, ceiling_picnum=385, wall_shade=8, floor_shade=12, ceiling_shade=10,
              floor_z=FLOOR, clear_height=2 * PH)

#: which kind of light each place is lit by: the first key found in a region's path wins
LIGHTS = (
    ("door", Rule("none", 0, 0, cut=False)),
    ("passage", Rule("none", 0, 0)),            # too low for a lamp of its own: it is lit from both ends
    # the stage lays lights in roofed rooms only: under the sky a lamp post is a sprite you place
    ("hall", Rule("hanging", 641, 4096)),
    ("", Rule("ceiling", 795, 3072)),
)


def light(region: str) -> Rule:
    return next(rule for key, rule in LIGHTS if key in region)


def program() -> tuple[LevelProgram, dict]:
    level = LevelProgram("__NAME__", name="__TITLE__", style=STONE, art_sizes=art_sizes(),
                         tile_extents=sprite_tile_extents())
    entry = level.rect_room("entry", size=(8 * U, 8 * U), note="where the level starts")
    passage = level.rect_room("passage", size=(10 * U, 3 * U), note="a low way through")
    passage.surfaces(clear_height=int(1.4 * PH))
    passage.place_against("west", entry.face("east", at=0.5, width=3 * U))
    # a rising door is a room of its own, shut at rest; pushed open by hand (key=..., or remote=True and a wire, for more)
    door = doors.rising_door(level, "door", wide=3 * U, floor_z=FLOOR, opening=int(1.4 * PH))
    door.place_against("west", passage.face("east"))
    hall = level.rect_room("hall", size=(16 * U, 14 * U), note="the big room: a stair up its east side")
    hall.surfaces(clear_height=4 * PH, wall_picnum=5)
    hall.place_against("west", door.face("east"))
    landing = level.rect_room("landing", size=(6 * U, 8 * U), note="up the stair: the way out")
    landing.surfaces(clear_height=2 * PH)
    rise = 5 * BODY.max_step
    # laid against the hall's east side, then set back by the stair's run and up by its rise (up is negative z)
    landing.place_against("west", hall.face("east", at=0.5, width=6 * U)).move(dx=5 * 2 * U, dz=-rise)
    # two rooms that share an edge are joined along ALL of it; `at` runs the way the outline walks (see `Room.face`)
    level.connect(entry.face("east", at=0.5, width=3 * U), passage.face("west"))
    level.connect(passage.face("east"), door.face("west"))
    level.connect(door.face("east"), hall.face("west", at=0.5, width=3 * U))
    hall.staircase("stairs:up", "east", at=0.5, width=6 * U, total_rise=-rise, step_rise=-BODY.max_step, tread=2 * U,
                   arrive_at=landing.region_id)
    # supplies: a tile is chosen by what it is (`python -m tools.catalog find <words>`), never by a number that looked right
    hall.decorate(floor_detail("barrel", 925, 0.75, local=(0.25, 0.25), cstat=129))
    level.set_start(entry, local=(0.3, 0.5), angle=0)
    return level, {"entry": entry, "passage": passage, "door": door, "hall": hall, "landing": landing}


def build_level():
    """The level as a program, for the tools that read a level by its parts (`python -m tools.observe program`)."""
    return program()[0]


def build(write: bool = True) -> finish.Finished:
    """Build the level; `write=False` builds and holds it to the gates without touching the files (a test)."""
    level, rooms = program()
    layout = level.compile()
    # a shut door has no height: the leaf a player sees is its neighbours' wall over it
    doors.hang_leaf(layout, rooms["door"], 495, ("west", rooms["passage"]), ("east", rooms["hall"]))
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
    made = finish.finish(layout, MAP if write else None, circuit=circuit, light=light)
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
