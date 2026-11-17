from datetime import datetime, timezone
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import platform
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading

from ReelSyntax_Skills.tools.registry import ROOT as SKILLS_ROOT, atomic_json, canonical, contained_path, digest, load_index, read_json
from ReelSyntax_Skills.tools.route import norm, terms

REPO_ROOT = SKILLS_ROOT.parent

INTEGRATIONS = {
    'blender': {
        'id': 'blender',
        'namespace': 'blender',
        'capability': 'blender-mcp',
        'repo': 'Remirdy/BlenderMCP',
        'url': 'https://github.com/Remirdy/BlenderMCP.git',
        'submodule_path': 'integrations/BlenderMCP',
        'package_name': 'remirdy-blender-studio-mcp',
        'server_names': {'Remirdy Blender Studio', 'remirdy-blender-studio-mcp'},
        'min_version': (0, 2, 0),
        'env_root': 'REELSYNTAX_BLENDER_MCP_ROOT',
        'env_cmd': 'REELSYNTAX_BLENDER_MCP_COMMAND',
        'sibling_Hints': ('BlenderMCP', 'Blender_MCP/remirdy-blender-studio-mcp', 'Blender_MCP', 'remirdy-blender-studio-mcp'),
        'cli_bin': 'remirdy-mcp',
    },
    'after-effects': {
        'id': 'after-effects',
        'namespace': 'after_effects',
        'capability': 'after-effects-mcp',
        'repo': 'Remirdy/AfterEffectsMCP',
        'url': 'https://github.com/Remirdy/AfterEffectsMCP.git',
        'submodule_path': 'integrations/AfterEffectsMCP',
        'package_name': 'motionpilot-ae-mcp',
        'server_names': {'motionpilot-ae-mcp'},
        'min_version': (1, 0, 0),
        'env_root': 'REELSYNTAX_AE_MCP_ROOT',
        'env_cmd': 'REELSYNTAX_AE_MCP_COMMAND',
        'sibling_Hints': ('AfterEffectsMCP', 'After_Effects_MCP/motionpilot-ae-mcp', 'After_Effects_MCP', 'motionpilot-ae-mcp'),
        'cli_bin': 'motionpilot-ae-mcp',
    },
}

NAMESPACE_TO_TARGET = {spec['namespace']: key for key, spec in INTEGRATIONS.items()}
ALIAS_TO_TARGET = {
    'blender': 'blender',
    'blender-mcp': 'blender',
    'blendermcp': 'blender',
    'after-effects': 'after-effects',
    'after_effects': 'after-effects',
    'after-effects-mcp': 'after-effects',
    'aftereffectsmcp': 'after-effects',
    'ae': 'after-effects',
}

PROHIBITED_OFFLINE_PREFIXES = (
    'comfyui', 'runway_', 'generate_ai_', 'poll_ai_', 'ai_inpaint',
    'plan_scene_with_all_llms', 'compare_llm_styles', 'check_llm_providers',
)
PROHIBITED_OFFLINE_EXACT = {
    'reconstruct_scene_from_photos', 'reconstruct_from_video', 'tts_voiceover', 'stt_transcribe',
}


def _parse_semver(value: str) -> tuple[int, int, int]:
    nums = [int(x) for x in re.findall(r'\d+', str(value or '0.0.0'))[:3]]
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def discover_blender_binary() -> dict:
    configured = os.environ.get('REELSYNTAX_BLENDER')
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    which_bl = shutil.which('blender') or shutil.which('Blender')
    if which_bl:
        candidates.append(Path(which_bl))
    if sys.platform == 'darwin':
        candidates.extend([
            Path('/Applications/Blender.app/Contents/MacOS/Blender'),
            Path.home() / 'Applications/Blender.app/Contents/MacOS/Blender',
        ])
    elif os.name == 'nt':
        pf = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Blender Foundation'
        if pf.is_dir():
            candidates.extend(sorted(pf.glob('Blender*/blender.exe'), reverse=True))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            version_line = None
            try:
                proc = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=8, check=False)
                if proc.returncode == 0 and proc.stdout:
                    version_line = proc.stdout.splitlines()[0].strip()
            except (OSError, subprocess.TimeoutExpired):
                pass
            return {'available': True, 'binary': str(path), 'version': version_line}
    return {'available': False, 'binary': None, 'version': None}


def discover_after_effects_binaries() -> dict:
    ae_bin = os.environ.get('AE_BINARY') or os.environ.get('REELSYNTAX_AE_BINARY')
    aerender_bin = os.environ.get('AERENDER_BINARY') or os.environ.get('REELSYNTAX_AERENDER_BINARY')
    found_ae = Path(ae_bin) if ae_bin and Path(ae_bin).exists() else None
    found_aerender = Path(aerender_bin) if aerender_bin and Path(aerender_bin).is_file() else None

    if sys.platform == 'darwin':
        app_Root = Path('/Applications')
        if app_Root.is_dir():
            folders = sorted(app_Root.glob('Adobe After Effects*'), reverse=True)
            for folder in folders:
                if not folder.is_dir():
                    continue
                if found_ae is None:
                    apps = [p for p in sorted(folder.glob('Adobe After Effects*.app')) if 'Render Engine' not in p.name]
                    if apps:
                        found_ae = apps[0]
                if found_aerender is None:
                    for rel in (folder / 'aerender', *(p / 'Contents/aerender' for p in folder.glob('*.app'))):
                        if rel.is_file() and os.access(rel, os.X_OK):
                            found_aerender = rel
                            break
    elif os.name == 'nt':
        adobe = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Adobe'
        if adobe.is_dir():
            for folder in sorted(adobe.glob('Adobe After Effects*'), reverse=True):
                fx = folder / 'Support Files/AfterFX.exe'
                ar = folder / 'Support Files/aerender.exe'
                if found_ae is None and fx.is_file():
                    found_ae = fx
                if found_aerender is None and ar.is_file():
                    found_aerender = ar

    return {
        'available': found_ae is not None or found_aerender is not None,
        'ae_binary': str(found_ae) if found_ae else None,
        'aerender_binary': str(found_aerender) if found_aerender else None,
    }


