from pathlib import Path
import os
import platform
import shutil
import signal
import subprocess


def executable(name):
    configured = os.environ.get('REELSYNTAX_' + name.upper())
    candidate = Path(configured).expanduser() if configured else None
    if candidate is not None:
        if not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise ValueError(f'REELSYNTAX_{name.upper()} must name an executable absolute path')
        return str(candidate)
    path = shutil.which(name)
    if path is None:
        raise ValueError(f'{name} is unavailable; install it separately or configure REELSYNTAX_{name.upper()}')
    return path


def run(args, timeout=180, cwd=None):
    environment = {key: value for key, value in os.environ.items() if key in {'PATH', 'HOME', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'FONTCONFIG_PATH'}}
    process = subprocess.Popen(
        [str(x) for x in args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=environment,
        start_new_session=os.name != 'nt',
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        if os.name == 'nt':
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
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


def doctor():
    import importlib.util
    from .gateway import discover_after_effects_binaries, discover_blender_binary, resolve_integration

    tools = {}
    for name in ['ffmpeg', 'ffprobe']:
        try:
            line = run([executable(name), '-version'], timeout=10).stdout.decode().splitlines()[0]
            tools[name] = {'available': True, 'version': line}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            tools[name] = {'available': False, 'diagnostic': str(error)}
    for name, package in [('pillow', 'PIL'), ('browser', 'playwright')]:
        installed = importlib.util.find_spec(package) is not None
        tools[name] = {'package_installed': installed, 'available': installed if name == 'pillow' else False}
    if tools['browser']['package_installed']:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                tools['browser']['available'] = Path(playwright.chromium.executable_path).is_file()
                tools['browser']['probe'] = 'binary presence only; use render test to verify launch'
        except (OSError, RuntimeError) as error:
            tools['browser']['diagnostic'] = str(error)

    tools['blender'] = discover_blender_binary()
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
    return {
        'platform': platform.system(),
        'architecture': platform.machine(),
        'python': platform.python_version(),
        'tools': tools,
        'first_party_mcp': first_party_mcp,
        'core_available': True,
        'render_available': all(tools[x]['available'] for x in ['ffmpeg', 'ffprobe', 'pillow']),
        'optional_engines': 'Headless Blender CLI and first-party Remirdy BlenderMCP / AfterEffectsMCP gateway adapters are optional; Three.js, HyperFrames, Remotion, Motion Canvas and Manim remain external guidance targets.',
    }


def encode_scene(directory, frames, output, timeout=180):
    run([
        executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-framerate', output['fps'], '-start_number', '0',
        '-i', str(directory / '%06d.png'), '-frames:v', str(frames), '-an', '-c:v', 'libx264', '-threads', '2',
        '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p',
        '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709',
        '-colorspace', 'bt709', '-color_primaries', 'bt709',
        '-color_trc', 'bt709', '-color_range', 'tv', str(directory / 'scene.mp4'),
    ], timeout=timeout)
