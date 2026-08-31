"""Decompiling a level into mechanisms rather than into shape.

The claim under test: closing over the objects bound to a moving sector, naming
each by the part it plays, and recording the relations *between* them recovers
the facts that were previously found one at a time by playing the level.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v5.MAP"


def have_campaign() -> bool:
    return bool([
        p for p in glob.glob(str(MAPS / "*.MAP"))
        if re.match(r"^E[1-46]M[1-9]$", Path(p).stem.upper())
    ])


class RoleTests(unittest.TestCase):
    def test_a_carried_sprite_keeps_what_it_is_in_its_role(self):
        """"carried" alone grouped gate leaves with exploder charges.

        Their modal fields then described neither, and the template asserted a
        gate leaf should be picnum 908 at x_repeat 4 -- which is a bomb.
        """
        from bloodmap.assembly import sprite_role

        class FakeSprite:
            def __init__(self, **kw):
                self.fields = {"type": 0, "picnum": 1044, "cstat": 0, "status": 0}
                self.fields.update(kw)

        self.assertEqual(
            sprite_role(None, FakeSprite(cstat=8192)), "carried_with_panel")
        self.assertEqual(
            sprite_role(None, FakeSprite(cstat=16384)), "carried_against_panel")
        self.assertEqual(
            sprite_role(None, FakeSprite(cstat=16384, type=459)),
            "carried_against_thing_459")


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class GateTemplateTests(unittest.TestCase):
    """The template must recover what was learned by hand, without being told."""

    @classmethod
    def setUpClass(cls):
        from tools.mine_assemblies import build_template, instances

        cls.found = instances(str(MAPS), 614)
        cls.template = build_template(cls.found)

    def test_it_finds_the_gate_in_every_map_that_has_one(self):
        self.assertGreater(self.template["instances"], 250)
        self.assertGreater(self.template["maps"], 30)

    def test_the_markers_are_recovered(self):
        """Both at angle 0, cstat 32896, tile 3997, statnum 10.

        Every one of these was derived by hand in an earlier pass, from separate
        queries. The extractor states them together because they belong to one
        object.
        """
        for role in ("marker_off", "marker_on"):
            spec = self.template["roles"][role]
            self.assertGreaterEqual(spec["per_assembly"], 0.9)
            self.assertEqual(spec["fields"]["angle"]["value"], 0)
            self.assertEqual(spec["fields"]["cstat"]["value"], 32896)
            self.assertEqual(spec["fields"]["picnum"]["value"], 3997)
            self.assertEqual(spec["fields"]["status"]["value"], 10)

    def test_state_and_busy_are_recovered_as_one_fact(self):
        """A relation of the whole assembly, not a field of the sector."""
        whole = self.template["assembly_relations"]["state_busy"]
        self.assertEqual(whole["modal"], (0, 0))
        self.assertIn((1, 65536), whole["seen"])
        # and nothing else: the two are one fact written twice
        self.assertEqual(set(whole["seen"]), {(0, 0), (1, 65536)})

    def test_a_leaf_is_judged_by_ratio_not_by_size(self):
        """`width_over_travel` is in the template; raw x_repeat is not judged.

        A gate leaf in a narrow doorway must be narrower than one in a wide
        doorway, so the absolute is not comparable across maps.
        """
        from tools.mine_assemblies import COVERED_BY_RELATION

        self.assertIn("x_repeat", COVERED_BY_RELATION)
        panel = self.template["roles"].get("carried_against_panel")
        self.assertIsNotNone(panel)
        self.assertIn("width_over_travel", panel["relations"])


@unittest.skipUnless(have_campaign(), "no Blood campaign maps")
class TemplateSerializationTests(unittest.TestCase):
    """A template nobody can write down is a template nobody can review.

    A distribution here is keyed by the measured value, and a measured value
    is sometimes a pair. `json.dumps(default=str)` rescues values and never
    keys, so every `-o` run of this miner raised TypeError and no root type
    could be written to disk at all.
    """

    def test_a_tuple_key_survives_being_written_out(self):
        import json

        from tools.mine_assemblies import jsonable

        template = {"assembly_relations": {
            "state_busy": {"modal": (0, 0),
                           "seen": {(0, 0): 0.99, (1, 65536): 0.01}}}}
        text = json.dumps(jsonable(template), indent=1, default=str)
        seen = json.loads(text)["assembly_relations"]["state_busy"]["seen"]
        self.assertEqual(seen, {"(0, 0)": 0.99, "(1, 65536)": 0.01})

    def test_the_in_memory_template_keeps_the_pair_as_a_pair(self):
        """The conversion belongs at the boundary: `check` and these tests
        read `seen[(0, 0)]`, and a tuple is the honest key for a fact that is
        a pair.
        """
        from tools.mine_assemblies import jsonable

        template = {"seen": {(0, 0): 1.0}}
        jsonable(template)
        self.assertEqual(set(template["seen"]), {(0, 0)})

    def test_string_keys_are_left_alone(self):
        from tools.mine_assemblies import jsonable

        self.assertEqual(jsonable({"roles": {"marker_off": 1}}),
                         {"roles": {"marker_off": 1}})

    def test_it_reaches_keys_nested_under_lists(self):
        from tools.mine_assemblies import jsonable

        self.assertEqual(jsonable({"shapes": [{"roles": {(1, 2): 3}}]}),
                         {"shapes": [{"roles": {"(1, 2)": 3}}]})

    def test_the_o_flag_actually_writes_a_file(self):
        """The defect was in main(), not in the converter, so this runs it.

        Every `-o` invocation of this miner raised TypeError before the fix,
        for every root type.
        """
        import json
        import tempfile

        from tools.mine_assemblies import main

        if not have_campaign():
            self.skipTest("the campaign population is not present")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "template.json"
            code = main(["--root", "614", "-o", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists(), "-o wrote nothing")
            template = json.loads(out.read_text(encoding="utf-8"))
            self.assertGreater(template["instances"], 250)
            self.assertIn("(0, 0)", template["assembly_relations"]["state_busy"]["seen"])

    def test_the_real_template_writes_and_reads_back(self):
        import json

        from tools.mine_assemblies import build_template, instances, jsonable

        if not have_campaign():
            self.skipTest("the campaign population is not present")
        template = build_template(instances(str(MAPS), 614))
        again = json.loads(json.dumps(jsonable(template), indent=1, default=str))
        self.assertEqual(again["instances"], template["instances"])
        self.assertEqual(again["maps"], template["maps"])


class SampleSizeTests(unittest.TestCase):
    def test_a_role_seen_once_states_nothing(self):
        """Exactly one campaign sludge sector has a switch in it.

        The first version of the template reported that switch's picnum, type
        and cstat as 100% conventions and failed this level for using another
        switch. A share means nothing without a denominator.
        """
        from tools.mine_assemblies import MIN_OBSERVATIONS, build_template, instances

        template = build_template(instances(str(MAPS), 618))
        switch = template["roles"].get("switch")
        self.assertIsNotNone(switch)
        self.assertLess(switch["instances"], MIN_OBSERVATIONS)
        self.assertFalse(switch["settled"])
        self.assertEqual(switch["fields"], {})


@unittest.skipUnless(have_campaign() and CANDIDATE.exists(), "no built candidate")
class CandidateAgreesTests(unittest.TestCase):
    def test_the_levels_doors_and_rotating_panel_match_their_templates(self):
        from bloodmap.assembly import assembly_around
        from bloodmap.format import read_map
        from tools.mine_assemblies import build_template, check, instances

        disk = read_map(CANDIDATE)
        for root in (600, 617):
            template = build_template(instances(str(MAPS), root))
            mine = [
                assembly_around(disk, index)
                for index, sector in enumerate(disk.sectors)
                if int(sector.fields["type"]) == root and sector.extra is not None
            ]
            self.assertTrue(mine, f"no instances of type {root}")
            self.assertEqual(check(mine, template), [], f"type {root} disagrees")


if __name__ == "__main__":
    unittest.main()