def _read_package_version(target: str, directory: Path) -> str | None:
    if target == 'after-effects':
        pkg = directory / 'package.json'
        if pkg.is_file():
            try:
                data = json.loads(pkg.read_text(encoding='utf-8'))
                if data.get('name') == 'motionpilot-ae-mcp':
                    return str(data.get('version', '0.0.0'))
            except (OSError, ValueError):
                return None
    elif target == 'blender':
        pyp = directory / 'pyproject.toml'
        if pyp.is_file():
            try:
                text = pyp.read_text(encoding='utf-8')
                if 'remirdy-blender-studio-mcp' in text:
                    m = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.M)
                    return m.group(1) if m else '0.0.0'
            except OSError:
                return None
    return None


def _submodule_status(spec: dict, repo_root: Path = REPO_ROOT) -> dict:
    sub_dir = repo_root / spec['submodule_path']
    marker = 'pyproject.toml' if spec['id'] == 'blender' else 'package.json'
    initialized = sub_dir.is_dir() and (sub_dir / marker).is_file()
    pinned_commit = None
    if initialized:
        try:
            proc = subprocess.run(['git', '-C', str(sub_dir), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5, check=False)
            if proc.returncode == 0:
                pinned_commit = proc.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {
        'submodule_path': spec['submodule_path'],
        'submodule_initialized': initialized,
        'pinned_commit': pinned_commit,
    }


def resolve_integration(target: str, repo_root: Path = REPO_ROOT) -> dict:
    key = ALIAS_TO_TARGET.get(target.lower())
    if not key:
        raise ValueError(f'Unknown integration target: {target}')
    spec = INTEGRATIONS[key]
    sub_info = _submodule_status(spec, repo_root)
    sub_dir = repo_root / spec['submodule_path']

    candidate_dirs = []
    env_root = os.environ.get(spec['env_root'])
    if env_root:
        candidate_dirs.append(('env', Path(env_root).expanduser()))
    if sub_info['submodule_initialized']:
        candidate_dirs.append(('submodule', sub_dir))
    parent = repo_root.parent
    if parent.is_dir():
        for hint in spec['sibling_Hints']:
            sib = parent / hint
            if sib.is_dir():
                candidate_dirs.append(('local-sibling', sib))

    valid_dirs = []
    for source_kind, d in candidate_dirs:
        ver = _read_package_version(key, d)
        if ver is not None:
            valid_dirs.append((source_kind, d.resolve(), ver))

    command = None
    cwd = None
    env_overrides = {}
    source_mode = 'unavailable'
    package_version = None
    source_root = None

    env_cmd = os.environ.get(spec['env_cmd'])
    if env_cmd:
        command = [env_cmd]
        source_mode = 'env-command'

    if command is None and key == 'blender':
        python_bin = None
        for _, d, _ in valid_dirs:
            venv_py = d / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
            if venv_py.exists():
                try:
                    probe = subprocess.run([str(venv_py), '-c', 'import mcp'], capture_output=True, timeout=5, check=False)
                    if probe.returncode == 0:
                        python_bin = str(venv_py)
                        break
                except (OSError, subprocess.TimeoutExpired):
                    continue
        if python_bin and valid_dirs:
            source_mode, source_root, package_version = valid_dirs[0]
            command = [python_bin, '-m', 'server.main']
            cwd = str(source_root)
        else:
            cli_path = shutil.which(spec['cli_bin'])
            if cli_path:
                command = [cli_path]
                source_mode = 'path-binary'
                if valid_dirs:
                    _, source_root, package_version = valid_dirs[0]

    elif command is None and key == 'after-effects':
        node_bin = shutil.which('node')
        built_entry = None
        node_modules_dir = None
        for kind, d, ver in valid_dirs:
            if (d / 'node_modules').is_dir() and node_modules_dir is None:
                node_modules_dir = d / 'node_modules'
            if (d / 'dist/index.js').is_file() and built_entry is None:
                built_entry = (kind, d, ver, d / 'dist/index.js')
        if node_bin and built_entry and node_modules_dir:
            source_mode, source_root, package_version, entry_js = built_entry
            command = [node_bin, str(entry_js)]
            cwd = str(source_root)
            if node_modules_dir.parent != source_root:
                env_overrides['NODE_PATH'] = str(node_modules_dir)
                source_mode = f'{source_mode}+reused-deps'
        else:
            cli_path = shutil.which(spec['cli_bin'])
            if cli_path:
                command = [cli_path]
                source_mode = 'path-binary'
        ae_bins = discover_after_effects_binaries()
        if ae_bins['ae_binary']:
            env_overrides['AE_BINARY'] = ae_bins['ae_binary']
        if ae_bins['aerender_binary']:
            env_overrides['AERENDER_BINARY'] = ae_bins['aerender_binary']

    if package_version is None and valid_dirs:
        source_mode, source_root, package_version = valid_dirs[0]

    version_ok = _parse_semver(package_version) >= spec['min_version'] if package_version else False
    host_app = discover_blender_binary() if key == 'blender' else discover_after_effects_binaries()
    return {
        'id': key,
        'namespace': spec['namespace'],
        'capability': spec['capability'],
        'repository': spec['repo'],
        'first_party': True,
        **sub_info,
        'source_root': str(source_root) if source_root else None,
        'source_mode': source_mode,
        'package_version': package_version,
        'min_compatible_version': '.'.join(map(str, spec['min_version'])),
        'version_compatible': version_ok,
        'mcp_server_ready': command is not None and (version_ok or source_mode in {'env-command', 'path-binary'}),
        'command': command,
        'cwd': cwd,
        'env_overrides': env_overrides,
        'host_application': host_app,
    }


class DownstreamMcpSession:
    def __init__(self, resolved: dict, timeout: float = 15.0):
        self.resolved = resolved
        self.timeout = float(timeout)
        self.process = None
        self._lines = queue.Queue()
        self._next_id = 0
        self._lock = threading.Lock()
        self.server_info = None

    def _reader(self, stream):
        try:
            for line in stream:
                stripped = line.strip()
                if stripped.startswith('{'):
                    self._lines.put(stripped)
        finally:
            self._lines.put(None)

    def close(self):
        proc = self.process
        self.process = None
        if proc is None:
            return
        if proc.poll() is None:
            if os.name == 'nt':
                proc.kill()
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        try:
            proc.communicate(timeout=2)
        except Exception:
            pass

    def ensure_started(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.close()
        if not self.resolved.get('command'):
            raise ValueError(f"First-party MCP integration '{self.resolved['id']}' is not installed or built; run 'reelsyntax install {self.resolved['id']}' or check 'reelsyntax doctor'")
        allowed = {'PATH', 'HOME', 'TMPDIR', 'TEMP', 'TMP', 'SystemRoot', 'WINDIR', 'LANG', 'LC_ALL', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'}
        env = {k: v for k, v in os.environ.items() if k in allowed}
        env.update(self.resolved.get('env_overrides', {}))
        while not self._lines.empty():
            try:
                self._lines.get_nowait()
            except queue.Empty:
                break
        self.process = subprocess.Popen(
            self.resolved['command'],
            cwd=self.resolved.get('cwd'),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            start_new_session=(os.name != 'nt'),
        )
        threading.Thread(target=self._reader, args=(self.process.stdout,), daemon=True).start()
        init_res = self._rpc('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'reelsyntax-gateway', 'version': '0.2.0'},
        })
        self.server_info = init_res.get('serverInfo', {})
        expected_names = INTEGRATIONS[self.resolved['id']]['server_names']
        if self.server_info.get('name') not in expected_names:
            self.close()
            raise ValueError(f"Rejected non-first-party MCP server identity: {self.server_info.get('name')}")
        self._notify('notifications/initialized', {})

    def _notify(self, method: str, params: dict):
        msg = {'jsonrpc': '2.0', 'method': method, 'params': params}
        self.process.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
        self.process.stdin.flush()

    def _rpc(self, method: str, params: dict) -> dict:
        self._next_id += 1
        req_id = self._next_id
        msg = {'jsonrpc': '2.0', 'id': req_id, 'method': method, 'params': params}
        try:
            self.process.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
        except OSError as error:
            self.close()
            raise ValueError(f"MCP write failed for {self.resolved['id']}: {error}") from error
        while True:
            try:
                raw = self._lines.get(timeout=self.timeout)
            except queue.Empty as error:
                self.close()
                raise ValueError(f"MCP request '{method}' timed out on {self.resolved['id']} after {self.timeout:.1f}s") from error
            if raw is None:
                stderr_tail = ''
                if self.process and self.process.stderr:
                    stderr_tail = self.process.stderr.read()[-600:].strip()
                self.close()
                raise ValueError(f"MCP server {self.resolved['id']} exited unexpectedly: {stderr_tail}")
            payload = json.loads(raw)
            if payload.get('id') != req_id:
                continue
            if 'error' in payload:
                err = payload['error']
                raise ValueError(f"MCP error on {self.resolved['id']}.{method}: {err.get('message', err)}")
            return payload.get('result', {})

    def request_with_recovery(self, method: str, params: dict) -> dict:
        with self._lock:
            for attempt in range(2):
                try:
                    self.ensure_started()
                    return self._rpc(method, params)
                except ValueError:
                    self.close()
                    if attempt == 1:
                        raise


def _infer_stage_and_assets(tool_name: str, description: str) -> tuple[str, list[str], bool]:
    low = f'{tool_name} {description}'.lower()
    prohibited = (
        any(tool_name.startswith(p) for p in PROHIBITED_OFFLINE_PREFIXES)
        or tool_name in PROHIBITED_OFFLINE_EXACT
        or any(x in low for x in ('comfyui', 'runway', 'midjourney', 'dall-e', 'meshy', 'tripo'))
    )
    if any(w in tool_name for w in ('analyze_psd', 'import_', 'ingest', 'brand_kit_ingest')):
        stage = 'ingest'
    elif any(w in tool_name for w in ('check_', 'inspect_', 'quality', 'audit_', 'validate_', 'dry_run', 'score_', 'critique', 'detect_')):
        stage = 'review'
    elif any(w in tool_name for w in ('export_', 'package', 'delivery', 'lottie', 'unity', 'alembic')):
        stage = 'export'
    elif any(w in tool_name for w in ('render_', 'bake_', 'turntable')):
        stage = 'render'
    elif any(w in tool_name for w in ('plan', 'storyboard', 'concept', 'brief', 'connect_', 'ping', 'status', 'list_')):
        stage = 'plan'
    else:
        stage = 'build'
    assets = []
    for ext in ('psd', 'aep', 'jsx', 'glb', 'fbx', 'obj', 'blend', 'png', 'mp4', 'mov', 'wav', 'abc'):
        if re.search(rf'\b{ext}\b', low):
            assets.append(ext)
    return stage, assets, prohibited


def _compatible_skills_for_tool(namespace: str, tool_name: str, stage: str) -> list[str]:
    base = ['remirdy-blender-nodes', 'blender-mcp'] if namespace == 'blender' else ['after-effects-mcp']
    if 'psd' in tool_name:
        base.insert(0, 'motionpilot-psd-pipeline')
    elif any(k in tool_name for k in ('vfx', 'flipbook', 'atlas', 'plate', 'normal_map')):
        base.insert(0, 'motionpilot-vfx-flipbook')
    elif any(k in tool_name for k in ('camera', 'export_glb', 'export_fbx', '3d_scene', 'alembic')):
        base.insert(0, 'blender-ae-interchange')
    elif 'lottie' in tool_name:
        base.insert(0, 'lottie-animation')
    elif 'typography' in tool_name or 'lower_third' in tool_name or 'text' in tool_name:
        base.insert(0, 'kinetic-typography')
    return list(dict.fromkeys(base))


def summarize_tool_entry(namespace: str, raw_tool: dict) -> dict:
    name = raw_tool['name']
    lines = (raw_tool.get('description') or '').strip().splitlines()
    desc = lines[0][:200] if lines else ''
    schema = raw_tool.get('inputSchema') or {'type': 'object', 'properties': {}}
    stage, assets, requires_external = _infer_stage_and_assets(name, desc)
    props = schema.get('properties') or {}
    req_fields = schema.get('required') or []
    return {
        'id': f'{namespace}:{name}',
        'namespace': namespace,
        'name': name,
        'summary': desc or f'{namespace} {name}',
        'stage': stage,
        'asset_types': assets,
        'requires_external_or_prohibited': requires_external,
        'required_args': list(req_fields),
        'arg_count': len(props),
        'schema_sha256': digest(canonical(schema)),
        'compatible_skills': _compatible_skills_for_tool(namespace, name, stage),
        'inputSchema': schema,
    }


def diff_capability_snapshots(previous: dict | None, current: dict) -> dict:
    prev_tools = {t['id']: t for t in (previous or {}).get('tools', [])}
    curr_tools = {t['id']: t for t in current.get('tools', [])}
    added = sorted(set(curr_tools) - set(prev_tools))
    removed = sorted(set(prev_tools) - set(curr_tools))
    modified = []
    breaking = []
    affected_skills = set()

    for tid in added:
        affected_skills.update(curr_tools[tid].get('compatible_skills', []))
    for tid in removed:
        breaking.append({'id': tid, 'reason': 'tool-removed'})
        affected_skills.update(prev_tools[tid].get('compatible_skills', []))

    for tid in sorted(set(prev_tools) & set(curr_tools)):
        old, new = prev_tools[tid], curr_tools[tid]
        if old.get('schema_sha256') == new.get('schema_sha256'):
            continue
        old_s = old.get('inputSchema') or {}
        new_s = new.get('inputSchema') or {}
        old_props = old_s.get('properties') or {}
        new_props = new_s.get('properties') or {}
        old_req = set(old_s.get('required') or [])
        new_req = set(new_s.get('required') or [])
        new_required_fields = sorted(new_req - old_req)
        removed_props = sorted(set(old_props) - set(new_props))
        type_changes = [
            k for k in sorted(set(old_props) & set(new_props))
            if old_props[k].get('type') != new_props[k].get('type')
        ]
        is_breaking = bool(new_required_fields or removed_props or type_changes)
        entry = {
            'id': tid,
            'breaking': is_breaking,
            'added_required_args': new_required_fields,
            'removed_args': removed_props,
            'type_changes': type_changes,
            'added_optional_args': sorted(set(new_props) - set(old_props) - set(new_required_fields)),
        }
        modified.append(entry)
        if is_breaking:
            breaking.append({'id': tid, 'reason': 'breaking-schema-change', 'details': entry})
        affected_skills.update(new.get('compatible_skills', []))

    return {
        'added_count': len(added),
        'removed_count': len(removed),
        'modified_count': len(modified),
        'breaking_count': len(breaking),
        'backward_compatible': len(breaking) == 0,
        'added': added,
        'removed': removed,
        'modified': modified,
        'breaking': breaking,
        'affected_skills': sorted(affected_skills),
    }


def validate_args_against_schema(arguments: dict, schema: dict, tool_id: str) -> None:
    if not isinstance(arguments, dict):
        raise ValueError(f'{tool_id}: arguments must be a JSON object')

    def validate(value, spec, location, depth=0):
        if depth > 64:
            raise ValueError(f'{location}: schema nesting exceeds 64 levels')
        if spec is False:
            raise ValueError(f'{location}: value is forbidden by the schema')
        if spec is True:
            return
        if not isinstance(spec, dict):
            raise ValueError(f'{location}: invalid schema')
        expected = spec.get('type')
        types = [expected] if isinstance(expected, str) else expected or []
        matches = {
            'null': value is None,
            'string': isinstance(value, str),
            'boolean': type(value) is bool,
            'integer': type(value) is int,
            'number': type(value) in {int, float},
            'array': isinstance(value, list),
            'object': isinstance(value, dict),
        }
        if any(kind not in matches for kind in types):
            raise ValueError(f'{location}: unsupported schema type')
        if types and not any(matches[kind] for kind in types):
            raise ValueError(f'{location}: expected {expected}')
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f'{location}: expected a finite number')
        if 'enum' in spec and not any(canonical(value) == canonical(item) for item in spec['enum']):
            raise ValueError(f'{location}: value is outside the declared enum')
        if 'const' in spec and canonical(value) != canonical(spec['const']):
            raise ValueError(f'{location}: value does not match the declared constant')
        for child in spec.get('allOf', []):
            validate(value, child, location, depth + 1)
        for keyword in ['anyOf', 'oneOf']:
            if keyword in spec:
                count = 0
                for child in spec[keyword]:
                    try:
                        validate(value, child, location, depth + 1)
                        count += 1
                    except ValueError:
                        continue
                if count == 0 or keyword == 'oneOf' and count != 1:
                    raise ValueError(f'{location}: value does not satisfy {keyword}')
        if isinstance(value, dict):
            props = spec.get('properties', {})
            missing = [key for key in spec.get('required', []) if key not in value]
            if missing:
                raise ValueError(f'{location}: missing required arguments: {", ".join(missing)}')
            additional = spec.get('additionalProperties', True)
            for key, item in value.items():
                if key in props:
                    validate(item, props[key], f'{location}.{key}', depth + 1)
                elif additional is False:
                    raise ValueError(f'{location}: unexpected argument: {key}')
                elif isinstance(additional, dict):
                    validate(item, additional, f'{location}.{key}', depth + 1)
        if isinstance(value, list):
            if len(value) < spec.get('minItems', 0) or 'maxItems' in spec and len(value) > spec['maxItems']:
                raise ValueError(f'{location}: array length is outside the declared bounds')
            if spec.get('uniqueItems') and len({canonical(item) for item in value}) != len(value):
                raise ValueError(f'{location}: duplicate array items')
            if 'items' in spec:
                for index, item in enumerate(value):
                    validate(item, spec['items'], f'{location}[{index}]', depth + 1)
        if isinstance(value, str) and (len(value) < spec.get('minLength', 0) or 'maxLength' in spec and len(value) > spec['maxLength']):
            raise ValueError(f'{location}: string length is outside the declared bounds')
        if type(value) in {int, float}:
            for key, invalid in [
                ('minimum', lambda bound: value < bound), ('maximum', lambda bound: value > bound),
                ('exclusiveMinimum', lambda bound: value <= bound), ('exclusiveMaximum', lambda bound: value >= bound),
            ]:
                if key in spec and invalid(spec[key]):
                    raise ValueError(f'{location}: value violates {key}')

    validate(arguments, schema, tool_id)


class McpGateway:
    def __init__(self, repo_root: Path = REPO_ROOT, state_root: Path | None = None, timeout: float = 15.0):
        self.repo_root = Path(repo_root).resolve()
        self.state_root = Path(state_root).resolve() if state_root else self.repo_root
        self.timeout = float(timeout)
        self._sessions: dict[str, DownstreamMcpSession] = {}
        self._catalog_cache: dict | None = None

    def close(self):
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def status(self) -> dict:
        items = {key: resolve_integration(key, self.repo_root) for key in INTEGRATIONS}
        return {
            'gateway_version': '1.0.0',
            'integrations': items,
            'ready_namespaces': sorted(v['namespace'] for v in items.values() if v['mcp_server_ready']),
        }

    def _session(self, target: str) -> DownstreamMcpSession:
        key = ALIAS_TO_TARGET.get(target) or NAMESPACE_TO_TARGET.get(target)
        if not key:
            raise ValueError(f'Unknown MCP namespace or target: {target}')
        if key not in self._sessions:
            self._sessions[key] = DownstreamMcpSession(resolve_integration(key, self.repo_root), timeout=self.timeout)
        return self._sessions[key]

    def refresh_capabilities(self, targets=('blender', 'after-effects'), persist: bool = True) -> dict:
        tools = []
        servers = {}
        for t in targets:
            resolved = resolve_integration(t, self.repo_root)
            if not resolved['mcp_server_ready']:
                servers[t] = {
                    'status': 'unavailable',
                    'reason': 'MCP server runtime not installed or built',
                    'submodule_initialized': resolved['submodule_initialized'],
                }
                continue
            try:
                session = self._session(t)
                listing = session.request_with_recovery('tools/list', {})
                raw_tools = listing.get('tools', [])
                ns = resolved['namespace']
                entries = [summarize_tool_entry(ns, rt) for rt in raw_tools if isinstance(rt, dict) and rt.get('name')]
                tools.extend(entries)
                servers[t] = {
                    'status': 'discovered',
                    'namespace': ns,
                    'package_version': resolved['package_version'],
                    'server_info': session.server_info,
                    'pinned_commit': resolved['pinned_commit'],
                    'tool_count': len(entries),
                }
            except ValueError as error:
                servers[t] = {'status': 'error', 'diagnostic': str(error)}

        tools.sort(key=lambda x: x['id'])
        snapshot = {
            'schema_version': 1,
            'refreshed_at': datetime.now(timezone.utc).isoformat(),
            'servers': servers,
            'total_tools': len(tools),
            'digest': digest(canonical([
                {'id': x['id'], 'schema_sha256': x['schema_sha256']} for x in tools
            ])),
            'tools': tools,
        }
        if persist:
            cap_path = contained_path(self.state_root, '.reelsyntax/gateway/capabilities.json', must_exist=False)
            prev = read_json(cap_path) if cap_path.exists() else None
            snapshot['changes_since_previous'] = diff_capability_snapshots(prev, snapshot) if prev else None
            atomic_json(cap_path, snapshot)
        self._catalog_cache = snapshot
        return snapshot

    def load_catalog(self, refresh: bool = False) -> dict:
        if not refresh and self._catalog_cache is not None:
            return self._catalog_cache
        cap_path = contained_path(self.state_root, '.reelsyntax/gateway/capabilities.json', must_exist=False)
        if not refresh and cap_path.exists():
            self._catalog_cache = read_json(cap_path)
            return self._catalog_cache
        return self.refresh_capabilities(persist=True)

    def search_tools(
        self,
        query: str,
        namespace: str | None = None,
        stage: str | None = None,
        assets: list[str] | tuple[str, ...] = (),
        constraints: dict | None = None,
        limit: int = 8,
        refresh: bool = False,
    ) -> dict:
        if not 1 <= limit <= 25:
            raise ValueError('Tool search limit must be between 1 and 25')
        constraints = constraints or {'offline': True, 'no_paid_services': True}
        strict_offline = bool(constraints.get('offline', True) or constraints.get('no_paid_services', True))
        catalog = self.load_catalog(refresh=refresh)
        q_norm = norm(query)
        q_terms = terms(query)
        asset_set = {str(a).lower().lstrip('.') for a in assets}
        scored, blocked = [], []

        for entry in catalog.get('tools', []):
            if namespace and entry['namespace'] != namespace:
                continue
            if stage and entry['stage'] != stage:
                continue
            doc_text = f"{entry['name'].replace('_', ' ')} {entry['summary']} {' '.join(entry.get('compatible_skills', []))}"
            doc_terms = terms(doc_text)
            overlap = q_terms & doc_terms
            exact_name = entry['name'].replace('_', ' ') in q_norm if q_norm else False
            score = len(overlap) * 2.2 + (8.0 if exact_name else 0.0)
            if asset_set & set(entry.get('asset_types', [])) and (score > 0 or not q_terms):
                score += 2.5
            if not q_terms and not exact_name and (namespace or stage or asset_set):
                score = max(score, 1.0)
            if score < 2.0 and q_terms:
                continue
            if score <= 0:
                continue
            if strict_offline and entry.get('requires_external_or_prohibited'):
                blocked.append({'id': entry['id'], 'reason': 'blocked-by-offline-or-no-paid-policy'})
                continue
            if constraints.get('no_text') and any(k in entry['name'] for k in ('typography', 'text_morph', 'lower_third')):
                blocked.append({'id': entry['id'], 'reason': 'blocked-by-no_text'})
                continue
            scored.append({
                'id': entry['id'],
                'namespace': entry['namespace'],
                'name': entry['name'],
                'stage': entry['stage'],
                'score': round(score, 3),
                'summary': entry['summary'],
                'required_args': entry['required_args'],
                'arg_count': entry['arg_count'],
                'compatible_skills': entry['compatible_skills'],
            })

        scored.sort(key=lambda x: (-x['score'], x['id']))
        return {
            'query': query,
            'catalog_total_tools': catalog.get('total_tools', 0),
            'full_schemas_exposed': 0,
            'selected_tools': scored[:limit],
            'policy_filtered': blocked[:10],
            'disclosure_mode': 'progressive-summary-only; call gateway_describe_tool for full JSON inputSchema',
        }

    def describe_tool(self, tool_id: str) -> dict:
        if ':' not in tool_id:
            raise ValueError("Expected namespaced tool ID '<namespace>:<tool_name>' (e.g. 'blender:render_preview' or 'after_effects:render_preview')")
        catalog = self.load_catalog(refresh=False)
        match = next((t for t in catalog.get('tools', []) if t['id'] == tool_id), None)
        if match is None:
            catalog = self.load_catalog(refresh=True)
            match = next((t for t in catalog.get('tools', []) if t['id'] == tool_id), None)
        if match is None:
            raise ValueError(f'Unknown gateway tool: {tool_id}')
        return {
            'id': match['id'],
            'namespace': match['namespace'],
            'name': match['name'],
            'summary': match['summary'],
            'stage': match['stage'],
            'compatible_skills': match['compatible_skills'],
            'requires_external_or_prohibited': match['requires_external_or_prohibited'],
            'schema_sha256': match['schema_sha256'],
            'inputSchema': match['inputSchema'],
        }

    def call_tool(self, tool_id: str, arguments: dict | None = None, constraints: dict | None = None) -> dict:
        arguments = arguments or {}
        constraints = constraints or {'offline': True, 'no_paid_services': True}
        info = self.describe_tool(tool_id)
        if (constraints.get('offline', True) or constraints.get('no_paid_services', True)) and info['requires_external_or_prohibited']:
            raise ValueError(f"Tool '{tool_id}' is blocked by ReelSyntax offline/no_paid_services policy")
        if tool_id == 'after_effects:houdini_alembic_bridge':
            abc = arguments.get('alembicPath')
            if not abc or not Path(abc).is_file():
                raise ValueError('Refusing houdini_alembic_bridge: alembicPath does not exist on disk (prevents mock placeholder generation)')
        validate_args_against_schema(arguments, info['inputSchema'], tool_id)
        session = self._session(info['namespace'])
        raw = session.request_with_recovery('tools/call', {'name': info['name'], 'arguments': arguments})
        is_error = bool(raw.get('isError'))
        return {
            'ok': not is_error,
            'tool_id': tool_id,
            'namespace': info['namespace'],
            'execution_mode': 'live-mcp-stdio',
            'content': raw.get('content', []),
        }


def camera_to_after_effects(width: int, height: int, focal_mm: float, blender_xyz: tuple[float, float, float], target_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0), scale_px_per_m: float = 100.0, sensor_width_mm: float = 36.0) -> dict:
    zoom_px = width * float(focal_mm) / float(sensor_width_mm)
    fov_h_deg = math.degrees(2.0 * math.atan(float(sensor_width_mm) / (2.0 * float(focal_mm))))

    def map_pt(pt):
        bx, by, bz = pt
        return [
            round(width * 0.5 + bx * scale_px_per_m, 4),
            round(height * 0.5 - bz * scale_px_per_m, 4),
            round(by * scale_px_per_m, 4),
        ]

    return {
        'zoom_pixels': round(zoom_px, 4),
        'horizontal_fov_deg': round(fov_h_deg, 4),
        'sensor_width_mm': sensor_width_mm,
        'focal_length_mm': focal_mm,
        'ae_position': map_pt(blender_xyz),
        'ae_point_of_interest': map_pt(target_xyz),
    }


