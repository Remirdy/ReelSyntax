from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json
from .drawing import scene_geometry
from .project import load
from .render import output_settings


def _format_tc(seconds: Fraction, srt: bool = False) -> str:
    total_ms = round(seconds * 1000)
    hrs, rem = divmod(total_ms, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    sep = ',' if srt else '.'
    return f'{hrs:02d}:{mins:02d}:{secs:02d}{sep}{ms:03d}'


def _master_reference(root: Path, plan: dict, metadata: dict, profile: str) -> tuple[str, dict]:
    if profile not in {'draft', 'production', 'hero'}:
        raise ValueError('Unknown quality profile')
    settings = output_settings(plan, profile)
    artifact = contained_path(root, f'output/{profile}.mp4', must_exist=False)
    manifest = contained_path(root, f'output/{profile}-manifest.json', must_exist=False)
    if manifest.exists():
        record = read_json(manifest)
        if (not isinstance(record, dict)
                or record.get('plan_sha256') != metadata['plan_sha256']
                or record.get('profile') != profile
                or record.get('frames') != metadata['frames']
                or record.get('output_settings') != settings):
            raise ValueError(f'{profile}: render the current plan before exporting its master timeline')
        from .ingest import verify_sources
        verify_sources(root, record)
    return artifact.as_uri(), settings


def build_otio_dict(root: Path, plan: dict, metadata: dict, profile: str = 'production') -> dict:
    fps = Fraction(plan['output']['fps'])
    rate_float = float(fps)
    video_children = []
    cursor = 0
    target_url, settings = _master_reference(root, plan, metadata, profile)

    for scene in plan['scenes']:
        dur = scene['duration_frames']
        markers = []
        heading = scene.get('params', {}).get('heading')
        if heading:
            markers.append({
                'OTIO_SCHEMA': 'Marker.2',
                'name': heading,
                'color': 'ORANGE',
                'marked_range': {
                    'OTIO_SCHEMA': 'TimeRange.1',
                    'start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': cursor, 'rate': rate_float},
                    'duration': {'OTIO_SCHEMA': 'RationalTime.1', 'value': min(dur, max(1, round(rate_float))), 'rate': rate_float},
                },
                'metadata': {'subheading': scene.get('params', {}).get('subheading', '')},
            })
        clip_metadata = {'recipe': scene['recipe'], 'engine': scene['engine'], 'fps_rational': str(fps)}
        transition = scene.get('transition')
        if transition and transition.get('type', 'cut') != 'cut' and video_children:
            clip_metadata['baked_transition'] = dict(transition)
        video_children.append({
            'OTIO_SCHEMA': 'Clip.2',
            'name': scene['id'],
            'source_range': {
                'OTIO_SCHEMA': 'TimeRange.1',
                'start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': cursor, 'rate': rate_float},
                'duration': {'OTIO_SCHEMA': 'RationalTime.1', 'value': dur, 'rate': rate_float},
            },
            'media_reference': {
                'OTIO_SCHEMA': 'ExternalReference.1',
                'name': f"{plan['id']}_{profile}",
                'target_url': target_url,
                'available_range': {
                    'OTIO_SCHEMA': 'TimeRange.1',
                    'start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': 0, 'rate': rate_float},
                    'duration': {'OTIO_SCHEMA': 'RationalTime.1', 'value': metadata['frames'], 'rate': rate_float},
                },
            },
            'markers': markers,
            'effects': [],
            'metadata': clip_metadata,
        })
        cursor += dur

    tracks = [{
        'OTIO_SCHEMA': 'Track.1',
        'name': 'V1_Picture',
        'kind': 'Video',
        'children': video_children,
        'markers': [],
        'effects': [],
        'metadata': {},
    }]
    if plan['audio']['enabled']:
        wav_path = contained_path(root, f'output/{profile}-mix.wav', must_exist=False)
        wav_url = wav_path.as_uri() if wav_path.is_file() else target_url
        cue_markers = [
            {
                'OTIO_SCHEMA': 'Marker.2',
                'name': f"cue_{c['frequency']}hz",
                'color': 'CYAN',
                'marked_range': {
                    'OTIO_SCHEMA': 'TimeRange.1',
                    'start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': c['frame'], 'rate': rate_float},
                    'duration': {'OTIO_SCHEMA': 'RationalTime.1', 'value': c['duration_frames'], 'rate': rate_float},
                },
                'metadata': {'instrument': c.get('instrument', 'sine')},
            }
            for c in plan['audio']['cues']
        ]
        tracks.append({
            'OTIO_SCHEMA': 'Track.1',
            'name': 'A1_Mix',
            'kind': 'Audio',
            'children': [{
                'OTIO_SCHEMA': 'Clip.2',
                'name': f"{plan['id']}_mix",
                'source_range': {
                    'OTIO_SCHEMA': 'TimeRange.1',
                    'start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': 0, 'rate': rate_float},
                    'duration': {'OTIO_SCHEMA': 'RationalTime.1', 'value': metadata['frames'], 'rate': rate_float},
                },
                'media_reference': {'OTIO_SCHEMA': 'ExternalReference.1', 'target_url': wav_url},
                'markers': cue_markers,
                'effects': [],
                'metadata': {'sample_rate': 48000},
            }],
            'markers': [],
            'effects': [],
            'metadata': {},
        })

    return {
        'OTIO_SCHEMA': 'Timeline.1',
        'name': plan['id'],
        'global_start_time': {'OTIO_SCHEMA': 'RationalTime.1', 'value': 0, 'rate': rate_float},
        'tracks': {'OTIO_SCHEMA': 'Stack.1', 'name': 'tracks', 'children': tracks, 'markers': [], 'effects': [], 'metadata': {}},
        'metadata': {
            'generator': 'reelsyntax', 'plan_sha256': metadata['plan_sha256'],
            'fps_rational': str(fps), 'output_settings': settings, 'media_layout': 'flattened_master',
        },
    }


