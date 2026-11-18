import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from reelsyntax.gateway import (
    INTEGRATIONS,
    REPO_ROOT,
    McpGateway,
    camera_to_after_effects,
    diff_capability_snapshots,
    resolve_integration,
    summarize_tool_entry,
    validate_args_against_schema,
)
from reelsyntax.mcp_server import GATEWAY_TOOLS, UnifiedMcpServer
from reelsyntax.sync_audit import evaluate_submodule_candidate

MOCK_DOWNSTREAM_SERVER = textwrap.dedent("""
import json, os, sys
crash_once_file = sys.argv[1]
tools = [
    {
        "name": "render_preview",
        "description": "Render preview frame in mock studio",
        "inputSchema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}, "width": {"type": "integer"}},
            "required": ["filename"],
            "additionalProperties": False
        }
    },
    {
        "name": "comfyui_generate_texture",
        "description": "External generative diffusion workflow",
        "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}}
    }
]
for raw in sys.stdin:
    msg = json.loads(raw)
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        out = {"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "Remirdy Blender Studio", "version": "0.2.0"}}}
        sys.stdout.write(json.dumps(out) + "\\n"); sys.stdout.flush()
    elif method == "tools/list":
        out = {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}}
        sys.stdout.write(json.dumps(out) + "\\n"); sys.stdout.flush()
    elif method == "tools/call":
        if os.path.exists(crash_once_file):
            os.remove(crash_once_file)
            sys.exit(1)
        args = msg["params"].get("arguments", {})
        out = {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": json.dumps({"rendered": args["filename"]})}], "isError": False}}
        sys.stdout.write(json.dumps(out) + "\\n"); sys.stdout.flush()
""")


