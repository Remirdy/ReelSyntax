import json
from pathlib import Path
import sys

from . import __version__
from .gateway import McpGateway, validate_args_against_schema
from ReelSyntax_Skills.tools.registry import contained_path, unique_object
from . import project, quality, skills

GATEWAY_TOOLS = [
    {
        'name': 'reelsyntax_skills_search',
        'description': 'Search the 500+ ReelSyntax production skills and matching first-party MCP tool summaries without loading full bodies or schemas.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'intent': {'type': 'string', 'description': 'Production work item or creative intent.'},
                'stage': {'type': 'string', 'enum': ['plan', 'ingest', 'build', 'edit', 'render', 'review', 'export', 'operate']},
                'assets': {'type': 'array', 'items': {'type': 'string'}},
                'capabilities': {'type': 'array', 'items': {'type': 'string'}},
                'max_skills': {'type': 'integer', 'minimum': 1, 'maximum': 20, 'default': 6},
                'context_budget': {'type': 'integer', 'minimum': 1, 'maximum': 64000, 'default': 6000},
                'include_mcp_tools': {'type': 'boolean', 'default': True},
            },
            'required': ['intent'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_skills_get',
        'description': 'Lazily load one hash-verified ReelSyntax skill instruction body or declared supporting resource.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'id': {'type': 'string', 'description': 'Skill identifier from reelsyntax_skills_search.'},
                'resource': {'type': 'string', 'description': 'Optional relative resource path declared by the skill.'},
                'context_budget': {'type': 'integer', 'minimum': 1, 'maximum': 64000, 'default': 6000},
            },
            'required': ['id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_skills_explain',
        'description': 'Return detailed routing diagnostics, morphological stems, constraint locks, and score breakdowns.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'intent': {'type': 'string'},
                'stage': {'type': 'string', 'enum': ['plan', 'ingest', 'build', 'edit', 'render', 'review', 'export', 'operate']},
            },
            'required': ['intent'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'gateway_search_tools',
        'description': 'Progressive discovery across first-party Remirdy BlenderMCP (blender:*) and AfterEffectsMCP (after_effects:*) tools. Returns concise summaries only.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'Intent or capability keywords.'},
                'namespace': {'type': 'string', 'enum': ['blender', 'after_effects']},
                'stage': {'type': 'string', 'enum': ['plan', 'ingest', 'build', 'edit', 'render', 'review', 'export', 'operate']},
                'assets': {'type': 'array', 'items': {'type': 'string'}},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25, 'default': 8},
                'refresh': {'type': 'boolean', 'default': False},
            },
            'required': ['query'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'gateway_describe_tool',
        'description': 'Lazily fetch the full JSON inputSchema and compatible skill bindings for one namespaced downstream MCP tool (e.g. blender:render_preview or after_effects:render_preview).',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'tool_id': {'type': 'string', 'description': "Namespaced tool ID '<namespace>:<tool_name>'."},
            },
            'required': ['tool_id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'gateway_call_tool',
        'description': 'Validate arguments, lazily initialize the target first-party MCP server on demand, and invoke one namespaced tool.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'tool_id': {'type': 'string', 'description': "Namespaced tool ID '<namespace>:<tool_name>'."},
                'arguments': {'type': 'object', 'default': {}},
                'offline': {'type': 'boolean', 'default': True},
                'no_paid_services': {'type': 'boolean', 'default': True},
            },
            'required': ['tool_id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_project_validate',
        'description': 'Validate a local ReelSyntax project directory and return its canonical timing metadata.',
        'inputSchema': {
            'type': 'object',
            'properties': {'project': {'type': 'string'}},
            'required': ['project'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_project_plan',
        'description': 'Inspect the sequential integer-frame timeline and constraints of a local ReelSyntax project.',
        'inputSchema': {
            'type': 'object',
            'properties': {'project': {'type': 'string'}},
            'required': ['project'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_project_qc',
        'description': 'Run technical and visual/audio heuristic QC checks on an encoded ReelSyntax project artifact.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string'},
                'profile': {'type': 'string', 'enum': ['draft', 'production', 'hero'], 'default': 'draft'},
            },
            'required': ['project'],
            'additionalProperties': False,
        },
    },
]


