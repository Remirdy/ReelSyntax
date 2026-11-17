import tempfile
import json
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

from reelsyntax.gateway import validate_args_against_schema
from reelsyntax.mcp_server import UnifiedMcpServer
from reelsyntax.project import initialize


def call(server, name, arguments):
    return server.handle_message({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}})


class McpBoundaryTests(unittest.TestCase):
    def test_published_schema_rejects_bad_policy_types_before_dispatch(self):
        gateway = Mock()
        gateway.call_tool.return_value = {'ok': True}
        server = UnifiedMcpServer(gateway=gateway)
        try:
            for arguments in [
                {'tool_id': 'blender:render_preview', 'offline': 'false'},
                {'tool_id': 'blender:render_preview', 'no_paid_services': None},
                {'tool_id': 'blender:render_preview', 'extra': 'unexpected'},
                {'tool_id': 'blender:render_preview', 'arguments': []},
            ]:
                with self.subTest(arguments=arguments):
                    response = call(server, 'gateway_call_tool', arguments)
                    self.assertTrue(response['result']['isError'], response)
            gateway.call_tool.assert_not_called()
        finally:
            server.close()

    def test_nested_null_and_numeric_schema_constraints(self):
        schema = {'type': 'object', 'properties': {
            'budget': {'type': 'integer', 'minimum': 1, 'maximum': 20},
            'assets': {'type': 'array', 'items': {'type': 'string'}},
            'settings': {'type': 'object', 'properties': {'offline': {'type': 'boolean'}}, 'additionalProperties': False},
        }}
        for arguments in [{'budget': None}, {'budget': 0}, {'budget': 21}, {'assets': [3]}, {'settings': {'offline': 'false'}}, {'settings': {'unknown': True}}]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                validate_args_against_schema(arguments, schema, 'test')
        validate_args_against_schema({'budget': 2, 'assets': ['wav'], 'settings': {'offline': False}}, schema, 'test')

    def test_project_calls_stay_in_authorized_workspace(self):
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as external:
            initialize(Path(workspace, 'inside'))
            initialize(Path(external, 'outside'))
            server = UnifiedMcpServer(gateway=Mock(), workspace=Path(workspace))
            try:
                allowed = call(server, 'reelsyntax_project_validate', {'project': 'inside'})
                self.assertFalse(allowed['result']['isError'], allowed)
                absolute = call(server, 'reelsyntax_project_validate', {'project': str(Path(workspace, 'inside'))})
                self.assertFalse(absolute['result']['isError'], absolute)
                for tool in ['reelsyntax_project_validate', 'reelsyntax_project_plan', 'reelsyntax_project_qc']:
                    response = call(server, tool, {'project': str(Path(external, 'outside'))})
                    self.assertTrue(response['result']['isError'], response)
                link = Path(workspace, 'link')
                try:
                    link.symlink_to(Path(workspace, 'inside'), target_is_directory=True)
                except OSError:
                    return
                self.assertTrue(call(server, 'reelsyntax_project_validate', {'project': 'link'})['result']['isError'])
            finally:
                server.close()

    def test_invalid_params_is_a_protocol_error(self):
        server = UnifiedMcpServer(gateway=Mock())
        try:
            response = server.handle_message({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': []})
            self.assertEqual(response['error']['code'], -32602)
        finally:
            server.close()

    def test_stdio_survives_invalid_json_and_honors_workspace(self):
        with tempfile.TemporaryDirectory() as workspace:
            initialize(Path(workspace, 'inside'))
            requests = b'not JSON\n' + json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'reelsyntax_project_validate', 'arguments': {'project': 'inside'}}}).encode() + b'\n'
            result = subprocess.run([sys.executable, '-m', 'reelsyntax', 'mcp', '--workspace', workspace], input=requests, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(responses[0]['error']['code'], -32700)
            self.assertFalse(responses[1]['result']['isError'], responses[1])

    def test_invalid_frame_size_exits_without_reading_an_unbounded_body(self):
        result = subprocess.run([sys.executable, '-m', 'reelsyntax', 'mcp'], input=b'Content-Length: -1\r\n\r\n', capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        body = result.stdout.split(b'\r\n\r\n', 1)[-1]
        self.assertEqual(json.loads(body)['error']['code'], -32700)


if __name__ == '__main__':
    unittest.main()
