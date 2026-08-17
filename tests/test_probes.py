"""Focused tests for Design Probe semantics.

Tests cover:
    - simple reachable path
    - locked path
    - key unlock
    - vertical clearance failure
    - lift-enabled path
    - teleporter/water transition
    - state-dependent revisit
    - branching/escape options
"""

from __future__ import annotations

import unittest

from bloodmap.build_ir import BuildIR
from bloodmap.counterfactual import evaluate_candidates
from bloodmap.design_contract import (
    DesignContract,
    HardAssertion,
    SoftEvidenceQuestion,
    evaluate_contract,
)
from bloodmap import probes  # noqa: F401 - import triggers @register_probe
from bloodmap.probe_schema import (
    DesignProbe,
    Evidence,
    ProbeResult,
    run_probe,
)
from bloodmap.state_model import (
    PlayerKnowledge,
    PlayerState,
    WorldState,
)
from tests.fixtures import (
    fixture_branching_escape,
    fixture_key_unlock,
    fixture_lift_enabled_path,
    fixture_locked_path,
    fixture_simple_reachable,
    fixture_teleporter_transition,
    fixture_vertical_clearance_failure,
)


def _to_build(disk) -> BuildIR:
    return disk.to_build_ir()


class TestSimpleReachable(unittest.TestCase):
    def test_access_probe_finds_reachable_path(self):
        build = _to_build(fixture_simple_reachable())
        probe = DesignProbe(
            probe_type="access",
            question="Can the player reach sector 1 from sector 0?",
            player_state=PlayerState(sector=0),
            parameters={"target_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.route, [0, 1])
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0].source, "static_exact")

    def test_route_probe_returns_compressed_route(self):
        build = _to_build(fixture_simple_reachable())
        probe = DesignProbe(
            probe_type="route",
            question="Route from sector 0 to sector 1",
            player_state=PlayerState(sector=0),
            parameters={"target_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertEqual(len(result.route), 2)
        self.assertEqual(result.fidelity_level, "L0")


class TestLockedPath(unittest.TestCase):
    def test_access_probe_finds_blocked_path(self):
        build = _to_build(fixture_locked_path())
        probe = DesignProbe(
            probe_type="access",
            question="Can the player reach sector 1 when the gate is locked?",
            player_state=PlayerState(sector=0),
            parameters={"target_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "fail")
        self.assertEqual(len(result.blocking_reasons), 1)

    def test_access_probe_finds_opened_path(self):
        build = _to_build(fixture_locked_path())
        probe = DesignProbe(
            probe_type="access",
            question="Can the player reach sector 1 when the gate is opened?",
            player_state=PlayerState(sector=0),
            world_state=WorldState(opened_portals=frozenset({"portal:1"})),
            parameters={"target_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.route, [0, 1])


class TestKeyUnlock(unittest.TestCase):
    def test_initially_unreachable(self):
        build = _to_build(fixture_key_unlock())
        probe = DesignProbe(
            probe_type="access",
            question="Can the player reach sector 2 initially?",
            player_state=PlayerState(sector=0),
            parameters={"target_sector": 2},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "fail")

    def test_reachable_after_unlock(self):
        build = _to_build(fixture_key_unlock())
        probe = DesignProbe(
            probe_type="access",
            question="Can the player reach sector 2 after unlocking the gate?",
            player_state=PlayerState(sector=0),
            world_state=WorldState(opened_portals=frozenset({"portal:1"})),
            parameters={"target_sector": 2},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.route, [0, 1, 2])


class TestVerticalClearanceFailure(unittest.TestCase):
    def test_transition_probe_measures_height_delta(self):
        build = _to_build(fixture_vertical_clearance_failure())
        probe = DesignProbe(
            probe_type="transition",
            question="Transition from sector 0 to sector 1",
            player_state=PlayerState(sector=0),
            parameters={"source_sector": 0, "destination_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("area_ratio", result.measurements)
        self.assertIn("clear_height_delta", result.measurements)


class TestLiftEnabledPath(unittest.TestCase):
    def test_progression_probe_identifies_reachable_sectors(self):
        build = _to_build(fixture_lift_enabled_path())
        probe = DesignProbe(
            probe_type="progression",
            question="What is the progression structure?",
            player_state=PlayerState(sector=0),
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("initial_reachable_count", result.measurements)
        self.assertIn("reachable_sectors", result.measurements)


class TestTeleporterTransition(unittest.TestCase):
    def test_progression_probe_with_teleporter(self):
        build = _to_build(fixture_teleporter_transition())
        probe = DesignProbe(
            probe_type="progression",
            question="What is the progression structure with teleporter?",
            player_state=PlayerState(sector=0),
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("reachable_sectors", result.measurements)


class TestBranchingEscape(unittest.TestCase):
    def test_escape_probe_finds_viable_exits(self):
        build = _to_build(fixture_branching_escape())
        probe = DesignProbe(
            probe_type="escape",
            question="What are the escape options from sector 0?",
            player_state=PlayerState(sector=0),
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("viable_exit_count", result.measurements)
        self.assertGreater(result.measurements["viable_exit_count"], 0)

    def test_escape_probe_finds_dead_end_depth(self):
        build = _to_build(fixture_branching_escape())
        probe = DesignProbe(
            probe_type="escape",
            question="What is the dead-end depth from sector 0?",
            player_state=PlayerState(sector=0),
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("dead_end_depth", result.measurements)


class TestRevisitProbe(unittest.TestCase):
    def test_revisit_probe_compares_world_states(self):
        build = _to_build(fixture_key_unlock())
        probe = DesignProbe(
            probe_type="revisit",
            question="What changes when the gate is unlocked?",
            player_state=PlayerState(sector=0),
            parameters={
                "target_sector": 2,
                "alt_world_state": {
                    "opened_portals": ["portal:1"],
                },
            },
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("newly_reachable_count", result.measurements)
        self.assertGreater(result.measurements["newly_reachable_count"], 0)


class TestVisibilityProbe(unittest.TestCase):
    def test_visibility_probe_finds_visible_target(self):
        build = _to_build(fixture_simple_reachable())
        probe = DesignProbe(
            probe_type="visibility",
            question="Is sector 1 visible from sector 0?",
            player_state=PlayerState(sector=0),
            parameters={"target_sector": 1},
        )
        result = run_probe(probe, build)
        self.assertEqual(result.status, "pass")
        self.assertIn("first_visible_step", result.measurements)


class TestStateModel(unittest.TestCase):
    def test_player_state_serialization(self):
        state = PlayerState(sector=5, x=100, y=200, z=300, angle=512, keys=frozenset({"key:blue"}))
        d = state.to_dict()
        restored = PlayerState.from_dict(d)
        self.assertEqual(restored.sector, 5)
        self.assertEqual(restored.x, 100)
        self.assertEqual(restored.keys, frozenset({"key:blue"}))

    def test_world_state_serialization(self):
        state = WorldState(
            opened_portals=frozenset({"portal:1"}),
            activated_mechanisms=frozenset({"switch:0"}),
        )
        d = state.to_dict()
        restored = WorldState.from_dict(d)
        self.assertEqual(restored.opened_portals, frozenset({"portal:1"}))
        self.assertEqual(restored.activated_mechanisms, frozenset({"switch:0"}))

    def test_player_knowledge_serialization(self):
        state = PlayerKnowledge(
            seen_sectors=frozenset({0, 1, 2}),
            known_landmarks=frozenset({"church", "crypt"}),
        )
        d = state.to_dict()
        restored = PlayerKnowledge.from_dict(d)
        self.assertEqual(restored.seen_sectors, frozenset({0, 1, 2}))
        self.assertEqual(restored.known_landmarks, frozenset({"church", "crypt"}))


class TestDesignContract(unittest.TestCase):
    def test_contract_serialization(self):
        contract = DesignContract(name="Test Contract", brief="A test brief")
        contract.add_hard_assertion(
            "player_start_exists",
            "Player start sector must be valid",
            assertion_type="structural",
            expected=True,
        )
        contract.add_soft_evidence_question(
            "crypt_should_feel_constrained",
            "The crypt should feel spatially constrained",
            probe_type="transition",
            evidence_metrics=["area_ratio"],
            target_direction="lower",
            threshold=0.5,
        )
        d = contract.to_dict()
        restored = DesignContract.from_dict(d)
        self.assertEqual(restored.name, "Test Contract")
        self.assertEqual(len(restored.hard_assertions), 1)
        self.assertEqual(len(restored.soft_evidence_questions), 1)

    def test_contract_evaluation(self):
        build = _to_build(fixture_simple_reachable())
        contract = DesignContract(name="Test Contract")
        contract.add_hard_assertion(
            "player_start_exists",
            "Player start sector must be valid",
            assertion_type="structural",
            expected=True,
            player_start_valid=True,
        )
        contract.add_soft_evidence_question(
            "transition_test",
            "Test transition",
            probe_type="transition",
            evidence_metrics=["area_ratio"],
            target_direction="higher",
            threshold=1.0,
        )
        probe = DesignProbe(
            probe_type="transition",
            player_state=PlayerState(sector=0),
            parameters={"source_sector": 0, "destination_sector": 1},
        )
        probe_result = run_probe(probe, build)
        evaluation = evaluate_contract(
            contract,
            {"transition_test": probe_result},
            build=build,
        )
        self.assertEqual(evaluation.overall_status, "pass")

    def test_contract_does_not_pass_on_self_certified_assertion_parameters(self):
        from tests.helpers import synthetic_map

        disk = synthetic_map()
        disk.header["start_sector"] = -1
        contract = DesignContract(name="Self-certified")
        contract.add_hard_assertion(
            "player_start_exists",
            "Player start sector must be valid",
            assertion_type="structural",
            expected=True,
            player_start_valid=True,
        )
        contract.add_hard_assertion(
            "exit_reachable",
            "Exit must be reachable",
            assertion_type="structural",
            expected=True,
            exit_reachable=True,
        )
        evaluation = evaluate_contract(contract, {}, disk=disk)
        statuses = [item["status"] for item in evaluation.hard_assertion_results]
        self.assertNotIn("pass", statuses)
        self.assertNotEqual(evaluation.overall_status, "pass")
        self.assertTrue(evaluation.blocking_hard_failures())


class TestCounterfactualEvaluation(unittest.TestCase):
    def test_evaluate_candidates_compares_edits(self):
        build = _to_build(fixture_simple_reachable())
        probe = DesignProbe(
            probe_type="transition",
            player_state=PlayerState(sector=0),
            parameters={"source_sector": 0, "destination_sector": 1},
        )
        candidates = {
            "wider_entrance": {
                "type": "set_sector_z",
                "sector_id": 1,
                "ceiling_z": -16384,
                "floor_z": 8192,
            },
        }
        results = evaluate_candidates(build, [probe], candidates)
        self.assertIn("original", results)
        self.assertIn("candidates", results)
        self.assertIn("wider_entrance", results["candidates"])
        self.assertIn("comparison", results)


if __name__ == "__main__":
    unittest.main()
