from __future__ import annotations

import unittest

from bloodmap.decompiler import decompile_level
from bloodmap.planar_layout import PlanarLayout
from bloodmap.structures import KINDS, detect_structures, structure_index
from bloodmap.vocabulary import Anchor, recess, staircase

U = 384
PH = 0x1600
SURFACE = dict(wall_picnum=180, floor_picnum=292, ceiling_picnum=385,
               wall_shade=8, floor_shade=16, ceiling_shade=8)


def _rect(x0, y0, x1, y1):
    return [(x0 * U, y0 * U), (x1 * U, y0 * U), (x1 * U, y1 * U), (x0 * U, y1 * U)]


def _two_room_layout(*, total_rise=4 * 4096, step_rise=4096, ceiling_drop=6 * PH):
    """A lower room, a stair, an upper room, and one niche off the upper room."""
    layout = PlanarLayout(name="structures-fixture", visibility=800)
    floor = 8192
    layout.add_region("region:lower", _rect(0, 0, 12, 12), role="interior",
                      floor_z=floor, ceiling_z=floor - 8 * PH, **SURFACE)
    stairs = staircase(
        layout, "stairs:up",
        base=Anchor("region:lower", (12 * U, 4 * U), (12 * U, 8 * U)),
        total_rise=-total_rise, step_rise=-step_rise, tread=2 * U,
        clear_height=5 * PH, base_floor_z=floor, **SURFACE,
    )
    top = stairs.far
    layout.add_region(
        "region:upper",
        [top.a, (top.a[0] + 10 * U, top.a[1]), (top.a[0] + 10 * U, top.b[1]), top.b],
        role="interior", floor_z=floor - total_rise,
        ceiling_z=floor - total_rise - 10 * PH, **SURFACE,
    )
    stairs.arrive_at("region:upper")
    recess(
        layout, "recess:niche",
        anchor=Anchor("region:upper", (top.a[0] + 7 * U, top.b[1]), (top.a[0] + 5 * U, top.b[1])),
        depth=2 * U, ceiling_drop=ceiling_drop, **SURFACE,
    )
    layout.set_player_start("region:lower", x=6 * U, y=6 * U, z=floor)
    return layout


class StructureRecoveryTests(unittest.TestCase):
    def test_a_generated_staircase_is_recovered_with_its_essential_parameters(self):
        level = _two_room_layout().compile().level

        document = detect_structures(level)

        runs = [item for item in document["structures"] if item["kind"] == "stepped_run"]
        self.assertEqual(len(runs), 1)
        run = runs[0]
        self.assertEqual(run["parameters"]["rises"], 4)
        self.assertEqual(abs(run["parameters"]["total_rise"]), 4 * 4096)
        self.assertEqual(set(abs(value) for value in run["evidence"]["rise_sequence"]), {4096})
        self.assertTrue(run["residual"]["uniform_rise"])
        self.assertEqual(round(run["parameters"]["width"]), 4 * U)

    def test_a_generated_recess_is_recovered_with_the_corpus_defaults_it_was_built_on(self):
        level = _two_room_layout().compile().level

        recesses = [item for item in detect_structures(level)["structures"]
                    if item["kind"] == "recess"]

        self.assertEqual(len(recesses), 1)
        found = recesses[0]
        self.assertEqual(found["parameters"]["floor_delta"], 0)
        self.assertGreater(found["parameters"]["ceiling_delta"], 0)
        self.assertLess(found["parameters"]["depth_ratio"], 0.25)

    def test_a_step_taller_than_the_player_becomes_an_overlook_and_not_a_stair(self):
        layout = PlanarLayout(name="overlook-fixture", visibility=800)
        floor = 8192
        layout.add_region("region:low", _rect(0, 0, 8, 8), role="interior",
                          floor_z=floor, ceiling_z=floor - 8 * PH, **SURFACE)
        layout.add_region("region:high", _rect(8, 0, 14, 8), role="interior",
                          floor_z=floor - 6144, ceiling_z=floor - 6144 - 8 * PH, **SURFACE)
        layout.add_connection("connection:look", "region:low", "region:high",
                              a1=(8 * U, 0), a2=(8 * U, 8 * U), min_width=1536)
        layout.set_player_start("region:low", x=4 * U, y=4 * U, z=floor)

        document = detect_structures(layout.compile().level)

        kinds = {item["kind"] for item in document["structures"]}
        self.assertIn("overlook", kinds)
        self.assertNotIn("stepped_run", kinds)
        overlook = next(item for item in document["structures"] if item["kind"] == "overlook")
        self.assertEqual(overlook["parameters"]["drop"], 6144)

    def test_a_carved_mass_is_recovered_as_an_embedded_shell(self):
        layout = PlanarLayout(name="shell-fixture", visibility=800)
        floor = 8192
        layout.add_region("region:yard", _rect(0, 0, 20, 20), role="exterior",
                          floor_z=floor, ceiling_z=floor - 12 * PH, **SURFACE)
        layout.carve_hole("region:yard", _rect(6, 6, 14, 14))
        layout.add_region("region:block", _rect(6, 6, 14, 14), role="interior",
                          floor_z=floor, ceiling_z=floor - 6 * PH, **SURFACE)
        for name, a1, a2 in (
            ("s", (6, 6), (14, 6)), ("e", (14, 6), (14, 14)),
            ("n", (14, 14), (6, 14)), ("w", (6, 14), (6, 6)),
        ):
            layout.add_connection(
                f"connection:{name}", "region:yard", "region:block",
                a1=(a1[0] * U, a1[1] * U), a2=(a2[0] * U, a2[1] * U), min_width=512,
            )
        layout.set_player_start("region:yard", x=2 * U, y=2 * U, z=floor)

        shells = [item for item in detect_structures(layout.compile().level)["structures"]
                  if item["kind"] == "embedded_shell"]

        self.assertEqual(len(shells), 1)
        self.assertEqual(shells[0]["parameters"]["contained_sectors"], 1)

    def test_detection_is_deterministic_and_indexes_every_claimed_sector(self):
        level = _two_room_layout().compile().level

        first, second = detect_structures(level), detect_structures(level)

        self.assertEqual(first, second)
        index = structure_index(first)
        claimed = {value for item in first["structures"] for value in item["sectors"]}
        self.assertEqual(set(index), claimed)
        self.assertEqual(first["coverage"]["sectors_in_a_structure"], len(claimed))
        self.assertEqual(set(first["coverage"]["by_kind"]), set(KINDS))

    def test_no_structure_reads_an_authored_label(self):
        """The same geometry with different authored roles recovers identically."""
        plain = _two_room_layout().compile().level
        relabelled = _two_room_layout()
        for region in relabelled.regions.values():
            region.role = "gameplay"
            region.intent = {"purpose": "deliberately misleading", "classification": "OPTIONAL"}

        self.assertEqual(
            detect_structures(plain)["structures"],
            detect_structures(relabelled.compile().level)["structures"],
        )


