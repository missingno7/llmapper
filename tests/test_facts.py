"""One fact store, written from both ends.

`bloodmap/read_store.py` owns the row shape and the predicate table;
`bloodmap/facts.py` is the compiler's writing end and adds the two things a
reader does not need: a level of detail on every declaration, and the gate
that makes one mean something.

The gate's failure is silent by construction: a facade pass that nudges an
envelope by a single unit still compiles, still partitions, still aligns, and
the only evidence anywhere is a level-0 row that moved.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.facts import (
    COMPILER_PREDICATES, LEVELS, FactStore, compare_below, diff_stores,
    diff_summary, lod_faults)
from bloodmap.read_store import PREDICATES, FactError
from bloodmap.read_store import FactStore as ReadStore


def _store():
    store = FactStore()
    store.add("part_of", ("span", "x", "avenue"), lod=LEVELS["plan"],
              source="city_solve.solve_axis", parent="city", lo=41472,
              hi=48640, kind="gutter")
    store.add("part_of", ("span", "y", "quay"), lod=LEVELS["plan"],
              source="city_solve.solve_axis", parent="city", lo=55296,
              hi=61440, kind="gutter")
    store.add("surface", ("surface", "plane"), lod=LEVELS["massing"],
              source="emitter", kind="road", floor_z=10240)
    store.add("frame", ("run", 0), lod=LEVELS["facades"],
              source="texture_frame.frame_map", walls=[0, 1, 2], tile=400)
    return store


class OneStoreOneTable(unittest.TestCase):

    def test_every_compiler_predicate_is_in_the_reader_s_table(self):
        # The rule that keeps them one store: a compiler predicate the table
        # does not have is ADDED there with a description, never invented
        # locally.
        for name in COMPILER_PREDICATES:
            self.assertIn(name, PREDICATES, name)
            self.assertTrue(PREDICATES[name].strip(), name)

    def test_an_undeclared_predicate_is_refused_by_the_table(self):
        with self.assertRaises(FactError) as caught:
            FactStore().add("vibe", ("x",), lod=0, source="me")
        self.assertIn("not a declared predicate", str(caught.exception))

    def test_a_compiler_fact_without_a_level_is_refused(self):
        with self.assertRaises(FactError) as caught:
            FactStore().add("surface", ("s",), source="me")
        self.assertIn("level of detail", str(caught.exception))

    def test_the_row_is_the_reader_s_shape_with_lod_on_it(self):
        row = _store().of("surface")[0].to_dict()
        self.assertEqual(row["id"], "surface:plane")
        self.assertEqual(row["_reader"], "compiler")
        self.assertEqual(row["_from"], ["emitter"])
        self.assertEqual(row["_layer"], LEVELS["massing"])
        self.assertEqual(row["lod"], LEVELS["massing"])
        self.assertEqual(row["kind"], "road")

    def test_what_is_written_reads_back_through_the_reader_s_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            _store().write(tmp)
            again = ReadStore.read(tmp)
            self.assertEqual(again.by_predicate(), _store().by_predicate())
            self.assertEqual(again["surface"][0].attrs["lod"],
                             LEVELS["massing"])


class ALevelTwoPassMayNotMoveThePlan(unittest.TestCase):

    def test_a_facade_pass_that_moves_an_envelope_by_one_unit_is_caught(self):
        # THE FAIL-FIRST, and it is one unit on one number.
        store = _store()
        before = store.lines_below(LEVELS["facades"])
        store.of("part_of")[0].attrs["lo"] += 1
        faults = compare_below(before, store.lines_below(LEVELS["facades"]),
                               LEVELS["facades"])
        self.assertEqual(len(faults), 1)
        self.assertIn("part_of", faults[0])
        self.assertIn("below its level", faults[0])

    def test_a_facade_pass_adding_facade_facts_is_silent(self):
        store = _store()
        before = store.lines_below(LEVELS["facades"])
        store.add("frame", ("run", 1), lod=LEVELS["facades"], source="frames",
                  walls=[3, 4], tile=401)
        self.assertEqual(
            compare_below(before, store.lines_below(LEVELS["facades"]),
                          LEVELS["facades"]), [])

    def test_the_gate_is_a_query_over_lod_on_disk_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = Path(tmp) / "before", Path(tmp) / "after"
            store = _store()
            store.write(before)
            store.of("part_of")[0].attrs["lo"] += 1
            store.write(after)
            faults = lod_faults(before, after, LEVELS["facades"])
            self.assertEqual(len(faults), 1)
            self.assertIn("part_of", faults[0])

    def test_an_untouched_plan_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = Path(tmp) / "a", Path(tmp) / "b"
            _store().write(before)
            _store().write(after)
            self.assertEqual(lod_faults(before, after, LEVELS["facades"]), [])
            self.assertEqual((before / "part_of.jsonl").read_bytes(),
                             (after / "part_of.jsonl").read_bytes())


class TheDiffIsTheSymmetryTest(unittest.TestCase):
    """Decisions section 20: decompile, recompile, diff STRUCTURE. With one
    store that is a diff of two sets of rows."""

    def test_a_predicate_only_one_side_writes_is_named(self):
        mine = _store()
        theirs = ReadStore()
        theirs.add("surface_kind", "sector:0", {"kind": "road"},
                   reader="read_joins")
        summary = diff_summary(diff_stores(mine, theirs))
        self.assertIn("part_of", summary["declared only"])
        self.assertIn("surface_kind", summary["recovered only"])

    def test_a_matching_id_is_a_stronger_agreement_than_a_matching_count(self):
        mine = _store()
        theirs = ReadStore()
        theirs.add("surface", "surface:plane", {"kind": "road"},
                   reader="read_surfaces")
        theirs.add("surface", "surface:somewhere-else", {"kind": "road"},
                   reader="read_surfaces")
        diff = diff_stores(mine, theirs)
        self.assertEqual(diff["surface"]["declared"], 1)
        self.assertEqual(diff["surface"]["recovered"], 2)
        self.assertEqual(diff["surface"]["same_id"], 1)
        self.assertEqual(diff["surface"]["recovered_only"], 1)

    def test_the_base_predicates_are_marked_so_they_do_not_read_as_a_gap(self):
        theirs = ReadStore()
        theirs.add("sector", "sector:0", {"floor_z": 0}, reader="map")
        diff = diff_stores(FactStore(), theirs)
        self.assertTrue(diff["sector"]["base"])
        self.assertNotIn("sector",
                         diff_summary(diff)["recovered only"])


class TheStoreCarriesWhatTheMapCannot(unittest.TestCase):

    def test_a_depth_is_recorded_although_no_sector_holds_one(self):
        store = FactStore()
        store.add("shade_depth", ("sector", 7), lod=LEVELS["massing"],
                  source="piece:plane#3", depth=2, base=8, step=12, shade=32)
        row = store.of("shade_depth")[0]
        self.assertEqual(row.attrs["depth"], 2)
        self.assertEqual(row.attrs["base"] + 2 * row.attrs["step"],
                         row.attrs["shade"])

    def test_a_lamp_s_contribution_survives_being_summed(self):
        store = FactStore()
        store.add("lamp_delta", ("lamp", "plaza:0"), lod=LEVELS["dressing"],
                  source="piece:market_plaza#0", sector=7, delta=-6, depth=0)
        self.assertEqual(store.of("lamp_delta")[0].attrs["delta"], -6)

    def test_a_surface_keeps_its_identity_through_a_path(self):
        store = FactStore()
        for name in ("col_b/row_2", "market_plaza"):
            store.add("surface", ("surface", name), lod=LEVELS["massing"],
                      source="emitter", kind="pavement", floor_z=8192)
        self.assertEqual(len(store.of("surface")), 2,
                         "two surfaces, however connected the map makes them")


if __name__ == "__main__":
    unittest.main()
