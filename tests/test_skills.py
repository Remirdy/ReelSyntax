import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ReelSyntax_Skills.tools.registry import ROOT, atomic_json, contained_path, digest, load_index, load_skill, read_json, rebuild, validate_rows
from ReelSyntax_Skills.tools.route import route, route_task
from reelsyntax import hosts, skills

ROWS = load_index()['skills']
BY_ID = {r['id']: r for r in ROWS}


class RoutingTests(unittest.TestCase):
    def test_reindex_csv_reflects_relation_overrides_and_keeps_utf8(self):
        import csv
        from ReelSyntax_Skills.tools.reindex import rebuild as rebuild_catalog
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / BY_ID['frame-clock']['path']
            source.parent.mkdir(parents=True)
            source.write_bytes((ROOT / BY_ID['frame-clock']['path']).read_bytes())
            atomic_json(root / 'registry/relations.json', {'frame-clock': {'requires': [], 'status': 'validated'}})
            document = rebuild_catalog(quiet=True, root=root)
            with (root / 'registry/catalog.csv').open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['status'], document['skills'][0]['status'])
            self.assertEqual(rows[0]['aliases'], ', '.join(document['skills'][0]['aliases']))
            self.assertEqual(rows[0]['requires'], '')

    def test_production_workflow_resources_are_lazy_hashed_and_budgeted(self):
        targets = ['j-cut', 'l-cut', 'psd-to-video', 'shader-effects', 'otio-export', 'fcpxml-export', 'render-cache', 'partial-render', 'ffmpeg-trimming']
        load_index()
        original = Path.read_bytes
        original_text = Path.read_text
        def no_instruction_reads(path, *args, **kwargs):
            if path.name == 'SKILL.md' or 'references' in path.parts:
                self.fail('Search read an instruction/reference body')
            return original(path, *args, **kwargs)
        def no_instruction_text(path, *args, **kwargs):
            if path.name == 'SKILL.md' or 'references' in path.parts:
                self.fail('Search read an instruction/reference body')
            return original_text(path, *args, **kwargs)
        with patch.object(Path, 'read_bytes', no_instruction_reads), patch.object(Path, 'read_text', no_instruction_text):
            result = skills.search({'intent': 'j cut source audio', 'include': ['j-cut']})
        self.assertEqual(result['skill_bodies_read'], 0)
        for sid in targets:
            row = BY_ID[sid]
            self.assertTrue(row['resources'])
            for resource in row['resources']:
                result = skills.get_skill(sid, 6000, resource)
                self.assertEqual(result['sha256'], row['resource_sha256'][resource])
                self.assertEqual(result['skill_bodies_read'], 0)
                self.assertFalse(result['executed'])
                with self.assertRaisesRegex(ValueError, 'context budget'):
                    skills.get_skill(sid, 1, resource)

    def test_native_otio_export_does_not_require_an_optional_sdk(self):
        result = route('', ROWS, available=[], include=['otio-export'])
        self.assertIn('otio-export', [row['id'] for row in result['selected']])
        self.assertFalse(result['unfulfilled_explicit_ids'])

    def test_updated_resource_is_reloaded_and_charged_in_the_same_session(self):
        with tempfile.TemporaryDirectory() as catalog, tempfile.TemporaryDirectory() as project:
            root = Path(catalog)
            row = BY_ID['frame-clock']
            source = root / row['path']
            source.parent.mkdir(parents=True)
            source.write_bytes((ROOT / row['path']).read_bytes())
            relative = 'library/render/frame-clock/references/session-resource.md'
            resource = root / relative
            resource.parent.mkdir()
            resource.write_text('First frame timing reference.', encoding='utf-8')
            atomic_json(root / 'registry/relations.json', {'frame-clock': {'resources': [relative]}})
            first_digest = rebuild(root)['skills'][0]['sha256']
            with patch.object(skills, 'ROOT', root), patch.object(skills, 'load_index', side_effect=lambda: load_index(root)):
                first = skills.session_load(project, 'resource-review', 'frame-clock', 6000, relative)
                duplicate = skills.session_load(project, 'resource-review', 'frame-clock', 6000, relative)
                self.assertTrue(duplicate['already_loaded'])
                resource.write_text('Updated exact frame timing reference with a different content hash.', encoding='utf-8')
                revised = skills.session_load(project, 'resource-review', 'frame-clock', 6000, relative)
                self.assertFalse(revised.get('already_loaded', False))
                self.assertIn('Updated exact', revised['content'])
                self.assertGreater(revised['charged_tokens'], first['charged_tokens'])
                self.assertEqual(load_index(root)['skills'][0]['sha256'], first_digest)
                atomic_json(root / 'registry/relations.json', {'frame-clock': {}})
                with self.assertRaisesRegex(ValueError, 'not declared'):
                    skills.session_load(project, 'resource-review', 'frame-clock', 6000, relative)

    def test_search_reads_no_specialist_bodies(self):
        original_text, original_bytes = Path.read_text, Path.read_bytes
        def text(path, *args, **kwargs):
            if path.name == 'SKILL.md' and 'library' in path.parts:
                self.fail('Search opened a specialist body')
            return original_text(path, *args, **kwargs)
        def binary(path, *args, **kwargs):
            if path.name == 'SKILL.md' and 'library' in path.parts:
                self.fail('Search opened a specialist body')
            return original_bytes(path, *args, **kwargs)
        with patch.object(Path, 'read_text', text), patch.object(Path, 'read_bytes', binary):
            result = skills.search({'intent': 'word anchored timeline'})
        self.assertEqual(result['skill_bodies_read'], 0)
        self.assertIn('word-anchored-timeline', [r['id'] for r in result['selected']])

    def test_dependencies_precede_dependents(self):
        result = route('', ROWS, include=['partial-render'])
        ids = [r['id'] for r in result['selected']]
        self.assertLess(ids.index('render-cache'), ids.index('partial-render'))

    def test_missing_dependency_blocks_dependent(self):
        rows = copy.deepcopy(ROWS)
        next(r for r in rows if r['id'] == 'render-cache')['requires'] = ['unavailable']
        result = route('', rows, available=[], include=['partial-render'])
        self.assertNotIn('partial-render', [r['id'] for r in result['selected']])
        self.assertIn('partial-render', result['unfulfilled_explicit_ids'])

    def test_budget_preserves_constraints_and_explicit_failures(self):
        result = route('no text, camera locked', ROWS, context_budget=1, include=['asset-matching'])
        self.assertEqual(result['selected'], [])
        self.assertTrue(result['constraints']['no_text'])
        self.assertTrue(result['constraints']['camera_locked'])
        self.assertIn('asset-matching', result['unfulfilled_explicit_ids'])

    def test_unknown_capability_is_not_verified(self):
        result = route('blender cycles', ROWS)
        self.assertEqual(next(r for r in result['selected'] if r['id'] == 'blender-cycles')['capability_status'], 'unknown')
        strict = route('blender cycles', ROWS, available=[])
        self.assertNotIn('blender-cycles', [r['id'] for r in strict['selected']])

    def test_structured_constraints(self):
        result = route_task({'intent': 'cinematic drone foley kinetic typography orbit camera', 'constraints': {'no_audio': True, 'no_text': True, 'camera_locked': True}}, ROWS)
        self.assertFalse(any(r['category'] in {'audio', 'music'} for r in result['selected']))
        self.assertNotIn('orbit-camera', [r['id'] for r in result['selected']])
        self.assertNotIn('kinetic-typography', [r['id'] for r in result['selected']])

    def test_bad_envelopes(self):
        for task in [{'intent': 'x', 'max_skills': True}, {'intent': 'x', 'capabilities': 'ffmpeg'}, {'intent': 'x', 'constraints': {'no_text': 'yes'}}, {'intent': 'x', 'unknown': 1}]:
            with self.subTest(task=task), self.assertRaises(ValueError):
                route_task(task, ROWS)

    def test_cycles_duplicates_and_unknown_relations(self):
        for mutate in ['cycle', 'duplicate', 'unknown']:
            rows = copy.deepcopy(ROWS)
            if mutate == 'cycle':
                rows[0]['dependencies'] = [rows[1]['id']]
                rows[1]['dependencies'] = [rows[0]['id']]
            elif mutate == 'duplicate':
                rows.append(rows[0])
            else:
                rows[0]['dependencies'] = ['unknown-skill']
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                validate_rows(rows)

    def test_hash_boundary_and_traversal(self):
        for value in ['../LICENSE', '/tmp/file', 'library/../../LICENSE', 'C:\\private', 'library/nope']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                contained_path(ROOT, value)
        row = dict(BY_ID['frame-clock'], sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'content changed'):
            load_skill(row)

    def test_lazy_resource_integrity_and_no_execution(self):
        relative = 'library/render/frame-clock/references/exact-timing.md'
        result = skills.get_skill('frame-clock', resource=relative)
        self.assertFalse(result['executed'])
        self.assertEqual(result['skill_bodies_read'], 0)
        with self.assertRaises(ValueError):
            skills.get_skill('frame-clock', resource='../LICENSE')
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw + b'drift' if path == ROOT / relative else raw
        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(ValueError, 'Resource changed'):
            skills.get_skill('frame-clock', resource=relative)

    def test_session_cumulative_budget_and_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = BY_ID['frame-clock']['estimated_tokens'] + 120
            first = skills.session_load(tmp, 'work-item', 'frame-clock', budget)
            self.assertIn('instructions', first)
            second = skills.session_load(tmp, 'work-item', 'frame-clock', budget)
            self.assertTrue(second['already_loaded'])
            self.assertEqual(second['skill_bodies_read'], 0)
            with self.assertRaises(ValueError):
                skills.session_load(tmp, 'work-item', 'asset-matching', budget)

    def test_cache_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = {'intent': 'siyah kare', 'constraints': {'offline': True}}
            self.assertFalse(skills.search(task, tmp)['cache_hit'])
            self.assertTrue(skills.search(task, tmp)['cache_hit'])
            changed = copy.deepcopy(task)
            changed['constraints']['no_text'] = True
            self.assertFalse(skills.search(changed, tmp)['cache_hit'])
            Path(tmp, 'artifact.txt').write_text('real fixture')
            with self.assertRaises(ValueError):
                skills.record_execution(tmp, 'frame-clock', 'success')
            event = skills.record_execution(tmp, 'frame-clock', 'success', ['artifact.txt'])
            self.assertEqual(len(event['evidence'][0]['sha256']), 64)
            self.assertEqual(skills.effectiveness(tmp)['skills']['frame-clock']['reported_success_rate'], 1)

    def test_route_cache_invalidates_on_registry_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = load_index()
            with patch('reelsyntax.skills.load_index', return_value=document):
                self.assertFalse(skills.search({'intent': 'siyah kare'}, tmp)['cache_hit'])
                self.assertTrue(skills.search({'intent': 'siyah kare'}, tmp)['cache_hit'])
            changed = dict(document, digest='0' * 64)
            with patch('reelsyntax.skills.load_index', return_value=changed):
                self.assertFalse(skills.search({'intent': 'siyah kare'}, tmp)['cache_hit'])

    def test_install_uninstall_and_modified_file_protection(self):
        for host, directory in hosts.HOST_PATHS.items():
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                hosts.install(tmp, host)
                hosts.install(tmp, host)
                self.assertEqual(len(list(Path(tmp).rglob('SKILL.md'))), 1)
                target = Path(tmp, directory, 'reelsyntax-router', 'SKILL.md')
                original = target.read_bytes()
                target.write_text('user edits')
                with self.assertRaises(ValueError):
                    hosts.install(tmp, host)
                with self.assertRaises(ValueError):
                    hosts.uninstall(tmp, host)
                target.write_bytes(original)
                Path(tmp, directory, 'reelsyntax-router', 'user.txt').write_text('keep')
                hosts.uninstall(tmp, host)
                self.assertTrue(Path(tmp, directory, 'reelsyntax-router', 'user.txt').exists())

    def test_install_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as external:
            try:
                Path(tmp, '.agents').symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest('Symlinks unavailable')
            with self.assertRaises(ValueError):
                hosts.install(tmp, 'codex')
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_reindex_tracks_add_update_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / BY_ID['frame-clock']['path']
            path.parent.mkdir(parents=True)
            path.write_bytes((ROOT / BY_ID['frame-clock']['path']).read_bytes())
            first = rebuild(root)
            path.write_text(path.read_text() + '\nAdditional test acceptance evidence.\n')
            second = load_index(root)
            self.assertNotEqual(first['digest'], second['digest'])
            duplicate = root / 'library/render/another-clock/SKILL.md'
            duplicate.parent.mkdir()
            duplicate.write_text(path.read_text().replace('name: frame-clock', 'name: another-clock'))
            with self.assertRaisesRegex(ValueError, 'Duplicate instruction bodies'):
                rebuild(root)
            duplicate.unlink()
            self.assertEqual(len(rebuild(root)['skills']), 1)

    def test_crlf_skill_reindex_preserves_exact_bytes_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / BY_ID['frame-clock']['path']
            path.parent.mkdir(parents=True)
            raw = (ROOT / BY_ID['frame-clock']['path']).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            path.write_bytes(raw)
            row = rebuild(root)['skills'][0]
            self.assertEqual(row['sha256'], digest(raw))
            self.assertEqual(load_skill(row, root).encode('utf-8'), raw)
            self.assertEqual(path.read_bytes(), raw)
            path.write_bytes(raw + b'Changed\r\n')
            with self.assertRaisesRegex(ValueError, 'content changed'):
                load_skill(row, root)

    def test_scale_bounds(self):
        rows = copy.deepcopy(ROWS)
        for i in range(4500):
            import hashlib
            row = dict(ROWS[0], id=f'extra-{i}', aliases=[f'unrelated-{i}'], dependencies=[], conflicts=[], recommended_next=[], body_sha256=hashlib.sha256(f'extra-{i}'.encode()).hexdigest())
            rows.append(row)
        result = route('siyah kare', rows)
        self.assertEqual(result['catalog_size'], len(ROWS) + 4500)
        self.assertGreaterEqual(result['catalog_size'], 5000)
        self.assertLessEqual(len(result['selected']), 6)
        self.assertLessEqual(result['estimated_loaded_tokens_if_all_selected'], 6000)


if __name__ == '__main__':
    unittest.main()
