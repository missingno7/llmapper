"""Authoring transfer test: a nested structure written in the level-program language.

The point of this file is not the level.  It is the *shape of the source*.  The
brief for it is the nesting the flat language could not express locally:

    a large exterior parent area
      containing a building
        containing several rooms
          one of which contains a staircase
            which owns its own details

Read it the way the claim about the language should be tested.  ``build_level``
is nine lines and names the three areas.  ``build_manor`` names its rooms and
the stair between two of them.  ``build_lobby`` is the lobby and nothing else:
its outline in its own coordinates, its own surfaces, its niche, its lamps.  No
function here mentions a sector index, a wall index, or an absolute coordinate
outside the one place each area is anchored.

Run it:

    python -m experiments.nested_authoring --map work/nested-authoring.MAP
    python -m experiments.nested_authoring --tree
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bloodmap.authoring_loop import (
    AuthoredAssembly,
    AuthoredIntent,
    AuthoredTransition,
    Candidate,
    ProbeRequest,
    evaluate_candidate,
)
from bloodmap.levelprog import (
    Assembly,
    Frame,
    LevelProgram,
    Room,
    Style,
    ceiling_detail,
    floor_detail,
    wall_detail,
)
from bloodmap.vocabulary import art_sizes_from_directory
from bloodmap.viewpoints import ViewpointSpec

U = 384          # one player body width
PH = 0x1600      # one player standing height

# Surface vocabulary as named roles rather than bare tile numbers.  The exact
# ids stay right here, one line away, because hiding them would be worse.
COURT_WALL, COURT_FLOOR, SKY = 110, 2448, 2500
MANOR_WALL, MANOR_FLOOR, MANOR_CEILING = 5, 294, 454
WING_WALL, WING_FLOOR, WING_CEILING = 80, 294, 285
GALLERY_WALL, GALLERY_FLOOR, GALLERY_CEILING = 91, 44, 455
CELLAR_WALL, CELLAR_FLOOR, CELLAR_CEILING = 194, 568, 67

TORCH, SCONCE, EMBLEM, LAMP, GRILLE = 506, 2542, 2540, 1701, 1044


def build_lobby(manor: Assembly) -> Room:
    """The manor's entrance hall: 14 by 12 player widths, with a wall niche.

    Everything the lobby is, is in this function.  Its outline is written around
    its own origin, so moving the manor moves the lobby without touching a
    number here.
    """
    lobby = manor.rect_room("lobby", size=(14 * U, 12 * U), note="entrance hall")
    lobby.surfaces(clear_height=9 * PH, floor_shade=18, wall_shade=16, ceiling_shade=14)
    # The west face carries the wing and the east face the stair, so the niche
    # goes south.  A face is a real resource: one structure per stretch of it.
    lobby.recess(
        "recess:lobby_niche", "south", at=0.5, width=3 * U,
        depth=int(1.5 * U), ceiling_drop=4 * PH,
    )
    lobby.decorate(
        wall_detail("torch_north", TORCH, 1.5, face="north", at=0.25,
                    height=1.9, cstat=128, shade=-128),
        wall_detail("torch_south", TORCH, 1.5, face="south", at=0.75,
                    height=1.9, cstat=128, shade=-128),
        ceiling_detail("chandelier", LAMP, 1.6, local=(0.5, 0.5), height=0.8,
                       cstat=384, shade=-96),
        floor_detail("floor_emblem", EMBLEM, 0.9, local=(0.5, 0.5), cstat=32),
    )
    return lobby


def build_west_wing(manor: Assembly, lobby: Room) -> Room:
    """A side room off the lobby's west face, one step of the manor's own style."""
    wing = manor.rect_room("west_wing", size=(8 * U, 8 * U), note="west wing")
    wing.place_against("east", lobby.face("west", at=0.5, width=8 * U))
    wing.surfaces(
        wall_picnum=WING_WALL, floor_picnum=WING_FLOOR, ceiling_picnum=WING_CEILING,
        clear_height=6 * PH, floor_shade=24, wall_shade=22, ceiling_shade=20,
    )
    wing.decorate(
        wall_detail("wing_grille", GRILLE, 1.6, face="west", at=0.5, height=1.9,
                    cstat=16, shade=-16),
        ceiling_detail("wing_lamp", LAMP, 1.1, local=(0.5, 0.5), height=0.6,
                       cstat=384, shade=-96),
    )
    return wing


def build_upper_gallery(manor: Assembly, lobby: Room, rise: int) -> Room:
    """The floor above, reached by the lobby stair; its own elevation and light."""
    gallery = manor.rect_room("upper_gallery", size=(12 * U, 6 * U), note="upper gallery")
    gallery.place_against("west", lobby.face("east", at=0.5, width=6 * U))
    # The stair eats the first eight player widths of the gap it crosses.
    gallery.frame = Frame(gallery.frame.dx + 8 * U, gallery.frame.dy, -rise)
    gallery.surfaces(
        wall_picnum=GALLERY_WALL, floor_picnum=GALLERY_FLOOR,
        ceiling_picnum=GALLERY_CEILING, clear_height=11 * PH,
        floor_shade=10, wall_shade=8, ceiling_shade=6,
    )
    gallery.recess(
        "recess:gallery_niche", "north", at=0.7, width=int(2.5 * U),
        depth=int(1.5 * U), ceiling_drop=7 * PH,
    )
    # THE ESCAPE HATCH, used on purpose.  The level-program language has no
    # vocabulary for mechanisms yet, so the exit switch is added natively, with
    # a note saying so, rather than by inventing a half-thought-out mechanism
    # abstraction to avoid one raw call.
    gallery.raw(
        "exit switch: the language has no mechanism vocabulary yet",
        lambda layout, room: layout.place_on_wall(
            "sw_exit", room.region_id,
            a1=room.face_anchor("east").a, a2=room.face_anchor("east").b,
            t=0.5, height_player_heights=2.18, offset_player_widths=0.12,
            type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8,
            behavior={"tx_id": 4, "command": 1, "trigger_on": 1, "trigger_push": 1},
        ),
    )
    gallery.decorate(
        wall_detail("gallery_emblem", EMBLEM, 1.2, face="east", at=0.3, height=2.4,
                    cstat=16, shade=-24),
        ceiling_detail("gallery_lamp_west", LAMP, 2.0, local=(0.3, 0.5), height=0.9,
                       cstat=384, shade=-96),
        ceiling_detail("gallery_lamp_east", LAMP, 2.0, local=(0.7, 0.5), height=0.9,
                       cstat=384, shade=-96),
    )
    return gallery


def build_manor(level: LevelProgram, *, rise: int) -> Assembly:
    """The building: three rooms and the stair that joins two of them.

    The stair is declared on the lobby, owns its own decoration, and states
    where it arrives.  Nothing about it is written twice.
    """
    manor = level.assembly(
        "manor",
        style=Style(
            wall_picnum=MANOR_WALL, floor_picnum=MANOR_FLOOR,
            ceiling_picnum=MANOR_CEILING, floor_z=8192, clear_height=8 * PH,
        ),
        note="an embedded building inside the grounds",
    )
    lobby = build_lobby(manor)
    wing = build_west_wing(manor, lobby)
    gallery = build_upper_gallery(manor, lobby, rise)

    stairs = lobby.staircase(
        "stairs:grand", "east", at=0.5, width=6 * U,
        total_rise=-rise, step_rise=-4096, tread=2 * U,
        arrive_at=gallery.region_id, shade_ramp=(18, 10),
    )
    # Details attach to the stair, not to a level-wide sprite list.
    stairs.decorate(
        wall_detail("stair_sconce", SCONCE, 0.9, face="flank", at=0.5, height=2.1,
                    cstat=464, shade=-24),
    )

    level.connect(
        lobby.face("west", at=0.5, width=8 * U),
        wing.face("east", at=0.5, width=8 * U),
        connection_id="connection:lobby_wing",
    )
    return manor


def build_grounds(level: LevelProgram, *, manor: Assembly) -> Assembly:
    """The large exterior parent the building stands in."""
    grounds = level.assembly(
        "grounds",
        style=Style(
            wall_picnum=COURT_WALL, floor_picnum=COURT_FLOOR, ceiling_picnum=SKY,
            parallax_ceiling=True, floor_z=8192, clear_height=13 * PH,
            floor_shade=16, wall_shade=14, ceiling_shade=0,
        ),
        note="the exterior parent area",
    )
    yard = grounds.rect_room(
        "yard", origin=(-20 * U, -18 * U), size=(60 * U, 52 * U),
        role="exterior", note="the walled ground the manor stands in",
    )
    # The manor's footprint is solid mass from the yard's point of view.  The
    # hole is stated once, in the yard's own coordinates, and is deliberately
    # larger than the building so no interior wall accidentally opens onto the
    # yard; the only way through is the porch.
    yard.carve([
        (8 * U, 12 * U), (58 * U, 12 * U), (58 * U, 48 * U), (8 * U, 48 * U),
    ])
    yard.decorate(
        wall_detail("yard_torch", TORCH, 1.7, face="west", at=0.5, height=2.0,
                    cstat=128, shade=-128),
        # Floor fractions are of the room's bounding box, so a carved room needs
        # a spot that is actually open ground rather than inside its own mass.
        floor_detail("yard_emblem", EMBLEM, 1.1, local=(0.08, 0.2), cstat=32),
    )
    return grounds


def build_undercroft(level: LevelProgram, *, lobby: Room, drop: int) -> Assembly:
    """A lower area reached by a stair down out of the west wing."""
    undercroft = level.assembly(
        "undercroft",
        style=Style(
            wall_picnum=CELLAR_WALL, floor_picnum=CELLAR_FLOOR,
            ceiling_picnum=CELLAR_CEILING, floor_z=8192, clear_height=5 * PH,
            floor_shade=34, wall_shade=32, ceiling_shade=30,
        ),
        note="a lower area under the grounds",
    )
    cellar = undercroft.rect_room("cellar", size=(10 * U, 10 * U), note="vaulted cellar")
    cellar.frame = Frame(cellar.frame.dx, cellar.frame.dy, drop)
    cellar.recess(
        "recess:cellar_niche", "south", at=0.5, width=2 * U,
        depth=int(1.5 * U), ceiling_drop=2 * PH,
    )
    cellar.decorate(
        ceiling_detail("cellar_chain", LAMP, 1.0, local=(0.5, 0.5), height=0.5,
                       cstat=384, shade=-64),
    )
    return undercroft


def build_level() -> LevelProgram:
    """A walled ground, a manor inside it, and a cellar under the manor."""
    rise, drop = 4 * 4096, 4 * 3072
    level = LevelProgram(
        "nested", name="nested-authoring-v1",
        art_sizes=art_sizes_from_directory("reference/blood"),
        note="authoring transfer test for the level-program language",
    )
    manor = build_manor(level, rise=rise)
    lobby = next(room for room in manor.rooms() if room.node_id == "lobby")
    wing = next(room for room in manor.rooms() if room.node_id == "west_wing")
    grounds = build_grounds(level, manor=manor)
    undercroft = build_undercroft(level, lobby=lobby, drop=drop)

    yard = next(room for room in grounds.rooms() if room.node_id == "yard")
    cellar = next(room for room in undercroft.rooms() if room.node_id == "cellar")
    cellar.place_against("north", wing.face("south", at=0.5, width=8 * U))
    cellar.frame = Frame(cellar.frame.dx, cellar.frame.dy + 6 * U, drop)

    descent = wing.staircase(
        "stairs:cellar", "south", at=0.5, width=4 * U,
        total_rise=drop, step_rise=3072, tread=int(1.5 * U),
        arrive_at=cellar.region_id, shade_ramp=(24, 34),
    )
    descent.decorate(
        wall_detail("cellar_stair_sconce", SCONCE, 0.8, face="flank", at=0.5,
                    height=1.8, cstat=464, shade=-16),
    )

    # The one way in: a porch that bridges the solid mass, from the hole's own
    # north edge to the lobby's north wall.
    porch = grounds.rect_room("porch", size=(3 * U, 6 * U), role="gateway",
                              note="the way in from the yard")
    porch.place_against("south", lobby.face("north", at=0.5, width=3 * U))
    porch.surfaces(parallax_ceiling=False, ceiling_picnum=MANOR_CEILING,
                   clear_height=4 * PH, floor_shade=20, wall_shade=18, ceiling_shade=18)
    level.connect(lobby.face("north", at=0.5, width=3 * U),
                  porch.face("south", width=3 * U),
                  connection_id="connection:porch_lobby")
    # The porch states the interval; the yard is simply the other side of it.
    # Naming the stretch from the side that owns it is what keeps this free of
    # the "which fraction along the hole is that?" arithmetic.
    level.connect(porch.face("north", width=3 * U),
                  yard.hole_face(0, "north"),
                  connection_id="connection:yard_porch")
    level.set_start(yard, local=(0.08, 0.5), angle=0)
    return level


# ---------------------------------------------------------------------------
# The authoring-loop candidate, so the same gates and evidence apply
# ---------------------------------------------------------------------------

def _layout():
    return build_level().compile()


def intent() -> AuthoredIntent:
    return AuthoredIntent(
        brief="a walled ground containing a manor whose lobby stair rises to an "
              "upper gallery, with a cellar beneath the west wing",
        start_region="region:nested/grounds/yard",
        exit_region="region:nested/manor/upper_gallery",
        assemblies=(
            AuthoredAssembly(
                "assembly:grounds", "grounds", "exterior_parent",
                "the large walled exterior the manor stands in",
                ("region:nested/grounds/yard", "region:nested/grounds/porch"),
            ),
            AuthoredAssembly(
                "assembly:manor", "manor", "embedded_building",
                "the building inside the grounds: lobby, west wing, upper gallery",
                ("region:nested/manor/lobby", "region:nested/manor/west_wing",
                 "region:nested/manor/upper_gallery"),
                parent_assembly="assembly:grounds",
            ),
            AuthoredAssembly(
                "assembly:undercroft", "undercroft", "lower_interior",
                "the cellar under the west wing",
                ("region:nested/undercroft/cellar",),
            ),
        ),
        transitions=(
            AuthoredTransition(
                "transition:porch", "yard into the manor",
                "region:nested/grounds/porch", "region:nested/manor/lobby",
                "constrained_to_open",
                "a low porch releasing into a nine player-height hall",
                connection_id="connection:porch_lobby",
                expectation={"area_ratio_at_least": 6},
            ),
        ),
        progression=(
            {"step": 1, "action": "cross the yard and enter through the porch"},
            {"step": 2, "action": "climb the lobby stair to the upper gallery"},
            {"step": 3, "action": "take the wing stair down into the cellar"},
        ),
    )


def candidate() -> Candidate:
    return Candidate(
        iteration_id="nested-v1",
        module="experiments/nested_authoring.py",
        factory=_layout,
        intent=intent(),
        probes=(
            ProbeRequest("probe:reach_gallery", "access",
                         "can the upper gallery be reached from the yard?",
                         "the nesting claim depends on the stair actually connecting",
                         target_region="region:nested/manor/upper_gallery"),
            ProbeRequest("probe:reach_cellar", "access",
                         "can the cellar be reached?",
                         "the second stair is the second half of the nesting test",
                         target_region="region:nested/undercroft/cellar"),
            ProbeRequest("probe:porch_contrast", "transition",
                         "does the porch to lobby step read as a release?",
                         "one composed constrained-to-open transition",
                         source_region="region:nested/grounds/porch",
                         destination_region="region:nested/manor/lobby"),
        ),
        viewpoints=(
            ViewpointSpec("view:yard", "player_start", "region:nested/grounds/yard",
                          -16 * U, 8 * U, 8192 - 1024, 0,
                          note="open ground west of the manor, facing it"),
            ViewpointSpec("view:lobby", "assembly_center", "region:nested/manor/lobby",
                          7 * U, 6 * U, 8192 - 1024, 512,
                          note="the lobby, facing the stair"),
            ViewpointSpec("view:gallery", "assembly_center", "region:nested/manor/upper_gallery",
                          28 * U, 6 * U, 8192 - 4 * 4096 - 1024, 1536,
                          note="the upper gallery, looking back down the stair"),
        ),
        declared_changes=(
            "authored entirely in bloodmap.levelprog: no absolute coordinate outside "
            "the yard's own outline, no sector or wall index anywhere",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", help="write the compiled MAP here")
    parser.add_argument("--tree", action="store_true", help="print the program outline")
    parser.add_argument("--room", help="print one room's complete summary")
    parser.add_argument("--evaluate", action="store_true",
                        help="run the authoring-loop gates over the compiled candidate")
    parser.add_argument("--nblood", help="NBlood executable, for the load smoke")
    parser.add_argument("--game-dir", help="Blood game data directory")
    parser.add_argument("--report", help="write the evidence packet here")
    args = parser.parse_args(argv)

    program = build_level()
    if args.tree:
        print(program.tree())
    if args.room:
        room = next(item for item in program.rooms() if item.node_id == args.room)
        print(json.dumps(room.summary(), indent=1))
    layout = program.compile()
    compiled = layout.compile()
    print(json.dumps({
        "sectors": len(compiled.level.sectors),
        "walls": len(compiled.level.walls),
        "sprites": len(compiled.level.sprites),
        "rooms": len(program.rooms()),
    }, indent=1))
    if args.map:
        from bloodmap.format import write_map

        Path(args.map).parent.mkdir(parents=True, exist_ok=True)
        write_map(compiled.level.to_disk_map(), args.map)
        print(f"wrote {args.map}")
    if args.evaluate:
        engine: dict[str, Any] | None = None
        if args.nblood and args.game_dir:
            engine = {
                "nblood": args.nblood, "game_dir": args.game_dir,
                "grace_seconds": 14.0, "startup_timeout": 45.0, "settle_seconds": 3.0,
            }
        packet = evaluate_candidate(
            candidate(), map_path=args.map, engine=engine,
            view_dir=None if not args.report else str(Path(args.report).parent / "views"),
        )
        failed = [item["gate_id"] for item in packet.hard_gates if item["status"] == "fail"]
        smoke = next(item for item in packet.hard_gates
                     if item["gate_id"] == "nblood_load_smoke")
        structures = packet.independent_hierarchy["structure_recovery"]["coverage"]
        print(json.dumps({
            "failed_gates": failed or "none",
            "nblood_load_smoke": smoke["status"],
            "derived_structures": structures["by_kind"],
        }, indent=1))
        if args.report:
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(packet.to_dict(), indent=1, default=str),
                            encoding="utf-8")
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
