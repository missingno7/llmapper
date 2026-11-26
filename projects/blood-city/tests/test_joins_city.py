"""How the city's boundary meets the world: the join table read on Gravesend's plan."""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")


class TheBoundaryIsStatedPerSide(unittest.TestCase):
    def _plan(self):
        import sys

        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        try:
            import city_plan
        except ImportError as error:                   # pragma: no cover
            raise unittest.SkipTest(str(error))
        return city_plan

    def test_every_side_of_the_city_says_how_it_ends(self):
        from bloodmap.joins import EDGE_KINDS

        plan = self._plan()
        allowed = set(EDGE_KINDS) | {"building_back", "waterfront", "gate"}
        self.assertEqual(set(plan.BOUNDARY), {"north", "south", "east", "west"})
        for side, chain in plan.BOUNDARY.items():
            self.assertTrue(chain, side)
            for segment in chain:
                self.assertIn(segment["kind"], allowed, side)

    def test_the_south_side_is_the_waterfront(self):
        self.assertEqual([s["kind"] for s in self._plan().BOUNDARY["south"]],
                         ["waterfront"])

    def test_the_perimeter_lane_is_dropped_where_buildings_back_onto_it(self):
        # The one consequence the boundary has for the solve: nothing walks
        # behind a building, so no lane is built there.
        plan = self._plan()
        sides = plan.building_back_sides()
        self.assertIn("north", sides)
        self.assertIn("east", sides)
        self.assertIn("west", sides)
        self.assertNotIn("south", sides, "the quay is walkable")


if __name__ == "__main__":
    unittest.main()