class GatewayAndMcpSimulatedTests(unittest.TestCase):
    def test_uninitialized_submodules_degrade_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp, 'isolated_workspace', 'ReelSyntax')
            (fake_root / 'integrations/BlenderMCP').mkdir(parents=True)
            (fake_root / 'integrations/AfterEffectsMCP').mkdir(parents=True)
            env_backup = {k: os.environ.pop(k, None) for k in ('REELSYNTAX_BLENDER_MCP_ROOT', 'REELSYNTAX_BLENDER_MCP_COMMAND', 'REELSYNTAX_AE_MCP_ROOT', 'REELSYNTAX_AE_MCP_COMMAND')}
            try:
                with McpGateway(repo_root=fake_root, state_root=fake_root) as gw:
                    st = gw.status()
                    self.assertFalse(st['integrations']['blender']['submodule_initialized'])
                    self.assertFalse(st['integrations']['after-effects']['submodule_initialized'])
                    snap = gw.refresh_capabilities(persist=True)
                    self.assertIsInstance(snap['total_tools'], int)
            finally:
                for k, v in env_backup.items():
                    if v is not None:
                        os.environ[k] = v

    def test_capability_schema_diff_detects_additive_and_breaking_changes(self):
        t_v1 = summarize_tool_entry('blender', {
            'name': 'setup_camera',
            'description': 'Configure camera',
            'inputSchema': {'type': 'object', 'properties': {'focal_length': {'type': 'number'}}, 'required': []},
        })
        t_v1_removed = summarize_tool_entry('blender', {'name': 'old_op', 'description': 'Legacy', 'inputSchema': {'type': 'object', 'properties': {}}})

        t_v2_additive = summarize_tool_entry('blender', {
            'name': 'setup_camera',
            'description': 'Configure camera',
            'inputSchema': {'type': 'object', 'properties': {'focal_length': {'type': 'number'}, 'dof': {'type': 'boolean'}}, 'required': []},
        })
        t_v2_new = summarize_tool_entry('blender', {'name': 'render_sequence', 'description': 'Render PNG pass', 'inputSchema': {'type': 'object', 'properties': {}}})

        additive_diff = diff_capability_snapshots({'tools': [t_v1]}, {'tools': [t_v2_additive, t_v2_new]})
        self.assertTrue(additive_diff['backward_compatible'])
        self.assertEqual(additive_diff['added'], ['blender:render_sequence'])
        self.assertEqual(additive_diff['modified'][0]['added_optional_args'], ['dof'])

        t_v3_breaking = summarize_tool_entry('blender', {
            'name': 'setup_camera',
            'description': 'Configure camera',
            'inputSchema': {'type': 'object', 'properties': {'focal_length': {'type': 'string'}}, 'required': ['focal_length']},
        })
        breaking_diff = diff_capability_snapshots({'tools': [t_v1, t_v1_removed]}, {'tools': [t_v3_breaking]})
        self.assertFalse(breaking_diff['backward_compatible'])
        self.assertEqual(breaking_diff['removed'], ['blender:old_op'])
        self.assertGreaterEqual(breaking_diff['breaking_count'], 2)

    def test_schema_argument_validation(self):
        schema = {
            'type': 'object',
            'properties': {'width': {'type': 'integer'}, 'format': {'type': 'string', 'enum': ['mp4', 'mov']}},
            'required': ['width'],
            'additionalProperties': False,
        }
        validate_args_against_schema({'width': 1920, 'format': 'mp4'}, schema, 'after_effects:render_preview')
        for bad in [{}, {'width': True}, {'width': '1920'}, {'width': 1920, 'format': 'avi'}, {'width': 1920, 'extra': 1}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_args_against_schema(bad, schema, 'after_effects:render_preview')

    def test_mock_downstream_lazy_startup_policy_and_crash_recovery(self):
        from reelsyntax.gateway import DownstreamMcpSession
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, 'mock_mcp.py')
            crash_flag = Path(tmp, 'crash_once.flag')
            script.write_text(MOCK_DOWNSTREAM_SERVER, encoding='utf-8')
            crash_flag.write_text('1', encoding='utf-8')

            gw = McpGateway(repo_root=Path(tmp), state_root=Path(tmp), timeout=5.0)
            try:
                resolved = {
                    'id': 'blender',
                    'namespace': 'blender',
                    'capability': 'blender-mcp',
                    'repository': 'Remirdy/BlenderMCP',
                    'submodule_initialized': True,
                    'pinned_commit': 'deadbeef',
                    'package_version': '0.2.0',
                    'mcp_server_ready': True,
                    'command': [sys.executable, str(script), str(crash_flag)],
                    'cwd': tmp,
                    'env_overrides': {},
                }
                session = DownstreamMcpSession(resolved, timeout=5.0)
                self.assertIsNone(session.process)
                gw._sessions['blender'] = session
                listing = session.request_with_recovery('tools/list', {})
                entries = [summarize_tool_entry('blender', t) for t in listing['tools']]
                gw._catalog_cache = {'total_tools': len(entries), 'tools': entries}

                search_res = gw.search_tools('render preview comfyui texture', constraints={'offline': True, 'no_paid_services': True})
                selected_ids = [x['id'] for x in search_res['selected_tools']]
                self.assertIn('blender:render_preview', selected_ids)
                self.assertNotIn('blender:comfyui_generate_texture', selected_ids)
                self.assertEqual(search_res['full_schemas_exposed'], 0)

                with self.assertRaisesRegex(ValueError, 'blocked by ReelSyntax offline'):
                    gw.call_tool('blender:comfyui_generate_texture', {'prompt': 'stone'})

                call_res = gw.call_tool('blender:render_preview', {'filename': 'shot01.png', 'width': 960})
                self.assertTrue(call_res['ok'])
                self.assertIn('shot01.png', call_res['content'][0]['text'])
            finally:
                gw.close()

    def test_unified_mcp_stdio_server_wire_protocol_and_bounded_list(self):
        self.assertLessEqual(len(GATEWAY_TOOLS), 16)
        proc = subprocess.Popen(
            [sys.executable, '-m', 'reelsyntax', 'mcp'],
            cwd=str(REPO_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            init_req = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}}).encode()
            proc.stdin.write(init_req + b'\n')
            proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
            list_body = json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}).encode()
            proc.stdin.write(f'Content-Length: {len(list_body)}\r\n\r\n'.encode('ascii') + list_body)
            call_req = json.dumps({
                'jsonrpc': '2.0',
                'id': 3,
                'method': 'tools/call',
                'params': {'name': 'reelsyntax_skills_search', 'arguments': {'intent': 'siyah kare', 'include_mcp_tools': False}},
            }).encode()
            proc.stdin.write(call_req + b'\n')
            proc.stdin.flush()

            init_resp = json.loads(proc.stdout.readline().decode())
            self.assertEqual(init_resp['result']['serverInfo']['name'], 'reelsyntax-unified-gateway')

            hdr = proc.stdout.readline().decode()
            self.assertTrue(hdr.lower().startswith('content-length:'))
            length = int(hdr.split(':', 1)[1].strip())
            proc.stdout.readline()
            list_resp = json.loads(proc.stdout.read(length).decode())
            self.assertEqual(len(list_resp['result']['tools']), len(GATEWAY_TOOLS))

            call_resp = json.loads(proc.stdout.readline().decode())
            self.assertFalse(call_resp['result']['isError'])
            payload = json.loads(call_resp['result']['content'][0]['text'])
            self.assertEqual(payload['skill_bodies_read'], 0)
            self.assertIn('black-frame-detection', [s['id'] for s in payload['selected']])
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()
            proc.wait(timeout=5)

    def test_camera_optics_interchange_math(self):
        ae = camera_to_after_effects(1920, 1080, focal_mm=50.0, blender_xyz=(0.0, -4.0, 1.0), target_xyz=(0.0, 0.0, 0.0), scale_px_per_m=100.0, sensor_width_mm=36.0)
        self.assertAlmostEqual(ae['zoom_pixels'], 1920 * 50.0 / 36.0, places=3)
        self.assertEqual(ae['ae_position'], [960.0, 440.0, -400.0])
        self.assertEqual(ae['ae_point_of_interest'], [960.0, 540.0, 0.0])


