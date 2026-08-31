"""The owner's tile readings, and the two rules in them that are executable.

A malformed entry has to fail here rather than three modules away in the
middle of a mining run, so most of this is the validator.
"""

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.owner_anchors import (
    BINDINGS, KINDS, OwnerAnchor, OwnerAnchorError, load_owner_anchors,
    owner_label, parse_owner_anchors,
)

SCHEMA = "llmapper.blood-owner-anchors"


def document(*anchors, **extra):
    return {"$schema": SCHEMA, "schema_version": "1",
            "anchors": list(anchors), **extra}


def anchor(picnum=100, **over):
    base = {"picnum": picnum, "kind": "wall", "label_en": "a thing",
            "label_cs": "vec"}
    base.update(over)
    return base


class ValidationTest(unittest.TestCase):
    def test_a_good_document_parses(self):
        anchors = parse_owner_anchors(document(anchor()))
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors.get(100).label_en, "a thing")

    def test_the_wrong_schema_is_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors({"$schema": "something else", "anchors": [anchor()]})

    def test_an_empty_document_is_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document())

    def test_a_missing_label_is_refused(self):
        raw = anchor()
        del raw["label_en"]
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(raw))

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor(kind="doorknob")))

    def test_an_unknown_binding_is_refused(self):
        # "quite strong" is not a grade. Accepting it would let a tile
        # quietly stop counting as naming evidence.
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor(binding="quite strong")))

    def test_a_tile_named_twice_is_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor(100), anchor(100)))

    def test_a_state_pair_pointing_nowhere_is_refused(self):
        # A pairing to a tile the file does not name is a dangling claim.
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor(100, state_pair={"broken": 999})))

    def test_a_state_pair_to_a_named_tile_is_kept(self):
        anchors = parse_owner_anchors(document(
            anchor(100, state_pair={"broken": 101}), anchor(101)))
        self.assertEqual(anchors.state_pairs(), {100: {"broken": 101}})

    def test_a_non_numeric_picnum_is_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor("the crate one")))

    def test_cross_refs_given_as_a_string_are_refused(self):
        with self.assertRaises(OwnerAnchorError):
            parse_owner_anchors(document(anchor(cross_refs="one_ref")))


class BindingRuleTest(unittest.TestCase):
    """Strong binding may name; weak and untested never may."""

    def test_a_strong_tile_may_name(self):
        self.assertTrue(OwnerAnchor(1, "sprite", "mannequin",
                                    binding="strong").may_name)

    def test_a_weak_tile_may_not(self):
        self.assertFalse(OwnerAnchor(1, "wall", "crate look",
                                     binding="weak").may_name)

    def test_an_untested_tile_may_not(self):
        # Not "probably fine". An untested claim is not evidence.
        self.assertFalse(OwnerAnchor(1, "wall", "some wall").may_name)

    def test_naming_evidence_keeps_only_the_strong_ones(self):
        anchors = parse_owner_anchors(document(
            anchor(10, binding="strong", label_en="mannequin"),
            anchor(11, binding="weak", label_en="crate look"),
            anchor(12, label_en="untested")))
        evidence = anchors.naming_evidence([10, 11, 12, 999], used_for="dressing")
        self.assertEqual([item["anchor"] for item in evidence], [10])
        self.assertEqual(evidence[0]["source"], "OWNER")
        self.assertEqual(evidence[0]["used_for"], "dressing")

    def test_provenance_records_the_binding_a_name_was_allowed_on(self):
        # So a wrong name leads back to the tile and its grade, not to a
        # module that once typed a number into a list.
        found = OwnerAnchor(2377, "sprite", "mannequin", binding="strong")
        record = found.provenance("naming")
        self.assertEqual(record["anchor"], 2377)
        self.assertEqual(record["binding"], "strong")
        self.assertTrue(record["may_name"])
        self.assertIn("owner-anchors-v1.json", record["file"])

    def test_an_untested_tile_says_so_rather_than_claiming_weak(self):
        record = OwnerAnchor(1, "wall", "a wall").provenance()
        self.assertEqual(record["binding"], "untested")


