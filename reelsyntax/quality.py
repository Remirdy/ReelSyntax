from fractions import Fraction
import json
import struct
import wave

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json
from ReelSyntax_Skills.tools.quality_audit import audit
from .drawing import LEGACY_RECIPES
from .media import executable, probe, run
from .palette import contrast_ratio, hex_to_rgb, relative_luminance
from .project import load
from .render import verify_roi_locks
from .skills import file_digest
from .typography import check_glyph_coverage, glyph_sample_for_locale, resolve_font

ISO3_TO_LOCALE = {
    'eng': 'en',
    'tur': 'tr',
    'deu': 'de',
    'spa': 'es',
    'fra': 'fr',
    'por': 'pt',
    'pol': 'pl',
    'vie': 'vi',
    'ara': 'ar',
    'zho': 'zh',
    'jpn': 'ja',
    'kor': 'ko',
}


def _check_typography_and_glyphs(plan: dict) -> tuple[dict, dict]:
    contrast_observations = []
    missing_glyphs = {}
    has_text = False
    for scene in plan['scenes']:
        params = scene.get('params', {})
        recipe = scene['recipe']
        default_bg = '#14171c' if recipe == 'prism-monolith' else '#eee9df'
        default_fg = '#ede8de' if recipe == 'prism-monolith' else '#252925'
        bg_rgb = hex_to_rgb(params.get('background', default_bg))
        fg_rgb = hex_to_rgb(params.get('foreground', default_fg))
        ac_rgb = hex_to_rgb(params.get('accent', '#bb5537'))
        use_default = params.get('font_mode') == 'default' or (params.get('font_mode') is None and recipe in LEGACY_RECIPES)

        for key, min_ratio, color_rgb, bold in [
            ('heading', 3.0, fg_rgb, True),
            ('subheading', 4.5, fg_rgb, False),
            ('kicker', 3.0, ac_rgb, True),
        ]:
            val = params.get(key, '')
            if not val:
                continue
            has_text = True
            ratio = round(contrast_ratio(color_rgb, bg_rgb), 2)
            contrast_observations.append({'scene': scene['id'], 'field': key, 'ratio': ratio, 'target': min_ratio, 'ok': ratio >= min_ratio})
            font = resolve_font(24, bold=bold, prefer_default=use_default)
            cov = check_glyph_coverage(val, font)
            if not cov['ok']:
                missing_glyphs[f"{scene['id']}.{key}"] = cov['missing_chars']

    if not has_text:
        return (
            {'id': 'typography_contrast', 'status': 'not-applicable', 'observed': [], 'expected': 'no scene text'},
            {'id': 'glyph_coverage', 'status': 'not-applicable', 'observed': {}, 'expected': 'no scene text'},
        )
    iso_lang = plan.get('delivery', {}).get('language')
    mapped_locale = ISO3_TO_LOCALE.get(iso_lang) if iso_lang else None
    if mapped_locale:
        try:
            req_sample = glyph_sample_for_locale(mapped_locale)
            prof_cov = check_glyph_coverage(req_sample, resolve_font(24))
            if not prof_cov['ok']:
                missing_glyphs[f'lang_profile.{mapped_locale}'] = prof_cov['missing_chars']
        except ValueError:
            pass
    contrast_ok = all(x['ok'] for x in contrast_observations)
    glyph_ok = len(missing_glyphs) == 0
    return (
        {'id': 'typography_contrast', 'status': 'pass' if contrast_ok else 'fail', 'observed': contrast_observations, 'expected': 'WCAG >=3.0:1 large / >=4.5:1 normal'},
        {'id': 'glyph_coverage', 'status': 'pass' if glyph_ok else 'fail', 'observed': missing_glyphs, 'expected': 'zero .notdef missing characters'},
    )


