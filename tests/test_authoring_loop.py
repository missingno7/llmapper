from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from bloodmap.authoring_loop import (
    AuthoredAssembly,
    AuthoredIntent,
    AuthoredTransition,
    AuthoringIteration,
    AuthoringLoopError,
    Candidate,
    NextAction,
    ProbeRequest,
    ReasoningReview,
    ReviewClaim,
    attach_review,
    blocking_failures,
    compare_iterations,
    compile_candidate,
    evaluate_candidate,
    packet_evidence_refs,
    record_review,
    resolve_evidence,
    review_from_dict,
)
from bloodmap.format import encode_map, read_map
from bloodmap.planar_layout import PlanarLayout
from bloodmap.viewpoints import (
    ViewpointError,
    ViewpointSpec,
    apply_viewpoint,
    prepare_viewpoints,
    resolve_viewpoint,
    start_marker_sprites,
    viewpoint_manifest,
    viewpoint_variant_diff,
)
from bloodmap.workspace import initialize_project

U = 384
PH = 0x1600
FLOOR = 8192


def _p(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))


def _r(x0, y0, x1, y1):
    return [_p(x0, y0), _p(x1, y0), _p(x1, y1), _p(x0, y1)]


def _layout(*, with_exit: bool) -> PlanarLayout:
    """Two rooms joined by a tight neck; the exit switch is optional."""
    layout = PlanarLayout(name="fixture", visibility=800)
    layout.add_region(
        "region:hall", _r(0, 3, 12, 7), role="start",
        ceiling_z=FLOOR - 4 * PH, floor_z=FLOOR,
        floor_shade=30, ceiling_shade=30, wall_shade=28,
    )
    layout.add_region(
        "region:yard", _r(12, -6, 30, 16), role="exterior",
        ceiling_z=FLOOR - 12 * PH, floor_z=FLOOR, parallax_ceiling=True,
        floor_picnum=294, wall_picnum=181,
        floor_shade=4, ceiling_shade=0, wall_shade=2,
    )
    layout.add_connection(
        "connection:hall_yard", "region:hall", "region:yard",
        a1=_p(12, 3), a2=_p(12, 7), min_width=1024,
    )
    start = _p(6, 5)
    layout.set_player_start("region:hall", x=start[0], y=start[1], z=FLOOR - 1024, angle=0)
    layout.add_sprite(
        "sp_start", "region:hall", x=start[0], y=start[1], z=FLOOR - 1024,
        type=1, picnum=2528, cstat=128, x_repeat=64, y_repeat=64, behavior={"state": 1},
    )
    if with_exit:
        layout.place_on_wall(
            "sw_exit", "region:yard", a1=_p(30, -6), a2=_p(30, 16), t=0.5,
            height_player_heights=2.18, offset_player_widths=0.12,
            type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8,
            behavior={"tx_id": 4, "command": 1, "trigger_on": 1, "trigger_push": 1},
        )
    return layout


def _intent() -> AuthoredIntent:
    return AuthoredIntent(
        brief="a hall opening onto a yard",
        start_region="region:hall",
        exit_region="region:yard",
        assemblies=(
            AuthoredAssembly("assembly:hall", "hall", "arrival", "the covered start",
                             ("region:hall",)),
            AuthoredAssembly("assembly:yard", "yard", "exterior_parent", "the open yard",
                             ("region:yard",)),
        ),
        transitions=(
            AuthoredTransition("transition:reveal", "hall into yard", "region:hall",
                               "region:yard", "constrained_to_open", "release into the open",
                               connection_id="connection:hall_yard"),
        ),
    )


def _candidate(*, with_exit: bool = True, iteration_id: str = "fixture-v0") -> Candidate:
    return Candidate(
        iteration_id=iteration_id,
        module="tests/test_authoring_loop.py",
        factory=lambda: _layout(with_exit=with_exit),
        intent=_intent(),
        probes=(
            ProbeRequest("probe:reach_yard", "access", "is the yard reachable?",
                         "the yard is mandatory", target_region="region:yard"),
            ProbeRequest("probe:reveal", "transition", "does the neck release?",
                         "the brief asks for one release",
                         source_region="region:hall", destination_region="region:yard"),
        ),
        viewpoints=(
            ViewpointSpec("view:hall", "player_start", "region:hall",
                          *_p(6, 5), FLOOR - 1024, 0),
            ViewpointSpec("view:yard", "assembly_center", "region:yard",
                          *_p(20, 5), FLOOR - 1024, 1024),
        ),
        declared_changes=("fixture",),
    )


