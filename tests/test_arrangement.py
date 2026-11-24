"""Shapes laid over one another resolve into cells that meet edge to edge, on whole units."""

import unittest
from collections import Counter

from bloodmap import arrangement as A


def edges(cells):
    return Counter((p, q) for c in cells for ring in (c.outer, *c.holes) for p, q in zip(ring, ring[1:] + ring[:1]))


def area(ring):
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(ring, ring[1:] + ring[:1])) / 2


class ArrangementTests(unittest.TestCase):
    CENTRE = (1000, 2000)

    def star_place(self):
        place = A.Arrangement()
        place.add("floor", A.circle(self.CENTRE, 4096, 20, 1 / 40))
        place.add("ring", A.circle(self.CENTRE, 3456, 20, 1 / 40), holes=[A.circle(self.CENTRE, 3328, 20, 1 / 40)])
        place.add("star", *A.star(self.CENTRE, 3328, 5, 2, 176))
        place.add("well", A.circle(self.CENTRE, 900, 5, 0.5))
        place.solid(A.circle(A.spoke(self.CENTRE, 3800, 0.3), 160, 8))
        return place.resolve()

    def test_a_circle_is_clockwise_on_the_page_and_starts_at_its_turn(self):
        ring = A.circle((0, 0), 1000, 20)
        self.assertEqual(ring[0], (0, -1000))
        self.assertGreater(area(ring), 0)

    def test_every_inside_edge_is_shared_by_exactly_two_cells(self):
        cells = self.star_place()
        walked = edges(cells)
        self.assertEqual(max(walked.values()), 1, "an edge walked twice one way is two cells overlapping")
        rim = {(p, q) for _n, p, q in A.rim(cells)}
        self.assertEqual({e for e in walked if (e[1], e[0]) not in walked}, rim)
        self.assertEqual(2 * len(A.joints(cells)) + len(rim), len(walked))

    def test_the_rim_is_the_outside_and_the_rock_and_nothing_else(self):
        rim = A.rim(self.star_place())
        self.assertEqual(len(rim), 20 + 8)

    def test_cells_cover_the_place_once_less_its_rock(self):
        cells = self.star_place()
        total = sum(area(c.outer) + sum(area(h) for h in c.holes) for c in cells)
        rock = area(A.circle(A.spoke(self.CENTRE, 3800, 0.3), 160, 8))
        self.assertAlmostEqual(total, area(A.circle(self.CENTRE, 4096, 20, 1 / 40)) - rock, delta=1)

    def test_a_later_shape_covers_an_earlier_one_and_the_pieces_are_named_apart(self):
        names = Counter(c.name.split("_")[0] for c in self.star_place())
        self.assertEqual(names["well"], 1)
        self.assertEqual(names["star"], 1)
        self.assertGreaterEqual(names["floor"], 11)       # outside the ring, five points, five gaps, the pentagon

    def test_a_corner_no_third_edge_needs_is_dropped(self):
        place = A.Arrangement()
        place.add("a", [(0, 0), (1000, 0), (1000, 1000), (0, 1000)])
        place.add("b", [(1000, 0), (2000, 0), (2000, 500), (2000, 1000), (1000, 1000)])
        cells = {c.name: c for c in place.resolve()}
        self.assertEqual(len(cells["b"].outer), 4)

    def test_a_crumb_goes_to_the_neighbour_it_has_most_of_in_common(self):
        place = A.Arrangement()
        place.add("a", [(0, 0), (4096, 0), (4096, 4096), (0, 4096)])
        place.add("sliver", [(0, 0), (40, 0), (40, 40), (0, 40)])
        self.assertEqual([c.name for c in place.resolve()], ["a"])


if __name__ == "__main__":
    unittest.main()