def build_fcpxml_string(root: Path, plan: dict, metadata: dict, profile: str = 'production') -> str:
    fps = Fraction(plan['output']['fps'])
    frame_dur = f'{fps.denominator}/{fps.numerator}s'
    total_dur = f"{metadata['frames'] * fps.denominator}/{fps.numerator}s"
    src_uri, settings = _master_reference(root, plan, metadata, profile)
    width, height = settings['width'], settings['height']

    fcpxml = ET.Element('fcpxml', {'version': '1.10'})
    resources = ET.SubElement(fcpxml, 'resources')
    ET.SubElement(resources, 'format', {
        'id': 'r1',
        'name': f'FFVideoFormat{height}p',
        'frameDuration': frame_dur,
        'width': str(width),
        'height': str(height),
        'colorSpace': '1-1-1 (Rec. 709)',
    })
    asset = ET.SubElement(resources, 'asset', {
        'id': 'r2',
        'name': plan['id'],
        'start': '0s',
        'duration': total_dur,
        'hasVideo': '1',
        'hasAudio': '1' if plan['audio']['enabled'] else '0',
        'format': 'r1',
    })
    ET.SubElement(asset, 'media-rep', {'kind': 'original-media', 'src': src_uri})

    library = ET.SubElement(fcpxml, 'library')
    event = ET.SubElement(library, 'event', {'name': plan['id']})
    proj = ET.SubElement(event, 'project', {'name': f"{plan['id']}_{profile}"})
    seq = ET.SubElement(proj, 'sequence', {'format': 'r1', 'duration': total_dur, 'tcStart': '0s', 'tcFormat': 'NDF'})
    spine = ET.SubElement(seq, 'spine')

    offset_frames = 0
    for scene in plan['scenes']:
        dur_f = scene['duration_frames']
        dur_str = f'{dur_f * fps.denominator}/{fps.numerator}s'
        off_str = f'{offset_frames * fps.denominator}/{fps.numerator}s'
        clip = ET.SubElement(spine, 'asset-clip', {
            'name': scene['id'],
            'ref': 'r2',
            'offset': off_str,
            'start': off_str,
            'duration': dur_str,
            'format': 'r1',
        })
        heading = scene.get('params', {}).get('heading')
        if heading:
            ET.SubElement(clip, 'marker', {'start': off_str, 'duration': frame_dur, 'value': heading})
        offset_frames += dur_f

    ET.indent(fcpxml, space='  ')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(fcpxml, encoding='unicode') + '\n'


def build_captions(plan: dict, srt: bool = False) -> str:
    fps = Fraction(plan['output']['fps'])
    blocks = [] if srt else ['WEBVTT', '']
    cursor = 0
    index = 1
    for scene in plan['scenes']:
        dur = scene['duration_frames']
        params = scene.get('params', {})
        lines = [x for x in (params.get('heading', '').strip(), params.get('subheading', '').strip()) if x]
        if lines:
            t0 = _format_tc(Fraction(cursor, 1) / fps, srt=srt)
            t1 = _format_tc(Fraction(cursor + dur, 1) / fps, srt=srt)
            if srt:
                blocks.extend([str(index), f'{t0} --> {t1}', *lines, ''])
            else:
                blocks.extend([f'{scene["id"]}', f'{t0} --> {t1}', *lines, ''])
            index += 1
        cursor += dur
    return '\n'.join(blocks).rstrip() + '\n'