class UnifiedMcpServer:
    def __init__(self, gateway: McpGateway | None = None, workspace: Path | None = None):
        self.workspace_alias = Path(workspace or Path.cwd()).expanduser().absolute()
        self.workspace = self.workspace_alias.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError('MCP workspace must be an existing directory')
        self.gateway = gateway or McpGateway()

    def close(self):
        self.gateway.close()

    def project_directory(self, value: str) -> Path:
        candidate = Path(value)
        if not candidate.is_absolute():
            relative = candidate.as_posix()
        else:
            for root in [self.workspace, self.workspace_alias]:
                try:
                    relative = candidate.relative_to(root).as_posix()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError('Project must stay inside the authorized MCP workspace')
        directory = contained_path(self.workspace, relative, must_exist=False)
        if not directory.is_dir():
            raise ValueError('Project directory does not exist inside the MCP workspace')
        return directory

    def dispatch_tool(self, name: str, arguments: dict) -> dict:
        definition = next((tool for tool in GATEWAY_TOOLS if tool['name'] == name), None)
        if definition is None:
            raise ValueError(f'Unknown MCP tool: {name}')
        validate_args_against_schema(arguments, definition['inputSchema'], name)
        if name == 'reelsyntax_skills_search':
            include_mcp = arguments.get('include_mcp_tools', True)
            task = {k: v for k, v in arguments.items() if k != 'include_mcp_tools'}
            route_res = skills.search(task)
            if include_mcp:
                try:
                    mcp_hits = self.gateway.search_tools(
                        arguments['intent'],
                        stage=arguments.get('stage'),
                        assets=arguments.get('assets', []),
                        limit=5,
                    )
                    route_res['gateway_mcp_tools'] = mcp_hits['selected_tools']
                except ValueError as err:
                    route_res['gateway_mcp_tools_note'] = str(err)
            return route_res
        if name == 'reelsyntax_skills_get':
            return skills.get_skill(arguments['id'], arguments.get('context_budget', 6000), arguments.get('resource'))
        if name == 'reelsyntax_skills_explain':
            return skills.search(arguments, explain=True)
        if name == 'gateway_search_tools':
            return self.gateway.search_tools(
                arguments['query'],
                namespace=arguments.get('namespace'),
                stage=arguments.get('stage'),
                assets=arguments.get('assets', []),
                limit=arguments.get('limit', 8),
                refresh=bool(arguments.get('refresh', False)),
            )
        if name == 'gateway_describe_tool':
            return self.gateway.describe_tool(arguments['tool_id'])
        if name == 'gateway_call_tool':
            constraints = {
                'offline': bool(arguments.get('offline', True)),
                'no_paid_services': bool(arguments.get('no_paid_services', True)),
            }
            return self.gateway.call_tool(arguments['tool_id'], arguments.get('arguments', {}), constraints=constraints)
        if name == 'reelsyntax_project_validate':
            return project.load(self.project_directory(arguments['project']))[2]
        if name == 'reelsyntax_project_plan':
            _, plan, metadata = project.load(self.project_directory(arguments['project']))
            start, scenes = 0, []
            for s in plan['scenes']:
                scenes.append({'id': s['id'], 'engine': s['engine'], 'recipe': s['recipe'], 'frame_range': [start, start + s['duration_frames']]})
                start += s['duration_frames']
            return {**metadata, 'scenes': scenes, 'constraints': plan.get('constraints', {})}
        if name == 'reelsyntax_project_qc':
            return quality.check(self.project_directory(arguments['project']), arguments.get('profile', 'draft'))
        raise ValueError(f'Unknown MCP tool: {name}')

    def handle_message(self, message: dict) -> dict | None:
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return {'jsonrpc': '2.0', 'id': message.get('id') if isinstance(message, dict) else None, 'error': {'code': -32600, 'message': 'Invalid JSON-RPC 2.0 request'}}
        method = message.get('method')
        if 'id' not in message:
            return None
        req_id = message['id']
        params = message.get('params', {})
        if not isinstance(params, dict):
            return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32602, 'message': 'params must be an object'}}
        try:
            if method == 'initialize':
                protocol = params.get('protocolVersion', '2024-11-05')
                return {
                    'jsonrpc': '2.0',
                    'id': req_id,
                    'result': {
                        'protocolVersion': protocol if protocol in {'2024-11-05', '2025-03-26'} else '2024-11-05',
                        'capabilities': {'tools': {'listChanged': False}},
                        'serverInfo': {'name': 'reelsyntax-unified-gateway', 'version': __version__},
                        'instructions': 'Unified ReelSyntax Gateway. Search skills with reelsyntax_skills_search; discover downstream BlenderMCP/AfterEffectsMCP tools progressively via gateway_search_tools -> gateway_describe_tool -> gateway_call_tool.',
                    },
                }
            if method == 'ping':
                return {'jsonrpc': '2.0', 'id': req_id, 'result': {}}
            if method == 'tools/list':
                return {'jsonrpc': '2.0', 'id': req_id, 'result': {'tools': GATEWAY_TOOLS}}
            if method == 'tools/call':
                tool_name = params.get('name')
                if not isinstance(tool_name, str) or tool_name not in {t['name'] for t in GATEWAY_TOOLS}:
                    return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32602, 'message': f'Unknown gateway meta-tool: {tool_name}'}}
                try:
                    payload = self.dispatch_tool(tool_name, params.get('arguments', {}))
                    return {
                        'jsonrpc': '2.0',
                        'id': req_id,
                        'result': {'content': [{'type': 'text', 'text': json.dumps(payload, ensure_ascii=False)}], 'isError': False},
                    }
                except (ValueError, OSError, KeyError, TypeError) as err:
                    return {
                        'jsonrpc': '2.0',
                        'id': req_id,
                        'result': {'content': [{'type': 'text', 'text': json.dumps({'ok': False, 'error': str(err)}, ensure_ascii=False)}], 'isError': True},
                    }
            return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32601, 'message': f'Method not found: {method}'}}
        except Exception as err:
            return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32603, 'message': str(err)}}


