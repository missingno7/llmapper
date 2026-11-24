"""A counter that hears four keyed switches opens with the fourth key and not before: DWE1M9's, which the station's lock is made of."""

import unittest

from bloodmap import corpus
from bloodmap.format import read_map


class CountedKeysTests(unittest.TestCase):
    def test_the_carnivals_four_locks_want_four_keys(self):
        disk = read_map(corpus.corpus_map_path("DWE1M9"))
        from bloodmap.conditional import Held, build_graph
        graph = build_graph(disk)
        everywhere = set(range(len(disk.sectors)))
        sectors = {int(disk.sprites[i].fields["sector"]) for i in (1399, 1401, 1403, 1405)}
        self.assertTrue(sectors <= everywhere)
        self.assertFalse(graph.counted(119, everywhere, Held(keys=frozenset({2, 3, 4}))))
        self.assertTrue(graph.counted(119, everywhere, Held(keys=frozenset({2, 3, 4, 5}))))
        self.assertTrue(graph.counted(118, everywhere, Held()))              # nothing counts here


if __name__ == "__main__":
    unittest.main()
