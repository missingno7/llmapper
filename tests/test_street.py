"""Street anatomy, against the campaign street it was measured from.

E3M1 is Blood's own city street. Every number in `bloodmap.street` comes out
of it, so these tests re-measure the map rather than restating the constant --
a test that asserts `KERB_RISE == 2048` proves only that someone typed 2048
twice.
"""

import collections
import unittest
from pathlib import Path

E3M1 = Path("maps/blood/campaign/E3M1.MAP")


def _e3m1():
    from bloodmap.format import read_map

    if not E3M1.exists():
        raise unittest.SkipTest("E3M1 is not present")
    return read_map(E3M1)


class TheSplitIsMeasuredFromE3M1(unittest.TestCase):
    """Tile 4 over tile 352, and the step between them."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _e3m1()

    def _shared(self):
        from bloodmap import motion

        owners = motion.wall_owners(self.disk)
        out = []
        for wall_id, wall in enumerate(self.disk.walls):
            other = int(wall.fields["next_sector"])
            if other < 0:
                continue
            a = self.disk.sectors[owners[wall_id]].fields
            b = self.disk.sectors[other].fields
            tiles = {int(a["floor_picnum"]), int(b["floor_picnum"])}
            if tiles == {4, 352}:
                high = a if int(a["floor_picnum"]) == 4 else b
                low = b if int(a["floor_picnum"]) == 4 else a
                out.append((int(low["floor_z"]) - int(high["floor_z"])))
        return out

    def test_the_two_tiles_meet_and_the_step_never_varies(self):
        from bloodmap.street import KERB_RISE, ROADWAY_TILE, SIDEWALK_TILE

        steps = self._shared()
        self.assertEqual(len(steps), 22, "the measured population")
        self.assertEqual(set(steps), {KERB_RISE},
                         "every shared wall gives the same step")
        self.assertEqual((SIDEWALK_TILE, ROADWAY_TILE), (4, 352))

    def test_the_sidewalk_is_the_higher_of_the_two(self):
        # Build z grows downward, so a positive step means the roadway sits
        # BELOW the pavement. Getting this backwards would put a step down
        # into every shop door in the city.
        self.assertTrue(all(step > 0 for step in self._shared()))

    def test_the_step_is_climbable(self):
        # Blood lets a body up 4096. A kerb you cannot step onto is a wall.
        from bloodmap.street import KERB_RISE

        self.assertLess(KERB_RISE, 4096)

    def test_the_sidewalk_band_is_the_modal_narrow_dimension(self):
        from bloodmap import motion
        from bloodmap.street import SIDEWALK

        owners = motion.wall_owners(self.disk)
        touching = set()
        for wall_id, wall in enumerate(self.disk.walls):
            other = int(wall.fields["next_sector"])
            if other < 0:
                continue
            mine = owners[wall_id]
            tiles = (int(self.disk.sectors[mine].fields["floor_picnum"]),
                     int(self.disk.sectors[other].fields["floor_picnum"]))
            if set(tiles) == {4, 352}:
                touching.add(mine if tiles[0] == 4 else other)
        widths = []
        for sector_id in touching:
            walls = list(motion.sector_walls(self.disk, sector_id))
            xs = [int(self.disk.walls[w].fields["x"]) for w in walls]
            ys = [int(self.disk.walls[w].fields["y"]) for w in walls]
            widths.append(min(max(xs) - min(xs), max(ys) - min(ys)))
        modal, count = collections.Counter(widths).most_common(1)[0]
        self.assertEqual(modal, SIDEWALK)
        self.assertGreaterEqual(count, len(widths) // 2)


class ARunGetsAnAnatomy(unittest.TestCase):
    """The constructor, on runs of each width class."""

    def _run(self, width, length=16384, horizontal=True):
        from bloodmap.street import Run

        end = (length, 0) if horizontal else (0, length)
        return Run(name="probe", a=(0, 0), b=end, width=width)

    def test_a_lane_is_pedestrian_end_to_end(self):
        # 3072 with a pavement each side leaves 1024 of road, which is not a
        # road. The campaign's lanes are pedestrian too.
        from bloodmap.street import carriageway

        self.assertIsNone(carriageway(self._run(3072)))

    def test_a_street_row_and_avenue_all_get_a_carriageway(self):
        from bloodmap.street import carriageway

        for width in (5120, 6144, 7168):
            self.assertIsNotNone(carriageway(self._run(width)), width)

    def test_the_carriageway_is_centred_and_leaves_two_pavements(self):
        from bloodmap.street import carriageway, sidewalk_for

        for width in (5120, 6144, 7168):
            run = self._run(width)
            x0, y0, x1, y1 = carriageway(run)
            band = sidewalk_for(width)
            self.assertEqual(y1 - y0, width - 2 * band, width)
            #: centred on the run's own centreline
            self.assertEqual((y0 + y1) // 2, 0, width)
            self.assertEqual((x0, x1), (0, 16384))

    def test_a_vertical_run_works_the_same_way(self):
        from bloodmap.street import carriageway, sidewalk_for

        run = self._run(7168, horizontal=False)
        x0, y0, x1, y1 = carriageway(run)
        self.assertEqual(x1 - x0, 7168 - 2 * sidewalk_for(7168))
        self.assertEqual((y0, y1), (0, 16384))

    def test_a_width_of_nothing_is_refused(self):
        from bloodmap.street import StreetError, carriageway

        with self.assertRaises(StreetError):
            carriageway(self._run(0))

    def test_the_kerb_declares_itself_as_a_junction(self):
        from bloodmap.street import KERB_RISE, kerb_junction

        kerb = kerb_junction(self._run(6144))
        self.assertEqual(kerb["role"], "junction")
        self.assertEqual(kerb["rise"], KERB_RISE)


class SlotsAreDerivedFromLength(unittest.TestCase):
    """The prefab-slot idea: how many is a function of how long."""

    def _run(self, length, width=6144):
        from bloodmap.street import Run

        return Run(name="probe", a=(0, 0), b=(length, 0), width=width)

    def test_a_longer_run_gets_more_lamps(self):
        from bloodmap.street import lamp_slots

        short = len(lamp_slots(self._run(9 * 1024)))
        long = len(lamp_slots(self._run(36 * 1024)))
        self.assertGreater(long, short)

    def test_every_run_gets_at_least_one_pair(self):
        from bloodmap.street import lamp_slots

        slots = lamp_slots(self._run(2048))
        self.assertEqual(len(slots), 2)
        self.assertEqual({s.side for s in slots}, {"low", "high"})

    def test_a_lamp_stands_on_the_pavement_not_over_the_drop(self):
        # Inset from the kerb by half a band, so no lamp overhangs the road.
        from bloodmap.street import carriageway, lamp_slots

        run = self._run(36 * 1024, width=7168)
        _x0, y0, _x1, y1 = carriageway(run)
        for slot in lamp_slots(run):
            self.assertFalse(y0 < slot.y < y1,
                             f"{slot.slot_id} stands in the roadway")
            self.assertLessEqual(abs(slot.y), run.width // 2)

    def test_the_ends_stay_clear(self):
        # Spaced from the middle outwards: a junction or a doorway at the end
        # of a run does not find a lamp in it.
        from bloodmap.street import lamp_slots

        run = self._run(36 * 1024)
        xs = [slot.x for slot in lamp_slots(run)]
        self.assertGreater(min(xs), 0)
        self.assertLess(max(xs), run.length)


class ThePorchRuleIsAThreshold(unittest.TestCase):
    def test_a_tall_facade_wants_a_porch_and_a_shopfront_does_not(self):
        from bloodmap.street import wants_porch

        self.assertTrue(wants_porch(4 * 16960))
        self.assertFalse(wants_porch(2 * 16960))

    def test_only_the_tall_doors_get_slots(self):
        from bloodmap.street import porch_slots

        doors = [{"id": "a", "x": 0, "y": 0, "facade_height": 5 * 16960},
                 {"id": "b", "x": 100, "y": 0, "facade_height": 16960}]
        slots = porch_slots([], doors)
        self.assertEqual([slot.slot_id for slot in slots], ["a:porch"])


class ThePlanBecomesRuns(unittest.TestCase):
    """The city's own circulation graph, read into runs."""

    def _runs(self):
        import sys

        sys.path.insert(0, "projects/blood-city/level")
        try:
            import city_plan
            import resolution
        except Exception:                              # pragma: no cover
            raise unittest.SkipTest("blood-city plan is not importable")
        from bloodmap.street import runs_from_plan

        return runs_from_plan(city_plan.NODES, city_plan.EDGES,
                              resolution.WIDTH_UNITS, unit=1024)

    def test_every_edge_becomes_a_run(self):
        self.assertEqual(len(self._runs()), 18)

    def test_the_lanes_are_the_ones_left_pedestrian(self):
        from bloodmap.street import carriageway

        runs = self._runs()
        pedestrian = [run for run in runs if carriageway(run) is None]
        self.assertEqual(len(pedestrian), 5)
        self.assertTrue(all(run.width == 3072 for run in pedestrian))

    def test_an_unknown_node_is_refused(self):
        from bloodmap.street import StreetError, runs_from_plan

        with self.assertRaises(StreetError):
            runs_from_plan({"a": (0, 0)},
                           [("a", "nowhere", "row", "d", "x")],
                           {"row": 6144})


if __name__ == "__main__":
    unittest.main()
