import unittest
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map, encode_map
from bloodmap.construction import LevelBuilder
from bloodmap.conditional import build_graph, Held
from experiments.mashup_gate import build

try:
    AVAILABLE = all(corpus_map_path(n + '.MAP').is_file() for n in ('E1M3', 'E1M4'))
except (ValueError, FileNotFoundError):
    AVAILABLE = False

@unittest.skipUnless(AVAILABLE, 'requires local E1M3 and E1M4 source maps')
class MashupGateTests(unittest.TestCase):
    def test_rebuild_and_ordered_wall_activation(self):
        level, report = build()
        self.assertEqual(encode_map(level.to_disk_map()), encode_map(build()[0].to_disk_map()))
        self.assertEqual(report['reachable_at_rest'], [0, 2])
        self.assertEqual(report['activation_chain']['newly_reachable'], [1, 3])
        for reason in report['activation_chain']['why']:
            self.assertEqual(reason['topology_delta']['rest_state'], 'off')
            self.assertEqual(reason['topology_delta']['opening_at_rest'], 0)
            self.assertEqual(reason['topology_delta']['opening_when_moved'], 26624)
        steps = report['progression']['rounds']
        self.assertEqual(steps[1]['actions'][0]['action']['kind'], 'use_wall')
        self.assertEqual(steps[2]['actions'][0]['action']['channel'], 4)

    def test_unwired_or_locked_control_is_not_an_available_action(self):
        level, _ = build()
        for change in ({'tx_id': 0}, {'locked': 1}, {'trigger_push': 0}):
            disk = level.to_disk_map()
            disk.walls[18].extra.fields.update(change)
            graph = build_graph(disk)
            actions = graph.available_actions(graph.at_rest(), graph.reachable(graph.at_rest()))
            self.assertFalse([a for a in actions if a.kind == 'use_wall'], change)

    def test_donor_tx_and_rx_remap_together_on_channel_collision(self):
        source = read_map(corpus_map_path('E1M4.MAP')).to_level_ir()
        donor = source.extract_closed([359], max_sectors=6).fragment
        builder = LevelBuilder()
        builder.add_sector([(0,0),(2048,0),(2048,2048),(0,2048)])
        builder.set_player_start(sector=0,x=1024,y=1024,z=0,angle=0)
        builder.set_behavior('sector',0,rx_id=129)
        result = builder.build().insert(donor,channel_policy='remap')
        remapped = result.channel_map[129]
        self.assertNotEqual(remapped,129)
        wall = result.allocations['wall'].resolve(6)
        sector = result.allocations['sector'].resolve(0)
        self.assertEqual(result.level.walls[wall]['blood']['fields']['tx_id'],remapped)
        self.assertEqual(result.level.sectors[sector]['blood']['fields']['rx_id'],remapped)
        self.assertEqual(result.level.sectors[0]['blood']['fields']['rx_id'],129)

if __name__ == '__main__': unittest.main()
