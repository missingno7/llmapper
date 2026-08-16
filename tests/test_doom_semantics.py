from __future__ import annotations

import os
import unittest
from pathlib import Path

from bloodmap.doom import read_wad, wad_map
from bloodmap.doom_fixtures import (
    fixture_keyed_door, fixture_switch_door, fixture_teleport, fixture_unreachable_remote_switch,
)
from bloodmap.doom_semantics import (
    BOOM_SPECIALS_IN_VANILLA_RANGE, LINEDEF_SPECIALS, VANILLA_SPECIAL_MAX,
    analyze_doom_mechanisms, doom_to_semantic_level,
)
from bloodmap.mechanisms import Representability, representability_matrix, solve_progression


DOOM_WAD = Path(os.environ.get("DOOM_IWAD", Path(__file__).resolve().parents[1] / "maps" / "doom" / "doom.wad"))


class DoomSemanticsTests(unittest.TestCase):
    def test_vanilla_specials_are_sourced_from_gzdoom_xlat(self):
        self.assertEqual(LINEDEF_SPECIALS[1].action, "Door_Raise")
        self.assertEqual(LINEDEF_SPECIALS[1].activation, "use")
        self.assertTrue(LINEDEF_SPECIALS[1].local_backsector)
        self.assertEqual(LINEDEF_SPECIALS[26].key, "blue")
        self.assertEqual(LINEDEF_SPECIALS[39].kind, "teleport")
        self.assertEqual(LINEDEF_SPECIALS[11].kind, "exit")
        self.assertNotIn(78, LINEDEF_SPECIALS)

    def test_keyed_fixture_is_a_semantic_key_gate(self):
        _semantic, doom, _blood = fixture_keyed_door()
        inventory = analyze_doom_mechanisms(doom)
        kinds = {item["kind"] for item in inventory["mechanisms"]}
        self.assertIn("key_gate", kinds)
        compiled = doom_to_semantic_level(doom)
        solution = solve_progression(compiled)
        self.assertTrue(solution["exit_reachable"])
        self.assertIn("key:blue", solution["keys"])

    def test_switch_and_teleport_fixtures_compile(self):
        _semantic, door_map, _blood = fixture_switch_door()
        doors = analyze_doom_mechanisms(door_map)
        self.assertTrue(any(item["kind"] == "door" for item in doors["mechanisms"]))
        _semantic, teleport_map, _blood = fixture_teleport()
        teleports = analyze_doom_mechanisms(teleport_map)
        self.assertTrue(any(item["kind"] == "teleport" for item in teleports["mechanisms"]))

    def test_representability_is_asymmetric(self):
        matrix = { (item["source"], item["target"], item["concept"]): item for item in representability_matrix() }
        self.assertEqual(matrix[("doom", "blood", "keyed door")]["representability"], Representability.SEMANTIC.value)
        self.assertEqual(
            matrix[("blood", "doom", "rotating sector")]["representability"],
            Representability.REQUIRES_REDESIGN.value,
        )
        self.assertEqual(
            matrix[("build", "doom", "stacked/overlapping sectors")]["representability"],
            Representability.UNSUPPORTED.value,
        )

    def test_e1m1_recognizes_vanilla_doors_and_exits(self):
        if not DOOM_WAD.exists():
            self.skipTest("DOOM.WAD is not present")
        level = wad_map(read_wad(DOOM_WAD), "E1M1")
        inventory = analyze_doom_mechanisms(level)
        self.assertEqual(inventory["format"], "doom")
        self.assertGreater(inventory["counts"].get("door", 0), 0)
        self.assertGreater(inventory["counts"].get("exit", 0), 0)
        self.assertIn("player_start", inventory["thing_roles"])

    @unittest.expectedFailure
    def test_vanilla_special_scope_is_explicit_for_every_value(self):
        scope = [number for number in range(1, VANILLA_SPECIAL_MAX + 1) if number not in BOOM_SPECIALS_IN_VANILLA_RANGE]
        missing = [number for number in scope if number not in LINEDEF_SPECIALS]
        self.assertEqual(missing, [], msg=f"sparse inventory leaves {missing} classified only by absence")
        self.assertIn(14, LINEDEF_SPECIALS)
        self.assertNotEqual(getattr(LINEDEF_SPECIALS.get(14), "action", "boom-or-unknown"), "boom-or-unknown")

    @unittest.expectedFailure
    def test_previously_omitted_specials_are_not_boom_or_unknown(self):
        from bloodmap.doom import DoomLinedef, DoomSector, DoomSidedef, DoomVertex, _tex8, NO_SIDE, ML_BLOCKING
        from bloodmap.doom import DoomDiskMap

        representatives = (14, 53, 141)
        linedefs = []
        sidedefs = []
        for special in representatives:
            front = len(sidedefs)
            sidedefs.append(DoomSidedef(0, 0, _tex8("-"), _tex8("-"), _tex8("STARTAN2"), 0))
            linedefs.append(DoomLinedef(0, 1, ML_BLOCKING, special, 1, front, NO_SIDE))
        level = DoomDiskMap(
            name="MAP01", format="doom",
            things=[],
            linedefs=linedefs,
            sidedefs=sidedefs,
            vertices=[DoomVertex(0, 0), DoomVertex(64, 0)],
            sectors=[DoomSector(0, 128, _tex8(b"FLOOR0_1"), _tex8(b"CEIL1_1"), 192, 0, 1)],
        )
        inventory = analyze_doom_mechanisms(level)
        by_special = {item["special"]: item for item in inventory["mechanisms"]}
        unsupported = {item["special"]: item for item in inventory["unsupported"]}
        for special in representatives:
            self.assertNotIn(special, unsupported, msg=f"special {special} must not be boom-or-unknown")
            self.assertIn(special, by_special)

    @unittest.expectedFailure
    def test_unreachable_remote_switch_does_not_open_the_exit(self):
        semantic, _doom, _blood = fixture_unreachable_remote_switch()
        solution = solve_progression(semantic)
        self.assertFalse(solution["exit_reachable"])
        self.assertNotIn("exit", solution["reached_regions"])

    def test_e1m3_recognizes_keyed_progression(self):
        if not DOOM_WAD.exists():
            self.skipTest("DOOM.WAD is not present")
        level = wad_map(read_wad(DOOM_WAD), "E1M3")
        inventory = analyze_doom_mechanisms(level)
        self.assertGreater(inventory["counts"].get("key_gate", 0), 0)
        compiled = doom_to_semantic_level(level)
        self.assertTrue(any(item.kind == "key_gate" for item in compiled.mechanisms))


if __name__ == "__main__":
    unittest.main()