class LookupTest(unittest.TestCase):
    def setUp(self):
        self.anchors = parse_owner_anchors(document(
            anchor(10, kind="sprite", binding="strong", label_en="mannequin"),
            anchor(11, kind="wall", binding="weak", label_en="crate look"),
            anchor(12, kind="sprite", wiring=True, label_en="sound marker")))

    def test_by_kind(self):
        self.assertEqual([a.picnum for a in self.anchors.by_kind("sprite")],
                         [10, 12])

    def test_by_binding(self):
        self.assertEqual([a.picnum for a in self.anchors.by_binding("weak")], [11])

    def test_an_unknown_kind_or_binding_is_refused_rather_than_empty(self):
        with self.assertRaises(OwnerAnchorError):
            self.anchors.by_kind("doorknob")
        with self.assertRaises(OwnerAnchorError):
            self.anchors.by_binding("medium")

    def test_wiring_and_naming_sets(self):
        self.assertEqual(self.anchors.wiring_picnums(), {12})
        self.assertEqual(self.anchors.naming_picnums(), {10})

    def test_a_label_carries_its_source(self):
        self.assertEqual(self.anchors.label(10), "mannequin (owner)")
        self.assertEqual(self.anchors.label(999, "unknown"), "unknown")

    def test_membership(self):
        self.assertIn(10, self.anchors)
        self.assertNotIn(999, self.anchors)
        self.assertNotIn("not a tile", self.anchors)


class TheRealFileTest(unittest.TestCase):
    """The owner's actual file, which ships in the repository."""

    def setUp(self):
        self.anchors = load_owner_anchors()

    def test_it_parses(self):
        self.assertGreater(len(self.anchors), 90)

    def test_every_kind_and_binding_is_one_this_module_knows(self):
        for item in self.anchors:
            self.assertIn(item.kind, KINDS, item.picnum)
            if item.binding is not None:
                self.assertIn(item.binding, BINDINGS, item.picnum)

    def test_the_wiring_tiles_are_the_three_the_owner_named(self):
        self.assertEqual(self.anchors.wiring_picnums(), {2520, 2521, 2332})

    def test_wiring_tiles_agree_with_blood_types_sprite_visibility(self):
        # The owner's "invisible in game" and `sprite_visibility`'s
        # non-visible categories are the same rule read from two ends. Kept
        # in step by this test rather than by hand.
        from bloodmap.blood_types import NON_VISIBLE_CATEGORIES

        self.assertTrue(NON_VISIBLE_CATEGORIES)
        for picnum in self.anchors.wiring_picnums():
            anchor = self.anchors.get(picnum)
            #: A wiring tile is never a visible object, so it can never be
            #: evidence for what something *is*.
            self.assertFalse(anchor.may_name, picnum)
            #: Every one of them is a marker. 2332 is drawn as an arrow and
            #: its label says so rather than saying "invisible", which is
            #: why this asks what they are rather than how they look.
            self.assertIn("marker", anchor.label_en.lower(), picnum)

    def test_the_crate_the_project_got_wrong_once_is_named_correctly(self):
        # 459 is a moss-grown rock and 452 is the small crate. A build once
        # shipped the rock as a crate.
        self.assertIn("crate", self.anchors.get(452).label_en)
        self.assertIn("rock", self.anchors.get(459).label_en)
        self.assertEqual(self.anchors.get(452).state_pair, {"broken": 462})

    def test_the_convenience_label_reads_as_a_report_should_print_it(self):
        self.assertEqual(owner_label(332), "grate/lattice (owner)")
        self.assertEqual(owner_label(999999, "nothing"), "nothing")

    def test_a_malformed_file_on_disk_raises_rather_than_returning_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text(json.dumps(document(anchor(kind="nonsense"))),
                            encoding="utf-8")
            with self.assertRaises(OwnerAnchorError):
                load_owner_anchors(path)

    def test_a_missing_file_raises(self):
        with self.assertRaises(OwnerAnchorError):
            load_owner_anchors(Path("no-such-anchors.json"))


class AnchorSpecTest(unittest.TestCase):
    """`anchors.py` builds classes from the owner's readings."""

    def test_a_class_can_be_the_tiles_the_owner_called_crates(self):
        from bloodmap.anchors import anchor_from_owner

        spec = anchor_from_owner("crate")
        self.assertIn(452, spec.tiles)
        self.assertIn(462, spec.tiles)
        self.assertIn("owner-anchors-v1.json", spec.origin)
        self.assertIn("OWNER", spec.origin)

    def test_a_class_can_be_narrowed_by_binding(self):
        from bloodmap.anchors import anchor_from_owner

        spec = anchor_from_owner("crate", binding="weak")
        self.assertEqual(spec.tiles, (456,))

    def test_naming_nothing_the_owner_named_is_refused(self):
        from bloodmap.anchors import AnchorError, anchor_from_owner

        with self.assertRaises(AnchorError):
            anchor_from_owner("a thing the owner never mentioned")

    def test_the_default_kit_is_the_tiles_a_name_may_rest_on(self):
        from bloodmap.anchors import owner_anchor_kit

        kit = owner_anchor_kit()
        anchors = load_owner_anchors()
        self.assertEqual({spec.tiles[0] for spec in kit},
                         set(anchors.naming_picnums()))
        for spec in kit:
            self.assertIn("OWNER", spec.origin)


if __name__ == "__main__":
    unittest.main()