def _check_cue_onset_alignment(root, plan: dict, profile: str, fps: Fraction) -> dict:
    if not plan['audio']['enabled'] or not plan['audio']['cues']:
        return {'id': 'cue_onset_alignment', 'status': 'not-applicable', 'observed': [], 'expected': 'enabled cues'}
    mix_path = root / f'output/{profile}-mix.wav'
    if not mix_path.is_file():
        return {'id': 'cue_onset_alignment', 'status': 'review', 'observed': 'mix.wav absent', 'expected': 'cue onset <= 2 frames'}
    with wave.open(str(mix_path), 'rb') as w:
        rate = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    samples_per_video_frame = max(1, int(round(rate / float(fps))))
    aligned = []
    for cue in plan['audio']['cues']:
        anchor_sample = int(round(float(Fraction(cue['frame'], 1) / fps) * rate))
        w0 = max(0, anchor_sample)
        w1 = min(nframes, anchor_sample + 2 * samples_per_video_frame)
        peak = 0
        for s_idx in range(w0, w1, 4):
            off = s_idx * 4
            if off + 4 <= len(raw):
                sl, sr = struct.unpack_from('<hh', raw, off)
                peak = max(peak, abs(sl), abs(sr))
        aligned.append({'frame': cue['frame'], 'window_peak_int16': peak, 'ok': peak >= 180})
    return {
        'id': 'cue_onset_alignment',
        'status': 'pass' if all(x['ok'] for x in aligned) else 'fail',
        'observed': aligned,
        'expected': 'nonzero cue energy within <=2 video frames of anchor',
    }


def _check_temporal_continuity(root, manifest: dict) -> dict:
    from PIL import Image
    snaps = manifest.get('snapshots') or []
    if len(snaps) < 3:
        return {'id': 'temporal_continuity', 'status': 'not-applicable', 'observed': [], 'expected': 'sampled scene frames'}
    by_scene = {}
    for rel in snaps:
        parts = rel.split('-')
        sid = '-'.join(parts[1:-1]) if len(parts) >= 3 else rel
        with Image.open(root / rel) as im:
            small = im.convert('RGB').resize((64, 36))
            buf = small.tobytes()
            px_count = len(buf) // 3
            mean_luma = sum(relative_luminance((buf[i], buf[i + 1], buf[i + 2])) for i in range(0, len(buf), 3)) / max(1, px_count)
        by_scene.setdefault(sid, []).append(round(mean_luma, 4))
    spikes = {sid: vals for sid, vals in by_scene.items() if len(vals) >= 3 and max(vals) - min(vals) > 0.65}
    return {
        'id': 'temporal_continuity',
        'status': 'review' if spikes else 'pass',
        'observed': {'scene_luma_samples': by_scene, 'flagged_spikes': spikes},
        'expected': 'intra-shot mean luminance delta <= 0.65',
    }


