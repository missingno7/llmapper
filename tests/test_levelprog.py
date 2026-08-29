from __future__ import annotations

import unittest

from bloodmap.decompiler import decompile_level
from bloodmap.levelprog import (
    Frame,
    LevelProgram,
    LevelProgramError,
    Style,
    ceiling_detail,
    floor_detail,
    native_detail,
    wall_detail,
)
from bloodmap.structures import detect_structures

U = 384
PH = 0x1600

BASE = Style(
    wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
    wall_shade=8, floor_shade=16, ceiling_shade=8,
    floor_z=8192, clear_height=8 * PH,
)
ART = {506: (12, 43), 1701: (30, 119), 2540: (58, 58)}


def _program(*, lobby_height: int = 9 * PH, rise: int = 4 * 4096,
             extra_detail: bool = False) -> LevelProgram:
    """A yard containing a building containing rooms containing a stair."""
    level = LevelProgram("fixture", name="levelprog-fixture", style=BASE, art_sizes=ART)
    manor = level.assembly("manor", style=Style(wall_picnum=5, clear_height=8 * PH))
    lobby = manor.rect_room("lobby", size=(14 * U, 12 * U), note="entrance hall")
    lobby.surfaces(clear_height=lobby_height)
    lobby.recess("recess:niche", "south", at=0.5, width=3 * U,
                 depth=int(1.5 * U), ceiling_drop=3 * PH)
    lobby.decorate(
        wall_detail("torch", 506, 1.5, face="north", at=0.3, cstat=128, shade=-128),
        ceiling_detail("lamp", 1701, 1.4),
    )
    if extra_detail:
        lobby.decorate(floor_detail("emblem", 2540, 0.9))
    wing = manor.rect_room("wing", size=(8 * U, 8 * U))
    wing.place_against("east", lobby.face("west", at=0.5, width=8 * U))
    wing.surfaces(floor_picnum=294, clear_height=6 * PH)
    level.connect(lobby.face("west", at=0.5, width=8 * U),
                  wing.face("east", at=0.5, width=8 * U),
                  connection_id="connection:lobby_wing")
    gallery = manor.rect_room("gallery", size=(12 * U, 6 * U))
    gallery.place_against("west", lobby.face("east", at=0.5, width=6 * U))
    gallery.frame = Frame(
        gallery.frame.dx + (rise // 4096) * 2 * U, gallery.frame.dy, -rise,
    )
    gallery.surfaces(clear_height=10 * PH)
    stairs = lobby.staircase(
        "stairs:grand", "east", at=0.5, width=6 * U,
        total_rise=-rise, step_rise=-4096, tread=2 * U,
        arrive_at=gallery.region_id, shade_ramp=(18, 10),
    )
    stairs.decorate(wall_detail("sconce", 506, 0.9, face="flank", at=0.5, cstat=464))
    level.set_start(lobby, local=(0.2, 0.5))
    return level


class LocalityTests(unittest.TestCase):
    def test_room_light_source_is_visible_in_source_and_compiles(self):
        level = LevelProgram(
            "lit", style=Style(wall_picnum=180, floor_picnum=292,
                               ceiling_picnum=385, floor_z=8192,
                               clear_height=8 * PH),
        )
        room = level.rect_room("room", size=(8 * U, 8 * U),
                               region_kwargs={"declared_zero_exit": True})
        room.light_source("window", local=(0.25, 0.5), height_player_heights=2.0)
        level.set_start(room)

        compiled = level.compile().compile()

        self.assertEqual(room.summary()["light_sources"], ["window"])
        self.assertEqual(compiled.lighting_report["source_ids"], ["light:lit/room:window"])

    def test_a_room_summary_answers_everything_about_that_room(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")

        summary = lobby.summary()

        self.assertEqual(summary["path"], "fixture/manor/lobby")
        self.assertEqual(summary["faces"], ["east", "north", "south", "west"])
        self.assertEqual(summary["footprint_player_areas"], 168.0)
        self.assertEqual([item["id"] for item in summary["structures"]],
                         ["recess:niche", "stairs:grand"])
        self.assertEqual(summary["details"], ["torch", "lamp"])
        self.assertIn("wall_picnum", summary["surfaces"])

    def test_the_tree_names_every_part_without_naming_a_sector(self):
        text = _program().tree()

        for name in ("fixture", "manor", "lobby", "wing", "gallery"):
            self.assertIn(name, text)
        self.assertNotIn("sector", text)


class LocalCoordinateTests(unittest.TestCase):
    def test_moving_a_parent_moves_its_children_without_touching_their_outlines(self):
        level = _program()
        manor = next(node for node in level.children if node.node_id == "manor")
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")
        before_local = list(lobby.outline)
        before_world = lobby.world_outline()

        manor.frame = Frame(7 * U, 3 * U)

        self.assertEqual(lobby.outline, before_local)
        after = lobby.world_outline()
        self.assertEqual(
            [(x + 7 * U, y + 3 * U) for x, y in before_world], after,
        )

    def test_place_against_produces_an_exactly_shared_edge(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")
        wing = next(room for room in level.rooms() if room.node_id == "wing")

        left = lobby.face_anchor("west", at=0.5, width=8 * U)
        right = wing.face_anchor("east", at=0.5, width=8 * U)

        self.assertEqual(left.a, right.b)
        self.assertEqual(left.b, right.a)

    def test_a_wrong_face_name_says_what_the_room_offers(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")

        with self.assertRaises(LevelProgramError) as caught:
            lobby.face("northwest")

        self.assertIn("northwest", str(caught.exception))
        self.assertIn("north", str(caught.exception))


class InheritanceTests(unittest.TestCase):
    def test_a_child_inherits_and_every_value_names_the_node_that_set_it(self):
        level = _program()
        wing = next(room for room in level.rooms() if room.node_id == "wing")

        provenance = wing.style_provenance()

        self.assertEqual(provenance["ceiling_picnum"], {"value": 385, "from": "fixture"})
        self.assertEqual(provenance["wall_picnum"], {"value": 5, "from": "fixture/manor"})
        self.assertEqual(provenance["floor_picnum"],
                         {"value": 294, "from": "fixture/manor/wing"})
        self.assertEqual(provenance["clear_height"]["from"], "fixture/manor/wing")

    def test_a_room_states_only_what_differs(self):
        level = _program()
        wing = next(room for room in level.rooms() if room.node_id == "wing")

        self.assertEqual(set(wing.style.stated()), {"floor_picnum", "clear_height"})

    def test_an_unknown_style_field_is_refused_by_name(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")

        with self.assertRaises(LevelProgramError) as caught:
            lobby.surfaces(wall_colour=3)

        self.assertIn("wall_colour", str(caught.exception))

    def test_a_room_with_no_answer_anywhere_says_which_field_is_missing(self):
        level = LevelProgram("bare", style=Style(wall_picnum=180))
        level.rect_room("room", size=(4 * U, 4 * U))

        with self.assertRaises(LevelProgramError) as caught:
            level.compile()

        self.assertIn("floor_picnum", str(caught.exception))


class CompilationTests(unittest.TestCase):
    def test_the_program_lowers_to_planar_source_and_compiles(self):
        compiled = _program().compile().compile()

        self.assertGreater(len(compiled.level.sectors), 5)
        self.assertTrue(compiled.level.sprites)

    def test_one_number_changes_the_independently_derived_structure(self):
        before = detect_structures(_program(rise=4 * 4096).compile().compile().level)
        after = detect_structures(_program(rise=7 * 4096).compile().compile().level)

        before_run = next(item for item in before["structures"]
                          if item["kind"] == "stepped_run")
        after_run = next(item for item in after["structures"]
                         if item["kind"] == "stepped_run")
        self.assertEqual(before_run["parameters"]["rises"], 4)
        self.assertEqual(after_run["parameters"]["rises"], 7)

    def test_the_nesting_is_recovered_by_the_independent_decompiler(self):
        compiled = _program().compile().compile()

        source = decompile_level(compiled.level)

        kinds = {
            node["structure"]["kind"]
            for node in source.hierarchy["nodes"] if node["kind"] == "structure"
        }
        self.assertIn("stepped_run", kinds)
        self.assertIn("recess", kinds)


class ContainmentTests(unittest.TestCase):
    def test_adding_a_detail_to_one_room_changes_only_that_room(self):
        plain = _program().compile().compile().level
        extra = _program(extra_detail=True).compile().compile().level

        self.assertEqual(len(extra.sprites), len(plain.sprites) + 1)
        self.assertEqual(len(extra.sectors), len(plain.sectors))
        self.assertEqual(
            [sector["fields"]["floor_picnum"] for sector in plain.sectors],
            [sector["fields"]["floor_picnum"] for sector in extra.sectors],
        )

    def test_a_structure_owns_its_own_details(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")

        stairs = next(item for item in lobby.structures
                      if item.structure_id == "stairs:grand")

        self.assertEqual([item.detail_id for item in stairs.details], ["sconce"])
        self.assertNotIn("sconce", [item.detail_id for item in lobby.details])


class EscapeHatchTests(unittest.TestCase):
    def test_raw_runs_against_the_lowered_layout_and_is_recorded(self):
        level = _program()
        lobby = next(room for room in level.rooms() if room.node_id == "lobby")
        seen: list[str] = []
        lobby.raw(
            "a mechanism the language cannot say yet",
            lambda layout, room: seen.append(room.region_id),
        )

        level.compile()

        self.assertEqual(seen, [lobby.region_id])
        self.assertEqual(
            lobby.summary()["raw_escapes"], ["a mechanism the language cannot say yet"],
        )


class NativeDetailTests(unittest.TestCase):
    def test_stated_repeats_win_over_a_derived_target_height(self):
        level = LevelProgram("native", style=BASE, art_sizes={})
        room = level.rect_room("room", size=(6 * U, 6 * U),
                               region_kwargs={"declared_zero_exit": True})
        room.decorate(native_detail("thing", 9999, x_repeat=17, y_repeat=23))
        level.set_start(room, local=(0.5, 0.5))

        compiled = level.compile().compile()

        sprite = next(item["fields"] for item in compiled.level.sprites
                      if int(item["fields"]["picnum"]) == 9999)
        self.assertEqual(int(sprite["x_repeat"]), 17)
        self.assertEqual(int(sprite["y_repeat"]), 23)


if __name__ == "__main__":
    unittest.main()