def build_handoff_package(project_dir: str | Path, output_dir: str | Path | None = None, verify_jsx: bool = True) -> dict:
    from .project import load
    from .skills import file_digest
    root, plan, metadata = load(project_dir)
    target_dir = Path(output_dir).resolve() if output_dir else contained_path(root, 'output/interchange', must_exist=False)
    target_dir.mkdir(parents=True, exist_ok=True)

    fps = Fraction(plan['output']['fps'])
    width, height = plan['output']['width'], plan['output']['height']
    total_frames = metadata['frames']
    duration_seconds = float(Fraction(total_frames, 1) / fps)

    cam_cfg = plan.get('camera') or next((s['camera'] for s in plan['scenes'] if s.get('camera')), {})
    focal_mm = float(cam_cfg.get('focal_mm', 50.0))
    cam_pos = tuple(cam_cfg.get('position', [0.0, -4.2, 1.35]))
    cam_target = tuple(cam_cfg.get('target', [0.0, 0.0, 0.45]))
    ae_cam = camera_to_after_effects(width, height, focal_mm, cam_pos, cam_target)

    scene_cameras = []
    frame_cursor = 0
    for sc in plan['scenes']:
        sc_cam = sc.get('camera') or cam_cfg
        sc_focal = float(sc_cam.get('focal_mm', focal_mm))
        sc_pos = tuple(sc_cam.get('position', cam_pos))
        sc_tgt = tuple(sc_cam.get('target', cam_target))
        scene_cameras.append({
            'scene_id': sc['id'],
            'start_frame': frame_cursor,
            'end_frame': frame_cursor + sc['duration_frames'],
            'camera_3d': camera_to_after_effects(width, height, sc_focal, sc_pos, sc_tgt),
        })
        frame_cursor += sc['duration_frames']

    blender_ops = [
        {'tool': 'blender:set_frame_range', 'arguments': {'start': 1, 'end': total_frames, 'fps': round(float(fps))}, 'note': f'Set scene.render.fps={fps.numerator} and fps_base={fps.denominator} for exact rational timing'},
        {'tool': 'blender:setup_camera', 'arguments': {'focal_length': focal_mm}},
        {'tool': 'blender:setup_three_point_lighting', 'arguments': {'strength': 1.0}},
    ]

    verified_passes = []
    out_dir = root / 'output'
    if out_dir.is_dir():
        for p in sorted(out_dir.iterdir()):
            if p.is_file() and p.suffix in {'.mp4', '.wav'}:
                verified_passes.append({
                    'path': p.relative_to(root).as_posix(),
                    'bytes': p.stat().st_size,
                    'sha256': file_digest(p),
                })

    comp_name = f"RS_{plan['id'].replace('-', '_')}"
    zoom_kf_lines = ''
    if len({c['camera_3d']['zoom_pixels'] for c in scene_cameras}) > 1:
        zoom_steps = []
        for c in scene_cameras:
            t_sec = float(Fraction(c['start_frame'], 1) / fps)
            zoom_steps.append(
                f"var zIdx = zoomProp.addKey({t_sec:.6f});\n"
                f"zoomProp.setValueAtKey(zIdx, {c['camera_3d']['zoom_pixels']});\n"
                f"zoomProp.setInterpolationTypeAtKey(zIdx, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);"
            )
        zoom_kf_lines = "var zoomProp = cam.property('ADBE Camera Options Group').property('ADBE Camera Zoom');\n" + '\n'.join(zoom_steps) + '\n'
    else:
        zoom_kf_lines = f"cam.property('ADBE Camera Options Group').property('ADBE Camera Zoom').setValue({ae_cam['zoom_pixels']});\n"

    jsx_preview = (
        f"app.beginUndoGroup('ReelSyntax Handoff');\n"
        f"var comp = app.project.items.addComp({json.dumps(comp_name)}, {width}, {height}, 1.0, {duration_seconds:.6f}, {float(fps):.6f});\n"
        f"var cam = comp.layers.addCamera('RS_Camera_3D', [{width / 2}, {height / 2}]);\n"
        f"{zoom_kf_lines}"
        f"cam.property('ADBE Transform Group').property('ADBE Position').setValue({json.dumps(ae_cam['ae_position'])});\n"
        f"cam.property('ADBE Transform Group').property('ADBE Anchor Point').setValue({json.dumps(ae_cam['ae_point_of_interest'])});\n"
        f"app.endUndoGroup();\n"
    )

    ae_payload = {
        'tool': 'after_effects:execute_after_effects_actions',
        'comp': {'name': comp_name, 'width': width, 'height': height, 'fps_rational': str(fps), 'duration_seconds': round(duration_seconds, 6)},
        'camera_3d': ae_cam,
        'jsx_bridge_script': jsx_preview,
    }

    jsx_validation = {'checked': False, 'valid': None, 'mode': 'not-run'}
    if verify_jsx:
        ae_res = resolve_integration('after-effects')
        if ae_res['mcp_server_ready']:
            with McpGateway() as gw:
                try:
                    res = gw.call_tool('after_effects:jsx_dry_run', {'jsxContent': jsx_preview})
                    jsx_validation = {'checked': True, 'valid': res['ok'], 'mode': 'live-mcp-jsx_dry_run', 'detail': res['content']}
                except ValueError as err:
                    jsx_validation = {'checked': False, 'valid': None, 'mode': 'unavailable', 'diagnostic': str(err)}

    blender_status = resolve_integration('blender')
    ae_status = resolve_integration('after-effects')
    fallbacks = []
    if not blender_status['host_application']['available']:
        fallbacks.append('Blender binary absent: use ReelSyntax pillow 3D software PBR renderer (prism-monolith)')
    elif not blender_status['mcp_server_ready']:
        fallbacks.append('BlenderMCP server offline: use ReelSyntax headless blender CLI adapter (--background --factory-startup)')
    if not ae_status['host_application']['available']:
        fallbacks.append('Adobe After Effects binary absent: use ReelSyntax native compositing + export .otio/.fcpxml')

    manifest = {
        'schema_version': 1,
        'project_id': plan['id'],
        'plan_sha256': metadata['plan_sha256'],
        'fps_rational': str(fps),
        'frames': total_frames,
        'dimensions': [width, height],
        'color_contract': {'working': 'Linear Rec.709', 'view_transform': 'AgX', 'delivery': 'BT.709', 'alpha_mode': 'straight'},
        'camera_interchange': ae_cam,
        'scene_cameras': scene_cameras,
        'verified_artifacts': verified_passes,
        'blender_mcp_plan': blender_ops,
        'after_effects_mcp_plan': ae_payload,
        'jsx_dry_run': jsx_validation,
        'fallbacks': fallbacks,
    }
    atomic_json(target_dir / 'interchange-manifest.json', manifest)
    (target_dir / 'after-effects-camera.jsx').write_text(jsx_preview, encoding='utf-8')
    return {
        'manifest': str((target_dir / 'interchange-manifest.json')),
        'jsx_script': str((target_dir / 'after-effects-camera.jsx')),
        'camera_interchange': ae_cam,
        'verified_artifact_count': len(verified_passes),
        'jsx_dry_run': jsx_validation,
        'fallbacks': fallbacks,
    }


