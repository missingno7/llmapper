"""Vertical mashup controls: retained gate, real stair route, layers and deck."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from experiments.mashup_upper import build, verify, standing_routes, layer_view
from bloodmap import layers
from bloodmap.format import encode_map
from bloodmap.corpus import corpus_map_path

try:
    AVAILABLE = all(corpus_map_path(n+'.MAP').is_file() for n in ('E1M2','E1M3','E1M4'))
except (ValueError, FileNotFoundError):
    AVAILABLE = False

@unittest.skipUnless(AVAILABLE, 'requires the local E1M2/E1M3/E1M4 sources')
class UpperMashupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.level, cls.report = build()

    def test_rebuild_and_material_correction_preserve_gate(self):
        report=verify(self.level,copy.deepcopy(self.report))
        self.assertEqual(encode_map(self.level.to_disk_map()),encode_map(build()[0].to_disk_map()))
        self.assertTrue(report['gate_preserved'])
        self.assertTrue(all(self.level.walls[w]['fields']['picnum']==255 for w in range(20,26)))
        anchors=json.loads(Path('knowledge/blood/design/owner-anchors-v1.json').read_text(encoding='utf-8'))['anchors']
        self.assertEqual([a['label_en'] for a in anchors if a['picnum']==315],['metal door texture'])
        old=Path('work/mashup-gate/v1-verified/mashup.MAP')
        if old.exists():
            self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),self.report['baseline_sha256'])

    def test_upper_route_requires_stairs_not_a_jump_from_gallery_floor(self):
        route=standing_routes(self.level)
        self.assertIn(16,route['paths'])
        self.assertIn(3,route['paths'])
        self.assertNotIn(1,route['paths'])
        blocked=copy.deepcopy(self.level)
        wall=blocked.walls[10]['fields']
        wall['cstat'] |= 1
        blocked.walls[wall['next_wall']]['fields']['cstat'] |= 1
        cut=standing_routes(blocked)
        self.assertNotIn(16,cut['paths'])
        self.assertNotIn(3,cut['paths'])

    def test_vertical_collision_is_detected(self):
        self.assertEqual(self.report['errors'],[])
        self.assertGreaterEqual(len(self.report['layers']['overlaps']),2)
        broken=copy.deepcopy(self.level)
        broken.sectors[16]['fields']['floor_z']=8192
        # The native inspection adapter preserves each source sector's topology.
        groups=['ground']*4+['stairs']*10+['upper']*10+['descent']*21
        changed=copy.deepcopy(self.report)
        changed['layers']=layers.report(layer_view(broken,groups))
        # The general engine rule permits distant overlaps; this specimen
        # deliberately requires disjoint bands in every stacked pair.
        with self.assertRaisesRegex(AssertionError,'vertical'):
            verify(broken,changed)

    def test_deck_is_contiguous_and_seated_on_upper_portal(self):
        r=verify(self.level,copy.deepcopy(self.report))
        boxes=r['deck_footprints']
        self.assertEqual(boxes[-1][2],7936)
        self.assertEqual(len(boxes),4)
        self.assertGreaterEqual(r['deck_headroom'],16960)
        self.assertTrue(all(a[2]==b[0] for a,b in zip(boxes,boxes[1:])))

if __name__=='__main__':unittest.main()
