from fractions import Fraction
from pathlib import Path
import shutil

from ReelSyntax_Skills.tools.registry import contained_path
from .media import executable, local_input_args, probe, run
from .skills import file_digest


def scene_sources(scene):
    params = scene['params']
    if scene['recipe'] == 'footage':
        return [params['source']]
    if scene['recipe'] == 'layer-stack':
        return [layer['source'] for layer in params['layers']]
    return []


def asset_hashes(root, plan):
    sources = {source for scene in plan['scenes'] for source in scene_sources(scene)}
    sources.update(track['source'] for track in plan['audio'].get('tracks', []))
    return {source: file_digest(contained_path(root, source)) for source in sorted(sources)}


def verify_sources(root, record):
    assets = record.get('source_assets', {})
    if not isinstance(assets, dict):
        raise ValueError('Invalid source asset integrity record')
    for source, expected in assets.items():
        if file_digest(contained_path(root, source)) != expected:
            raise ValueError(f'Source asset changed since render: {source}; render the current sources')


def render_footage(root, scene, output, destination, timeout=180):
    params = scene['params']
    source = contained_path(root, params['source'])
    streams = probe(source, safe_input=True)['streams']
    video = next((s for s in streams if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('Footage has no video stream: ' + params['source'])
    if video.get('color_transfer') in {'smpte2084', 'arib-std-b67'}:
        raise ValueError('HDR footage requires an explicit SDR grade before ingest')
    width, height = output['width'], output['height']
    start = params.get('in_frame', 0)
    filters = [
        f'trim=start_frame={start}', 'setpts=PTS-STARTPTS', f"fps={output['fps']}",
        f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2',
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={params.get('background', '#000000')}",
        'setsar=1',
    ]
    run([
        executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', *local_input_args(source), '-i', str(source),
        '-map', '0:v:0', '-an', '-vf', ','.join(filters), '-frames:v', str(scene['duration_frames']),
        '-threads', '2', '-start_number', '0', str(destination / '%06d.png'),
    ], timeout=timeout)
    for frame in range(scene['duration_frames']):
        if not (destination / f'{frame:06d}.png').is_file():
            raise ValueError(f"Footage '{params['source']}' is too short for {scene['id']} after source frame {start}")
    return {'source': params['source'], 'in_frame': start, 'source_rate': video.get('avg_frame_rate'), 'audio': 'picture only; use audio.tracks for independent J/L cuts'}


def render_layers(root, scene, original_output, output, destination):
    from PIL import Image, ImageOps
    sx, sy = output['width'] / original_output['width'], output['height'] / original_output['height']
    canvas = Image.new('RGBA', (output['width'], output['height']), scene['params'].get('background', '#000000'))
    for layer in scene['params']['layers']:
        with Image.open(contained_path(root, layer['source'])) as image:
            image = ImageOps.exif_transpose(image).convert('RGBA')
            size = (max(1, round(layer.get('width', image.width) * sx)), max(1, round(layer.get('height', image.height) * sy)))
            image = image.resize(size, Image.Resampling.LANCZOS)
            opacity = layer.get('opacity', 1.0)
            if opacity != 1.0:
                image.putalpha(image.getchannel('A').point(lambda a: round(a * opacity)))
            canvas.alpha_composite(image, (round(layer.get('x', 0) * sx), round(layer.get('y', 0) * sy)))
    first = destination / '000000.png'
    canvas.convert('RGB').save(first)
    for frame in range(1, scene['duration_frames']):
        shutil.copyfile(first, destination / f'{frame:06d}.png')
    return {'layers': len(scene['params']['layers']), 'blend_mode': 'normal', 'alpha': 'straight RGBA inputs composited over opaque SDR background'}
