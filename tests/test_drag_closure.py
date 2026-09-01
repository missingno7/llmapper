"""The DragPoint closure: what a motion moves besides the mover's own polygon.

`TranslateSector` (triggers.cpp:856) never moves a polygon. It calls
`DragPoint` per vertex, and `DragPoint` (triggers.cpp:817-854) sets that
vertex for every wall that shares it, found by walking `nextwall` -- not by
looking for equal coordinates. These tests pin the transcription to a
fixture whose answer is known by construction, then to the originals.
"""

import unittest
from pathlib import Path

ORACLE = Path("maps/blood/mechanism/casket.map")
CURTAINS = Path("maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map")
CITY = Path("projects/blood-city/level/blood-city-current.MAP")


def _fixture():
    from tests.test_swept_state import _strip_with_thin_neighbour

    return _strip_with_thin_neighbour()


def _map(path: Path):
    from bloodmap.format import read_map

    if not path.exists():
        raise unittest.SkipTest(f"{path} is not present")
    return read_map(path)


def _vertex(disk, wall_id):
    fields = disk.walls[wall_id].fields
    return int(fields["x"]), int(fields["y"])


class LoopsAndLastWallTest(unittest.TestCase):
    def test_every_wall_of_a_sector_is_in_exactly_one_loop(self):
        from bloodmap.motion_sim import sector_loops

        disk, sectors = _fixture()
        for sector_id in sectors.values():
            fields = disk.sectors[sector_id].fields
            start = int(fields["wall_ptr"])
            expected = set(range(start, start + int(fields["wall_count"])))
            loops = sector_loops(disk, sector_id)
            self.assertEqual(len(loops), 1)
            self.assertEqual(set(loops[0]), expected)

    def test_last_wall_is_the_inverse_of_point2(self):
        # engine.cpp:13227: the wall whose point2 is the argument.
        from bloodmap.motion_sim import last_wall

        disk, _ = _fixture()
        for wall_id, wall in enumerate(disk.walls):
            following = int(wall.fields["point2"])
            self.assertEqual(last_wall(disk, following), wall_id)


class DragChainTest(unittest.TestCase):
    def test_the_chain_is_the_fan_of_walls_around_the_vertex(self):
        # The motor's flagged wall starts at a corner shared by the motor and
        # the thin neighbour (the room does not reach it), so DragPoint sets
        # two walls -- one per sector -- and they sit on one point.
        from bloodmap.motion_sim import drag_chain, drag_drivers, wall_owners

        disk, sectors = _fixture()
        owners = wall_owners(disk)
        drivers = drag_drivers(disk, sectors["motor"])
        self.assertEqual([why for _, _, why in drivers][0], "cstat 16384")
        self.assertTrue(drivers[1][2].startswith("point2 of"))
        for wall_id, sign, _ in drivers:
            chain = drag_chain(disk, wall_id)
            self.assertEqual(chain[0], wall_id)
            self.assertEqual(sorted(owners[w] for w in chain),
                             sorted([sectors["motor"], sectors["thin"]]))
            self.assertEqual({_vertex(disk, w) for w in chain},
                             {_vertex(disk, wall_id)})

    def test_a_one_sided_wall_stops_the_walk_but_the_other_way_is_still_taken(self):
        # A corner of the motor that touches nothing: the chain is the wall
        # alone, whichever direction the walk tries first.
        from bloodmap.motion_sim import drag_chain

        disk, sectors = _fixture()
        start = int(disk.sectors[sectors["motor"]].fields["wall_ptr"])
        count = int(disk.sectors[sectors["motor"]].fields["wall_count"])
        lonely = [w for w in range(start, start + count)
                  if _vertex(disk, w)[1] == 0]
        self.assertEqual(len(lonely), 2)
        for wall_id in lonely:
            self.assertEqual(drag_chain(disk, wall_id), [wall_id])


class DragClosureTest(unittest.TestCase):
    def test_the_closure_names_the_neighbour_and_its_loop(self):
        from bloodmap.motion_sim import drag_closure

        disk, sectors = _fixture()
        closure = drag_closure(disk, sectors["motor"])
        self.assertEqual(closure["sectors"],
                         sorted([sectors["motor"], sectors["thin"]]))
        self.assertEqual(closure["coincidence_sectors"], closure["sectors"])
        self.assertEqual(sorted(closure["loops"]),
                         sorted([(sectors["motor"], 0), (sectors["thin"], 0)]))
        self.assertEqual(closure["disagreements"], [])
        self.assertEqual(len(closure["walls"]), 4)

    def test_an_unwelded_vertex_is_a_disagreement_not_a_member(self):
        # Break the pairing: the portal between motor and thin becomes two
        # one-sided walls on the same points. Coordinates still say the thin
        # sector shares the vertex; nextwall says nothing does. The engine
        # follows nextwall, so the thin sector is NOT in the closure -- and
        # the map is defective at exactly that point.
        from bloodmap.motion_sim import drag_closure

        disk, sectors = _fixture()
        start = int(disk.sectors[sectors["motor"]].fields["wall_ptr"])
        count = int(disk.sectors[sectors["motor"]].fields["wall_count"])
        for wall_id in range(start, start + count):
            other = int(disk.walls[wall_id].fields["next_wall"])
            if other >= 0:
                disk.walls[other].fields["next_wall"] = -1
                disk.walls[other].fields["next_sector"] = -1
                disk.walls[wall_id].fields["next_wall"] = -1
                disk.walls[wall_id].fields["next_sector"] = -1
        closure = drag_closure(disk, sectors["motor"])
        self.assertEqual(closure["sectors"], [sectors["motor"]])
        self.assertEqual(closure["coincidence_sectors"],
                         sorted([sectors["motor"], sectors["thin"]]))
        kinds = {d["kind"] for d in closure["disagreements"]}
        self.assertEqual(kinds, {"coincident but not chained"})
        self.assertEqual(
            {s for d in closure["disagreements"] for s in d["sectors"]},
            {sectors["thin"]})


