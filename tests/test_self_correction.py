"""The self-correction machinery: conformance, contradictions, and links.

Phase 11's owner-steered half. What these protect is that the machinery
CATCHES things -- a check that has never failed proves nothing, so the
conformance tests here deliberately construct the deviation and assert it is
found, rather than only asserting that a good build passes.
"""

import unittest


def _campaign(stem):
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [entry for entry in list_corpus_maps(population="blood-campaign")
             if entry.path.stem.upper().startswith(stem)]
    if not found:
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(found[0].path)


class TurnstileConformanceTest(unittest.TestCase):
    """The check that caught the square blades."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M4")

    def test_the_campaigns_own_rotors_conform(self):
        # Calibration: the template has to accept the maps it came from, or
        # it is measuring something else.
        from bloodmap.conformance import measure_turnstile

        for sector_id in (151, 314):
            self.assertTrue(measure_turnstile(self.disk, sector_id).conforms)

    def test_blades_in_a_square_are_caught(self):
        # The regression the owner found by walking. Four blades whose own
        # angle equals their bearing from the axis form a square: the same
        # four positions, every vane turned to face outward instead of
        # across. Rotating positions without rotating angles does exactly
        # this, and nothing else in the project noticed.
        from bloodmap.conformance import measure_turnstile

        disk = _campaign("E1M4")
        axis = None
        for sprite in disk.sprites:
            fields = sprite.fields
            if (int(fields["sector"]) == 151 and int(fields["status"]) == 10
                    and int(fields["type"]) == 5):
                axis = (int(fields["x"]), int(fields["y"]))
        self.assertIsNotNone(axis)
        from math import atan2, degrees

        for sprite in disk.sprites:
            fields = sprite.fields
            if int(fields["sector"]) != 151 or int(fields["picnum"]) != 332:
                continue
            bearing = degrees(atan2(int(fields["y"]) - axis[1],
                                    int(fields["x"]) - axis[0])) % 360.0
            fields["angle"] = int(round(bearing * 2048 / 360.0)) % 2048
        found = measure_turnstile(disk, 151)
        self.assertFalse(found.conforms)
        self.assertIn("vane orientation",
                      " ".join(str(d) for d in found.deviations))

    def test_blades_stacked_on_the_axis_are_caught(self):
        from bloodmap.conformance import measure_turnstile

        disk = _campaign("E1M4")
        axis = next((int(s.fields["x"]), int(s.fields["y"]))
                    for s in disk.sprites
                    if int(s.fields["sector"]) == 151
                    and int(s.fields["status"]) == 10
                    and int(s.fields["type"]) == 5)
        for sprite in disk.sprites:
            if (int(sprite.fields["sector"]) == 151
                    and int(sprite.fields["picnum"]) == 332):
                sprite.fields["x"], sprite.fields["y"] = axis
        found = measure_turnstile(disk, 151)
        self.assertFalse(found.conforms)
        self.assertIn("radial stand-off",
                      " ".join(str(d) for d in found.deviations))

    def test_a_blade_that_does_not_span_its_rotor_is_caught(self):
        from bloodmap.conformance import measure_turnstile

        disk = _campaign("E1M4")
        for sprite in disk.sprites:
            if (int(sprite.fields["sector"]) == 151
                    and int(sprite.fields["picnum"]) == 332):
                sprite.fields["y_repeat"] = 32
        found = measure_turnstile(disk, 151)
        self.assertFalse(found.conforms)
        self.assertIn("span", " ".join(str(d) for d in found.deviations))


class SpritePayloadConformanceTest(unittest.TestCase):
    def test_a_leaf_edge_on_to_its_travel_is_caught(self):
        # The same root cause one construct along: four sliding gates whose
        # leaves faced along the slide instead of across it.
        from bloodmap.conformance import measure_sprite_payload

        disk = _campaign("E1M1")
        self.assertTrue(measure_sprite_payload(disk, 65).conforms)
        for index in (37, 38):
            disk.sprites[index].fields["angle"] = 1792 - 512
        found = measure_sprite_payload(disk, 65)
        self.assertFalse(found.conforms)


class WallSpriteConformanceTest(unittest.TestCase):
    def test_the_campaign_is_overwhelmingly_perpendicular(self):
        # Calibration for the general oddity-catcher: 97.6% over 1495 wall
        # sprites in twelve maps.
        from bloodmap.conformance import measure_wall_sprites

        disk = _campaign("E1M1")
        found = measure_wall_sprites(disk)
        total = found.measured["wall_sprites"]
        if total < 20:
            self.skipTest("too few wall sprites to calibrate on")
        self.assertLess(found.measured["edge_on"] / total, 0.08)


class StackLinkTest(unittest.TestCase):
    """Queue rank 1: PlanarLayout can build a room-over-room link."""

    def _linked(self):
        from bloodmap.planar_layout import PlanarLayout

        unit = 1024
        layout = PlanarLayout(name="probe")
        layout.add_region("up", [(0, 0), (2048, 0), (2048, 2048), (0, 2048)],
                          floor_z=0, ceiling_z=-33280, declared_zero_exit=True)
        layout.add_region("down",
                          [(256, 256), (1792, 256), (1792, 1792), (256, 1792)],
                          floor_z=33280, ceiling_z=0, layer="under",
                          declared_zero_exit=True)
        layout.set_player_start("up", x=unit, y=unit, z=0, angle=0)
        layout.stack_link(10, "up", "down", upper_at=(unit, unit),
                          lower_at=(unit, unit), upper_z=0, lower_z=33280)
        return layout

    def test_the_pair_is_found_by_reachability(self):
        from bloodmap.reachability import link_pairs

        disk = self._linked().compile().level.to_disk_map()
        pairs = link_pairs(disk)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["link_id"], 10)

    def test_the_markers_are_on_statnum_zero(self):
        # statnum 10 is culled at load, so a link built there is a link that
        # does not exist. A shipped map lost its room-over-room this way.
        disk = self._linked().compile().level.to_disk_map()
        markers = [s for s in disk.sprites if int(s.fields["type"]) in (11, 12)]
        self.assertEqual(len(markers), 2)
        for sprite in markers:
            self.assertEqual(int(sprite.fields["status"]), 0)
            self.assertIsNotNone(sprite.extra)

    def test_a_link_declares_its_own_overlap(self):
        # Two rooms one above the other necessarily share plan area, which
        # every other pair of regions is refused for.
        layout = self._linked()
        self.assertTrue(any(kind == "stack"
                            for _a, _b, kind in layout.special_pairs))


class ConditionedLinkTest(unittest.TestCase):
    """A link re-partitioned by a planar door is not always open."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    def test_the_caskets_link_is_conditioned(self):
        from bloodmap.conditional import conditioned_links

        found = conditioned_links(self.disk)
        self.assertTrue(found)
        row = found[0]
        self.assertEqual(sorted(row["sectors"]), [28, 30])
        self.assertEqual(row["channel"], 102)

    def test_it_becomes_a_gated_edge_with_a_cause(self):
        # The gap the casket exposed: `conditional` looks for portals that
        # open or shut, and a planar door has neither. Every route through
        # one was invisible.
        from bloodmap.conditional import repartition_edges

        edges = repartition_edges(self.disk)
        self.assertTrue(edges)
        edge = edges[0]
        self.assertEqual(edge.verdict, "conditional")
        self.assertTrue(edge.causes)

    def test_the_covered_at_rest_reading_is_reported_not_assumed(self):
        # E1M1's own casket markers sit clear of the swept band on BOTH
        # halves, so the intuitive picture -- a lid sliding off to uncover
        # the link -- is not what those fields say. The measurement is
        # recorded rather than the story being forced onto it.
        from bloodmap.conditional import conditioned_links

        for row in conditioned_links(self.disk):
            self.assertIn("covered_at_rest", row)
            self.assertFalse(row["covered_at_rest"])


class ContradictionQueueTest(unittest.TestCase):
    def test_it_ranks_and_names_every_item(self):
        from bloodmap.contradictions import run

        report = run()
        self.assertTrue(report["queue"])
        names = [item["name"] for item in report["queue"]]
        self.assertEqual(len(names), len(set(names)))
        for item in report["queue"]:
            self.assertTrue(item["says"].strip(), item["name"])
            self.assertTrue(item["ask"].strip(), item["name"])

    def test_the_two_standing_items_are_carried(self):
        from bloodmap.contradictions import run

        names = {item["name"] for item in run()["queue"]}
        self.assertIn("mask-law-two-sided-exception", names)
        self.assertIn("gallery-topology-exemption", names)

    def test_conflicts_outrank_drifts_which_outrank_open_questions(self):
        from bloodmap.contradictions import RANK, run

        kinds = [item["kind"] for item in run()["queue"]]
        self.assertEqual(kinds, sorted(kinds, key=lambda k: RANK[k]))


if __name__ == "__main__":
    unittest.main()
