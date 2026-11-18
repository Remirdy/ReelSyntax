import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from ReelSyntax_Skills.tools.registry import read_json
from reelsyntax.mcp_server import FORMAT_TOOLS, GATEWAY_TOOLS, UnifiedMcpServer
from reelsyntax.project import initialize
from reelsyntax.render import lock

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAT_TOOL_NAMES = ['reelsyntax_format_list', 'reelsyntax_format_show', 'reelsyntax_format_make', 'reelsyntax_format_revise']
PROMPT = '12s vertical reel on clean architecture'


def call(server, name, arguments):
    response = server.handle_message({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}})
    return response['result']['isError'], json.loads(response['result']['content'][0]['text'])


class McpFormatToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name).resolve()
        self.server = UnifiedMcpServer(gateway=Mock(), workspace=self.workspace)

    def tearDown(self):
        self.server.close()
        self._tmp.cleanup()

    def ok(self, name, arguments):
        is_error, payload = call(self.server, name, arguments)
        self.assertFalse(is_error, payload)
        return payload

    def rejected(self, name, arguments):
        is_error, payload = call(self.server, name, arguments)
        self.assertTrue(is_error, payload)
        self.assertFalse(payload['ok'])
        return payload['error']

    def test_tools_list_publishes_closed_bounded_format_schemas(self):
        response = self.server.handle_message({'jsonrpc': '2.0', 'id': 7, 'method': 'tools/list', 'params': {}})
        names = [tool['name'] for tool in response['result']['tools']]
        self.assertEqual([name for name in names if name.startswith('reelsyntax_format_')], FORMAT_TOOL_NAMES)
        self.assertEqual(len(names), len(set(names)))
        self.assertLessEqual(len(GATEWAY_TOOLS), 16)
        for tool in FORMAT_TOOLS:
            with self.subTest(tool=tool['name']):
                self.assertIs(tool['inputSchema']['additionalProperties'], False)
                self.assertTrue(tool['description'])
        make_props = FORMAT_TOOLS[2]['inputSchema']['properties']
        for key in ['dry_run', 'step', 'yes', 'video_lang', 'ui_lang', 'attribution', 'offline']:
            self.assertIn(key, make_props)
        self.assertTrue(make_props['offline']['default'])
        self.assertIs(make_props['step']['additionalProperties'], False)

    def test_format_list_returns_summaries_without_paths_or_full_manifests(self):
        payload = self.ok('reelsyntax_format_list', {})
        ids = [item['id'] for item in payload['formats']]
        self.assertEqual(payload['count'], len(ids))
        self.assertEqual(payload['full_manifests_exposed'], 0)
        self.assertIn('kinetic-typography', ids)
        self.assertIn('prompt-direct', ids)
        self.assertEqual(ids, sorted(ids))
        for item in payload['formats']:
            self.assertNotIn('path', item)
            self.assertNotIn('qc_rules', item)
            self.assertTrue(all(isinstance(step, str) for step in item['steps']))
        social = self.ok('reelsyntax_format_list', {'category': 'social'})
        self.assertTrue(all(item['category'] == 'social' for item in social['formats']))
        self.assertIn('enum', self.rejected('reelsyntax_format_list', {'category': 'horror'}))
        self.rejected('reelsyntax_format_list', {'limit': 3})

    def test_format_show_loads_manifest_and_rejects_path_identifiers(self):
        payload = self.ok('reelsyntax_format_show', {'format_id': 'kinetic-typography'})
        self.assertEqual(payload['manifest']['id'], 'kinetic-typography')
        self.assertNotIn('path', payload['manifest'])
        self.assertNotIn('docs', payload)
        self.assertIn('idea', payload['summary']['approval_gates'])
        with_docs = self.ok('reelsyntax_format_show', {'format_id': 'kinetic-typography', 'include_docs': True})
        self.assertIn('#', with_docs['docs'])
        builtin = self.ok('reelsyntax_format_show', {'format_id': 'prompt-direct'})
        self.assertTrue(builtin['manifest'].get('builtin', False) or builtin['manifest']['id'] == 'prompt-direct')
        formats_dir = str(REPO_ROOT / 'formats' / 'kinetic-typography')
        for bad in [formats_dir, '../formats/kinetic-typography', 'formats/kinetic-typography', 'Kinetic', 'a' * 65, 'kinetic_typography']:
            with self.subTest(bad=bad):
                self.rejected('reelsyntax_format_show', {'format_id': bad})
        self.assertIn('Unknown format', self.rejected('reelsyntax_format_show', {'format_id': 'no-such-format'}))

    def test_format_make_dry_run_is_offline_and_writes_nothing(self):
        payload = self.ok('reelsyntax_format_make', {'prompt': PROMPT, 'dry_run': True, 'attribution': True, 'video_lang': 'tr', 'ui_lang': 'de', 'seed': 77})
        self.assertTrue(payload['dry_run'])
        self.assertEqual(payload['provider'], 'offline_rules')
        self.assertTrue(payload['attribution'])
        self.assertEqual(payload['languages']['video_lang'], 'tr')
        self.assertEqual(payload['languages']['ui_lang'], 'de')
        self.assertEqual(payload['seed'], 77)
        self.assertEqual(list(self.workspace.iterdir()), [])
        self.assertIn('omit project', self.rejected('reelsyntax_format_make', {'prompt': PROMPT, 'dry_run': True, 'project': 'p'}))
        self.assertIn('project is required', self.rejected('reelsyntax_format_make', {'prompt': PROMPT}))
        self.assertIn('prompt is required', self.rejected('reelsyntax_format_make', {'project': 'p'}))

    def test_format_make_closed_parameter_validation(self):
        for arguments in [
            {'prompt': PROMPT, 'dry_run': 'true'},
            {'prompt': PROMPT, 'dry_run': True, 'aspect': '21:9'},
            {'prompt': PROMPT, 'dry_run': True, 'duration_sec': 3},
            {'prompt': PROMPT, 'dry_run': True, 'duration_sec': 181},
            {'prompt': PROMPT, 'dry_run': True, 'seed': -1},
            {'prompt': PROMPT, 'dry_run': True, 'provider': 'openai_compat'},
            {'prompt': PROMPT, 'dry_run': True, 'allow_network': True},
            {'prompt': PROMPT, 'dry_run': True, 'video_lang': 'EN_us'},
            {'prompt': PROMPT, 'dry_run': True, 'ui_lang': '../en'},
            {'prompt': PROMPT, 'dry_run': True, 'format_id': '/etc'},
            {'prompt': '', 'dry_run': True},
            {'project': 'p', 'step': {'id': 'idea', 'action': 'skip'}},
            {'project': 'p', 'step': {'id': 'idea', 'extra': 1}},
        ]:
            with self.subTest(arguments=arguments):
                self.rejected('reelsyntax_format_make', arguments)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_format_make_offline_by_default_and_explicit_opt_in(self):
        captured = []

        def fake_make_video(prompt, **kwargs):
            captured.append(kwargs)
            return {'dry_run': True}

        with patch('reelsyntax.make.make_video', side_effect=fake_make_video):
            self.ok('reelsyntax_format_make', {'prompt': PROMPT, 'dry_run': True})
            self.ok('reelsyntax_format_make', {'prompt': PROMPT, 'dry_run': True, 'offline': False})
        self.assertEqual(captured[0]['provider_name'], 'offline_rules')
        self.assertFalse(captured[0]['allow_network'])
        self.assertIsNone(captured[1]['provider_name'])
        self.assertTrue(captured[1]['allow_network'])

    def test_format_make_creates_gated_project_and_steps_inside_workspace(self):
        started = self.ok('reelsyntax_format_make', {'prompt': PROMPT, 'project': 'out/reel', 'format_id': 'kinetic-typography'})
        self.assertEqual(started['project'], 'out/reel')
        self.assertEqual(started['status'], 'awaiting_approval')
        self.assertEqual(started['pending_gate'], 'idea')
        self.assertEqual(started['provider'], 'offline_rules')
        self.assertNotIn('next_actions', started)
        self.assertEqual([item['arguments']['step']['action'] for item in started['next_steps']], ['approve', 'edit', 'back'])
        self.assertTrue((self.workspace / 'out/reel/prompt.json').is_file())
        self.assertFalse(read_json(self.workspace / 'out/reel/prompt.json')['attribution'])

        self.assertIn('absent or empty', self.rejected('reelsyntax_format_make', {'prompt': PROMPT, 'project': 'out/reel'}))
        self.assertIn('Current gate', self.rejected('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'script', 'action': 'approve'}}))
        self.assertIn('step.edit', self.rejected('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'idea', 'action': 'edit'}}))
        self.assertIn('step.edit', self.rejected('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'idea', 'edit': 'x'}}))
        self.assertIn('cannot be combined', self.rejected('reelsyntax_format_make', {'project': 'out/reel', 'prompt': PROMPT, 'step': {'id': 'idea'}}))
        self.assertIn('Unknown step', self.rejected('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'render-all'}}))
        self.assertIn('existing workspace project', self.rejected('reelsyntax_format_make', {'step': {'id': 'idea'}}))

        approved = self.ok('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'idea', 'action': 'approve'}})
        self.assertEqual(approved['pending_gate'], 'script')
        self.assertIn('idea', approved['approvals'])
        edited = self.ok('reelsyntax_format_make', {'project': str(self.workspace / 'out/reel'), 'step': {'id': 'script', 'action': 'edit', 'edit': 'Shorter, punchier lines'}})
        self.assertEqual(edited['project'], 'out/reel')
        revisions = read_json(self.workspace / 'out/reel/prompt.json')['revisions']
        self.assertEqual(revisions[-1]['kind'], 'step_edit')
        backed = self.ok('reelsyntax_format_make', {'project': 'out/reel', 'step': {'id': 'script', 'action': 'back'}})
        self.assertIn(backed['status'], {'awaiting_approval', 'paused'})

    def test_format_make_and_revise_enforce_path_containment(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external).resolve()
            initialize(outside / 'proj')
            (self.workspace / 'occupied').mkdir()
            (self.workspace / 'occupied/file.txt').write_text('x', encoding='utf-8')
            (self.workspace / 'plain.txt').write_text('x', encoding='utf-8')
            for target in [str(outside / 'new'), '../escape', 'a/../../escape', '.', '/escape', 'C:/x', 'C:rel', 'a\\b', 'occupied', 'plain.txt']:
                with self.subTest(target=target):
                    self.rejected('reelsyntax_format_make', {'prompt': PROMPT, 'project': target})
            for target in [str(outside / 'proj'), '../proj', '/escape', 'C:rel', 'a\\b', 'missing']:
                with self.subTest(target=target):
                    self.rejected('reelsyntax_format_revise', {'project': target, 'instruction': 'heading: Escape'})
                    self.rejected('reelsyntax_format_make', {'project': target, 'step': {'id': 'idea'}})
            link = self.workspace / 'link'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('symlinks unavailable')
            self.assertIn('Symbolic links', self.rejected('reelsyntax_format_make', {'prompt': PROMPT, 'project': 'link/new'}))
            self.assertIn('Symbolic links', self.rejected('reelsyntax_format_revise', {'project': 'link/proj', 'instruction': 'heading: Escape'}))
            self.assertFalse((outside / 'new').exists())
            self.assertFalse((outside / '..' / 'escape').exists())

    def test_windows_path_forms_preserve_backslashes_and_reject_roots(self):
        fake = UnifiedMcpServer.__new__(UnifiedMcpServer)
        fake.workspace = PureWindowsPath('C:/ws')
        fake.workspace_alias = PureWindowsPath('C:/ws')
        with patch('reelsyntax.mcp_server.Path', PureWindowsPath):
            self.assertEqual(fake.workspace_relative('out/reel'), 'out/reel')
            self.assertEqual(fake.workspace_relative('a\\b'), 'a\\b')
            self.assertEqual(fake.workspace_relative('C:\\ws\\out\\reel'), 'out/reel')
            for bad in ['/escape', '\\escape', 'C:rel', 'C:\\outside\\proj']:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    fake.workspace_relative(bad)
        with tempfile.TemporaryDirectory() as empty_ws:
            empty_server = UnifiedMcpServer(gateway=Mock(), workspace=Path(empty_ws))
            try:
                is_error, payload = call(empty_server, 'reelsyntax_format_make', {'prompt': PROMPT, 'project': '.'})
                self.assertTrue(is_error, payload)
            finally:
                empty_server.close()

    def test_format_revise_is_checkpointed_lock_aware_and_offline(self):
        root = self.workspace / 'inside'
        initialize(root)
        scenes = [scene['id'] for scene in read_json(root / 'reel.json')['scenes']]
        lock(root, [scenes[0]])
        self.assertIn('locked', self.rejected('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'heading: Nope', 'scene_id': scenes[0]}))
        self.assertIn('profile requires render', self.rejected('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'x', 'profile': 'hero'}))
        self.rejected('reelsyntax_format_revise', {'project': 'inside', 'instruction': ''})
        self.rejected('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'x', 'render': 'yes'})
        revised = self.ok('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'scene 2 heading: Cache Hits'})
        self.assertEqual(revised['project'], 'inside')
        self.assertEqual(revised['changed_scenes'], [scenes[1]])
        self.assertIn(scenes[0], revised['preserved_scenes'])
        self.assertTrue((root / f".reelsyntax/checkpoints/{revised['checkpoint']}.json").is_file())
        self.assertNotIn('render', revised)
        self.assertEqual(read_json(root / 'reel.json')['scenes'][1]['params']['heading'], 'Cache Hits')

        captured = []

        def fake_revise(project_dir, instruction, **kwargs):
            captured.append(kwargs)
            return {'project': str(project_dir)}

        with patch('reelsyntax.make.revise_project', side_effect=fake_revise):
            self.ok('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'warm palette'})
            self.ok('reelsyntax_format_revise', {'project': 'inside', 'instruction': 'warm palette', 'offline': False, 'render': True, 'profile': 'draft'})
        self.assertEqual((captured[0]['provider_name'], captured[0]['allow_network'], captured[0]['render_after']), ('offline_rules', False, False))
        self.assertEqual((captured[1]['provider_name'], captured[1]['allow_network'], captured[1]['render_after'], captured[1]['profile']), (None, True, True, 'draft'))

    def test_format_tools_run_without_pillow(self):
        script = (
            "import json, sys, tempfile\n"
            "sys.modules['PIL'] = None\n"
            "from pathlib import Path\n"
            "from unittest.mock import Mock\n"
            "from reelsyntax.mcp_server import UnifiedMcpServer\n"
            "from reelsyntax.project import initialize\n"
            "ws = Path(tempfile.mkdtemp()).resolve()\n"
            "server = UnifiedMcpServer(gateway=Mock(), workspace=ws)\n"
            "out = {}\n"
            "out['list'] = server.dispatch_tool('reelsyntax_format_list', {})['count']\n"
            "out['show'] = server.dispatch_tool('reelsyntax_format_show', {'format_id': 'kinetic-typography'})['manifest']['id']\n"
            "out['dry'] = server.dispatch_tool('reelsyntax_format_make', {'prompt': 'calm 10s reel', 'dry_run': True})['budget']['frames']\n"
            "out['make'] = server.dispatch_tool('reelsyntax_format_make', {'prompt': 'calm 10s reel', 'project': 'p'})['pending_gate']\n"
            "initialize(ws / 'q')\n"
            "out['revise'] = server.dispatch_tool('reelsyntax_format_revise', {'project': 'q', 'instruction': 'scene 1 heading: Hi'})['changed_scenes']\n"
            "out['pil'] = 'PIL' in sys.modules and sys.modules['PIL'] is None\n"
            "print(json.dumps(out))\n"
        )
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join(filter(None, [str(REPO_ROOT), os.environ.get('PYTHONPATH', '')]))}
        result = subprocess.run([sys.executable, '-c', script], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(payload['pil'])
        self.assertGreater(payload['list'], 0)
        self.assertEqual(payload['show'], 'kinetic-typography')
        self.assertEqual(payload['dry'], 300)
        self.assertEqual(payload['make'], 'idea')
        self.assertEqual(len(payload['revise']), 1)


if __name__ == '__main__':
    unittest.main()
