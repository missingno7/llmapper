"""Regression checks for evidence preservation and isolated reevaluation."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments import monastery_pilot as runner
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


class RunTests(unittest.TestCase):
    def test_actual_run_has_bound_map_and_no_inherited_review(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(runner.main(['v0', '--run-id', 'actual', '--output-root', folder]), 0)
            run = Path(folder) / 'actual'
            packet = json.loads((run / 'v0/iteration.json').read_text())
            self.assertFalse(packet.get('review'))
            self.assertEqual(digest((run / 'v0/candidate.MAP').read_bytes()), packet['identity']['map_sha256'])
            before = {p.relative_to(run): digest(p.read_bytes()) for p in run.rglob('*') if p.is_file()}
            with self.assertRaises(SystemExit) as raised:
                runner.main(['v0', '--run-id', 'actual', '--output-root', folder])
            self.assertEqual(raised.exception.code, 2)
            after = {p.relative_to(run): digest(p.read_bytes()) for p in run.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(check_archive(), [])

    def test_fresh_run_snapshots_sources_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run = runner.prepare_run(root, 'test-001', ['v0'])
            manifest = json.loads((run / 'run.json').read_text())
            self.assertTrue(manifest['source_files'])
            for row in manifest['source_files']:
                self.assertEqual(digest((run / 'source' / row['path']).read_bytes()), row['sha256'])
            sentinel = run / 'v0.MAP'
            sentinel.write_bytes(b'preserve me')
            with self.assertRaises(FileExistsError):
                runner.prepare_run(root, 'test-001', ['v0'])
            self.assertEqual(sentinel.read_bytes(), b'preserve me')
            for label, iterations in [('../escape', ['v0']), ('duplicate', ['v0', 'v0']), ('unknown', ['v999'])]:
                with self.assertRaises(ValueError):
                    runner.prepare_run(root, label, iterations)

    def test_compile_exception_leaves_explicit_failure_record(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(runner, 'record_inputs'), patch.object(runner, 'run_iteration', side_effect=ValueError('compile failed')):
                with self.assertRaisesRegex(ValueError, 'compile failed'):
                    runner.main(['v0', '--run-id', 'failure', '--output-root', folder])
            run = Path(folder) / 'failure'
            self.assertEqual(json.loads((run / 'run.json').read_text())['status'], 'failed')
            self.assertEqual(json.loads((run / 'failure.json').read_text())['iteration'], 'v0')
            self.assertEqual(check_archive(), [])

if __name__ == '__main__':
    unittest.main()
