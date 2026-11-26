from __future__ import annotations

import unittest

from bloodmap.experience import probe_progression, probe_route, probe_transition, probe_visibility
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

if __name__ == "__main__":
    unittest.main()