def check(project, profile='draft', *, loop=False, html=False):
    root, plan, metadata = load(project)
    manifest = read_json(contained_path(root, f'output/{profile}-manifest.json'))
    if manifest['plan_sha256'] != metadata['plan_sha256']:
        raise ValueError('Plan changed since render; render current sources before QC')
    from .ingest import verify_sources
    verify_sources(root, manifest)
    artifact = contained_path(root, manifest['artifact'])
    if file_digest(artifact) != manifest['artifact_sha256']:
        raise ValueError('Delivered artifact hash differs from render manifest')
    fps = Fraction(plan['output']['fps'])
    output = manifest['output_settings']
    expected = {
        'width': output['width'], 'height': output['height'], 'fps': str(fps), 'frames': metadata['frames'],
        'codec': 'h264', 'duration': float(Fraction(metadata['duration'])),
        'audio_required': plan['audio']['enabled'], 'audio_forbidden': not plan['audio']['enabled'], 'sample_rate': 48000,
    }
    allowed = {key: [[float(Fraction(a, 1) / fps), float(Fraction(b, 1) / fps)] for a, b in intervals] for key, intervals in plan.get('quality', {}).get('exceptions', {}).items()}
    checks = audit(artifact, expected, allowed, tools={'ffmpeg': executable('ffmpeg'), 'ffprobe': executable('ffprobe')})
    timestamp_data = json.loads(run([
        executable('ffprobe'), '-v', 'error', '-select_streams', 'v:0', '-show_frames',
        '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(artifact),
    ]).stdout)
    timestamps = [Fraction(x['best_effort_timestamp_time']) for x in timestamp_data.get('frames', []) if 'best_effort_timestamp_time' in x]
    cadence = len(timestamps) == metadata['frames'] and all(abs(t - Fraction(i, 1) / fps) <= Fraction(1, 100000) for i, t in enumerate(timestamps))
    checks.append({'id': 'frame_cadence', 'status': 'pass' if cadence else 'fail', 'observed': len(timestamps), 'expected': f'{metadata["frames"]} timestamps at {fps} fps within 10 microseconds'})

    from .typography import BRAND_FONT
    font = plan.get('delivery', {}).get('font')
    token = BRAND_FONT.set(contained_path(root, font) if font else None)
    try:
        contrast_check, glyph_cov_check = _check_typography_and_glyphs(plan)
    finally:
        BRAND_FONT.reset(token)
    checks.append(contrast_check)
    checks.append(glyph_cov_check)
    checks.append(_check_cue_onset_alignment(root, plan, profile, fps))
    checks.append(_check_temporal_continuity(root, manifest))

    from .review import html_report, motion_checks
    checks.extend(motion_checks(artifact, fps, metadata['frames'], loop))
    roi_results = verify_roi_locks(root, plan, manifest, profile)
    if roi_results:
        checks.append({
            'id': 'roi_locks',
            'status': 'pass' if all(r['status'] == 'pass' for r in roi_results) else 'fail',
            'observed': roi_results,
            'expected': 'protected pixel regions unchanged from locked baseline',
        })

    if plan['audio']['enabled']:
        checks.append({'id': 'cue_sync', 'status': 'review', 'observed': 'Sample-accurate synthesis anchors verified; perceived audio/video alignment requires playback review', 'expected': 'Playback review of actual encoded cue events'})
    checks.append({
        'id': 'glyph_integrity',
        'status': 'review' if any(s['params'].get('heading') or s['params'].get('subheading') or s['params'].get('kicker') for s in plan['scenes']) else 'not-applicable',
        'observed': 'Text bounds and glyph coverage checked; full visual shaping needs frame review',
        'expected': 'Readable intended glyphs in rendered frames',
    })
    stream = next(s for s in probe(artifact)['streams'] if s['codec_type'] == 'video')
    colors = {key: stream.get(key) for key in ['color_space', 'color_transfer', 'color_primaries', 'color_range']}
    expected_colors = {'color_space': 'bt709', 'color_transfer': 'bt709', 'color_primaries': 'bt709', 'color_range': 'tv'}
    checks.append({'id': 'color_metadata', 'status': 'pass' if colors == expected_colors else 'fail', 'observed': colors, 'expected': expected_colors})
    technical = [x for x in checks if x['id'] not in {'creative_review', 'cue_sync', 'glyph_integrity'}]
    status = 'fail' if any(x['status'] == 'fail' for x in technical) else 'blocked' if any(x['status'] == 'blocked' for x in technical) else 'review' if any(x['status'] == 'review' for x in technical) else 'pass'
    report = {
        'schema_version': 1, 'artifact': manifest['artifact'], 'artifact_sha256': manifest['artifact_sha256'],
        'checks': checks, 'technical_status': status, 'release_status': 'requires creative/audio review', 'profile': profile,
    }
    atomic_json(contained_path(root, f'review/{profile}-qc.json', must_exist=False), report)
    if html:
        target = contained_path(root, f'review/{profile}-qc.html', must_exist=False)
        filmstrip = contained_path(root, f'review/{profile}-filmstrip.png')
        target.write_text(html_report(report, filmstrip), encoding='utf-8')
        report['html'] = target.relative_to(root).as_posix()
    return report
