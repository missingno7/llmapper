"""Pins for the module boundaries `docs/architecture.md` states.

Only boundaries that are load-bearing *and* were untested. The motivating one
is real: `context_signature` was written inside `anchors.py`, the unsigned
pattern pipeline needed the same key, and the import would have closed a cycle
`patterns -> anchors -> patterns`. The alternative on offer was a second copy
that would drift. These tests fail if either mistake is made again.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "bloodmap"


def module_level_imports(module: str) -> set[str]:
    """Sibling modules imported at import time, not inside a function.

    A function-level import is how `relations.py` reaches the corpus registry
    without closing a cycle, so the distinction is the whole point.
    """
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:                       # module level only, by construction
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            found.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("bloodmap."):
                    found.add(alias.name.split(".")[1])
    return found


class LayeringTests(unittest.TestCase):
    def test_the_pattern_pipeline_does_not_import_the_anchor_query(self):
        """The cycle that moved `context_signature`. `patterns.py` owns the
        corpus registry that `anchors.py` needs, so the arrow only points one
        way: anchors -> patterns, never back."""
        self.assertNotIn("anchors", module_level_imports("patterns"))

    def test_the_anchor_query_may_depend_on_both_layers_below_it(self):
        imports = module_level_imports("anchors")
        self.assertIn("patterns", imports)
        self.assertIn("relations", imports)

    def test_relations_does_not_import_the_pattern_pipeline_at_module_level(self):
        """`relations.mine_relations` needs the corpus registry, and reaches it
        inside the function body. Hoisting that import would close the cycle
        from the other side."""
        self.assertNotIn("patterns", module_level_imports("relations"))

    def test_the_type_catalog_stays_a_leaf(self):
        """`blood_types.py` answers "what does this native number mean". If it
        grew a dependency on a sensor, every sensor would depend on it
        transitively and the catalog would stop being citable on its own."""
        self.assertEqual(module_level_imports("blood_types"), set())

    def test_reachability_does_not_depend_on_the_mining_stack(self):
        """It is consumed by the miners, never the other way round; a parallel
        reachability classifier inside a miner is the defect this pins."""
        imports = module_level_imports("reachability")
        for consumer in ("patterns", "relations", "anchors"):
            self.assertNotIn(consumer, imports)


class SingleHomeTests(unittest.TestCase):
    def test_the_context_signature_has_exactly_one_definition(self):
        """`anchors` re-exports it; it must be the same object, not a copy.
        Two copies of a signature reduction drift, and then two mining reports
        disagree for no visible reason."""
        from bloodmap import anchors, relations

        self.assertIs(anchors.context_signature, relations.context_signature)
        self.assertIs(anchors.OBJECT_FACETS, relations.OBJECT_FACETS)
        self.assertIs(anchors.CONTEXT_FACETS, relations.CONTEXT_FACETS)

        source = (PACKAGE / "anchors.py").read_text(encoding="utf-8")
        self.assertNotIn("def context_signature(", source,
                         "anchors.py must import the signature, not redefine it")

    def test_visibility_is_decided_in_the_type_catalog(self):
        """One place decides what the engine draws. A miner that hardcoded a
        picnum list would be guessing: picnum 2520 is a sound marker 1247 times
        and a switch 3 times in the same campaign."""
        from bloodmap import blood_types

        self.assertTrue(callable(blood_types.sprite_visibility))
        for module in ("relations", "patterns", "anchors"):
            source = (PACKAGE / f"{module}.py").read_text(encoding="utf-8")
            self.assertNotIn("NON_VISIBLE_CATEGORIES = ", source,
                             f"{module}.py must not keep its own copy")

    def test_the_rendering_law_has_exactly_one_reader(self):
        """Which band the engine draws which tile on lives in
        `render_slots.py` and nowhere else. It was first written as three
        lines inside `conformance.fabric_is_visible` -- a cstat test with no
        heights in it -- which is how the E1M1 "pelmet" was recorded as a
        drawn valance when the step is on the other sector's side."""
        from bloodmap import render_slots

        self.assertTrue(callable(render_slots.draws_in_walkable_band))
        self.assertTrue(callable(render_slots.draws_on_a_step))
        source = (PACKAGE / "conformance.py").read_text(encoding="utf-8")
        self.assertIn("draws_in_walkable_band", source)
        for copy in ("cstat & MASKED) or bool(cstat & ONE_WAY",
                     'ceiling_z"]) != int(neighbour["ceiling_z"]'):
            self.assertNotIn(copy, source,
                             "conformance.py must ask render_slots, not "
                             "re-derive the rendering law from the flags")

    def test_the_rendering_law_reader_stays_a_leaf(self):
        """A transcription of `engine.cpp`'s wall pass depends on nothing in
        the package: it must stay citable and testable on a hand-built map."""
        self.assertEqual(module_level_imports("render_slots"), set())

    def test_sector_kinds_are_decided_in_reachability(self):
        from bloodmap import reachability

        self.assertTrue(callable(reachability.sector_kinds))
        self.assertIn("reachable", reachability.SECTOR_KINDS)
        self.assertIn("logic_closet", reachability.SECTOR_KINDS)