def install_integration(target: str, repo_root: Path = REPO_ROOT, dry_run: bool = False) -> dict:
    targets = list(INTEGRATIONS) if target == 'all' else [ALIAS_TO_TARGET.get(target.lower(), '')]
    if '' in targets or not targets:
        raise ValueError(f'Unsupported install target: {target}')
    reports = {}
    for key in targets:
        spec = INTEGRATIONS[key]
        current = resolve_integration(key, repo_root)
        actions = []
        if current['mcp_server_ready']:
            reports[key] = {
                'status': 'ready-reused',
                'reused_existing': True,
                'source_mode': current['source_mode'],
                'source_root': current['source_root'],
                'package_version': current['package_version'],
                'actions': ['Reused existing compatible installation; no download needed'],
            }
            continue
        sub_dir = repo_root / spec['submodule_path']
        if not current['submodule_initialized'] and (repo_root / '.git').exists():
            actions.append(f"git submodule update --init {spec['submodule_path']}")
            if not dry_run:
                subprocess.run(['git', '-C', str(repo_root), 'submodule', 'update', '--init', spec['submodule_path']], check=True, timeout=180)
        if key == 'blender':
            venv_dir = sub_dir / '.venv'
            py_cmd = [sys.executable, '-m', 'venv', str(venv_dir)]
            pip_bin = venv_dir / ('Scripts/pip.exe' if os.name == 'nt' else 'bin/pip')
            actions.extend([' '.join(py_cmd), f"{pip_bin} install -e {sub_dir} 'mcp<2'"])
            if not dry_run and sub_dir.is_dir():
                subprocess.run(py_cmd, check=True, timeout=120)
                subprocess.run([str(pip_bin), 'install', '-e', str(sub_dir), 'mcp<2'], check=True, timeout=300)
        elif key == 'after-effects':
            npm_bin = shutil.which('npm')
            if not npm_bin:
                reports[key] = {'status': 'blocked', 'reason': 'Node.js/npm is required to build AfterEffectsMCP', 'actions': actions}
                continue
            actions.extend([f'{npm_bin} ci (in {sub_dir})', f'{npm_bin} run build (in {sub_dir})'])
            if not dry_run and sub_dir.is_dir():
                subprocess.run([npm_bin, 'ci'], cwd=str(sub_dir), check=True, timeout=300)
                subprocess.run([npm_bin, 'run', 'build'], cwd=str(sub_dir), check=True, timeout=180)
        updated = resolve_integration(key, repo_root) if not dry_run else current
        reports[key] = {
            'status': 'dry-run' if dry_run else ('installed' if updated['mcp_server_ready'] else 'incomplete'),
            'reused_existing': False,
            'actions': actions,
            'mcp_server_ready': updated['mcp_server_ready'],
        }
    return {'targets': reports, 'dry_run': dry_run}


