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

    A function-level import is how a module reaches a layer above it without
    closing a cycle, so the distinction is the whole point.
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
    def test_the_corpus_registry_is_a_leaf_below_every_sensor(self):
        """`corpus.py` answers "where did this map come from". It sat inside
        `patterns.py` until 2026-11-19, so a tool that only wanted a list of
        maps imported the whole sensor stack, `relations.py` could reach it
        only from inside a function, and seventeen miners globbed a directory
        instead. It reads maps and nothing else."""
        self.assertEqual(module_level_imports("corpus"), {"format"})

    def test_the_pattern_pipeline_does_not_import_the_anchor_query(self):
        """The cycle that moved `context_signature`: the arrow only points one
        way, anchors -> patterns, never back."""
        self.assertNotIn("anchors", module_level_imports("patterns"))

    def test_the_anchor_query_may_depend_on_both_layers_below_it(self):
        imports = module_level_imports("anchors")
        self.assertIn("corpus", imports)
        self.assertIn("relations", imports)

    def test_relations_does_not_import_the_pattern_pipeline_at_module_level(self):
        """`relations.mine_relations` needs the corpus registry and takes it
        from `corpus.py`. Reaching for `patterns.py` instead would close the
        cycle from the other side."""
        imports = module_level_imports("relations")
        self.assertNotIn("patterns", imports)
        self.assertIn("corpus", imports)

    def test_the_library_imports_nothing_from_the_scripts_around_it(self):
        """A sensor lives in the library and a tool is its corpus run, never
        the other way. Until 2026-11-19 `aperture.audit`, `keys.check` and
        four rules in `rules_blood.py` imported their own evidence from
        `tools/mine_*.py`, and the command line imported three blueprints from
        `experiments/`. Function-local imports, so nothing failed until the
        package was used without the scripts beside it -- which is what
        installing it does (`pyproject.toml` packages `bloodmap*` only)."""
        offenders = []
        for path in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                elif isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                else:
                    continue
                for name in names:
                    if name.split(".")[0] in ("tools", "experiments", "projects"):
                        offenders.append(f"{path.name}:{node.lineno} imports {name}")
        self.assertEqual(offenders, [])

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

    def test_the_sound_marker_that_started_this_is_wiring_by_its_own_bit(self):
        """picnum 2520 is type 709 in 1247 of its 1250 campaign occurrences, and it is unseen because it carries the
        invisible bit: the engine hides no sound sprite by its kind, and only the trigger generator of the generators
        (triggers.cpp:2360, InitGenerator)."""
        from bloodmap.blood_types import sprite_visibility

        found = sprite_visibility(709, 32896)
        self.assertEqual(found["kind"], "wiring")
        self.assertEqual(found["type_name"], "kSoundSector")
        self.assertEqual(found["reasons"], ["cstat carries Build's invisible bit"])
        self.assertEqual(sprite_visibility(703, 128)["kind"], "visible")       # the stone face that spits fire
        self.assertEqual(sprite_visibility(700, 0)["kind"], "wiring")          # the one the engine hides itself

    def test_the_switch_that_wears_the_same_tile_is_not_wiring(self):
        """The other 3 occurrences of picnum 2520 are switches. A picnum
        blocklist would have thrown them away."""
        from bloodmap.blood_types import sprite_visibility

        self.assertEqual(sprite_visibility(21, 0)["kind"], "visible")


class EvidenceRuleTests(unittest.TestCase):
    def test_a_generated_map_is_never_a_population_that_can_be_cited(self):
        """The rule every phase repeats. `generated` exists so a reconstruction
        cannot be mined as convention."""
        from bloodmap.corpus import POPULATIONS, classify_map_population

        self.assertEqual(
            classify_map_population("work/BB2-semantic-reconstruction-v3.MAP"),
            "generated")
        self.assertEqual(classify_map_population("work/E1M1-BLOOD.MAP"), "generated")
        self.assertIn("generated", POPULATIONS)

    def test_the_promotion_rule_is_written_down_where_the_note_says(self):
        readme = PACKAGE.parent / "knowledge" / "blood" / "design" / "README.md"
        self.assertTrue(readme.exists(), "the promotion rule must have a home")


#: The live levels: projects whose map the build rewrites. A library test that
#: reads one breaks when the level changes, and passes only while it exists.
def _live_levels() -> tuple[str, ...]:
    from bloodmap import project

    return tuple(p.key for p in project.projects("level"))


#: every project that says it is a level (`project.json`): not a list kept by hand
LIVE_LEVELS = _live_levels()

#: Library tests that still name a live level's project, each with the reason.
#: None of them reads the level's built map from the working tree. Shrink it;
#: do not grow it without the owner's word.
STILL_NAMES_A_LEVEL = {
    "test_readback.py":
        "its fail-first fixture is the city map as committed at 8c42701, pulled from git: "
        "a frozen revision, not the working tree",
    "test_rendering_law.py":
        "its fail-first fixture is the city map as committed at 8c42701, pulled from git: "
        "a frozen revision, not the working tree",
    "test_project.py":
        "names blood-city only to assert that a new project's starter does not carry it",
}


def _names_a_live_level(path: Path) -> list[int]:
    """The lines whose string literals (not docstrings) name a live level's project or map."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.body and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    import re

    level = "|".join(re.escape(name) for name in LIVE_LEVELS)
    named = re.compile(rf"(?:^|[/\\])(?:{level})(?:[/\\]|$)|(?:{level})-current|gravesend\.map", re.I)
    return sorted({node.lineno for node in ast.walk(tree)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)
                   and id(node) not in docstrings and named.search(node.value)})


class LevelTestsLiveWithTheirLevelTests(unittest.TestCase):
    """`tests/` holds what is true of the library and the tools whatever levels
    exist; `projects/<name>/tests/` holds one level's regression tests
    (`python -m tools.suite --library` and `--project <name>`)."""

    def test_no_library_test_names_a_live_level(self):
        here = PACKAGE.parent / "tests"
        found = {}
        for path in sorted(here.rglob("*.py")):
            if path.name == Path(__file__).name or path.name in STILL_NAMES_A_LEVEL:
                continue
            lines = _names_a_live_level(path)
            if lines:
                found[path.relative_to(here.parent).as_posix()] = lines
        self.assertEqual(found, {}, (
            "these library tests read a live level (" + ", ".join(LIVE_LEVELS) + "). A test of "
            "one level goes in projects/<name>/tests/ (a test_<module>_city.py beside the "
            "others for blood-city), run by `python -m tools.suite --project <name>`; a frozen "
            "map or fact store the library's readers need is copied under tests/fixtures/ "
            "(as tests/fixtures/city-slices/). File:lines: " + repr(found)))

    def test_every_exception_still_needs_its_reason(self):
        here = PACKAGE.parent / "tests"
        for name, reason in STILL_NAMES_A_LEVEL.items():
            self.assertGreater(len(reason), 40, name)
            path = here / name
            self.assertTrue(path.exists(), f"{name} is gone: drop it from STILL_NAMES_A_LEVEL")
            self.assertTrue(_names_a_live_level(path),
                            f"{name} no longer names a live level: drop it from STILL_NAMES_A_LEVEL")


if __name__ == "__main__":
    unittest.main()