class ViewpointTests(unittest.TestCase):
    def test_variant_changes_only_the_player_start_pose(self):
        compiled = _layout(with_exit=True).compile()
        level = compiled.level
        allocations = {key: value.sector_id for key, value in compiled.allocations.items()}
        spec = ViewpointSpec("view:yard", "assembly_center", "region:yard",
                             *_p(20, 5), FLOOR - 1024, 1024)

        resolved = resolve_viewpoint(level, spec, allocations=allocations)
        variant = apply_viewpoint(level, resolved)
        diff = viewpoint_variant_diff(level, variant)

        self.assertTrue(diff["variant_is_pose_only"])
        self.assertEqual(diff["unexpected_changes"], [])
        self.assertTrue(diff["player_start_changed"])
        self.assertEqual(diff["player_start_markers_moved"], start_marker_sprites(level))
        # The candidate itself is untouched and the geometry is byte-identical.
        self.assertEqual(level.to_dict()["sectors"], variant.to_dict()["sectors"])
        self.assertEqual(level.to_dict()["walls"], variant.to_dict()["walls"])
        self.assertNotEqual(
            encode_map(level.to_disk_map()), encode_map(variant.to_disk_map()),
        )
        self.assertEqual(variant.player_start["sector"], allocations["region:yard"])

    def test_pose_outside_its_region_is_refused(self):
        compiled = _layout(with_exit=True).compile()
        allocations = {key: value.sector_id for key, value in compiled.allocations.items()}
        spec = ViewpointSpec("view:bad", "assembly_center", "region:hall",
                             *_p(20, 5), FLOOR - 1024, 0)

        with self.assertRaisesRegex(ViewpointError, "not inside sector"):
            resolve_viewpoint(compiled.level, spec, allocations=allocations)

    def test_manifest_is_deterministic_without_any_engine(self):
        compiled = _layout(with_exit=True).compile()
        allocations = {key: value.sector_id for key, value in compiled.allocations.items()}
        specs = _candidate().viewpoints

        first = viewpoint_manifest(compiled.level, specs, allocations=allocations, map_sha256="abc")
        second = viewpoint_manifest(compiled.level, specs, allocations=allocations, map_sha256="abc")

        self.assertEqual(first, second)
        self.assertEqual(len(first["viewpoints"]), 2)
        self.assertTrue(all(item["variant_is_pose_only"] for item in first["viewpoints"]))
        self.assertEqual(
            len(prepare_viewpoints(compiled.level, specs, allocations=allocations)), 2,
        )