def update_integrations(target: str = 'all', repo_root: Path = REPO_ROOT, check_only: bool = True, rollback: bool = False) -> dict:
    targets = list(INTEGRATIONS) if target == 'all' else [ALIAS_TO_TARGET.get(target.lower(), '')]
    if '' in targets or not targets:
        raise ValueError(f'Unsupported update target: {target}')
    sync_state_path = contained_path(repo_root, '.reelsyntax/gateway/sync-state.json', must_exist=False)
    sync_state = read_json(sync_state_path) if sync_state_path.exists() else {'last_known_good': {}}
    results = {}

    for key in targets:
        spec = INTEGRATIONS[key]
        info = resolve_integration(key, repo_root)
        sub_dir = repo_root / spec['submodule_path']
        if not info['submodule_initialized']:
            results[key] = {'status': 'skipped', 'reason': 'Submodule is not initialized locally'}
            continue
        current_sha = info['pinned_commit']
        if rollback:
            good_sha = sync_state.get('last_known_good', {}).get(key)
            if not good_sha:
                raise ValueError(f'No recorded last-known-good commit for {key}')
            subprocess.run(['git', '-C', str(sub_dir), 'checkout', good_sha], check=True, timeout=60)
            results[key] = {'status': 'rolled-back', 'from_commit': current_sha, 'to_commit': good_sha}
            continue

        if current_sha and key not in sync_state.get('last_known_good', {}):
            sync_state.setdefault('last_known_good', {})[key] = current_sha

        remote_sha = None
        latest_tag = None
        try:
            ls_proc = subprocess.run(['git', 'ls-remote', spec['url'], 'HEAD', 'refs/tags/*'], capture_output=True, text=True, timeout=20, check=False)
            if ls_proc.returncode == 0:
                tags = []
                for line in ls_proc.stdout.splitlines():
                    sha, ref = line.split('\t', 1)
                    if ref == 'HEAD':
                        remote_sha = sha
                    elif ref.startswith('refs/tags/') and not ref.endswith('^{}'):
                        tags.append(ref.removeprefix('refs/tags/'))
                if tags:
                    latest_tag = sorted(tags, key=_parse_semver)[-1]
        except (OSError, subprocess.TimeoutExpired):
            pass

        up_to_date = bool(remote_sha and current_sha == remote_sha)
        if check_only or up_to_date or not remote_sha:
            results[key] = {
                'status': 'up-to-date' if up_to_date else ('update-available' if remote_sha else 'offline-checked'),
                'pinned_commit': current_sha,
                'remote_head_commit': remote_sha,
                'latest_release_tag': latest_tag,
                'checked_only': True,
            }
            continue

        with McpGateway(repo_root=repo_root) as gw:
            before_snap = gw.refresh_capabilities(targets=(key,), persist=False)
        try:
            subprocess.run(['git', '-C', str(sub_dir), 'fetch', 'origin', 'main'], check=True, timeout=60)
            subprocess.run(['git', '-C', str(sub_dir), 'checkout', remote_sha], check=True, timeout=30)
            with McpGateway(repo_root=repo_root) as gw:
                after_snap = gw.refresh_capabilities(targets=(key,), persist=False)
            if after_snap['servers'].get(key, {}).get('status') != 'discovered':
                raise ValueError('Updated server failed live MCP discovery check')
            schema_diff = diff_capability_snapshots(before_snap, after_snap)
            sync_state.setdefault('last_known_good', {})[key] = remote_sha
            results[key] = {
                'status': 'updated',
                'previous_commit': current_sha,
                'updated_commit': remote_sha,
                'latest_release_tag': latest_tag,
                'schema_changes': schema_diff,
            }
        except Exception as error:
            if current_sha:
                subprocess.run(['git', '-C', str(sub_dir), 'checkout', current_sha], check=False, timeout=30)
            results[key] = {
                'status': 'rolled-back-on-failure',
                'preserved_commit': current_sha,
                'failed_commit': remote_sha,
                'error': str(error),
            }

    atomic_json(sync_state_path, sync_state)
    return {'results': results, 'check_only': check_only}
