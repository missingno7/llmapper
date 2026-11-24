"""The blast chain reader on Death Wish's and the campaign's own chains, and the engine's reach test."""

import unittest

from bloodmap import blasts, corpus
from bloodmap.format import read_map


class BlastTests(unittest.TestCase):
    def test_a_shaft_of_fifteen_two_tenths_apart(self):
        chain = next(c for c in blasts.chains(read_map(corpus.corpus_map_path("DWE3M5"))) if c.channel == 155)
        self.assertEqual((len(chain.blasts), chain.steps[1:4]), (15, (2, 4, 6)))
        self.assertAlmostEqual(chain.lasts, 2.7, places=2)
        self.assertLess(chain.rise, -11 * 16960)
        self.assertIn(20, {t for _i, t in chain.others})

    def test_reach_is_the_engines(self):
        self.assertTrue(blasts.hurts((0, 0, 0), (2300, 0, 0)))
        self.assertFalse(blasts.hurts((0, 0, 0), (2400, 0, 0)))
        self.assertFalse(blasts.hurts((0, 0, 0), (1900, 1900, 0)))           # approxDist: the longer and three eighths of the shorter
        self.assertTrue(blasts.hurts((0, 0, 0), (0, 0, 38000)))
        self.assertFalse(blasts.hurts((0, 0, 0), (0, 0, 38400)))
        self.assertTrue(blasts.harmless([(0, 0, 0)], [(0, 0, 50000), (5000, 0, 0)]))


if __name__ == "__main__":
    unittest.main()
