"""The decompilation as a fact store, and the rules that make it one.

`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 2: base facts as the
records store them, derived facts with provenance, ambiguity kept as
candidates and resolved by a named selection pass, and inconsistency recorded
rather than hidden. Each of those is a test here, because each is a property
that a store can quietly lose.
"""

from __future__ import annotations

import unittest


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [item for item in list_corpus_maps(population="blood-campaign")
             if item.path.stem.upper() == "E3M1"]
    if not found:
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return read_map(found[0].path)


class TheStore(unittest.TestCase):
    def test_a_predicate_nobody_declared_is_refused(self):
        """A file nobody described is not a fact store."""
        from bloodmap.read_store import FactError, FactStore

        store = FactStore()
        with self.assertRaises(FactError):
            store.add("vibes", "vibes:0", {})

    def test_base_facts_carry_no_provenance_and_derived_ones_do(self):
        from bloodmap.read_store import FactStore, base_facts

        level = _e3m1().to_level_ir()
        store = FactStore()
        store.extend(base_facts(level))
        self.assertEqual(store.count("sector"), 382)
        self.assertEqual(store.count("wall"), 2481)
        self.assertEqual(store.count("sprite"), 807)
        for fact in store["sector"]:
            self.assertEqual(fact.sources, ())
            self.assertEqual(fact.reader, "map")
        #: An XSECTOR is derived from its sector in the sense that matters
        #: here: it is the same record, and the row says so.
        for fact in store["xsector"]:
            self.assertTrue(fact.sources)

    def test_the_extras_come_through_at_the_supervisors_counts(self):
        """133 XSECTORs, 41 XWALLs, 716 XSPRITEs -- the inventory the layer-5
        denominator is measured against."""
        from bloodmap.read_store import FactStore, base_facts

        store = FactStore()
        store.extend(base_facts(_e3m1().to_level_ir()))
        self.assertEqual(store.count("xsector"), 133)
        self.assertEqual(store.count("xwall"), 41)
        self.assertEqual(store.count("xsprite"), 716)

    def test_a_round_trip_through_jsonl_keeps_every_row(self):
        import tempfile
        from pathlib import Path

        from bloodmap.read_store import FactStore, base_facts

        store = FactStore()
        store.extend(base_facts(_e3m1().to_level_ir()))
        with tempfile.TemporaryDirectory() as directory:
            store.write(directory)
            back = FactStore.read(directory)
        self.assertEqual(back.by_predicate(), store.by_predicate())
        self.assertEqual(back["sector"][0].attrs, store["sector"][0].attrs)


class TheReadersAreFunctionsFromFactsToFacts(unittest.TestCase):
    def test_reading_the_map_does_not_change_it(self):
        """Every reader in this experiment is pure. If one repaired its input
        the residue would measure the repair."""
        from copy import deepcopy

        from bloodmap.read_edges import read_edges
        from bloodmap.read_islands import read_islands
        from bloodmap.read_joins import read_joins
        from bloodmap.read_light import read_light
        from bloodmap.read_plan import read_plan
        from bloodmap.read_stairs import read_stairs

        level = _e3m1().to_level_ir()
        before = deepcopy(level.to_dict())
        for reader in (read_joins, read_islands, read_light, read_edges,
                       read_plan, read_stairs):
            reader(level)
            self.assertEqual(level.to_dict(), before,
                             f"{reader.__module__} changed its input")


class AmbiguityIsKept(unittest.TestCase):
    def test_a_tie_is_a_candidate_and_the_selection_chooses_nothing(self):
        """Manifold's rule both ways: a reader may not commit, and a selection
        pass may not be anonymous. The caster test is 8 against 8, so the
        candidate stands and the selection records that it chose nothing."""
        from bloodmap import read_facts
        from bloodmap.read_store import FactStore
        from bloodmap.read_light import read_light

        level = _e3m1().to_level_ir()
        store = FactStore()
        store.extend(read_facts.layer4(level, _islands(level), read_light(level)))
        casters = [row for row in store["candidate"] if row.id == "light:casters"]
        self.assertEqual(len(casters), 1)
        chosen = read_facts.selections(store)
        self.assertEqual(len(chosen), 1)
        self.assertIsNone(chosen[0].attrs["chosen"])
        self.assertIn("criterion", chosen[0].attrs)

    def test_a_selection_states_its_criterion(self):
        from bloodmap import read_facts
        from bloodmap.read_store import FactStore
        from bloodmap.read_plan import read_plan

        level = _e3m1().to_level_ir()
        store = FactStore()
        store.extend(read_facts.layer7(level, read_plan(level)))
        chosen = read_facts.selections(store)
        self.assertTrue(chosen)
        for row in chosen:
            self.assertTrue(row.attrs["criterion"])
            self.assertTrue(row.attrs["basis"])


def _islands(level):
    from bloodmap.read_islands import read_islands

    return read_islands(level)


if __name__ == "__main__":
    unittest.main()