class SubmoduleAndLiveFirstPartyMcpTests(unittest.TestCase):
    def test_submodule_static_sync_audit(self):
        for target, spec in INTEGRATIONS.items():
            sub_dir = REPO_ROOT / spec['submodule_path']
            if not (sub_dir / ('pyproject.toml' if target == 'blender' else 'package.json')).is_file():
                self.skipTest(f'{target} submodule not initialized in this checkout')
            report = evaluate_submodule_candidate(target, REPO_ROOT)
            self.assertTrue(report['ok'], report)
            self.assertGreater(report['extracted_tool_count'], 100)

    def test_live_first_party_gateway_discovery_and_dry_run(self):
        bl = resolve_integration('blender')
        ae = resolve_integration('after-effects')
        if not (bl['mcp_server_ready'] and ae['mcp_server_ready']):
            self.skipTest('Local first-party MCP server runtimes are not built in this environment')
        with McpGateway() as gw:
            snap = gw.refresh_capabilities(persist=False)
            self.assertGreater(snap['total_tools'], 500)
            bl_prev = gw.describe_tool('blender:render_preview')
            ae_prev = gw.describe_tool('after_effects:render_preview')
            self.assertNotEqual(bl_prev['schema_sha256'], ae_prev['schema_sha256'])
            self.assertIn('aepPath', ae_prev['inputSchema'].get('properties', {}))
            self.assertIn('filename', bl_prev['inputSchema'].get('properties', {}))

            good_jsx = gw.call_tool('after_effects:jsx_dry_run', {'jsxContent': 'var c = app.project.item(1);'})
            self.assertTrue(good_jsx['ok'])
            self.assertIn('"valid": true', good_jsx['content'][0]['text'])

            bad_jsx = gw.call_tool('after_effects:jsx_dry_run', {'jsxContent': 'var bad = comp.layer(0);'})
            self.assertIn('"valid": false', bad_jsx['content'][0]['text'])

            with self.assertRaisesRegex(ValueError, 'alembicPath does not exist'):
                gw.call_tool('after_effects:houdini_alembic_bridge', {'alembicPath': '/nonexistent/sim.abc', 'outputFolder': '/tmp'})


if __name__ == '__main__':
    unittest.main()
