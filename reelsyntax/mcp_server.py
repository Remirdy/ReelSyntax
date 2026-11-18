import json
from pathlib import Path
import sys

from . import __version__
from .formats.schema import FORMAT_CATEGORIES, FORMAT_ID_RE
from .gateway import McpGateway, validate_args_against_schema
from .lang.catalog import LOCALE_TAG_RE
from ReelSyntax_Skills.tools.registry import contained_path, unique_object
from . import project, quality, skills

FORMAT_ASPECT_ENUM = ['9:16', '1:1', '16:9', '4:5']
FORMAT_STEP_ACTIONS = ['run', 'approve', 'edit', 'back']
FORMAT_SUMMARY_KEYS = ('id', 'version', 'title', 'category', 'aspect', 'duration_sec', 'languages', 'engines', 'needs')
FORMAT_DOC_MAX_BYTES = 65_536
FORMAT_MAKE_CREATE_ONLY = ('prompt', 'format_id', 'video_lang', 'ui_lang', 'aspect', 'duration_sec', 'seed', 'dry_run', 'attribution')

FORMAT_TOOLS = [
    {
        'name': 'reelsyntax_format_list',
        'description': 'List installed declarative prompt-to-video formats as concise summaries without full manifests.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'category': {'type': 'string', 'enum': sorted(FORMAT_CATEGORIES)},
            },
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_format_show',
        'description': 'Lazily load one validated format manifest with its steps, approval gates and QC rules.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'format_id': {'type': 'string', 'minLength': 1, 'maxLength': 64, 'description': 'Format identifier from reelsyntax_format_list.'},
                'include_docs': {'type': 'boolean', 'default': False},
            },
            'required': ['format_id'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_format_make',
        'description': 'Create a prompt-to-video project inside the MCP workspace, preview it with dry_run, or advance an existing project one gated step.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'prompt': {'type': 'string', 'minLength': 1, 'maxLength': 4000},
                'project': {'type': 'string', 'minLength': 1, 'maxLength': 512, 'description': 'Workspace-relative project directory.'},
                'format_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                'video_lang': {'type': 'string', 'minLength': 2, 'maxLength': 16},
                'ui_lang': {'type': 'string', 'minLength': 2, 'maxLength': 16},
                'aspect': {'type': 'string', 'enum': FORMAT_ASPECT_ENUM},
                'duration_sec': {'type': 'integer', 'minimum': 4, 'maximum': 180},
                'seed': {'type': 'integer', 'minimum': 0, 'maximum': 4294967295, 'default': 42},
                'dry_run': {'type': 'boolean', 'default': False},
                'yes': {'type': 'boolean', 'default': False},
                'attribution': {'type': 'boolean', 'default': False},
                'offline': {'type': 'boolean', 'default': True},
                'step': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                        'action': {'type': 'string', 'enum': FORMAT_STEP_ACTIONS, 'default': 'run'},
                        'edit': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
                    },
                    'required': ['id'],
                    'additionalProperties': False,
                },
            },
            'additionalProperties': False,
        },
    },
    {
        'name': 'reelsyntax_format_revise',
        'description': 'Apply a checkpointed, lock-aware revision to unlocked scenes of a workspace project.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'project': {'type': 'string', 'minLength': 1, 'maxLength': 512},
                'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
                'scene_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                'render': {'type': 'boolean', 'default': False},
                'profile': {'type': 'string', 'enum': ['draft', 'production', 'hero']},
                'offline': {'type': 'boolean', 'default': True},
            },
            'required': ['project', 'instruction'],
            'additionalProperties': False,
        },
    },
]

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
    *FORMAT_TOOLS,
]


def _checked_format_id(value: str) -> str:
    if len(value) > 64 or not FORMAT_ID_RE.fullmatch(value):
        raise ValueError(f'Invalid format identifier: {value!r}')
    return value


