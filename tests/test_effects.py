"""The neutral effect vocabulary, and the rule that names come from space.

The corpus-backed half is gated and skips cleanly. What is not gated is the
reading itself, which is where the claims live: that the same primitive
describes a door and a lift, that the design object is decided by embedding,
and that the reading declines rather than guessing where its questions do not
apply.
"""

import unittest

from bloodmap.effects import (
    BOTH, CARRIES_BETWEEN_LEVELS, CLOSED, CROUCH_HEIGHT, EffectError,
    MOVE_CEILING_Z, MOVE_FLOOR_Z, NEITHER, OPENS_A_WAY, ROTATE_ABOUT_AXIS,
    STEP_UP, TRANSLATE_XY, UNCLASSIFIED, design_object, embedding, openings,
    physical_effects, style,
)
from bloodmap.doors import PLAYER_HEIGHT

try:
    from bloodmap.patterns import list_corpus_maps
    CORPUS = bool(list_corpus_maps(population="blood-campaign"))
except Exception:
    CORPUS = False


def record(*, type_id=600, off_floor=0, on_floor=0, off_ceil=-32768,
           on_ceil=-32768, rest=32768, **extra):
    """One `observe_motion_sector`-shaped record, with only what is read."""
    base = {
        "type_id": type_id, "off_floor_z": off_floor, "on_floor_z": on_floor,
        "off_ceiling_z": off_ceil, "on_ceiling_z": on_ceil,
        "rest_opening": rest, "busy_time_a": 10, "motion": "z_ceiling",
        "interaction": "wall_push", "triggers": [], "portals": [],
        "visually_distinct_from_fill": True, "distinct_approach_faces": [89],
        "nearby_sprites": [], "key": 0, "key_name": None,
    }
    base.update(extra)
    return base


class PrimitiveTest(unittest.TestCase):
    """Plane 1: what the engine does, and nothing more."""

    def test_a_moving_ceiling_is_one_effect(self):
        effects = physical_effects(record(off_ceil=0, on_ceil=-26624))
        self.assertEqual([item["effect"] for item in effects], [MOVE_CEILING_Z])
        self.assertEqual(effects[0]["travel"], -26624)

    def test_a_moving_floor_and_ceiling_are_two_effects(self):
        effects = physical_effects(
            record(off_floor=0, on_floor=-7168, off_ceil=0, on_ceil=-7168))
        self.assertEqual([item["effect"] for item in effects],
                         [MOVE_FLOOR_Z, MOVE_CEILING_Z])

    def test_a_sector_that_does_not_move_has_no_effects(self):
        self.assertEqual(physical_effects(record()), ())

    def test_a_sliding_sector_translates(self):
        effects = physical_effects(record(type_id=614))
        self.assertIn(TRANSLATE_XY, [item["effect"] for item in effects])

    def test_a_rotating_sector_turns(self):
        effects = physical_effects(record(type_id=615))
        self.assertIn(ROTATE_ABOUT_AXIS, [item["effect"] for item in effects])

    def test_no_record_is_refused_rather_than_read_as_empty(self):
        with self.assertRaises(EffectError):
            physical_effects(None)


class OpeningTest(unittest.TestCase):
    def test_the_gap_is_floor_minus_ceiling(self):
        # Blood's z grows downward, so the floor is the larger number. A
        # reciprocal of this survived elsewhere in the repo for months.
        gaps = openings(record(off_floor=0, off_ceil=-20000,
                               on_floor=0, on_ceil=-4000))
        self.assertEqual(gaps["off"], 20000)
        self.assertEqual(gaps["on"], 4000)
        self.assertEqual(gaps["widest"], 20000)
        self.assertEqual(gaps["narrowest"], 4000)