class AuthoringIterationTests(unittest.TestCase):
    def test_candidate_compilation_is_deterministic(self):
        _compiled, first, deterministic = compile_candidate(_candidate())
        _again, second, _ = compile_candidate(_candidate())

        self.assertTrue(deterministic)
        self.assertEqual(first, second)

    def test_valid_candidate_produces_a_deterministic_packet(self):
        first = evaluate_candidate(_candidate()).to_dict()
        second = evaluate_candidate(_candidate()).to_dict()

        self.assertEqual(first, second)
        self.assertEqual(first["$schema"], "llmapper.authoring-iteration")
        self.assertEqual(
            AuthoringIteration.from_dict(json.loads(json.dumps(first))).to_dict(), first,
        )
        self.assertTrue(first["identity"]["deterministic_compile"])

    def test_invalid_candidate_fails_hard_gates_and_skips_engine_capture(self):
        packet = evaluate_candidate(
            _candidate(with_exit=False),
            engine={"nblood": "does-not-exist.exe", "game_dir": "."},
        )

        self.assertIn("exit_reachable", blocking_failures(packet.hard_gates))
        self.assertFalse(packet.promotable)
        self.assertEqual(packet.render["capture_status"], "skipped")
        self.assertIsNone(packet.render["captures"])
        smoke = next(
            item for item in packet.hard_gates if item["gate_id"] == "nblood_load_smoke"
        )
        self.assertEqual(smoke["status"], "skipped")
        self.assertIn("structural gates failed first", smoke["detail"])

    def test_packet_reports_independent_analysis_not_authored_labels(self):
        packet = evaluate_candidate(_candidate())
        document = packet.to_dict()

        # Authored role words appear in intent and nowhere in the derived hierarchy.
        self.assertIn("exterior_parent", json.dumps(document["authored_intent"]))
        self.assertNotIn("exterior_parent", json.dumps(document["independent_hierarchy"]))
        derived = document["independent_hierarchy"]
        self.assertEqual(
            derived["basis"],
            "bloodmap.decompiler.decompile_level over the compiled candidate only",
        )
        self.assertGreaterEqual(derived["counts"]["spaces"], 1)
        # The comparison names the authored side and the derived side separately.
        row = document["hierarchy_comparison"]["assemblies"][0]
        self.assertIn("authored_regions", row)
        self.assertIn("derived_spaces", row)

    def test_every_evidence_reference_the_packet_emits_resolves(self):
        packet = evaluate_candidate(_candidate())

        refs = packet_evidence_refs(packet)
        self.assertTrue(refs)
        for ref in refs:
            resolved = resolve_evidence(packet, ref)
            self.assertEqual(resolved["ref"], ref)
            self.assertTrue(resolved["object"])

    def test_evidence_resolves_across_every_namespace(self):
        packet = evaluate_candidate(_candidate())

        for ref, kind in (
            ("gate:native_structure_valid", "hard_gate"),
            ("probe:reach_yard", "design_probe"),
            ("view:hall", "declared_viewpoint"),
            ("intent:assembly:yard", "authored_assembly"),
            ("transition:transition:reveal", "authored_transition"),
            ("authored:region:yard", "authored_region"),
            ("source:sector:0", "source_sector"),
        ):
            self.assertEqual(resolve_evidence(packet, ref)["kind"], kind, ref)
        with self.assertRaises(AuthoringLoopError):
            resolve_evidence(packet, "gate:no_such_gate")
        with self.assertRaises(AuthoringLoopError):
            resolve_evidence(packet, "nonsense:thing")

    def test_review_requires_resolvable_evidence(self):
        packet = evaluate_candidate(_candidate())
        good = ReasoningReview(
            reviewer="test", iteration_id="fixture-v0",
            claims=(ReviewClaim("the yard is reachable", "supported", ("probe:reach_yard",)),),
            next_actions=(NextAction("keep it", "no change", ("gate:exit_reachable",)),),
        )

        attach_review(packet, good)
        self.assertEqual(packet.review["claims"][0]["status"], "supported")

        with self.assertRaises(AuthoringLoopError):
            attach_review(packet, ReasoningReview(
                reviewer="test", iteration_id="fixture-v0",
                claims=(ReviewClaim("bogus", "supported", ("probe:does_not_exist",)),),
            ))
        with self.assertRaises(AuthoringLoopError):
            attach_review(packet, ReasoningReview(
                reviewer="test", iteration_id="other-id",
                claims=(ReviewClaim("x", "supported", ("probe:reach_yard",)),),
            ))
        with self.assertRaises(AuthoringLoopError):
            attach_review(packet, ReasoningReview(
                reviewer="test", iteration_id="fixture-v0",
                claims=(ReviewClaim("x", "supported", ()),),
            ))

    def test_review_round_trips_through_data(self):
        packet = evaluate_candidate(_candidate())
        payload = {
            "reviewer": "test", "iteration_id": "fixture-v0",
            "claims": [{"claim": "reachable", "status": "supported",
                        "evidence": ["probe:reach_yard"], "reasoning": "the probe passed"}],
            "accepted_strengths": ["structure is fine"],
            "problems": ["undecorated"],
            "next_actions": [{"action": "decorate", "expected_effect": "fewer empty spaces",
                              "evidence": ["gate:exit_reachable"]}],
            "uncertainties": ["nothing here measures play"],
        }

        review = review_from_dict(payload)
        attach_review(packet, review)

        self.assertEqual(review.to_dict()["$schema"], "llmapper.authoring-review")
        self.assertEqual(packet.review["next_actions"][0]["action"], "decorate")

    def test_workspace_records_stay_replayable(self):
        packet = evaluate_candidate(_candidate())
        review = review_from_dict({
            "reviewer": "test", "iteration_id": "fixture-v0",
            "claims": [{"claim": "reachable", "status": "supported",
                        "evidence": ["probe:reach_yard"]}],
            "next_actions": [{"action": "decorate", "expected_effect": "fewer empty spaces",
                              "evidence": ["gate:exit_reachable"]}],
        })
        attach_review(packet, review)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            initialize_project(root, name="fixture")
            written = record_review(root, packet, review)

            self.assertEqual(len(written["decisions"]), 1)
            self.assertEqual(len(written["episodes"]), 1)
            decisions = [
                json.loads(line)
                for line in (root / "design" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            episodes = [
                json.loads(line)
                for line in (root / "memory" / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(decisions[0]["decision"], "decorate")
            self.assertEqual(decisions[0]["evidence"], ["gate:exit_reachable"])
            self.assertEqual(episodes[0]["observed"]["map_sha256"], packet.identity["map_sha256"])
            self.assertEqual(episodes[0]["$schema"], "bloodmap.design-episode")

    def test_written_map_matches_the_hash_the_packet_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.MAP"
            packet = evaluate_candidate(_candidate(), map_path=path)

            reparsed = read_map(path)
            self.assertEqual(len(reparsed.sectors), packet.identity["counts"]["sectors"])
            self.assertEqual(path.stat().st_size, packet.identity["map_bytes"])

    def test_comparison_keeps_dimensions_separate(self):
        first = evaluate_candidate(_candidate(iteration_id="a"))
        second = evaluate_candidate(_candidate(iteration_id="b"))

        report = compare_iterations([first, second])

        self.assertEqual(report["$schema"], "llmapper.authoring-comparison")
        self.assertEqual(len(report["iterations"]), 2)
        row = report["iterations"][0]
        for key in (
            "hard_validation", "authored_vs_observed_hierarchy", "singleton_spaces",
            "route_structure", "transition_evidence", "major_space_scale",
            "art_differentiation", "decorative_distribution", "nblood_load",
        ):
            self.assertIn(key, row)
        # No aggregate score anywhere in the document.
        text = json.dumps(report)
        self.assertNotIn("quality_score", text)
        self.assertNotIn("overall_score", text)


class CorpusEvidenceTests(unittest.TestCase):
    def test_scale_and_shape_sections_degrade_honestly_without_corpora(self):
        packet = evaluate_candidate(_candidate())

        scale = packet.corpus_scale
        self.assertIsNone(scale["spatial_corpus"])
        self.assertEqual(scale["shape"]["status"], "no shape corpus supplied")
        self.assertEqual(scale["findings"], [])
        # Player-relative numbers are still reported; only the percentiles are absent.
        self.assertTrue(scale["spaces"])
        for row in scale["spaces"]:
            self.assertIsNone(row["height_percentile_vs_same_size_corpus_sectors"])
            self.assertIsNotNone(row["footprint_player_areas"])

    def test_shape_comparison_flags_a_pure_grid(self):
        from bloodmap.morphology import mine_shape_corpus, shape_signature

        build = _layout(with_exit=True).compile().level.to_disk_map().to_build_ir()
        corpus = mine_shape_corpus([("fixture", build)])

        self.assertEqual(len(corpus["maps"]), 1)
        signature = shape_signature(build)
        self.assertEqual(signature["orthogonal_length_fraction"], 1.0)
        self.assertEqual(signature["diagonal_length_fraction"], 0.0)
        for key in corpus["samples"]:
            self.assertEqual(len(corpus["samples"][key]), 1)

    def test_sprite_scale_reports_unavailable_without_art(self):
        packet = evaluate_candidate(_candidate())

        sprite_scale = packet.art_evidence["sprite_scale"]
        self.assertEqual(sprite_scale["status"], "unavailable")
        self.assertEqual(sprite_scale["findings"], [])


@unittest.skipUnless(os.name == "nt", "the NBlood viewpoint capture requires Windows")
class ViewpointCaptureEnvironmentTests(unittest.TestCase):
    def test_capture_is_skipped_honestly_when_nblood_is_absent(self):
        packet = evaluate_candidate(
            _candidate(),
            engine={"nblood": "no-such-nblood.exe", "game_dir": "."},
        )

        # An absent engine is never allowed to look like a pass.
        smoke = next(item for item in packet.hard_gates if item["gate_id"] == "nblood_load_smoke")
        self.assertEqual(smoke["status"], "skipped")
        self.assertIn(packet.render["capture_status"], {"unavailable", "skipped"})
        self.assertIsNone(packet.render["captures"])


if __name__ == "__main__":
    unittest.main()
