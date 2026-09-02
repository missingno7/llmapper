"""One shared `(record, field) -> [claims]` ledger, and the stairs that fill it.

The ledger is where understanding is counted, and it is deliberately hard to
flatter: a claim means the layer's model REPRODUCES the field, two layers
claiming one exclusive field with different values is a conflict rather than
double credit, and a field the format owns is not claimable at all.
"""

from __future__ import annotations

import unittest


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [item for item in list_corpus_maps(population="blood-campaign")
             if item.path.stem.upper() == "E3M1"]
    if not found:
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return read_map(found[0].path).to_level_ir()


class TheLedger(unittest.TestCase):
    def setUp(self):
        from bloodmap.read_ledger import ClaimLedger

        self.ledger = ClaimLedger()
        self.ledger.counts = {"sector": 2, "wall": 4, "sprite": 0,
                              "xsector": 0, "xwall": 0, "xsprite": 0}

    def test_a_structural_field_cannot_be_claimed(self):
        """`wall_ptr` is a pointer into the wall array. No design layer could
        explain it, and leaving it claimable would put a floor under every
        score that means nothing."""
        with self.assertRaises(KeyError):
            self.ledger.claim("sector", 0, "wall_ptr", layer=1, owner="x",
                              value=0, why="")

    def test_two_layers_agreeing_is_corroboration_not_a_conflict(self):
        self.ledger.claim("wall", 0, "picnum", layer=2, owner="surface:1",
                          value=6, why="a frame")
        self.ledger.claim("wall", 0, "picnum", layer=3, owner="join:kerb",
                          value=6, why="the kerb row")
        self.assertEqual(self.ledger.conflicts(), [])
        self.assertEqual(self.ledger.corroborations(), 1)

    def test_two_layers_disagreeing_on_an_exclusive_field_is_a_conflict(self):
        self.ledger.claim("wall", 0, "picnum", layer=2, owner="surface:1",
                          value=6, why="a frame")
        self.ledger.claim("wall", 0, "picnum", layer=3, owner="join:kerb",
                          value=400, why="the table's class")
        conflicts = self.ledger.conflicts()
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["field"], "picnum")
        self.assertEqual(conflicts[0]["channel"], "frame")

    def test_shade_is_additive_so_two_sources_do_not_conflict(self):
        """`channels.py` made shade additive precisely so a lamp under a
        shadow resolves itself. The ledger has to honour that or the sun and
        a lamp would read as two owners fighting."""
        self.ledger.claim("sector", 0, "floor_shade", layer=4, owner="sun",
                          value=8, why="depth 0")
        self.ledger.claim("sector", 0, "floor_shade", layer=4, owner="lamp",
                          value=-4, why="a source")
        self.assertEqual(self.ledger.conflicts(), [])

    def test_a_record_is_understood_in_proportion_to_its_claimed_fields(self):
        self.ledger.claim("sector", 0, "floor_z", layer=4, owner="island",
                          value=8192, why="a rise")
        per = self.ledger.per_record("sector")
        self.assertEqual(per[0]["claimed"], ["floor_z"])
        self.assertGreater(len(per[0]["unclaimed"]), 10)
        self.assertLess(per[0]["percent"], 10.0)
        self.assertEqual(per[1]["claimed"], [])


class Stairs(unittest.TestCase):
    """Stairs are structures with parameters and a residual, not mechanisms."""

    def setUp(self):
        from bloodmap.read_stairs import read_stairs

        self.level = _e3m1()
        self.result = read_stairs(self.level)

    def test_the_helix_is_a_constant_rise_of_2048_over_24_rises(self):
        helix = self.result["runs"][0]
        self.assertEqual(len(helix["sectors"]), 25)
        self.assertEqual(helix["fit"]["rise"], 2048)
        self.assertTrue(helix["fit"]["constant_rise"])
        self.assertEqual(len(helix["fit"]["reproduces"]), 25)
        self.assertEqual(helix["fit"]["residual"], [])
        self.assertEqual(helix["parameters"]["rises"], 24)
        self.assertEqual(helix["parameters"]["total_rise"], 49152)

    def test_one_run_in_twelve_does_not_have_a_constant_rise(self):
        """The residual E2M3's stage 3 insisted on: a constructor must not
        pretend to reproduce it. Run 008 climbs 19 sectors and one of them
        (s347) does not land on the fitted progression."""
        self.assertEqual(len(self.result["runs"]), 12)
        self.assertEqual(self.result["runs_with_a_constant_rise"], 11)
        self.assertEqual(self.result["sectors_in_the_residual"], [347])

    def test_a_stair_is_not_a_mechanism(self):
        """The helix carries no sector type on any of its 25 sectors. Reading
        it as a mechanism would move 25 sectors into layer 5 that belong to
        the structures of layer 2."""
        helix = self.result["runs"][0]
        for index in helix["sectors"]:
            self.assertEqual(int(self.level.sectors[index]["fields"]["type"]), 0)


if __name__ == "__main__":
    unittest.main()
