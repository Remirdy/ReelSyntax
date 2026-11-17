import copy
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from ReelSyntax_Skills.tools.registry import atomic_json, read_json
from reelsyntax.edits import edit_project, prepare_edit, undo_edit
from reelsyntax.project import initialize, load, starter
from reelsyntax.render import lock, render


class EditTests(unittest.TestCase):
    def test_checkpoint_restore_and_cache_share_the_active_edit_lock(self):
        from reelsyntax.cache import prune_cache
        from reelsyntax.revisions import checkpoint, restore
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, _, _ = load(tmp)
            checkpoint(root, 'original')
            source = (root / 'reel.json').read_bytes()
            mutex = root / '.reelsyntax/render.lock'
            mutex.write_text('active', encoding='utf-8')
            for action in (lambda: checkpoint(root, 'other'), lambda: restore(root, 'original'), lambda: prune_cache(root, 0, True), lambda: lock(root, ['form'])):
                with self.assertRaisesRegex(ValueError, 'project lock'):
                    action()
                self.assertEqual((root / 'reel.json').read_bytes(), source)
                self.assertEqual(mutex.read_text(encoding='utf-8'), 'active')

    def test_cli_preview_apply_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, _, metadata = load(tmp)
            operations = root / 'edit.json'
            atomic_json(operations, [{'type': 'update', 'scene_id': 'form', 'changes': {'params': {}}}])
            def invoke(*args):
                result = subprocess.run([sys.executable, '-m', 'reelsyntax', *map(str, args)], capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)['result']
            preview = invoke('edit', root, '--operations', operations)
            self.assertEqual(preview['status'], 'preview')
            self.assertEqual(load(root)[2]['plan_sha256'], metadata['plan_sha256'])
            applied = invoke('edit', root, '--operations', operations, '--apply', '--expected-plan', preview['before_sha256'])
            invoke('undo-edit', root, '--revision', applied['revision'])
            self.assertEqual(load(root)[2]['plan_sha256'], applied['after_sha256'])
            invoke('undo-edit', root, '--revision', applied['revision'], '--apply')
            self.assertEqual(load(root)[2]['plan_sha256'], metadata['plan_sha256'])

    def test_noop_keeps_quality_exceptions_and_creates_no_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            report = edit_project(root, [{'type': 'move', 'scene_id': 'form', 'to_index': 0}], True)
            self.assertEqual(report['status'], 'unchanged')
            self.assertIsNone(report['revision'])
            self.assertEqual(load(root)[1], plan)
            self.assertFalse((root / '.reelsyntax/edits').exists())

    def test_preview_apply_undo_and_redo_preserve_source_and_input_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, original, metadata = load(tmp)
            raw = (root / 'reel.json').read_bytes()
            operations = [{'type': 'move', 'scene_id': 'signal', 'to_index': 0}]
            saved_operations = copy.deepcopy(operations)
            preview = edit_project(root, operations, audio_mode='follow-scenes')
            self.assertEqual(preview['status'], 'preview')
            self.assertEqual(preview['before_frames'], preview['after_frames'])
            self.assertEqual(preview['audio_cue_frames'], [60, 150, 0])
            self.assertEqual((root / 'reel.json').read_bytes(), raw)
            self.assertFalse((root / '.reelsyntax').exists())
            applied = edit_project(root, operations, True, 'follow-scenes', metadata['plan_sha256'])
            self.assertEqual(applied['after_sha256'], preview['after_sha256'])
            self.assertEqual(operations, saved_operations)
            self.assertEqual([s['id'] for s in load(root)[1]['scenes']], ['signal', 'form', 'time'])
            self.assertEqual(load(root)[1]['quality']['exceptions'], {})
            record = read_json(root / f'.reelsyntax/edits/{applied["revision"]}.json')
            self.assertEqual((root / record['original_source']).read_bytes(), raw)
            undo_preview = undo_edit(root, applied['revision'])
            self.assertEqual(undo_preview['after_sha256'], metadata['plan_sha256'])
            undone = undo_edit(root, applied['revision'], True)
            self.assertEqual(load(root)[1], original)
            undo_edit(root, undone['revision'], True)
            self.assertEqual(load(root)[2]['plan_sha256'], applied['after_sha256'])

    def test_combined_operations_validate_only_the_complete_transaction(self):
        plan = starter()
        plan['audio'].update(enabled=False, cues=[])
        plan['quality']['exceptions'] = {}
        replacement = dict(plan['scenes'][0], id='replacement', duration_frames=15, params={})
        operations = [
            {'type': 'remove', 'scene_id': s['id']} for s in plan['scenes']
        ] + [
            {'type': 'insert', 'scene': replacement, 'at_index': 0},
            {'type': 'duplicate', 'scene_id': 'replacement', 'new_id': 'copy'},
            {'type': 'update', 'scene_id': 'copy', 'changes': {'duration_frames': 9}},
        ]
        after, report = prepare_edit(plan, operations)
        self.assertEqual([s['duration_frames'] for s in after['scenes']], [15, 9])
        self.assertEqual(report['after_frames'], 24)
        self.assertEqual(len(plan['scenes']), 3)

    def test_invalid_transaction_stale_preview_lock_and_busy_project_leave_source_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, _, _ = load(tmp)
            source = (root / 'reel.json').read_bytes()
            invalid = [
                [{'type': 'move', 'scene_id': 'unknown', 'to_index': 0}],
                [{'type': 'move', 'scene_id': 'time', 'to_index': True}],
                [{'type': 'duplicate', 'scene_id': 'time', 'new_id': 'form'}],
                [{'type': 'insert', 'scene': {'id': 'incomplete'}, 'at_index': 0}],
                [{'type': 'update', 'scene_id': 'time', 'changes': {'id': 'changed'}}],
            ]
            for operations in invalid:
                with self.subTest(operations=operations), self.assertRaises(ValueError):
                    edit_project(root, operations, True)
                self.assertEqual((root / 'reel.json').read_bytes(), source)
                self.assertFalse((root / '.reelsyntax/edits').exists())
            operations = [{'type': 'move', 'scene_id': 'time', 'to_index': 0}]
            with self.assertRaisesRegex(ValueError, 'expected plan'):
                edit_project(root, operations, True, expected_plan='0' * 64)
            lock(root, ['form'])
            with self.assertRaisesRegex(ValueError, 'Approved scene changed'):
                edit_project(root, operations, True)
            mutex = root / '.reelsyntax/render.lock'
            mutex.write_text('active', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'holds the project lock'):
                edit_project(root, operations, True)
            self.assertEqual(mutex.read_text(encoding='utf-8'), 'active')
            self.assertEqual((root / 'reel.json').read_bytes(), source)

    def test_audio_anchor_loss_and_later_changes_refuse_unsafe_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            with self.assertRaisesRegex(ValueError, 'Audio anchor'):
                edit_project(root, [{'type': 'remove', 'scene_id': 'signal'}], True, 'follow-scenes')
            applied = edit_project(root, [{'type': 'update', 'scene_id': 'form', 'changes': {'params': {}}}], True)
            plan = load(root)[1]
            plan['scenes'][1]['params'] = {'accent': '#446655'}
            atomic_json(root / 'reel.json', plan)
            with self.assertRaisesRegex(ValueError, 'Project changed after'):
                undo_edit(root, applied['revision'], True)
            self.assertEqual(load(root)[1], plan)

    def test_source_track_follows_its_scene_and_trim_uses_explicit_source_in_point(self):
        plan = starter()
        plan['audio']['cues'] = []
        plan['audio']['tracks'] = [{'id': 'source', 'source': 'assets/source.wav', 'kind': 'effects', 'start_frame': 90, 'duration_frames': 15}]
        plan['scenes'][1].update(recipe='footage', engine='ffmpeg', params={'source': 'assets/source.mp4', 'in_frame': 30})
        after, report = prepare_edit(plan, [
            {'type': 'move', 'scene_id': 'time', 'to_index': 0},
            {'type': 'update', 'scene_id': 'time', 'changes': {'duration_frames': 45, 'params': {'source': 'assets/source.mp4', 'in_frame': 48}}},
        ], 'follow-scenes')
        self.assertEqual(after['scenes'][0]['params']['in_frame'], 48)
        self.assertEqual(report['audio_track_frames'], {'source': 0})

    def test_corrupt_journal_and_source_backup_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, _, _ = load(tmp)
            applied = edit_project(root, [{'type': 'update', 'scene_id': 'form', 'changes': {'params': {}}}], True)
            journal = root / f'.reelsyntax/edits/{applied["revision"]}.json'
            record = read_json(journal)
            original = copy.deepcopy(record)
            record['before_plan']['seed'] = 100
            atomic_json(journal, record)
            with self.assertRaisesRegex(ValueError, 'journal integrity'):
                undo_edit(root, applied['revision'])
            atomic_json(journal, original)
            (root / original['original_source']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'backup integrity'):
                undo_edit(root, applied['revision'])

    @unittest.skipUnless(os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1', 'Enable actual media integration tests')
    def test_render_after_edit_reuses_unchanged_scenes_and_undo_restores_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output'] = {'width': 160, 'height': 90, 'fps': '24/1'}
            for scene in plan['scenes']:
                scene.update(duration_frames=4, params={})
            plan['audio'].update(enabled=False, cues=[])
            plan['quality']['exceptions'] = {}
            atomic_json(root / 'reel.json', plan)
            render(root, 'production')
            applied = edit_project(root, [
                {'type': 'move', 'scene_id': 'signal', 'to_index': 0},
                {'type': 'update', 'scene_id': 'time', 'changes': {'params': {'accent': '#445566'}}},
            ], True)
            revised = render(root, 'production')
            self.assertEqual([s['id'] for s in revised['scenes']], ['signal', 'form', 'time'])
            self.assertEqual([s['cache_hit'] for s in revised['scenes']], [True, True, False])
            undo_edit(root, applied['revision'], True)
            restored = render(root, 'production')
            self.assertTrue(all(s['cache_hit'] for s in restored['scenes']))
