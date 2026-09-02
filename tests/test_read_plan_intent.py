"""The plan recovered from E3M1, and the names it does and does not earn.

Layer 7 is decisions section 20's acid test -- "recover a city's street graph,
islands, blocks and envelopes from an original" -- and layer 8 is E2M3's
refusal rule applied to a second map. Both are easy to make look good by
loosening a threshold, so the tests pin the thresholds' consequences rather
than the thresholds.
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


class ThePlan(unittest.TestCase):
    def setUp(self):
        from bloodmap.read_plan import read_plan

        self.level = _e3m1().to_level_ir()
        self.plan = read_plan(self.level)

    def test_no_build_unit_leaves_the_reader(self):
        """The layer contract: no picnums, no z, no Build units. One stated
        conversion, and everything else in plan units.

        Checked on the KEYS and the magnitudes, not on the text: a sector id
        of 352 is not tile 352, and a substring test cannot tell them apart.
        A Build extent is thousands of units and a plan extent is tens, so a
        number over 200 in an extent field is a Build unit that escaped.
        """
        from bloodmap.read_plan import PLAN_UNIT

        self.assertEqual(PLAN_UNIT, 1024)
        forbidden = ("picnum", "floor_z", "ceiling_z", "tile", "shade",
                     "cstat", "x_panning")

        def walk(value, path=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, forbidden,
                                     f"{path}.{key} is a Build field")
                    walk(item, f"{path}.{key}")
            elif isinstance(value, list):
                for item in value:
                    walk(item, path)
            elif isinstance(value, (int, float)) and path.endswith("_pu"):
                self.assertLess(abs(value), 200,
                                f"{path} = {value} is a Build unit, not a "
                                f"plan unit")

        walk({key: value for key, value in self.plan.items()
              if key not in ("plan_unit_build", "ground_shapes")})

    def test_the_main_street_is_an_avenue_by_carriageway_and_by_full_width(self):
        main = self.plan["corridors"][0]
        self.assertEqual(main["sectors"], [8])
        self.assertEqual(main["carriageway_pu"], 7.28)
        self.assertEqual(main["carriageway_class"]["nearest"], "avenue")
        self.assertEqual(main["full_width_pu"], 10.78)

    def test_the_pavement_bands_come_back_at_the_measured_widths(self):
        """Section 1 lists E3M1's bands as 1024, 2048, 2560 and 512 Build
        units. The reader gives 1.0, 2.0 and 2.5 plan units on the main
        street, off the geometry."""
        main = self.plan["corridors"][0]
        self.assertEqual(sorted([main["flanks"]["band_low_pu"],
                                 main["flanks"]["band_high_pu"]]), [1.0, 2.5])

    def test_a_place_a_street_runs_along_is_not_a_band(self):
        """s175 is 18 by 17 plan units and runs the whole length of two
        corridors. Counted as a band it made both of them 23 pu wide."""
        touched = [row for run in self.plan["corridors"]
                   for row in run["flanks"]["touched_but_not_a_band"]]
        self.assertTrue(any(row["sector"] == 175 for row in touched))

    def test_an_ambiguous_piece_of_road_is_a_candidate_not_a_decision(self):
        road = [row for row in self.plan["candidates"]
                if row.get("sectors") == [7]]
        self.assertEqual(len(road), 1)
        self.assertEqual(sorted(road[0]["readings"]), ["edge", "junction"])

    def test_a_sector_two_streets_reach_at_once_is_a_candidate_too(self):
        """Item 30b: a mass is cut at its street frontages by a walk from
        each, and a sector both walks reach in the same step is not assigned
        by tie-break. Which building a shared back room belongs to is not a
        reader's to decide quietly."""
        shared = [row for row in self.plan["candidates"]
                  if str(row.get("about", "")).startswith("sector:")]
        self.assertTrue(shared)
        for row in shared:
            self.assertGreater(len(row["readings"]), 1)

    def test_a_block_is_cut_at_its_street_frontages(self):
        """E3M1's largest interior mass is 123 sectors -- a whole side of the
        city, because its buildings run together through their interiors.
        `city_plan`'s block is one buildable rectangle, so the mass is cut."""
        big = [row for row in self.plan["blocks"] if row["mass_sectors"] == 123]
        self.assertGreater(len(big), 1, "the 123-sector mass was left whole")
        self.assertEqual(sum(len(row["sectors"]) for row in big), 123)
        self.assertEqual(len({row["fronts"] for row in big}), len(big))

    def test_the_schematic_costs_something_and_the_reader_says_how_much(self):
        """Every plan element is a rect and a sector is not."""
        fill = self.plan["rectangular_fill"]
        self.assertLess(fill["median"], 1.0)
        self.assertLess(fill["worst"], 0.5)


