from pathlib import Path
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
from typing import Any

SETUP_GUIDE_BASE_URL = 'https://remirdy.github.io/ReelSyntax/getting-started/'

DOCTOR_REMEDIATION_GUIDES: dict[str, dict[str, str]] = {
    'ffmpeg': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#ffmpeg-and-ffprobe',
        'local_doc': 'docs/getting-started.md#ffmpeg-and-ffprobe',
        'summary': 'Install FFmpeg or set [paths].ffmpeg in reelsyntax.toml / REELSYNTAX_FFMPEG.',
    },
    'ffprobe': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#ffmpeg-and-ffprobe',
        'local_doc': 'docs/getting-started.md#ffmpeg-and-ffprobe',
        'summary': 'Install FFprobe alongside FFmpeg or set [paths].ffprobe / REELSYNTAX_FFPROBE.',
    },
    'pillow': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#install-reelsyntax',
        'local_doc': 'docs/getting-started.md#install-reelsyntax',
        'summary': 'Install the render extra: python -m pip install "reelsyntax[render]".',
    },
    'browser': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#optional-browser-and-3d-engines',
        'local_doc': 'docs/getting-started.md#optional-browser-and-3d-engines',
        'summary': 'Optional: python -m pip install "reelsyntax[browser]" && python -m playwright install chromium.',
    },
    'blender': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#optional-browser-and-3d-engines',
        'local_doc': 'docs/getting-started.md#optional-browser-and-3d-engines',
        'summary': 'Optional: install Blender 4.2+ (5.1+ for aperture) or set [paths].blender.',
    },
    'providers': {
        'doc_url': f'{SETUP_GUIDE_BASE_URL}#local-language-model-setup',
        'local_doc': 'docs/getting-started.md#local-language-model-setup',
        'summary': 'offline_rules runs without setup; optionally start a loopback model server.',
    },
}

USER_HOME_PATH_RE = re.compile(r'(?:/Users/|/home/|[A-Za-z]:[\\/]+Users[\\/]+)[^/\\\s"\']+')
URL_CREDENTIAL_RE = re.compile(r'(https?://)([^/@\s]+@)')
QUERY_SECRET_RE = re.compile(r'([?&](?:api_key|apikey|token|secret|password|key)=)([^&\s"\']+)', re.IGNORECASE)


def redact_diagnostic_payload(value: Any, *, home_dir: str | None = None) -> Any:
    home_str = home_dir if home_dir is not None else str(Path.home())
    if isinstance(value, str):
        out = value
        if home_str and len(home_str) > 3:
            out = out.replace(home_str, '<USER_HOME>')
            out = out.replace(home_str.replace('\\', '/'), '<USER_HOME>')
        out = USER_HOME_PATH_RE.sub('<USER_HOME>', out)
        out = URL_CREDENTIAL_RE.sub(r'\1<REDACTED>@', out)
        out = QUERY_SECRET_RE.sub(r'\1<REDACTED>', out)
        return out
    if isinstance(value, dict):
        return {k: redact_diagnostic_payload(v, home_dir=home_str) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_diagnostic_payload(item, home_dir=home_str) for item in value]
    return value


def standard_media_candidates(name: str, platform_name: str | None = None, environ: dict[str, str] | None = None) -> list[Path]:
    plat = sys.platform if platform_name is None else platform_name
    env = os.environ if environ is None else environ
    if plat == 'win32':
        binary = name if name.lower().endswith('.exe') else f'{name}.exe'
        found: list[Path] = []
        local_app = env.get('LOCALAPPDATA')
        if local_app:
            found.append(Path(local_app) / 'Microsoft/WinGet/Links' / binary)
        user_profile = env.get('USERPROFILE')
        if user_profile:
            found.append(Path(user_profile) / 'scoop/shims' / binary)
        found.extend([
            Path('C:/ProgramData/chocolatey/bin') / binary,
            Path('C:/ffmpeg/bin') / binary,
        ])
        return found
    if plat == 'darwin':
        return [
            Path('/opt/homebrew/bin') / name,
            Path('/usr/local/bin') / name,
            Path('/opt/local/bin') / name,
        ]
    return [
        Path('/usr/bin') / name,
        Path('/usr/local/bin') / name,
        Path('/snap/bin') / name,
    ]


