"""E3M1's mechanisms as sentences, against the supervisor's inventory.

The inventory is the denominator and it is not negotiable: 133 XSECTORs, 41
XWALLs, 716 XSPRITEs; sector types 600 x34, 614 x6, 615 x4, 616 x1, 617 x6,
618 x1; 18 walls of type 511; 26 sectors with a tx, 54 with an rx, 4
key-locked; 61 with a light wave, 45 with `shade_always`. If the reader's own
count of any of those drifts, it has stopped reading this map.
"""

from __future__ import annotations

import unittest


def _corpus():
    from bloodmap.format import read_map
    from bloodmap.patterns import corpus_map_path

    path = corpus_map_path("E3M1", missing_ok=True)
    if not path.exists():
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return path, read_map(path)


def _lessons():
    from bloodmap.patterns import corpus_map_path

    path = corpus_map_path("E1M1", missing_ok=True)
    lessons = path.parent.parent / "mechanism" / "Vanilla"
    if not lessons.exists():
        raise unittest.SkipTest("the taught course is not in the corpus")
    return lessons


class TheInventory(unittest.TestCase):
    def setUp(self):
        from bloodmap.curriculum import mine_map
        from bloodmap.read_mechanisms import read_mechanisms

        path, disk = _corpus()
        self.level = disk.to_level_ir()
        self.result = read_mechanisms(self.level, disk, lessons=_lessons(),
                                      reading=mine_map(path))
        self.inventory = self.result["inventory"]

    def test_the_reader_reproduces_the_supervisors_inventory(self):
        self.assertEqual(self.inventory["xsector"], 133)
        self.assertEqual(self.inventory["xwall"], 41)
        self.assertEqual(self.inventory["xsprite"], 716)
        self.assertEqual(self.inventory["sector_types"],
                         {600: 34, 614: 6, 615: 4, 616: 1, 617: 6, 618: 1})
        self.assertEqual(self.inventory["wall_types"], {511: 18})
        self.assertEqual(self.inventory["records_with_tx"]["sector"], 26)
        self.assertEqual(self.inventory["records_with_rx"]["sector"], 54)
        self.assertEqual(self.inventory["records_with_a_key"]["sector"], 4)
        self.assertEqual(self.inventory["sectors_with_a_light_wave"], 61)
        self.assertEqual(self.inventory["sectors_with_shade_always"], 45)

    def test_every_typed_sector_and_gib_wall_gets_a_sentence(self):
        """The experiment's demand: a sentence or a named residue, never
        silence."""
        sentences = {row["id"] for row in self.result["sentences"]}
        for index, sector in enumerate(self.level.sectors):
            if int(sector["fields"]["type"]):
                self.assertIn(f"sentence:sector:{index}", sentences)
        for index, wall in enumerate(self.level.walls):
            if int(wall["fields"]["type"]) == 511:
                self.assertIn(f"sentence:wall:{index}", sentences)

    def test_a_chain_is_one_sentence_and_it_carries_the_fan_out(self):
        """E3M1's collapsing house is one channel telling many records. Read
        receiver by receiver it would be a hundred mechanisms sharing a
        number; the chain is the mechanism."""
        chains = [row for row in self.result["sentences"]
                  if row["kind"] == "tx -> rx chain"]
        self.assertTrue(chains)
        biggest = max(chains, key=lambda row: row["receivers"])
        self.assertGreater(biggest["receivers"], 50)

    def test_every_sentence_was_checked_against_the_course(self):
        for row in self.result["sentences"]:
            self.assertTrue(row["against_the_course"]["consulted"],
                            f"{row['id']} was written without consulting the "
                            f"lessons of its kind")

    def test_some_of_e3m1_uses_a_combination_the_course_never_shows(self):
        """The finding, not a failure: the course teaches each slot alone and
        the campaign combines them."""
        off = [row for row in self.result["sentences"]
               if "but not this combination"
               in row["against_the_course"].get("verdict", "")]
        self.assertTrue(off)

    def test_all_three_stacks_carry_the_same_fault(self):
        """Three of three is a convention, not a mistake -- and the reader
        reports it as a fault, which is the queue item."""
        self.assertEqual(len(self.result["stacks"]), 3)
        for stack in self.result["stacks"]:
            self.assertTrue(stack["faults"])
            self.assertIn("floor marker floats", stack["faults"][0])

    def test_a_wired_record_no_sentence_reaches_is_named_residue(self):
        for row in self.result["residue"]:
            self.assertTrue(row["why"], f"{row['record']} is residue with no "
                                        f"reason given")


if __name__ == "__main__":
    unittest.main()