class TheNames(unittest.TestCase):
    def test_a_mechanism_is_named_by_the_course_that_teaches_its_type(self):
        """`DOOR-SWINGING.map` teaching type 617 is Blood's own name for a
        617, counted rather than chosen by us."""
        from bloodmap.read_intent import name_mechanisms

        index = {617: {"lessons": ["DOOR-SWINGING.map"], "constructs": 3,
                       "shapes": {"the whole sector travels": 3},
                       "slots": {}, "lessons_by_shape": {
                           "the whole sector travels": {
                               "DOOR-SWINGING.map": 3}}}}
        result = name_mechanisms(
            [{"id": "sentence:sector:44", "type": 617,
              "shape": "the whole sector travels"}], index)
        self.assertEqual(result["named"][0]["name"], "door")
        self.assertEqual(result["named"][0]["share"], 1.0)

    def test_no_majority_is_a_candidate_rather_than_a_coin_toss(self):
        from bloodmap.read_intent import name_mechanisms

        index = {600: {"lessons": ["DOOR-A.map", "MACHINERY-B.map"],
                       "constructs": 2, "shapes": {}, "slots": {},
                       "lessons_by_shape": {"(no shape)": {
                           "DOOR-A.map": 1, "MACHINERY-B.map": 1}}}}
        result = name_mechanisms(
            [{"id": "sentence:sector:1", "type": 600, "shape": ""}], index)
        self.assertEqual(result["named"], [])
        self.assertEqual(len(result["candidates"]), 1)

    def test_two_firing_rules_is_a_candidate_and_none_is_a_refusal(self):
        from bloodmap.read_intent import name_places

        level = _e3m1().to_level_ir()
        spaces = [{"id": "a", "sectors": [3]},        # on the street
                  {"id": "b", "sectors": [200]},      # nothing fires
                  {"id": "c", "sectors": [3, 18]}]    # street? no; a stair
        result = name_places(level, spaces, street=[3],
                             structures={"structure:stepped_run:001": [18]})
        self.assertEqual([row["space"] for row in result["named"]], ["a", "c"])
        self.assertEqual([row["space"] for row in result["refused"]], ["b"])

    def test_e3m1_refuses_most_of_its_places_as_e2m3_did(self):
        """E2M3 named 8 of 340. A reader that names everything has stopped
        measuring and started labelling."""
        import json

        from bloodmap.curriculum import mine_map
        from bloodmap.patterns import corpus_map_path
        from bloodmap.read_intent import name_mechanisms, summary
        from bloodmap.read_mechanisms import curriculum_index, read_mechanisms

        path = corpus_map_path("E3M1")
        disk = _e3m1()
        level = disk.to_level_ir()
        lessons = corpus_map_path("E1M1").parent.parent / "mechanism" / "Vanilla"
        if not lessons.exists():
            raise unittest.SkipTest("the taught course is not in the corpus")
        mechanisms = read_mechanisms(level, disk, lessons=lessons,
                                     reading=mine_map(path))
        names = name_mechanisms(mechanisms["sentences"],
                                curriculum_index(lessons))
        self.assertGreater(len(names["refused"]), len(names["named"]))
        self.assertTrue(all(row["name"] == "door" for row in names["named"]))


if __name__ == "__main__":
    unittest.main()