class ClosureSweepTest(unittest.TestCase):
    def test_by_loop_frames_agree_with_the_mover_only_frames(self):
        from bloodmap.motion_sim import blood_sweep

        disk, sectors = _fixture()
        own = blood_sweep(disk, sectors["motor"], steps=4)
        by_loop = blood_sweep(disk, sectors["motor"], steps=4, by_loop=True)
        self.assertIn((sectors["motor"], 0), by_loop)
        self.assertIn((sectors["thin"], 0), by_loop)
        for mine, theirs in zip(own, by_loop[(sectors["motor"], 0)]):
            self.assertEqual(sorted(mine), sorted(theirs))

    def test_the_neighbour_follows_the_dragged_vertex_exactly(self):
        # `DragPoint` assigns absolute coordinates, so at every step the
        # thin sector's near corners ARE the motor's boundary corners.
        from bloodmap.motion_sim import closure_sweep

        disk, sectors = _fixture()
        swept = closure_sweep(disk, sectors["motor"], steps=4)
        for step in range(5):
            for wall_id, item in swept.closure["moved"].items():
                self.assertEqual(swept.position(step, wall_id),
                                 swept.position(step, item["driver"]))

    def test_sweep_health_evaluates_every_loop(self):
        from bloodmap.motion_sim import blood_sweep, sweep_health

        disk, sectors = _fixture()
        frames = blood_sweep(disk, sectors["motor"], steps=4, by_loop=True)
        report = sweep_health(frames)
        self.assertFalse(report["healthy"])
        by_key = {(row["sector"], row["loop"]): row for row in report["loops"]}
        self.assertTrue(by_key[(sectors["motor"], 0)]["healthy"])
        self.assertFalse(by_key[(sectors["thin"], 0)]["healthy"])

    def test_closure_health_reports_the_inversion_against_the_drawn_winding(self):
        # The neighbour is inside out at busy 0 -- the pose the level LOADS
        # in -- and correct at busy 1, the drawn pose. A comparison against
        # the first frame would call the drawn pose the inverted one.
        from bloodmap.motion_sim import closure_health

        disk, sectors = _fixture()
        health = closure_health(disk, sectors["motor"], steps=4)
        thin = next(r for r in health["loops"] if r["sector"] == sectors["thin"])
        self.assertEqual(thin["inverted_steps"], [0, 1])
        self.assertGreater(thin["area_drawn"], 0)
        self.assertLess(thin["areas"][0], 0)
        self.assertFalse(health["healthy"])
        self.assertEqual(health["crossings"], [])


class OriginalsTest(unittest.TestCase):
    """The closure on maps whose motion sets are known."""

    def test_the_oracle_deforms_its_hole_and_nothing_else(self):
        from bloodmap.motion_sim import closure_health

        disk = _map(ORACLE)
        for sector_id, expected in ((2, [1, 2, 3]), (5, [4, 5, 6])):
            health = closure_health(disk, sector_id)
            self.assertEqual(health["sectors"], expected)
            self.assertEqual(health["coincidence_sectors"], expected)
            self.assertTrue(health["healthy"], health["problems"])
            self.assertEqual(health["disagreements"], [])

    def test_the_fin_is_isolated_and_the_plain_curtain_is_not(self):
        # The curriculum's own contrast (the-fin-is-an-isolation-technique):
        # DOOR-CURTAINS s3 keeps its motion to itself, s10 reaches a
        # neighbour. Same map, same author, deliberate.
        from bloodmap.motion_sim import closure_health

        disk = _map(CURTAINS)
        self.assertTrue(closure_health(disk, 3)["isolated"])
        self.assertFalse(closure_health(disk, 10)["isolated"])

    def test_the_city_curtain_drags_the_auditorium_hole_without_inverting_it(self):
        # The live example the supervisor measured: the curtain's tip
        # vertices belong to the auditorium's hole loop too, which grows
        # over the travel and never winds the other way.
        from bloodmap.motion_sim import closure_health

        disk = _map(CITY)
        curtains = []
        for sector_id, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) != 614 or sector.extra is None:
                continue
            start = int(sector.fields["wall_ptr"])
            count = int(sector.fields["wall_count"])
            if any(int(disk.walls[w].fields["picnum"]) == 146
                   for w in range(start, start + count)):
                curtains.append(sector_id)
        if not curtains:
            self.skipTest("the city has no curtain wearing tile 146")
        for sector_id in curtains:
            health = closure_health(disk, sector_id)
            neighbours = [r for r in health["loops"] if not r["own"]]
            self.assertTrue(neighbours, f"s{sector_id} drags no neighbour loop")
            for row in neighbours:
                self.assertEqual(row["inverted_steps"], [])
                self.assertNotEqual(row["areas"][0], row["areas"][-1])
            self.assertTrue(health["healthy"], health["problems"])


if __name__ == "__main__":
    unittest.main()
