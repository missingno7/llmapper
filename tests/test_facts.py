"""The fact store, and the one gate that makes a level of detail mean anything.

A pass at level N leaves every fact of level < N byte-identical. The failure
it is written for is silent by construction: a facade pass that nudges an
envelope by a single unit still compiles, still partitions, still aligns, and
the only evidence anywhere is a level-0 line that moved.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.facts import (
    LEVELS, FactError, FactStore, compare_below, lod_faults)


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


class TheStoreOnlyHoldsPredicatesItWasToldAbout(unittest.TestCase):

    def test_an_unknown_predicate_is_refused(self):
        with self.assertRaises(FactError) as caught:
            FactStore().add("vibe", ("x",), lod=0, source="me")
        self.assertIn("question for a person", str(caught.exception))

    def test_an_unknown_level_is_refused(self):
        with self.assertRaises(FactError):
            FactStore().add("surface", ("s",), lod=9, source="me")

    def test_rows_are_written_sorted_so_a_diff_is_a_diff_of_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _store().write(tmp)
            lines = (Path(tmp) / "part_of.jsonl").read_text(
                encoding="utf-8").splitlines()
            self.assertEqual(lines, sorted(lines))

    def test_what_is_written_reads_back_the_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            _store().write(tmp)
            again = FactStore.read(tmp)
            self.assertEqual(again.count(), _store().count())


class ALevelTwoPassMayNotMoveTheP1an(unittest.TestCase):

    def test_a_facade_pass_that_moves_an_envelope_by_one_unit_is_caught(self):
        # THE FAIL-FIRST, and it is one unit on one number.
        store = _store()
        before = store.lines_below(LEVELS["facades"])
        moved = store.of("part_of")[0]
        moved.fields["lo"] = int(moved.fields["lo"]) + 1
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

    def test_the_on_disk_gate_agrees_with_the_live_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / "before"
            after = Path(tmp) / "after"
            store = _store()
            store.write(before)
            store.of("part_of")[0].fields["lo"] += 1
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
            self.assertEqual(
                (before / "part_of.jsonl").read_bytes(),
                (after / "part_of.jsonl").read_bytes())


class TheStoreCarriesWhatTheMapCannot(unittest.TestCase):
    """The three read-back gaps of slice 2i, closed by the store."""

    def test_a_depth_is_recorded_although_no_sector_holds_one(self):
        store = FactStore()
        store.add("shade_depth", ("sector", 7), lod=LEVELS["massing"],
                  source="piece:plane#3", depth=2, base=8, step=12, shade=32)
        row = store.of("shade_depth")[0]
        self.assertEqual(row.fields["depth"], 2)
        self.assertEqual(row.fields["base"] + 2 * row.fields["step"],
                         row.fields["shade"])

    def test_a_lamp_s_contribution_survives_being_summed(self):
        store = FactStore()
        store.add("lamp_delta", ("lamp", "plaza:0"), lod=LEVELS["dressing"],
                  source="piece:market_plaza#0", sector=7, delta=-6, depth=0)
        self.assertEqual(store.of("lamp_delta")[0].fields["delta"], -6)

    def test_a_surface_keeps_its_identity_through_a_path(self):
        store = FactStore()
        for name in ("col_b/row_2", "market_plaza"):
            store.add("surface", ("surface", name), lod=LEVELS["massing"],
                      source="emitter", kind="pavement", floor_z=8192)
        self.assertEqual(len(store.of("surface")), 2,
                         "two surfaces, however connected the map makes them")


if __name__ == "__main__":
    unittest.main()
