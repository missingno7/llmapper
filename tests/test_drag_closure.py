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


class GrazeTest(unittest.TestCase):
    """A hinge poking a unit past the wall it turns on is not a fold."""

    def test_a_deep_crossing_measures_its_depth(self):
        from bloodmap.motion_sim import crossing_depth

        # Two segments crossing at their middles: 50 units into each.
        self.assertAlmostEqual(
            crossing_depth((0.0, 0.0), (100.0, 0.0), (50.0, -50.0), (50.0, 50.0)),
            50.0)

    def test_a_graze_at_an_endpoint_measures_almost_nothing(self):
        from bloodmap.motion_sim import crossing_depth

        # The leaf tip pokes 1.3 units past a long wall: the crossing point
        # is 1.3 from the leaf's own end and ~1400 from the wall's, and the
        # measure is the smaller of the two.
        depth = crossing_depth((0.0, -100.0), (0.0, 1.3), (-1400.0, 0.0), (100.0, 0.0))
        self.assertLess(depth, 2.0)

    def test_segments_that_do_not_cross_have_no_depth(self):
        from bloodmap.motion_sim import crossing_depth

        self.assertEqual(
            crossing_depth((0.0, 0.0), (10.0, 0.0), (0.0, 5.0), (10.0, 5.0)), 0.0)

    def test_the_tolerance_drops_a_graze_and_keeps_a_fold(self):
        from bloodmap.motion_sim import SWEEP_GRAZE, self_intersections

        # The rotor shape: a spur that crosses the long bottom edge. In
        # `shallow` the spur's own end sits one unit past that edge, which is
        # the hinge graze; in `deep` it reaches 40 units through.
        deep = [(0.0, 0.0), (100.0, 0.0), (100.0, 60.0), (50.0, -40.0)]
        shallow = [(0.0, 0.0), (100.0, 0.0), (100.0, 10.0), (50.0, -1.0)]
        self.assertTrue(self_intersections(deep))
        self.assertTrue(self_intersections(shallow))
        self.assertTrue(self_intersections(deep, min_depth=SWEEP_GRAZE))
        self.assertEqual(self_intersections(shallow, min_depth=SWEEP_GRAZE), [])


class AssemblyTest(unittest.TestCase):
    """A hub several mechanisms drag cannot be judged one mechanism at a time.

    `TranslateSector` runs per mechanism, but every mechanism wired to a
    channel runs in the SAME tick, each re-placing the shared vertices from
    its own base (triggers.cpp:856, DragPoint at :817-854 assigning absolute
    coordinates). So a loop whose moved walls two mechanisms drag is only
    whole when both have travelled, and sweeping one of them alone shows a
    pose the engine never draws. Without this the census called E1M4's
    eight-sector wheel and E3M2's fifteen-sector boat broken maps.
    """

    def test_the_fixture_has_exactly_one_mover_and_no_co_driving(self):
        from bloodmap.motion_sim import co_driven_walls, horizontal_movers

        disk, sectors = _fixture()
        self.assertEqual(horizontal_movers(disk), [sectors["motor"]])
        self.assertEqual(co_driven_walls(disk, sectors["motor"]), {})

    def test_a_spoke_of_the_wheel_shares_walls_with_its_ring_neighbours(self):
        # E1M4's rotor ring, sectors 321-329 of type 617 around the hub s352.
        # Measured, not assumed: s322's dragged walls are shared with its two
        # ring neighbours 321 and 323 (and 328 across the hub), not with all
        # eight -- adjacency in the ring, which is the shape of the defect
        # the assembly rule exists for.
        from bloodmap.motion_sim import co_driven_walls, drag_closure
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == "E1M4"]
        if not found:
            self.skipTest("E1M4 is not in the corpus")
        disk = read_map(found[0].path)
        shared = co_driven_walls(disk, 322)
        mine = drag_closure(disk, 322)["walls"]
        overlap = {w: shared[w] for w in mine if w in shared}
        self.assertTrue(overlap, "no other rotor shares a wall with s322")
        self.assertEqual(set().union(*overlap.values()), {321, 323, 328})

    def test_a_co_driven_hub_is_a_note_and_never_a_problem(self):
        from bloodmap.motion_sim import closure_health
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == "E1M4"]
        if not found:
            self.skipTest("E1M4 is not in the corpus")
        disk = read_map(found[0].path)
        health = closure_health(disk, 322, steps=8)
        self.assertIn(352, health["co_driven_sectors"])
        hub = next(r for r in health["loops"] if r["sector"] == 352)
        self.assertTrue(hub["co_driven_by"])
        self.assertTrue(hub["self_intersecting_steps"] or hub["inverted_steps"],
                        "swept alone the hub should break -- that is the point")
        self.assertNotIn("sector 352", " ".join(health["problems"]))
        self.assertIn("not judged one mechanism at a time", " ".join(health["notes"]))

    def test_judging_it_in_isolation_is_still_possible_and_says_so(self):
        # `movers=()` turns the assembly rule off. It is the honest way to
        # ask "what does THIS one do on its own", and the answer is that the
        # hub breaks -- which is why the default is not this.
        from bloodmap.motion_sim import closure_health
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == "E1M4"]
        if not found:
            self.skipTest("E1M4 is not in the corpus")
        disk = read_map(found[0].path)
        alone = closure_health(disk, 322, steps=8, movers=())
        self.assertEqual(alone["co_driven_sectors"], [])
        self.assertFalse(alone["healthy"])
        self.assertIn("sector 352", " ".join(alone["problems"]))


