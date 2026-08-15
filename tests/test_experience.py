from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.experience import probe_progression, probe_route, probe_transition, probe_visibility
from bloodmap.format import write_map
from bloodmap.workspace import (
    append_decision, append_episode, append_evidence, initialize_project,
    make_level_slice, store_level_slice,
)
from tests.helpers import synthetic_two_sector_map


class ExperienceAtlasTests(unittest.TestCase):
    def test_route_preserves_world_state_and_player_knowledge_separately(self):
        build = synthetic_two_sector_map().to_build_ir()
        result = probe_route(build, 0, 1, player_knowledge={"seen_sectors": [0]})

        self.assertEqual(result["status"], "reachable")
        self.assertEqual(result["path"], ["sector:0", "sector:1"])
        self.assertEqual(result["player_knowledge_before"]["seen_sectors"], [0])
        self.assertEqual(result["player_knowledge_after"]["seen_sectors"], [0, 1])
        self.assertEqual(result["world_state"]["opened_portals"], [])

        build.walls[1]["fields"]["cstat"] = 1
        blocked = probe_route(build, 0, 1)
        self.assertEqual(blocked["status"], "unreachable_under_declared_state")
        opened = probe_route(build, 0, 1, world_state={"opened_portals": ["portal:1"]})
        self.assertEqual(opened["status"], "reachable")
        self.assertEqual(opened["transitions"][0]["edge"]["kind"], "world_state_override")

    def test_transition_visibility_and_progression_probes_are_bounded(self):
        build = synthetic_two_sector_map().to_build_ir()
        transition = probe_transition(build, 0, 1)
        visibility = probe_visibility(build, 0, 1)
        progression = probe_progression(build)

        self.assertEqual(transition["status"], "observed")
        self.assertEqual(transition["measured_change"]["area_ratio"], 1.0)
        self.assertEqual(visibility["first_direct_portal_candidate_step"], 0)
        self.assertEqual(progression["reachable_sectors"], ["sector:0", "sector:1"])
        self.assertIn("does not infer key ownership", progression["limitations"][0])

    def test_project_memory_keeps_evidence_decisions_episodes_and_contextual_slices(self):
        build = synthetic_two_sector_map().to_build_ir()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "crypt-project"
            initialize_project(root, name="Crypt", brief="A compact test brief.")
            evidence = append_evidence(root, {
                "concept": "test_door", "status": "heuristic", "claim": "A test channel is linked.",
                "evidence": ["sprite:0", "sprite:1"], "unknowns": ["runtime motion"],
            })
            decision = append_decision(root, intent="Make a route memorable", decision="Use a visible gate", expected="Seen early")
            episode = append_episode(root, intent="Check route", expected="Reach sector 1", observed=probe_route(build, 0, 1))
            sample = make_level_slice(build, [0], source={"map": "synthetic.MAP", "game": "blood"})
            stored = store_level_slice(root, sample)

            self.assertEqual(evidence["id"], "evidence:0000")
            self.assertEqual(decision["status"], "proposed")
            self.assertEqual(episode["observed"]["status"], "reachable")
            self.assertEqual(stored["id"], "slice:0000")
            memory = json.loads((root / "memory" / "design-memory.json").read_text(encoding="utf-8"))
            self.assertEqual(memory["samples"][0]["sectors"], ["sector:0"])

    def test_cli_creates_project_and_records_a_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "synthetic.MAP"
            project = root / "project"
            output = root / "route.json"
            init_output = root / "project-init.json"
            write_map(synthetic_two_sector_map(), map_path)

            self.assertEqual(main(["project-init", str(project), "--name", "Test", "-o", str(init_output)]), 0)
            self.assertEqual(main([
                "probe-route", str(map_path), "--from-sector", "0", "--to-sector", "1", "-o", str(output),
            ]), 0)
            route = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(route["status"], "reachable")
            self.assertTrue((project / "memory" / "evidence-ledger.json").is_file())


if __name__ == "__main__":
    unittest.main()
