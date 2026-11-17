import os
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.cache import prune_cache
from reelsyntax.project import initialize


class CacheTests(unittest.TestCase):
    def entry(self, root, key, age):
        directory = root / '.reelsyntax/cache' / key
        directory.mkdir(parents=True)
        atomic_json(directory / 'manifest.json', {'key': key})
        (directory / '000000.png').write_bytes(b'cached-artifact')
        os.utime(directory, ns=(age, age))
        return directory

    def test_lru_preview_then_prune_preserves_referenced_and_unknown_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root = Path(tmp)
            oldest = self.entry(root, 'a' * 64, 1)
            newer = self.entry(root, 'b' * 64, 2)
            pinned = self.entry(root, 'c' * 64, 0)
            atomic_json(root / 'output/hero-manifest.json', {'scenes': [{'cache_key': pinned.name}]})
            unknown = root / '.reelsyntax/cache/notes.txt'
            unknown.write_text('keep user notes')
            report = prune_cache(root, 0)
            self.assertEqual([e['key'] for e in report['selected']], [oldest.name, newer.name])
            self.assertFalse(report['within_budget'])
            self.assertEqual(report['protected_entries'], 1)
            self.assertTrue(oldest.exists())
            result = prune_cache(root, report['selected'][1]['bytes'] + report['before_bytes'] - sum(e['bytes'] for e in report['selected']), apply=True)
            self.assertFalse(oldest.exists())
            self.assertTrue(newer.exists())
            self.assertTrue(pinned.exists())
            self.assertTrue(unknown.exists())
            self.assertEqual(result['removed_bytes'], report['selected'][0]['bytes'])

    def test_active_lock_and_malformed_references_refuse_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root = Path(tmp)
            directory = self.entry(root, 'a' * 64, 1)
            mutex = root / '.reelsyntax/render.lock'
            mutex.write_text('active')
            with self.assertRaisesRegex(ValueError, 'lock'):
                prune_cache(root, 0, apply=True)
            self.assertEqual(mutex.read_text(), 'active')
            mutex.unlink()
            atomic_json(root / '.reelsyntax/state.json', {'scenes': [{'cache_key': '../outside'}]})
            with self.assertRaisesRegex(ValueError, 'reference'):
                prune_cache(root, 0, apply=True)
            self.assertTrue(directory.exists())
            self.assertFalse(mutex.exists())

    def test_cache_symlinks_are_never_followed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            initialize(tmp)
            directory = self.entry(Path(tmp), 'a' * 64, 1)
            external = Path(outside, 'keep.txt')
            external.write_text('keep')
            try:
                (directory / 'linked').symlink_to(external)
            except OSError as error:
                self.skipTest(str(error))
            with self.assertRaisesRegex(ValueError, 'symbolic'):
                prune_cache(tmp, 0, apply=True)
            self.assertEqual(external.read_text(), 'keep')
            self.assertTrue(directory.exists())

    def test_negative_budget_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            with self.assertRaisesRegex(ValueError, 'nonnegative'):
                prune_cache(tmp, -1)
