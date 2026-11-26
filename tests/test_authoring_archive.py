"""The frozen pilot's evidence is preserved: every source, map, packet and frame still matches what was bound."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.check_authoring_archive import check_archive


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ArchiveTests(unittest.TestCase):
    def test_real_six_version_archive(self):
        self.assertEqual(check_archive(), [])

    def test_corruption_and_false_rebinding_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            packet = {'identity': {'iteration_id': 'v0', 'map_sha256': digest(b'map')},
                      'render': {'captures': {'views': [
                          {'viewpoint_id': 'start', 'status': 'pass', 'image': 'old.png', 'image_sha256': digest(b'image')},
                          {'viewpoint_id': 'missing', 'status': 'fail', 'image': None, 'image_sha256': None}]}}}
            data = {'source': b'source', 'map': b'map', 'review': b'{}',
                    'packet': json.dumps(packet).encode(), 'image': b'image'}
            for name, payload in data.items():
                (root / name).write_bytes(payload)
            entry = {'id': 'historic-v0', 'iteration_id': 'v0',
                     **{name: {'path': name, 'sha256': digest(data[name])}
                        for name in ('source', 'map', 'review', 'packet')},
                     'views': [{'id': 'start', 'status': 'pass', 'path': 'image', 'sha256': digest(b'image')},
                               {'id': 'missing', 'status': 'fail', 'path': None, 'sha256': None}]}
            manifest = root / 'manifest.json'
            def save():
                manifest.write_text(json.dumps({'iterations': [entry]}))
            save()
            self.assertEqual(check_archive(manifest, root), [])
            for name in data:
                with self.subTest(role=name):
                    (root / name).write_bytes(data[name] + b' ')
                    self.assertTrue(check_archive(manifest, root))
                    (root / name).write_bytes(data[name])
            (root / 'map').write_bytes(b'new map')
            entry['map']['sha256'] = digest(b'new map')
            save()
            self.assertTrue(any('packet identity' in f for f in check_archive(manifest, root)))
            (root / 'image').unlink()
            self.assertTrue(any('missing frame' in f for f in check_archive(manifest, root)))

if __name__ == '__main__':
    unittest.main()