class VisibilityCatalogTests(unittest.TestCase):
    """`sprite_visibility` needs both signals, and each alone must decide."""

    def test_a_category_with_no_drawn_form_is_wiring_without_the_cstat_bit(self):
        """Measured: `start` sprites never carry Build's invisible bit and are
        still invisible. Category alone has to be enough."""
        from bloodmap.blood_types import sprite_visibility

        found = sprite_visibility(1, 0)                  # kMarkerSPStart
        self.assertEqual(found["kind"], "wiring")
        self.assertTrue(found["non_visible_category"])
        self.assertFalse(found["invisible_cstat"])
        self.assertTrue(found["reasons"])

    def test_the_cstat_bit_is_enough_on_its_own(self):
        """Measured: 730 campaign `thing` sprites carry the invisible bit while
        their category is a visible one. cstat alone has to be enough."""
        from bloodmap.blood_types import INVISIBLE_CSTAT, sprite_visibility

        found = sprite_visibility(400, INVISIBLE_CSTAT)  # kThingTNTBarrel, hidden
        self.assertEqual(found["kind"], "wiring")
        self.assertFalse(found["non_visible_category"])
        self.assertTrue(found["invisible_cstat"])

    def test_a_drawn_decoration_is_visible(self):
        from bloodmap.blood_types import sprite_visibility

        found = sprite_visibility(0, 0)
        self.assertEqual(found["kind"], "visible")
        self.assertEqual(found["reasons"], [])

    def test_the_sound_marker_that_started_this_is_wiring_on_both_signals(self):
        """picnum 2520 is type 709 in 1247 of its 1250 campaign occurrences."""
        from bloodmap.blood_types import sprite_visibility

        found = sprite_visibility(709, 32896)
        self.assertEqual(found["kind"], "wiring")
        self.assertEqual(found["type_name"], "kSoundSector")
        self.assertEqual(len(found["reasons"]), 2)

    def test_the_switch_that_wears_the_same_tile_is_not_wiring(self):
        """The other 3 occurrences of picnum 2520 are switches. A picnum
        blocklist would have thrown them away."""
        from bloodmap.blood_types import sprite_visibility

        self.assertEqual(sprite_visibility(21, 0)["kind"], "visible")


class EvidenceRuleTests(unittest.TestCase):
    def test_a_generated_map_is_never_a_population_that_can_be_cited(self):
        """The rule every phase repeats. `generated` exists so a reconstruction
        cannot be mined as convention."""
        from bloodmap.patterns import POPULATIONS, classify_map_population

        self.assertEqual(
            classify_map_population("work/BB2-semantic-reconstruction-v3.MAP"),
            "generated")
        self.assertEqual(classify_map_population("work/E1M1-BLOOD.MAP"), "generated")
        self.assertIn("generated", POPULATIONS)

    def test_the_promotion_rule_is_written_down_where_the_note_says(self):
        readme = PACKAGE.parent / "knowledge" / "blood" / "design" / "README.md"
        self.assertTrue(readme.exists(), "the promotion rule must have a home")


if __name__ == "__main__":
    unittest.main()