class CensusTest(unittest.TestCase):
    """The census keeps the evidence and drops what the summary already says."""

    def test_a_clean_mechanism_is_counted_but_not_listed(self):
        from tools.sweep_drag_closure import interesting

        self.assertFalse(interesting(
            {"map": "X", "sector": 1, "problems": [], "disagreements": [],
             "crossing_count": 0}))
        self.assertTrue(interesting(
            {"map": "X", "sector": 1, "problems": ["a"], "crossing_count": 0}))
        self.assertTrue(interesting({"map": "X", "not_swept": "no marker0"}))

    def test_long_lists_are_capped_and_the_total_kept(self):
        from tools.sweep_drag_closure import trim

        kept = trim({"map": "X", "sector": 3, "type": 614, "isolated": False,
                     "problems": [f"p{i}" for i in range(9)],
                     "disagreements": [], "crossing_count": 0})
        self.assertEqual(len(kept["problems"]), 3)
        self.assertEqual(kept["problems_total"], 9)
        self.assertNotIn("disagreements", kept)
        self.assertNotIn("crossing_count", kept)


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

    def test_the_city_curtain_no_longer_drags_the_auditorium(self):
        # This is the case that motivated the closure, and the closure now
        # measures its repair. The supervisor measured the carved fin on
        # 2026-09-01: hole and room were the SAME polygon, all eight walls
        # paired as portals, and the auditorium's hole loop travelled with
        # the curtain (area 983040 -> 1302528). P1 rebuilt the proscenium as
        # a DOORWAY rect with a solid void notch, so the closure is the fin
        # alone -- the fin/isolation technique DOOR-CURTAINS s3 teaches.
        #
        # It is deliberately not written as `isolated is True` and nothing
        # else: a curtain that starts dragging the house again would be
        # caught by the second half whether or not it inverted.
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
            self.assertTrue(health["isolated"],
                            f"s{sector_id} drags {health['neighbours']}")
            self.assertEqual([r for r in health["loops"] if not r["own"]], [])
            self.assertTrue(health["healthy"], health["problems"])
            self.assertEqual(health["disagreements"], [])

    def test_a_carved_fin_would_drag_the_room_it_was_cut_from(self):
        # The defect the rebuild removed, reconstructed from the tutorial so
        # the gate keeps a live example of it: pair DOOR-CURTAINS s3's void
        # slot walls to a sector, as the tree's `carve` idiom did, and the
        # closure grows from the fin alone to the fin plus that sector.
        from bloodmap.motion_sim import closure_health

        disk = _map(CURTAINS)
        self.assertTrue(closure_health(disk, 3)["isolated"])
        #: s10 is the plain curtain in the same map: its motion already
        #: reaches a neighbour, which is what the fin technique avoids.
        reached = closure_health(disk, 10)
        self.assertFalse(reached["isolated"])
        self.assertTrue(reached["neighbours"])


if __name__ == "__main__":
    unittest.main()