class EmbeddingTest(unittest.TestCase):
    """Plane 3: the two spatial questions."""

    def test_a_gap_that_opens_from_shut_changes_what_fits(self):
        spatial = embedding(
            record(off_ceil=0, on_ceil=-PLAYER_HEIGHT - 1000), [0])
        self.assertTrue(spatial["changes_what_fits"])
        self.assertEqual(design_object(spatial), OPENS_A_WAY)

    def test_a_gap_that_shuts_from_open_changes_what_fits_too(self):
        # Symmetric on purpose. A leaf that rests open and closes restricts
        # exactly as much as one that rests shut and opens, and calling only
        # the second one a door is a reading, not a measurement.
        spatial = embedding(
            record(off_ceil=-PLAYER_HEIGHT - 1000, on_ceil=0), [0])
        self.assertTrue(spatial["changes_what_fits"])

    def test_a_floor_reaching_two_neighbour_levels_carries_a_body(self):
        spatial = embedding(
            record(off_floor=0, on_floor=-40000,
                   off_ceil=-200000, on_ceil=-200000), [0, -40000])
        self.assertTrue(spatial["carries_between_levels"])
        self.assertEqual(design_object(spatial), CARRIES_BETWEEN_LEVELS)

    def test_a_floor_reaching_one_level_carries_nobody(self):
        spatial = embedding(
            record(off_floor=0, on_floor=-40000,
                   off_ceil=-200000, on_ceil=-200000), [0])
        self.assertFalse(spatial["carries_between_levels"])

    def test_a_step_sized_rise_is_not_carrying(self):
        # A body walks up STEP_UP without help; below that nothing is needed.
        spatial = embedding(
            record(off_floor=0, on_floor=-STEP_UP + 1,
                   off_ceil=-200000, on_ceil=-200000), [0, -STEP_UP + 1])
        self.assertFalse(spatial["carries_between_levels"])

    def test_doing_both_is_reported_as_both(self):
        spatial = embedding(
            record(off_floor=0, on_floor=-40000, off_ceil=0, on_ceil=-200000),
            [0, -40000])
        self.assertEqual(design_object(spatial), BOTH)

    def test_a_motion_that_changes_neither_is_neither(self):
        spatial = embedding(record(off_ceil=-100000, on_ceil=-90000), [0])
        self.assertEqual(design_object(spatial), NEITHER)

    def test_a_gap_that_only_ever_admits_a_crouch(self):
        gap = (CROUCH_HEIGHT + PLAYER_HEIGHT) // 2
        spatial = embedding(record(off_ceil=0, on_ceil=-gap), [0])
        self.assertTrue(spatial["crouch_only"])
        self.assertFalse(spatial["changes_what_fits"])

    def test_a_gap_a_body_can_walk_through_is_not_crouch_only(self):
        # "Crouch-only" is a claim about what the gap *never* admits, so a
        # way through that a standing body can use has to fail it however
        # comfortably it also admits a crouching one.
        spatial = embedding(
            record(off_ceil=0, on_ceil=-PLAYER_HEIGHT - 4096), [0])
        self.assertFalse(spatial["crouch_only"])
        self.assertTrue(spatial["admits_a_ducked_body"]["on"])

    def test_shutting_to_nothing_is_noticed(self):
        spatial = embedding(record(off_ceil=-CLOSED + 1, on_ceil=-100000), [0])
        self.assertTrue(spatial["shuts_to_nothing"])


class NamingTest(unittest.TestCase):
    """The rule the phase turns on."""

    def test_the_name_is_decided_by_the_embedding_alone(self):
        # The same spatial answer, whatever the fields were: design_object
        # takes no type and cannot be told one.
        spatial = embedding(
            record(type_id=602, off_ceil=0, on_ceil=-PLAYER_HEIGHT - 1), [0])
        self.assertEqual(design_object(spatial), OPENS_A_WAY)

    def test_a_mechanism_that_does_not_move_in_z_is_not_named(self):
        # 662 campaign sectors slide or turn. Both questions above are about a
        # vertical opening, so those are untested -- and "untested" is a
        # different claim from "neither". Filing them under neither is the
        # first thing this experiment did wrong.
        spatial = embedding(record(type_id=615), [0])
        self.assertEqual(design_object(spatial, moves_in_z=False), UNCLASSIFIED)
        self.assertNotEqual(design_object(spatial, moves_in_z=False), NEITHER)


class StyleTest(unittest.TestCase):
    def test_style_reports_readability_and_not_meaning(self):
        read = style(record(key=2, key_name="skull",
                            nearby_sprites=[{"category": "switch"}]))
        self.assertTrue(read["face_unlike_its_surround"])
        self.assertTrue(read["keyed"])
        self.assertEqual(read["signifiers"], ["switch"])


@unittest.skipUnless(CORPUS, "the Blood corpus is not present")
class CorpusTest(unittest.TestCase):
    def test_one_campaign_map_reads_end_to_end(self):
        from bloodmap.effects import read_map_mechanisms
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        entry = [item for item in list_corpus_maps(population="blood-campaign")
                 if item.path.stem == "E1M1"][0]
        report = read_map_mechanisms(read_map(entry.path), map_name="E1M1")
        self.assertGreater(report["count"], 0)
        for mechanism in report["mechanisms"]:
            self.assertIn("primitive", mechanism)
            self.assertIn("embedding", mechanism)
            self.assertIn(mechanism["design_object"],
                          (OPENS_A_WAY, CARRIES_BETWEEN_LEVELS, BOTH, NEITHER,
                           UNCLASSIFIED))


if __name__ == "__main__":
    unittest.main()