MAX_MESSAGE_BYTES = 1024 * 1024
MAX_HEADER_BYTES = 8192


def _write_response(response, framed=False):
    encoded = json.dumps(response, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if framed:
        sys.stdout.buffer.write(f'Content-Length: {len(encoded)}\r\n\r\n'.encode('ascii') + encoded)
    else:
        sys.stdout.buffer.write(encoded + b'\n')
    sys.stdout.buffer.flush()


def _reject_constant(value):
    raise ValueError(f'Non-finite JSON constant: {value}')


def serve_stdio(workspace: Path | None = None):
    server = UnifiedMcpServer(workspace=workspace)
    try:
        while True:
            line = sys.stdin.buffer.readline(MAX_MESSAGE_BYTES + 1)
            if not line:
                break
            stripped = line.strip()
            if not stripped:
                continue
            framed = stripped.lower().startswith(b'content-length:')
            fatal = len(line) > MAX_MESSAGE_BYTES
            try:
                if fatal:
                    raise ValueError('MCP message exceeds the 1 MiB limit')
                if framed:
                    raw_length = stripped.split(b':', 1)[1].strip()
                    fatal = True
                    if not raw_length.isdigit() or len(raw_length) > 7:
                        raise ValueError('Content-Length must be a positive bounded integer')
                    length = int(raw_length)
                    if not 1 <= length <= MAX_MESSAGE_BYTES:
                        raise ValueError('Content-Length must be between 1 and 1048576 bytes')
                    header_size = len(line)
                    while True:
                        header = sys.stdin.buffer.readline(MAX_HEADER_BYTES + 1)
                        header_size += len(header)
                        if not header or header_size > MAX_HEADER_BYTES:
                            raise ValueError('MCP headers are incomplete or exceed the 8 KiB limit')
                        if header in (b'\r\n', b'\n'):
                            break
                    body = sys.stdin.buffer.read(length)
                    if len(body) != length:
                        raise ValueError('MCP framed body is incomplete')
                    fatal = False
                else:
                    body = stripped
                message = json.loads(body.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=_reject_constant)
            except (ValueError, UnicodeDecodeError, RecursionError) as error:
                _write_response({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': str(error)[:500]}}, framed)
                if fatal:
                    return 2
                continue
            response = server.handle_message(message)
            if response is not None:
                _write_response(response, framed)
    finally:
        server.close()
    return 0
