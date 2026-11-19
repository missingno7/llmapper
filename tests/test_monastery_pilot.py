from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from bloodmap.authoring_loop import blocking_failures, evaluate_candidate
from bloodmap.format import encode_map

LEVEL_DIR = Path("projects/reasoned-authoring-v1/level")
ITERATIONS = ("v0", "v1", "v2", "v3")


def _load(iteration: str):
    path = LEVEL_DIR / f"candidate_{iteration}.py"
    spec = importlib.util.spec_from_file_location(f"pilot_{iteration}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(LEVEL_DIR.is_dir(), "pilot project is not present")
class MonasteryPilotTests(unittest.TestCase):
    """Current early candidates v0-v3 must remain valid and deterministic; archive bindings cover all six historical versions."""

    def test_current_early_candidates_compile_deterministically_and_pass_hard_gates(self):
        for iteration in ITERATIONS:
            with self.subTest(iteration=iteration):
                module = _load(iteration)
                first = encode_map(module.make_layout().compile().level.to_disk_map())
                second = encode_map(module.make_layout().compile().level.to_disk_map())
                self.assertEqual(first, second, "compile is not byte-deterministic")

                packet = evaluate_candidate(module.candidate())
                self.assertEqual(blocking_failures(packet.hard_gates), [])
                self.assertTrue(packet.promotable)
                self.assertEqual(packet.identity["iteration_id"], iteration)

    def test_the_pilot_became_more_structured_across_iterations(self):
        v0 = evaluate_candidate(_load("v0").candidate())
        v3 = evaluate_candidate(_load("v3").candidate())

        # v0 collapsed three authored assemblies into one derived space; v3 does not.
        self.assertTrue(v0.hierarchy_comparison["discrepancies"])
        self.assertEqual(v3.hierarchy_comparison["discrepancies"], [])
        self.assertGreater(
            v3.independent_hierarchy["counts"]["spaces"],
            v0.independent_hierarchy["counts"]["spaces"],
        )
        # v0 finished three assemblies identically; v3 leaves only the intended pair.
        self.assertGreater(
            len(v0.art_evidence["identical_room_treatments"]),
            len(v3.art_evidence["identical_room_treatments"]),
        )
        self.assertGreater(
            v3.art_evidence["decorative_distribution"]["total_space_sprites"],
            v0.art_evidence["decorative_distribution"]["total_space_sprites"],
        )

    def test_reviews_reference_only_evidence_that_exists(self):
        import json

        from bloodmap.authoring_loop import AuthoringIteration, attach_review, review_from_dict

        # Reviews belong to saved packets, never to a current recompilation.
        for iteration in ("v0", "v1", "v2", "v3", "v4", "v5"):
            with self.subTest(iteration=iteration):
                root = Path("projects/reasoned-authoring-v1")
                packet = AuthoringIteration.from_dict(json.loads(
                    (root / "reports" / iteration / "iteration.json").read_text(encoding="utf-8")))
                review = review_from_dict(json.loads(
                    (root / "design/reviews" / f"{iteration}.json").read_text(encoding="utf-8")))
                attach_review(packet, review)
                self.assertTrue(packet.review["claims"])



if __name__ == "__main__":
    unittest.main()
