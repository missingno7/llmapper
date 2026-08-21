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
    """Every preserved iteration must stay compilable, valid, and deterministic."""

    def test_every_iteration_compiles_deterministically_and_passes_hard_gates(self):
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

        from bloodmap.authoring_loop import attach_review, review_from_dict

        # Later reviews cite corpus-relative scale and shape findings, which only
        # exist when the mined corpora are present.  Those come from the local
        # commercial map set, so this check follows the repo's usual policy and
        # skips rather than pretending the reviews were verified.
        spatial = Path("work/blood.spatial-corpus.json")
        shape = Path("work/blood.shape-corpus.json")
        if not (spatial.is_file() and shape.is_file()):
            self.skipTest("mined spatial/shape corpora are not available locally")

        for iteration in ITERATIONS:
            review_path = Path("projects/reasoned-authoring-v1/design/reviews") / f"{iteration}.json"
            if not review_path.is_file():
                continue
            with self.subTest(iteration=iteration):
                packet = evaluate_candidate(
                    _load(iteration).candidate(),
                    art_directory=Path("reference/blood") if Path("reference/blood").is_dir() else None,
                    spatial_corpus_path=spatial,
                    shape_corpus_path=shape,
                )
                review = review_from_dict(json.loads(review_path.read_text(encoding="utf-8")))
                attach_review(packet, review)
                self.assertTrue(packet.review["claims"])


if __name__ == "__main__":
    unittest.main()