class StructureHierarchyTests(unittest.TestCase):
    def test_the_decompiler_gains_a_structure_layer_between_space_and_sector(self):
        level = _two_room_layout().compile().level

        source = decompile_level(level, source_name="fixture.MAP")

        structures = [item for item in source.hierarchy["nodes"] if item["kind"] == "structure"]
        self.assertTrue(structures)
        for node in structures:
            self.assertIn("structure", node)
            self.assertEqual(node["parent"], "assembly:001")
            self.assertIn(node["id"], source.node("assembly:001")["children"])
        part_of = [item for item in source.hierarchy["relations"] if item["kind"] == "part_of"]
        self.assertTrue(part_of)
        self.assertIn("structure_recovery", source.hierarchy)

    def test_overlooks_stay_relations_rather_than_becoming_a_node_each(self):
        layout = PlanarLayout(name="relation-fixture", visibility=800)
        floor = 8192
        layout.add_region("region:low", _rect(0, 0, 8, 8), role="interior",
                          floor_z=floor, ceiling_z=floor - 8 * PH, **SURFACE)
        layout.add_region("region:high", _rect(8, 0, 14, 8), role="interior",
                          floor_z=floor - 6144, ceiling_z=floor - 6144 - 8 * PH, **SURFACE)
        layout.add_connection("connection:look", "region:low", "region:high",
                              a1=(8 * U, 0), a2=(8 * U, 8 * U), min_width=1536)
        layout.set_player_start("region:low", x=4 * U, y=4 * U, z=floor)

        source = decompile_level(layout.compile().level)

        self.assertFalse([item for item in source.hierarchy["nodes"] if item["kind"] == "structure"])
        self.assertTrue([item for item in source.hierarchy["relations"] if item["kind"] == "overlook"])


class SemanticSourceEditTests(unittest.TestCase):
    def test_one_number_in_the_source_changes_the_independently_derived_hierarchy(self):
        """The claim the whole authoring representation rests on."""
        before = detect_structures(_two_room_layout(total_rise=4 * 4096).compile().level)
        after = detect_structures(_two_room_layout(total_rise=7 * 4096).compile().level)

        before_run = next(item for item in before["structures"] if item["kind"] == "stepped_run")
        after_run = next(item for item in after["structures"] if item["kind"] == "stepped_run")
        self.assertEqual(before_run["parameters"]["rises"], 4)
        self.assertEqual(after_run["parameters"]["rises"], 7)
        self.assertGreater(after["coverage"]["sectors"], before["coverage"]["sectors"])

    def test_changing_only_a_recess_leaves_the_stair_evidence_untouched(self):
        before = detect_structures(_two_room_layout(ceiling_drop=6 * PH).compile().level)
        after = detect_structures(_two_room_layout(ceiling_drop=2 * PH).compile().level)

        self.assertEqual(
            [item for item in before["structures"] if item["kind"] == "stepped_run"],
            [item for item in after["structures"] if item["kind"] == "stepped_run"],
        )
        before_recess = next(item for item in before["structures"] if item["kind"] == "recess")
        after_recess = next(item for item in after["structures"] if item["kind"] == "recess")
        self.assertNotEqual(
            before_recess["parameters"]["ceiling_delta"],
            after_recess["parameters"]["ceiling_delta"],
        )


if __name__ == "__main__":
    unittest.main()