def build_svg_frame(plan: dict, scene_index: int = 0, frame: int = 0) -> str:
    from xml.sax.saxutils import escape
    width, height = plan['output']['width'], plan['output']['height']
    scene = plan['scenes'][scene_index]
    params = scene.get('params', {})
    bg = params.get('background', '#eee9df')
    fg = params.get('foreground', '#252925')
    ac = params.get('accent', '#bb5537')
    shapes = scene_geometry(scene, frame, width, height, plan['seed'])
    unit = min(width / 960.0, height / 540.0)
    progress = frame / max(1, scene['duration_frames'] - 1)

    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'  <rect width="{width}" height="{height}" fill="{escape(bg)}"/>',
    ]
    for kind, pts, colored, thickness in shapes:
        stroke = ac if colored else fg
        coord_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)
        if kind == 'polygon':
            elems.append(f'  <polygon points="{coord_str}" fill="{escape(bg)}" stroke="{escape(stroke)}" stroke-width="{max(1.0, thickness):.2f}"/>')
        else:
            elems.append(f'  <polyline points="{coord_str}" fill="none" stroke="{escape(stroke)}" stroke-width="{max(1.0, thickness):.2f}" stroke-linejoin="round"/>')
    elems.append(f'  <line x1="{width * 0.07:.2f}" y1="{height * 0.85:.2f}" x2="{width * 0.93:.2f}" y2="{height * 0.85:.2f}" stroke="{escape(fg)}" stroke-width="{max(1.0, unit):.2f}"/>')
    elems.append(f'  <line x1="{width * 0.07:.2f}" y1="{height * 0.85:.2f}" x2="{width * (0.07 + 0.86 * progress):.2f}" y2="{height * 0.85:.2f}" stroke="{escape(ac)}" stroke-width="{max(1.0, 3 * unit):.2f}"/>')
    if params.get('heading'):
        elems.append(f'  <text x="{width * 0.07:.2f}" y="{height * 0.46:.2f}" fill="{escape(fg)}" font-family="Helvetica, Arial, sans-serif" font-size="{max(8, round(56 * unit))}" font-weight="600">{escape(params["heading"])}</text>')
    if params.get('subheading'):
        elems.append(f'  <text x="{width * 0.07:.2f}" y="{height * 0.58:.2f}" fill="{escape(fg)}" font-family="Helvetica, Arial, sans-serif" font-size="{max(8, round(19 * unit))}">{escape(params["subheading"])}</text>')
    elems.append('</svg>\n')
    return '\n'.join(elems)


def export_project(project_dir: str | Path, fmt: str, profile: str = 'production', output_path: str | Path | None = None, frame: int = 0) -> dict:
    root, plan, metadata = load(project_dir)
    ext_map = {'otio': 'otio', 'fcpxml': 'fcpxml', 'vtt': 'vtt', 'srt': 'srt', 'svg': 'svg', 'blender': 'blend'}
    if fmt not in ext_map:
        raise ValueError(f'Unsupported export format: {fmt}')
    if profile not in {'draft', 'production', 'hero'}:
        raise ValueError('Unknown quality profile')
    if fmt in {'svg', 'blender'} and (type(frame) is not int or not 0 <= frame < metadata['frames']):
        raise ValueError(f'frame: expected an integer in [0, {metadata["frames"]})')
    default_rel = f'output/{plan["id"]}-{profile}.{ext_map[fmt]}'
    target = Path(output_path).resolve() if output_path else contained_path(root, default_rel, must_exist=False)
    target.parent.mkdir(parents=True, exist_ok=True)

    native = None
    if fmt == 'blender':
        from .editorial import export_blender_timeline
        native = export_blender_timeline(target, build_otio_dict(root, plan, metadata, profile), frame)
    elif fmt == 'otio':
        doc = build_otio_dict(root, plan, metadata, profile)
        atomic_json(target, doc)
    elif fmt == 'fcpxml':
        target.write_text(build_fcpxml_string(root, plan, metadata, profile), encoding='utf-8')
    elif fmt in {'vtt', 'srt'}:
        target.write_text(build_captions(plan, srt=(fmt == 'srt')), encoding='utf-8')
    elif fmt == 'svg':
        scene_idx, local_f = 0, frame
        acc = 0
        for idx, s in enumerate(plan['scenes']):
            if local_f < acc + s['duration_frames']:
                scene_idx, local_f = idx, local_f - acc
                break
            acc += s['duration_frames']
        target.write_text(build_svg_frame(plan, scene_idx, local_f), encoding='utf-8')

    rel_or_abs = target.relative_to(root).as_posix() if target.is_relative_to(root) else str(target)
    result = {
        'format': fmt,
        'profile': profile,
        'artifact': rel_or_abs,
        'bytes': target.stat().st_size,
        'fps_rational': metadata['fps'],
        'frames': metadata['frames'],
    }
    if native:
        result['native_import'] = native
    return result
