"""`tools/symmetry_diff.py`: the classes, and the city it was written for.

The classing is the whole tool, so it is tested on stores small enough to read
in one screen. The last class is the one that made the report usable: before
it existed, `join` reported 924 disagreements because the compiler writes
`picnum` and the reader writes `wears_tile`, and the one real content
disagreement on the map was buried under them.
"""

from __future__ import annotations

import unittest


def _store(rows):
    from bloodmap.read_store import FactStore

    store = FactStore()
    for predicate, one, attrs in rows:
        store.add(predicate, one, attrs, reader="test")
    return store


def _compare(declared, recovered, base=frozenset()):
    from tools.symmetry_diff import compare

    return compare(declared, recovered, base_predicates=base)


class TheClasses(unittest.TestCase):
    def test_a_declared_id_nobody_recovers_is_a_missing_id(self):
        result = _compare(_store([("island", "island:0", {"rise": 2048})]),
                          _store([]))
        found, = result["findings"]
        self.assertEqual(found["class"], "missing id")
        self.assertEqual(found["ids"], ["island:0"])
        self.assertEqual(result["predicates"]["island"]["missing_ids"], 1)

    def test_a_recovered_id_nobody_declared_is_an_extra_id(self):
        result = _compare(_store([]),
                          _store([("island", "island:0", {"rise": 2048})]))
        found, = result["findings"]
        self.assertEqual(found["class"], "extra id")
        self.assertEqual(result["summary"]["recovered_only"], ["island"])

    def test_the_same_id_with_a_different_value_is_a_content_disagreement(self):
        result = _compare(_store([("island", "island:0", {"rise": 2048})]),
                          _store([("island", "island:0", {"rise": 1024})]))
        found, = result["findings"]
        self.assertEqual(found["class"], "same id different attrs")
        self.assertEqual(found["fields"], {"rise": 1})
        self.assertEqual(found["examples"][0]["fields"]["rise"], [2048, 1024])

    def test_a_field_only_one_side_writes_is_a_shape_difference(self):
        """One finding, not one per row, and it does not become an attr diff."""
        result = _compare(
            _store([("island", "island:0", {"rise": 2048, "picnum": 6}),
                    ("island", "island:1", {"rise": 2048, "picnum": 6})]),
            _store([("island", "island:0", {"rise": 2048, "wears_tile": 6}),
                    ("island", "island:1", {"rise": 2048, "wears_tile": 6})]))
        classes = {found["class"] for found in result["findings"]}
        self.assertEqual(classes, {"field only one side writes"})
        found, = result["findings"]
        self.assertEqual(found["compiler_only"], ["picnum"])
        self.assertEqual(found["readers_only"], ["wears_tile"])
        self.assertEqual(found["both"], ["rise"])
        self.assertEqual(result["predicates"]["island"]["differing_ids"], 0)

    def test_a_shape_difference_does_not_hide_a_content_one(self):
        result = _compare(
            _store([("island", "island:0", {"rise": 2048, "picnum": 6})]),
            _store([("island", "island:0", {"rise": 1024, "wears_tile": 6})]))
        classes = {found["class"] for found in result["findings"]}
        self.assertEqual(classes, {"field only one side writes",
                                   "same id different attrs"})

    def test_a_vocabulary_value_one_side_never_uses_is_an_unknown_kind(self):
        result = _compare(
            _store([("surface_kind", "sector:0", {"kind": "road"})]),
            _store([("surface_kind", "sector:0", {"kind": "facade"})]))
        kinds = [found for found in result["findings"]
                 if found["class"] == "unknown kind"]
        self.assertEqual(len(kinds), 1)
        values = {(row["value"], row["seen_by"]) for row in kinds[0]["values"]}
        self.assertEqual(values, {("facade", "readers only"),
                                  ("road", "compiler only")})

    def test_an_unknown_kind_says_where_the_other_side_does_keep_it(self):
        """The compiler keeps surface kinds in `surface`, the readers in
        `surface_kind`. Both know the word; neither knows it where the other
        looks, and saying so is what stops nine lines reading as nine gaps."""
        result = _compare(
            _store([("surface", "surface:plane", {"kind": "pavement"})]),
            _store([("surface_kind", "sector:0", {"kind": "pavement"})]))
        kinds = {found["predicate"]: found for found in result["findings"]
                 if found["class"] == "unknown kind"}
        row, = kinds["surface_kind"]["values"]
        self.assertEqual(row["value"], "pavement")
        self.assertEqual(row["elsewhere"], ["surface.kind"])

    def test_an_extra_id_on_a_base_predicate_is_reported_but_not_a_gap(self):
        result = _compare(_store([]),
                          _store([("sector", "sector:0", {"floor_z": 0})]),
                          base=frozenset({"sector"}))
        found, = result["findings"]
        self.assertTrue(found["base"])
        self.assertEqual(result["summary"]["recovered_only"], [],
                         "a base predicate the compiler never declares is the "
                         "map's own records, not something it failed to say")
        self.assertEqual(result["summary"]["rows_in_disagreement"], 0)

    def test_two_stores_that_agree_produce_no_findings(self):
        rows = [("island", "island:0", {"rise": 2048})]
        result = _compare(_store(rows), _store(rows))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["rows_in_disagreement"], 0)