def _checked_locale(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not LOCALE_TAG_RE.fullmatch(value):
        raise ValueError(f'{field} must be a BCP-47 style locale tag such as en, tr or pt-BR')
    return value


def _format_summary(manifest: dict) -> dict:
    summary = {key: manifest[key] for key in FORMAT_SUMMARY_KEYS if key in manifest}
    summary['steps'] = [step['id'] for step in manifest.get('steps', [])]
    summary['approval_gates'] = [step['id'] for step in manifest.get('steps', []) if step.get('gate') == 'approve']
    return summary


class UnifiedMcpServer:
    def __init__(self, gateway: McpGateway | None = None, workspace: Path | None = None):
        self.workspace_alias = Path(workspace or Path.cwd()).expanduser().absolute()
        self.workspace = self.workspace_alias.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError('MCP workspace must be an existing directory')
        self.gateway = gateway or McpGateway()

    def close(self):
        self.gateway.close()

    def workspace_relative(self, value: str) -> str:
        candidate = Path(value)
        if not (candidate.is_absolute() or candidate.drive or candidate.root):
            return value
        for root in [self.workspace, self.workspace_alias]:
            try:
                return candidate.relative_to(root).as_posix()
            except ValueError:
                continue
        raise ValueError('Project must stay inside the authorized MCP workspace')

    def project_directory(self, value: str) -> Path:
        directory = contained_path(self.workspace, self.workspace_relative(value), must_exist=False)
        if not directory.is_dir():
            raise ValueError('Project directory does not exist inside the MCP workspace')
        return directory

    def new_project_directory(self, value: str) -> Path:
        directory = contained_path(self.workspace, self.workspace_relative(value), must_exist=False)
        if directory == self.workspace:
            raise ValueError('New project must use a subdirectory inside the MCP workspace')
        if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
            raise ValueError('New project directory must be absent or empty inside the MCP workspace')
        return directory

    def _format_response(self, result: dict) -> dict:
        root = Path(result['project'])
        relative = root.relative_to(self.workspace).as_posix()
        result['project'] = relative
        result.pop('next_actions', None)
        pending = result.get('pending_gate')
        if pending:
            steps = [{'id': pending, 'action': 'approve'}, {'id': pending, 'action': 'edit', 'edit': '...'}, {'id': pending, 'action': 'back'}]
            result['next_steps'] = [{'tool': 'reelsyntax_format_make', 'arguments': {'project': relative, 'step': item}} for item in steps]
        return result

    def format_list(self, arguments: dict) -> dict:
        from .formats.registry import discover_formats
        from .make import BUILTIN_PROMPT_DIRECT_MANIFEST

        category = arguments.get('category')
        manifests = discover_formats(category=category)
        summaries = [_format_summary(item) for item in manifests]
        known = {item['id'] for item in summaries}
        builtin = BUILTIN_PROMPT_DIRECT_MANIFEST
        if builtin['id'] not in known and category in (None, builtin['category']):
            summaries.append({**_format_summary(builtin), 'builtin': True})
        summaries.sort(key=lambda item: item['id'])
        return {'count': len(summaries), 'formats': summaries, 'full_manifests_exposed': 0}

    def format_show(self, arguments: dict) -> dict:
        import copy

        from .formats.registry import get_format
        from .formats.schema import validate_format_manifest
        from .make import BUILTIN_PROMPT_DIRECT_MANIFEST

        format_id = _checked_format_id(arguments['format_id'])
        try:
            manifest = get_format(format_id)
        except ValueError:
            if format_id != BUILTIN_PROMPT_DIRECT_MANIFEST['id']:
                raise
            manifest = {**copy.deepcopy(validate_format_manifest(BUILTIN_PROMPT_DIRECT_MANIFEST)), 'builtin': True}
        source = manifest.pop('path', None)
        result = {'manifest': manifest, 'summary': _format_summary(manifest)}
        if arguments.get('include_docs', False) and source:
            doc_path = contained_path(Path(source), 'FORMAT.md', must_exist=False)
            if doc_path.is_file():
                if doc_path.stat().st_size > FORMAT_DOC_MAX_BYTES:
                    raise ValueError('FORMAT.md exceeds the 64 KiB documentation limit')
                result['docs'] = doc_path.read_text(encoding='utf-8')
        return result

    def format_make(self, arguments: dict) -> dict:
        from . import make

        offline = bool(arguments.get('offline', True))
        provider_name = 'offline_rules' if offline else None
        yes = bool(arguments.get('yes', False))
        step = arguments.get('step')
        if step is not None:
            conflicting = sorted(key for key in FORMAT_MAKE_CREATE_ONLY if key in arguments)
            if conflicting:
                raise ValueError(f'step mode cannot be combined with: {", ".join(conflicting)}')
            if 'project' not in arguments:
                raise ValueError('step mode requires an existing workspace project')
            root = self.project_directory(arguments['project'])
            step_id = _checked_format_id(step['id'])
            action = step.get('action', 'run')
            if (action == 'edit') != ('edit' in step):
                raise ValueError("step.edit is required for action 'edit' and forbidden otherwise")
            result = make.step_project(
                root,
                step_id,
                approve=action == 'approve',
                edit=step.get('edit'),
                back=action == 'back',
                yes=yes,
                provider_name=provider_name,
                allow_network=not offline,
            )
            return self._format_response(result)
        if 'prompt' not in arguments:
            raise ValueError('prompt is required unless step is provided')
        format_id = arguments.get('format_id')
        if format_id is not None:
            _checked_format_id(format_id)
        dry_run = bool(arguments.get('dry_run', False))
        target = None
        if dry_run:
            if 'project' in arguments:
                raise ValueError('dry_run never writes files; omit project')
        else:
            if 'project' not in arguments:
                raise ValueError('project is required unless dry_run is true')
            target = self.new_project_directory(arguments['project'])
        result = make.make_video(
            arguments['prompt'],
            format_id=format_id,
            out_dir=target,
            provider_name=provider_name,
            video_lang=_checked_locale(arguments.get('video_lang'), 'video_lang'),
            ui_lang=_checked_locale(arguments.get('ui_lang'), 'ui_lang'),
            aspect=arguments.get('aspect'),
            duration_sec=arguments.get('duration_sec'),
            seed=int(arguments.get('seed', 42)),
            yes=yes,
            dry_run=dry_run,
            allow_network=not offline,
            attribution=bool(arguments.get('attribution', False)),
        )
        if dry_run:
            return result
        return self._format_response(result)

    def format_revise(self, arguments: dict) -> dict:
        from .make import revise_project

        offline = bool(arguments.get('offline', True))
        root = self.project_directory(arguments['project'])
        if 'profile' in arguments and not arguments.get('render', False):
            raise ValueError('profile requires render to be true')
        result = revise_project(
            root,
            arguments['instruction'],
            scene_id=arguments.get('scene_id'),
            provider_name='offline_rules' if offline else None,
            allow_network=not offline,
            render_after=bool(arguments.get('render', False)),
            profile=arguments.get('profile'),
        )
        result['project'] = Path(result['project']).relative_to(self.workspace).as_posix()
        return result

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
        if name == 'reelsyntax_format_list':
            return self.format_list(arguments)
        if name == 'reelsyntax_format_show':
            return self.format_show(arguments)
        if name == 'reelsyntax_format_make':
            return self.format_make(arguments)
        if name == 'reelsyntax_format_revise':
            return self.format_revise(arguments)
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
                        'instructions': 'Unified ReelSyntax Gateway. Search skills with reelsyntax_skills_search; discover downstream BlenderMCP/AfterEffectsMCP tools progressively via gateway_search_tools -> gateway_describe_tool -> gateway_call_tool; build prompt-to-video projects via reelsyntax_format_list -> reelsyntax_format_show -> reelsyntax_format_make -> reelsyntax_format_revise.',
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