def _is_usable_binary(path: Path, platform_name: str | None = None) -> bool:
    plat = sys.platform if platform_name is None else platform_name
    if not path.is_file():
        return False
    if plat == 'win32':
        return path.suffix.lower() in {'.exe', '.cmd', '.bat'}
    return os.access(path, os.X_OK)


def executable(name, *, platform_name: str | None = None, environ: dict[str, str] | None = None):
    env = os.environ if environ is None else environ
    plat = sys.platform if platform_name is None else platform_name
    configured = env.get('REELSYNTAX_' + name.upper())
    if not configured and name in {'ffmpeg', 'ffprobe', 'blender'}:
        from .config import load_config

        configured = getattr(load_config(environ=env).paths, name, '') or None
    candidate = Path(configured).expanduser() if configured else None
    if candidate is not None:
        if not candidate.is_absolute() or not _is_usable_binary(candidate, plat):
            raise ValueError(f'REELSYNTAX_{name.upper()} must name an executable absolute path')
        return str(candidate)
    path = shutil.which(name, path=env.get('PATH'))
    if path is None and plat == 'win32' and not name.lower().endswith('.exe'):
        path = shutil.which(name + '.exe', path=env.get('PATH'))
    if path is not None:
        return path
    for fallback in standard_media_candidates(name, plat, env):
        if _is_usable_binary(fallback, plat):
            return str(fallback)
    raise ValueError(f'{name} is unavailable; install it separately or configure REELSYNTAX_{name.upper()}')


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if os.name == 'nt':
        try:
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run(args, timeout=180, cwd=None):
    environment = {key: value for key, value in os.environ.items() if key in {'PATH', 'HOME', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'FONTCONFIG_PATH'}}
    popen_kwargs = {'creationflags': getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(
        [str(x) for x in args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=environment,
        **popen_kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        _terminate_process_tree(process)
        process.communicate()
        raise
    if process.returncode:
        message = stderr.decode('utf-8', errors='replace')[-3000:]
        raise ValueError(f'{Path(str(args[0])).name} failed ({process.returncode}): {message}')
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


def local_input_args(path):
    formats = {
        '.mp4': 'mov', '.mov': 'mov', '.m4v': 'mov', '.m4a': 'mov',
        '.mkv': 'matroska', '.webm': 'matroska', '.avi': 'avi',
        '.wav': 'wav', '.mp3': 'mp3', '.flac': 'flac', '.aac': 'aac',
        '.ogg': 'ogg', '.oga': 'ogg', '.aif': 'aiff', '.aiff': 'aiff',
        '.ts': 'mpegts', '.mts': 'mpegts', '.m2ts': 'mpegts', '.mpg': 'mpeg', '.mpeg': 'mpeg',
    }
    fmt = formats.get(Path(path).suffix.lower())
    if fmt is None:
        raise ValueError('Unsupported local media container; playlists and indirect media references are not accepted')
    return ['-protocol_whitelist', 'file', '-f', fmt]


def probe(path, count_frames=False, safe_input=False):
    import json
    args = [executable('ffprobe'), '-v', 'error']
    if count_frames:
        args += ['-count_frames']
    if safe_input:
        args += local_input_args(path)
    args += ['-show_streams', '-show_format', '-of', 'json', str(Path(path).resolve(strict=True))]
    return json.loads(run(args).stdout)


def doctor(*, probe_blender_headless: bool = False, redact: bool = False):
    import importlib.util
    from .gateway import discover_after_effects_binaries, discover_blender_binary, resolve_integration

    tools = {}
    for name in ['ffmpeg', 'ffprobe']:
        try:
            line = run([executable(name), '-version'], timeout=10).stdout.decode().splitlines()[0]
            tools[name] = {'available': True, 'version': line}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            tools[name] = {
                'available': False,
                'diagnostic': str(error),
                'guide': DOCTOR_REMEDIATION_GUIDES[name],
            }
    for name, package in [('pillow', 'PIL'), ('browser', 'playwright')]:
        installed = importlib.util.find_spec(package) is not None
        tools[name] = {'package_installed': installed, 'available': installed if name == 'pillow' else False}
        if not tools[name]['available'] and name == 'pillow':
            tools[name]['guide'] = DOCTOR_REMEDIATION_GUIDES['pillow']
    if tools['browser']['package_installed']:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                tools['browser']['available'] = Path(playwright.chromium.executable_path).is_file()
                tools['browser']['probe'] = 'binary presence only; use render test to verify launch'
        except (OSError, RuntimeError) as error:
            tools['browser']['diagnostic'] = str(error)
    if not tools['browser']['available']:
        tools['browser']['guide'] = DOCTOR_REMEDIATION_GUIDES['browser']

    tools['blender'] = discover_blender_binary()
    if not tools['blender']['available']:
        tools['blender']['guide'] = DOCTOR_REMEDIATION_GUIDES['blender']
    elif probe_blender_headless and tools['blender'].get('binary'):
        try:
            b_proc = subprocess.run(
                [
                    str(tools['blender']['binary']),
                    '--background',
                    '--factory-startup',
                    '--python-expr',
                    'import bpy; print("REELSYNTAX_BLENDER_OK", bpy.app.version_string)',
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            marker_line = next((ln for ln in b_proc.stdout.splitlines() if 'REELSYNTAX_BLENDER_OK' in ln), '')
            if b_proc.returncode == 0 and marker_line:
                tools['blender']['headless_probe'] = 'pass'
                tools['blender']['bpy_version'] = marker_line.split('REELSYNTAX_BLENDER_OK', 1)[1].strip()
            else:
                tools['blender']['headless_probe'] = 'fail'
                tools['blender']['diagnostic'] = (b_proc.stderr or b_proc.stdout)[-400:].strip()
        except (OSError, subprocess.TimeoutExpired) as error:
            tools['blender']['headless_probe'] = 'fail'
            tools['blender']['diagnostic'] = str(error)
    elif probe_blender_headless:
        tools['blender']['headless_probe'] = 'unavailable'

    tools['after_effects'] = discover_after_effects_binaries()
    bl_mcp = resolve_integration('blender')
    ae_mcp = resolve_integration('after-effects')
    first_party_mcp = {
        'blender_mcp': {
            'repository': bl_mcp['repository'],
            'submodule_initialized': bl_mcp['submodule_initialized'],
            'pinned_commit': bl_mcp['pinned_commit'],
            'package_version': bl_mcp['package_version'],
            'mcp_server_ready': bl_mcp['mcp_server_ready'],
            'source_mode': bl_mcp['source_mode'],
        },
        'after_effects_mcp': {
            'repository': ae_mcp['repository'],
            'submodule_initialized': ae_mcp['submodule_initialized'],
            'pinned_commit': ae_mcp['pinned_commit'],
            'package_version': ae_mcp['package_version'],
            'mcp_server_ready': ae_mcp['mcp_server_ready'],
            'source_mode': ae_mcp['source_mode'],
        },
    }
    remediation = [
        {'tool': name, **DOCTOR_REMEDIATION_GUIDES[name]}
        for name in ('ffmpeg', 'ffprobe', 'pillow', 'browser', 'blender')
        if not tools[name]['available']
    ]
    payload = {
        'platform': platform.system(),
        'architecture': platform.machine(),
        'python': platform.python_version(),
        'setup_guide': SETUP_GUIDE_BASE_URL,
        'tools': tools,
        'remediation': remediation,
        'first_party_mcp': first_party_mcp,
        'core_available': True,
        'render_available': all(tools[x]['available'] for x in ['ffmpeg', 'ffprobe', 'pillow']),
        'optional_engines': 'Headless Blender CLI and first-party Remirdy BlenderMCP / AfterEffectsMCP gateway adapters are optional; Three.js, HyperFrames, Remotion, Motion Canvas and Manim remain external guidance targets.',
    }
    if redact:
        payload = redact_diagnostic_payload(payload)
        payload['redacted'] = True
    return payload


def encode_scene(directory, frames, output, timeout=180):
    run([
        executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-framerate', output['fps'], '-start_number', '0',
        '-i', str(directory / '%06d.png'), '-frames:v', str(frames), '-an', '-c:v', 'libx264', '-threads', '2',
        '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p',
        '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709',
        '-colorspace', 'bt709', '-color_primaries', 'bt709',
        '-color_trc', 'bt709', '-color_range', 'tv', str(directory / 'scene.mp4'),
    ], timeout=timeout)
