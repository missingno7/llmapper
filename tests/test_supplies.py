"""The supplies sensor against facts of E1M1 that are known from its records and its walkthrough."""

from __future__ import annotations

import unittest

from bloodmap import supplies
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import DiskObject

E1M1 = corpus_map_path("E1M1", missing_ok=True)


class LaunchTests(unittest.TestCase):
    def test_the_launch_bits_lock_out(self):
        def sprite(**extra):
            class Extra:
                fields = extra
            return DiskObject(fields={"type": 203}, extra=Extra())
        self.assertTrue(supplies.launched(DiskObject(fields={"type": 203})))
        self.assertTrue(supplies.launched(sprite(launch_skill=0b00011, launch_single=0)))
        self.assertFalse(supplies.launched(sprite(launch_skill=0b00100, launch_single=0)))
        self.assertTrue(supplies.launched(sprite(launch_skill=0b00100, launch_single=0), skill=3))
        self.assertFalse(supplies.launched(sprite(launch_skill=0, launch_single=1)))
        self.assertTrue(supplies.launched(sprite(launch_skill=0, launch_bloodbath=1, launch_coop=1)))

    def test_what_a_type_gives_is_the_engines_table(self):
        self.assertEqual(supplies.item_type(68)["rounds"], 15)       # gAmmoItemData
        self.assertEqual(supplies.item_type(72)["rounds"], 100)
        self.assertEqual(supplies.item_type(109)["points"], 20)      # gPowerUpInfo
        self.assertEqual(supplies.damage_of(supplies.item_type(67)), 4 * 64)
        self.assertIsNone(supplies.item_type(203))


@unittest.skipUnless(E1M1.exists(), "the corpus is not here")
class E1M1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disk = read_map(E1M1)
        cls.row = supplies.read(cls.disk, "E1M1")

    def test_the_skull_gate_is_shut_when_the_level_loads(self):
        # both leaves are drawn open along the walls of sector 55, state 0
        walk = supplies.Walk(supplies.as_launched(self.disk))
        self.assertEqual(walk.joins[(55, 0, 1)], {50, 51})

    def test_the_exit_is_reached_and_wants_the_dagger(self):
        self.assertEqual(self.row["way_is"], "the exit")
        self.assertEqual(self.row["exits"][0]["needs"], [4])

    def test_the_keys_are_dropped_by_two_cultists_in_order(self):
        keys = [(k["name"], k["carried_by"], k["sprite"]) for k in self.row["keys"]]
        self.assertEqual(keys, [("skull", "shotgun cultist", 544), ("dagger", "shotgun cultist", 546)])
        self.assertEqual([k["opens"] for k in self.row["keys"]], [["a swinging door"], ["a sliding door"]])

    def test_the_secrets_hold_what_the_wiki_says(self):
        held = sorted(name for s in self.row["secrets"] for name in s["reward"])
        self.assertEqual(held, sorted([
            "box of flares", "TNT box", "body armor", "guns akimbo", "box of flares", "beast vision",
            "body armor", "life seed", "fire armor", "box of flares", "box of flares", "box of flares",
            "napalm launcher"]))
        self.assertEqual(sum(1 for s in self.row["secrets"] if s["super"]), 1)

    def test_the_budget_counts_what_this_difficulty_launches(self):
        budget = self.row["budget"]
        self.assertEqual(budget["by_foe"], {"axe zombie": 6, "buried zombie": 5, "rat": 13,
                                            "shotgun cultist": 7})
        self.assertEqual(budget["foe_health"], 6 * 60 + 5 * 60 + 13 * 10 + 7 * 40)
        self.assertGreater(budget["ammo_damage_in_secrets"], budget["ammo_damage"] / 2)

    def test_nothing_is_nearer_than_the_start_and_the_dagger_lies_past_the_skull(self):
        first, second = self.row["keys"]
        self.assertLess(0, first["at"])
        self.assertLess(first["at"], second["at"])
        self.assertLess(second["way"], 1.0)


if __name__ == "__main__":
    unittest.main()