class TheCity(unittest.TestCase):
    """The run that is committed, pinned so a reader change cannot move it
    without someone noticing."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.read_facts import recover
        from bloodmap.read_store import BASE_PREDICATES, FactStore
        from tools.symmetry_diff import compare

        try:
            declared = FactStore.read("projects/blood-city/facts")
            found = recover("projects/blood-city/level/slice2-streets.MAP")
        except Exception as error:  # pragma: no cover - environment-dependent
            raise unittest.SkipTest(f"the city is not readable here: {error}")
        cls.result = compare(declared, found["store"],
                             base_predicates=frozenset(BASE_PREDICATES))

    def test_the_two_halves_agree_on_the_join_row_for_every_shared_record(self):
        """924 records, one grammar row each, and not one disagreement.

        This is the strongest thing the diff says. The compiler chose a row
        while building and the readers chose one from the finished geometry,
        and on `a`, `b`, `height`, `frame` and `shows` they agree 924 times.
        """
        row = self.result["predicates"]["join"]
        self.assertEqual(row["same_id"], 924)
        self.assertEqual(row["differing_ids"], 0)

    def test_the_only_content_disagreement_left_is_shade_depth(self):
        attrs = [found for found in self.result["findings"]
                 if found["class"] == "same id different attrs"]
        self.assertEqual([found["predicate"] for found in attrs],
                         ["shade_depth"])
        self.assertEqual(attrs[0]["fields"], {"depth": 143})

    def test_the_reader_reads_every_depth_one_deeper_except_the_lamp_lit_three(self):
        """A lamp sets the reader's base, and one lamp shifts the whole field.

        `read_light.field` elects the base as the lightest shade with area,
        and sectors 35, 54 and 73 carry two lamps each, which puts them at
        shade -4 against the compiler's declared base of 8. So the reader
        reads -4 as depth 0 and everything the compiler calls depth 0 as
        depth 1. This is a reader defect and it is pinned here, not excused.
        """
        from bloodmap.read_facts import recover
        from bloodmap.read_store import FactStore

        declared = {fact.id: fact.to_dict() for fact in
                    FactStore.read("projects/blood-city/facts")["shade_depth"]}
        found = recover("projects/blood-city/level/slice2-streets.MAP")
        recovered = {fact.id: fact.to_dict()
                     for fact in found["store"]["shade_depth"]}
        shared = sorted(set(declared) & set(recovered))
        deeper = [one for one in shared
                  if recovered[one]["depth"] - declared[one]["depth"] == 1]
        same = [one for one in shared
                if recovered[one]["depth"] == declared[one]["depth"]]
        self.assertEqual(len(shared), 146)
        self.assertEqual(len(deeper), 143)
        self.assertEqual(same, ["sector:35", "sector:54", "sector:73"])
        for one in same:
            self.assertEqual(declared[one]["shade"], -4)
            self.assertEqual(declared[one]["depth"], 0)

    def test_the_134_joins_the_compiler_declares_and_no_reader_names(self):
        """The waterfront, on both sides of one number.

        The compiler declares a `join` for every two-sided record; the readers
        emit `join` only where the grammar has a row and `unknown_join` where
        it has none. The 134 missing `join` ids and the 134 recovered
        `unknown_join` ids are the same records.
        """
        self.assertEqual(self.result["predicates"]["join"]["missing_ids"], 134)
        self.assertEqual(
            self.result["predicates"]["unknown_join"]["recovered"], 134)
