from contextlib import ExitStack
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import time
import uuid

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json
from . import __version__
from . import art_recipes
from . import drawing
from .media import encode_scene, executable, probe, run
from .project import load
from .skills import file_digest
from .sound import synthesize


def output_settings(plan, profile):
    output = dict(plan['output'])
    if profile == 'draft' and all(output[key] % 4 == 0 and output[key] >= 128 for key in ['width', 'height']):
        output['width'] //= 2
        output['height'] //= 2
    return output


def scene_hash(scene, output, seed, profile, environment, engine_used=None):
    effective_scene = dict(scene, engine=engine_used) if engine_used else scene
    return digest(canonical({'scene': effective_scene, 'output': output, 'seed': seed, 'profile': profile, 'environment': environment}))


def _scale_region(region: list[int], plan_out: dict, actual_out: dict) -> tuple[int, int, int, int]:
    sx = actual_out['width'] / plan_out['width']
    sy = actual_out['height'] / plan_out['height']
    x0 = int(round(region[0] * sx))
    y0 = int(round(region[1] * sy))
    x1 = min(actual_out['width'], max(x0 + 1, int(round((region[0] + region[2]) * sx))))
    y1 = min(actual_out['height'], max(y0 + 1, int(round((region[1] + region[3]) * sy))))
    return (x0, y0, x1, y1)


def compute_roi_digests(directory: Path, scene: dict, plan_out: dict, actual_out: dict) -> list[dict]:
    regions = scene.get('locked_regions') or []
    if not regions:
        return []
    from PIL import Image
    samples = sorted({0, scene['duration_frames'] // 2, scene['duration_frames'] - 1})
    out = []
    for reg in regions:
        box = _scale_region(reg, plan_out, actual_out)
        h = hashlib.sha256()
        for f in samples:
            with Image.open(directory / f'{f:06d}.png') as im:
                crop = im.convert('RGB').crop(box)
                h.update(crop.tobytes())
        out.append({'region': reg, 'scaled_box': list(box), 'frames_checked': samples, 'sha256': h.hexdigest()})
    return out


def verify_cache(root, directory, key, frames):
    if not directory.exists():
        return False
    manifest = contained_path(root, directory.relative_to(root).as_posix() + '/manifest.json', must_exist=False)
    if not manifest.exists():
        return False
    try:
        record = read_json(manifest)
        expected_files = {'scene.mp4', *(f'{i:06d}.png' for i in range(frames))}
        if record.get('key') != key or record.get('frames') != frames or set(record.get('artifacts', {})) != expected_files:
            return False
        for relative, expected in record['artifacts'].items():
            file = contained_path(root, directory.relative_to(root).as_posix() + '/' + relative)
            if file_digest(file) != expected:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def check_locks(root, plan, update=False, ids=()):
    path = contained_path(root, '.reelsyntax/scene-locks.json', must_exist=False)
    locked = read_json(path) if path.exists() else {}
    current = {}
    start = 0
    for scene in plan['scenes']:
        contract = {'scene': scene, 'start_frame': start, 'output': plan['output'], 'seed': plan['seed'], 'constraints': plan.get('constraints', {})}
        if plan.get('delivery'):
            contract['delivery'] = plan['delivery']
        current[scene['id']] = digest(canonical(contract))
        start += scene['duration_frames']
    for sid, expected in locked.items():
        if current.get(sid) != expected:
            raise ValueError('Approved scene changed or was removed: ' + sid)
    if update:
        for sid in ids:
            if sid not in current:
                raise ValueError('Unknown scene: ' + sid)
            locked[sid] = current[sid]
        atomic_json(path, locked)
    return locked


def lock_roi(project, scene_id: str, profile: str = 'production') -> dict:
    root, plan, _ = load(project)
    scene = next((s for s in plan['scenes'] if s['id'] == scene_id), None)
    if scene is None or not scene.get('locked_regions'):
        raise ValueError(f"Scene '{scene_id}' does not exist or declares no locked_regions")
    state_manifest = read_json(contained_path(root, f'output/{profile}-manifest.json'))
    scene_entry = next((s for s in state_manifest.get('scenes', []) if s['id'] == scene_id), None)
    if not scene_entry:
        raise ValueError(f"Scene '{scene_id}' has not been rendered for profile '{profile}'")
    cache_dir = contained_path(root, f".reelsyntax/cache/{scene_entry['cache_key']}", must_exist=False)
    digests = compute_roi_digests(cache_dir, scene, plan['output'], state_manifest['output_settings'])
    roi_path = contained_path(root, f'.reelsyntax/roi-locks-{profile}.json', must_exist=False)
    ledger = read_json(roi_path) if roi_path.exists() else {}
    ledger[scene_id] = digests
    atomic_json(roi_path, ledger)
    return {'scene': scene_id, 'profile': profile, 'locked_regions': digests}


def verify_roi_locks(root: Path, plan: dict, state_manifest: dict, profile: str) -> list[dict]:
    roi_path = contained_path(root, f'.reelsyntax/roi-locks-{profile}.json', must_exist=False)
    if not roi_path.exists():
        return []
    ledger = read_json(roi_path)
    results = []
    for sid, expected_list in ledger.items():
        scene = next((s for s in plan['scenes'] if s['id'] == sid), None)
        scene_entry = next((s for s in state_manifest.get('scenes', []) if s['id'] == sid), None)
        if scene is None or scene_entry is None:
            results.append({'scene': sid, 'status': 'fail', 'reason': 'locked scene missing from render'})
            continue
        cache_dir = root / '.reelsyntax/cache' / scene_entry['cache_key']
        observed = compute_roi_digests(cache_dir, scene, plan['output'], state_manifest['output_settings'])
        ok = [x['sha256'] for x in observed] == [x['sha256'] for x in expected_list]
        results.append({'scene': sid, 'status': 'pass' if ok else 'fail', 'expected': expected_list, 'observed': observed})
    return results


def lock(project, ids, roi_profile: str | None = None):
    if roi_profile:
        return {'roi_locked': [lock_roi(project, sid, roi_profile) for sid in ids]}
    root, plan, _ = load(project)
    return {'locked': check_locks(root, plan, update=True, ids=ids)}


def _apply_transitions_and_encode(directories: list[Path], scenes: list[dict], output: dict, temp_dir: Path, timeout: int) -> list[Path]:
    has_transitions = any(s.get('transition', {}).get('type', 'cut') != 'cut' for s in scenes[1:])
    if not has_transitions:
        segments = []
        for idx, d in enumerate(directories):
            target = temp_dir / f'scene-{idx}.mp4'
            shutil.copy2(d / 'scene.mp4', target)
            segments.append(target)
        return segments

    from PIL import Image
    merged_frames_dir = temp_dir / 'timeline_frames'
    merged_frames_dir.mkdir(parents=True, exist_ok=True)
    all_sources = []
    for s_idx, (scene, d) in enumerate(zip(scenes, directories)):
        tr = scene.get('transition') if s_idx > 0 else None
        tr_type = tr.get('type', 'cut') if tr else 'cut'
        tr_len = min(tr.get('duration_frames', 10), len(all_sources), scene['duration_frames'] // 2) if tr and tr_type != 'cut' else 0
        cut_index = len(all_sources)
        for f in range(scene['duration_frames']):
            src_png = d / f'{f:06d}.png'
            if f < tr_len and tr_type != 'cut':
                alpha = (f + 1) / (tr_len + 1)
                prev_idx = cut_index - tr_len + f
                prev_png = all_sources[prev_idx]
                blended_path = merged_frames_dir / f'blend-{prev_idx:06d}.png'
                with Image.open(prev_png) as im_a, Image.open(src_png) as im_b:
                    ra, rb = im_a.convert('RGB'), im_b.convert('RGB')
                    from .transitions import blend
                    mixed = blend(ra, rb, tr_type, alpha)
                    mixed.save(blended_path)
                all_sources[prev_idx] = blended_path
            all_sources.append(src_png)

    seq_dir = temp_dir / 'seq_encode'
    seq_dir.mkdir(parents=True, exist_ok=True)
    for idx, src in enumerate(all_sources):
        shutil.copy2(src, seq_dir / f'{idx:06d}.png')
    encode_scene(seq_dir, len(all_sources), output, timeout)
    single_seg = temp_dir / 'scene-0.mp4'
    shutil.copy2(seq_dir / 'scene.mp4', single_seg)
    return [single_seg]


HIGH_MOTION_TRANSITIONS = frozenset({'wipe_left', 'slide_left', 'slide_right', 'glitch', 'radial', 'fade_white'})


def apply_reduced_motion_scenes(scenes: list[dict]) -> list[dict]:
    out = []
    for scene in scenes:
        s_copy = dict(scene)
        if 'camera' in s_copy and isinstance(s_copy['camera'], dict):
            cam = dict(s_copy['camera'])
            if cam.get('preset', 'locked') != 'locked':
                cam['preset'] = 'locked'
            s_copy['camera'] = cam
        if 'transition' in s_copy and isinstance(s_copy['transition'], dict):
            tr = dict(s_copy['transition'])
            if tr.get('type') in HIGH_MOTION_TRANSITIONS:
                tr['type'] = 'cut'
            s_copy['transition'] = tr
        out.append(s_copy)
    return out


def render(project, profile='draft', max_frames=18000, timeout=180, recover=False, fallback_engine=None, cache_budget_bytes=None, allow_browser_module=False, reduced_motion=False):
    if cache_budget_bytes is not None and (type(cache_budget_bytes) is not int or cache_budget_bytes < 0):
        raise ValueError('cache_budget_bytes must be a nonnegative integer')
    if profile not in {'draft', 'production', 'hero'}:
        raise ValueError('Unknown quality profile')
    if fallback_engine is not None and fallback_engine not in {'pillow', 'browser'}:
        raise ValueError('Unsupported fallback engine')
    root, plan, metadata = load(project)
    if any(s['recipe'] == 'three-scene' for s in plan['scenes']) and not allow_browser_module:
        raise ValueError('A three-scene module runs user JavaScript. Review the bundle and supply --allow-browser-module.')
    if metadata['frames'] > max_frames or max_frames < 1:
        raise ValueError('Render exceeds max_frames budget; explicitly increase --max-frames after reviewing cost')
    output = output_settings(plan, profile)
    if output['width'] * output['height'] > 3840 * 2160:
        raise ValueError('Baseline renderer supports at most 3840×2160 pixels per frame')
    check_locks(root, plan)
    from .ingest import asset_hashes, render_footage, render_layers, scene_sources
    sources = asset_hashes(root, plan)
    executable('ffmpeg')
    executable('ffprobe')
    state_path = contained_path(root, '.reelsyntax/state.json', must_exist=False)
    mutex = contained_path(root, '.reelsyntax/render.lock', must_exist=False)
    mutex.parent.mkdir(parents=True, exist_ok=True)
    if recover and mutex.exists():
        previous = read_json(mutex)
        if previous.get('host') != platform.node():
            raise ValueError('Recovery requires the lock to originate on this machine')
        try:
            os.kill(previous['pid'], 0)
        except ProcessLookupError:
            mutex.unlink()
        else:
            raise ValueError('Render process still exists; refusing to break its lock')
    try:
        with mutex.open('x', encoding='utf-8') as stream:
            json.dump({'pid': os.getpid(), 'host': platform.node()}, stream)
    except FileExistsError as error:
        raise ValueError('A render lock exists; use resume only after the previous process has stopped') from error

    started = time.perf_counter()
    job_id = uuid.uuid4().hex
    state = {
        'schema_version': 1, 'job_id': job_id, 'plan_sha256': metadata['plan_sha256'], 'profile': profile,
        'status': 'rendering', 'started_at': datetime.now(timezone.utc).isoformat(), 'scenes': [], 'source_assets': sources,
    }
    try:
        atomic_json(state_path, state)
        environment = {
            'core': __version__,
            'drawing_sha256': file_digest(Path(drawing.__file__)),
            'render_sha256': file_digest(Path(__file__)),
            'platform': platform.system(),
            'architecture': platform.machine(),
            'ffmpeg': run([executable('ffmpeg'), '-version'], timeout=10).stdout.decode().splitlines()[0],
        }
        if sources:
            environment['ingest_source_sha256'] = file_digest(Path(__file__).with_name('ingest.py'))
        if any(s['recipe'] in art_recipes.ART_RECIPES for s in plan['scenes']):
            environment['art_recipes_sha256'] = file_digest(Path(art_recipes.__file__))
        if reduced_motion:
            environment['reduced_motion'] = True
        active_scenes = apply_reduced_motion_scenes(plan['scenes']) if reduced_motion else plan['scenes']
        with ExitStack() as stack:
            from .gateway import discover_blender_binary
            blender_probe = discover_blender_binary()
            resolved_engines = {}
            fallbacks_used = []
            for s in plan['scenes']:
                eng = s['engine']
                if eng == 'blender' and not blender_probe['available']:
                    if s['recipe'] in ('aperture', 'cassette'):
                        raise ValueError(f"Scene '{s['id']}' requires native Blender optics or product geometry; no compatible software fallback exists")
                    if fallback_engine:
                        eng = fallback_engine
                        fallbacks_used.append({'scene': s['id'], 'requested': 'blender', 'used': fallback_engine, 'reason': 'Blender executable unavailable'})
                    else:
                        raise ValueError(f"Scene '{s['id']}' requires Blender, which is unavailable; install Blender or pass --fallback pillow")
                resolved_engines[s['id']] = eng

            browser = None
            if 'browser' in resolved_engines.values():
                from .browser import BrowserRenderer
                browser = stack.enter_context(BrowserRenderer(timeout=min(timeout, 15)))
                environment['browser'] = browser.version
                environment['browser_source_sha256'] = file_digest(Path(__file__).with_name('browser.py'))
                if any(s['recipe'] in ('shader-sculpture', 'custom-shader', 'three-scene') for s in plan['scenes']):
                    environment['webgl'] = browser.require_webgl()
                    environment['webgl_source_sha256'] = file_digest(Path(__file__).with_name('webgl.py'))
            if 'blender' in resolved_engines.values():
                environment['blender'] = blender_probe['version'] or blender_probe['binary']
                environment['blender_source_sha256'] = file_digest(Path(__file__).with_name('blender_engine.py'))
                if any(s['recipe'] == 'cassette' for s in plan['scenes']):
                    environment['cassette_source_sha256'] = file_digest(Path(__file__).with_name('blender_cassette.py'))
                if any(s['recipe'] in ('aperture', 'cassette') for s in plan['scenes']):
                    environment['aperture_source_sha256'] = file_digest(Path(__file__).with_name('blender_aperture.py'))
            if resolved_engines:
                try:
                    environment['pillow'] = importlib.metadata.version('Pillow')
                except importlib.metadata.PackageNotFoundError as error:
                    raise ValueError('Rendering review artifacts requires the optional Pillow package') from error

            from .variants import TARGETS, apply_brand
            from .typography import BRAND_FONT
            delivery = plan.get('delivery', {})
            if 'font' in delivery:
                if any(s['engine'] != 'pillow' and any(s['params'].get(k) for k in ('heading', 'subheading', 'kicker')) for s in plan['scenes']):
                    raise ValueError('A brand font requires Pillow for text scenes')
                font_token = BRAND_FONT.set(contained_path(root, delivery['font']))
                stack.callback(BRAND_FONT.reset, font_token)
            supersample = 1 if profile == 'draft' else (3 if profile == 'hero' else 2)
            directories = []
            for scene in active_scenes:
                eng = resolved_engines[scene['id']]
                effective_scene = dict(scene)
                if scene['recipe'] == 'shape-field':
                    effective_scene['shape_renderer'] = file_digest(Path(__file__).with_name('shapes.py'))
                    effective_scene['coordinate_space'] = plan['output']
                elif scene['recipe'] == 'brand-sting':
                    effective_scene['brand_renderer'] = file_digest(Path(__file__).with_name('brand.py'))
                dependencies = scene_sources(scene)
                if delivery:
                    effective_scene['delivery'] = delivery
                    dependencies.extend(delivery[k] for k in ('logo', 'font') if k in delivery)
                if dependencies:
                    effective_scene['source_assets'] = {source: sources[source] for source in dependencies}
                key = scene_hash(effective_scene, output, plan['seed'], profile, environment, engine_used=eng)
                directory = contained_path(root, f'.reelsyntax/cache/{key}', must_exist=False)
                cached = verify_cache(root, directory, key, scene['duration_frames'])
                if not cached:
                    directory.parent.mkdir(parents=True, exist_ok=True)
                    temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='scene-', dir=directory.parent)))
                    layout = []
                    engine_evidence = None
                    if eng == 'ffmpeg':
                        engine_evidence = render_footage(root, scene, output, temporary, timeout=timeout)
                    elif scene['recipe'] == 'layer-stack':
                        engine_evidence = render_layers(root, scene, plan['output'], output, temporary)
                    elif eng == 'blender':
                        from .blender_engine import render_blender_scene
                        engine_evidence, layout = render_blender_scene(scene, output, profile, temporary, timeout=timeout, reduced_motion=bool(reduced_motion))
                    else:
                        browser_scene = scene
                        if scene['recipe'] in ('custom-shader', 'three-scene'):
                            key = 'fragment_file' if scene['recipe'] == 'custom-shader' else 'module_file'
                            source = contained_path(root, scene['params'][key])
                            if source.stat().st_size > (65536 if key == 'fragment_file' else 4*1024*1024):
                                raise ValueError('Browser scene source exceeds its size budget')
                            if key == 'fragment_file':
                                browser_scene = dict(scene, params=dict(scene['params'], fragment=source.read_text(encoding='utf-8')))
                            else:
                                browser.install_module(source.read_text(encoding='utf-8'))
                        for frame in range(scene['duration_frames']):
                            destination = temporary / f'{frame:06d}.png'
                            if eng == 'browser':
                                bounds = browser.draw(browser_scene, frame, output, plan['seed'], destination)
                            elif scene['recipe'] in art_recipes.ART_RECIPES:
                                image, bounds = art_recipes.draw_art_scene(scene, frame, dict(output, original_size=(plan['output']['width'], plan['output']['height'])), plan['seed'], supersampling=supersample, reduced_motion=bool(reduced_motion))
                                image.save(destination)
                            else:
                                image, bounds = drawing.draw(scene, frame, dict(output, original_size=(plan['output']['width'], plan['output']['height']), reduced_motion=bool(reduced_motion)), plan['seed'], supersampling=supersample, reduced_motion=bool(reduced_motion))
                                image.save(destination)
                            if frame in {0, scene['duration_frames'] // 2, scene['duration_frames'] - 1}:
                                layout.append({'frame': frame, 'text': bounds})
                    if delivery and scene['recipe'] != 'brand-sting':
                        apply_brand(temporary, scene['duration_frames'], delivery, root)
                    encode_scene(temporary, scene['duration_frames'], output, timeout)
                    roi_digests = compute_roi_digests(temporary, scene, plan['output'], output)
                    artifacts = {p.name: file_digest(p) for p in temporary.iterdir() if p.is_file()}
                    atomic_json(
                        temporary / 'manifest.json',
                        {'key': key, 'scene_id': scene['id'], 'engine_used': eng, 'engine_evidence': engine_evidence, 'frames': scene['duration_frames'], 'artifacts': artifacts, 'layout_samples': layout, 'roi_digests': roi_digests},
                    )
                    if directory.exists():
                        quarantine = contained_path(root, '.reelsyntax/quarantine/' + uuid.uuid4().hex, must_exist=False)
                        quarantine.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(directory, quarantine)
                    shutil.copytree(temporary, directory)
                os.utime(directory, None)
                directories.append(directory)
                state['scenes'].append({'id': scene['id'], 'engine_used': eng, 'cache_key': key, 'cache_hit': cached, 'frames': scene['duration_frames']})
                atomic_json(state_path, state)

            output_dir = contained_path(root, 'output', must_exist=False)
            output_dir.mkdir(parents=True, exist_ok=True)
            review_dir = contained_path(root, 'review', must_exist=False)
            review_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.TemporaryDirectory(prefix='delivery-', dir=state_path.parent) as temp:
                temp = Path(temp)
                segments = _apply_transitions_and_encode(directories, active_scenes, output, temp, timeout)
                concat = temp / 'concat.txt'
                concat.write_text('\n'.join(f"file '{seg.name}'" for seg in segments) + '\n', encoding='utf-8')
                args = [executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-f', 'concat', '-safe', '1', '-i', 'concat.txt']
                sound = None
                stem_temp = temp / 'stems'
                if plan['audio']['enabled']:
                    sound = synthesize(temp / 'mix.wav', plan, stem_dir=stem_temp)
                    if plan['audio'].get('tracks'):
                        from .audio_sources import mix_sources
                        sound = mix_sources(root, temp / 'mix.wav', plan, sound, stem_temp, timeout)
                    args += ['-i', 'mix.wav', '-map', '0:v:0', '-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
                if 'target' in delivery:
                    _, bitrate, loudness, _ = TARGETS[delivery['target']]
                    if sound:
                        args += ['-af', f'loudnorm=I={loudness}:TP=-1.5:LRA=11']
                    args += ['-c:v', 'libx264', '-threads', '2', '-b:v', bitrate, '-pix_fmt', 'yuv420p']
                else:
                    args += ['-c:v', 'copy']
                if 'language' in delivery:
                    args += ['-metadata:s:v:0', 'language=' + delivery['language']]
                    if sound:
                        args += ['-metadata:s:a:0', 'language=' + delivery['language']]
                args += [ '-colorspace', 'bt709', '-color_primaries', 'bt709',
                    '-color_trc', 'bt709', '-color_range', 'tv',
                    '-t', str(float(Fraction(metadata['duration']))), '-movflags', '+faststart', 'master.mp4',
                ]
                run(args, timeout=timeout, cwd=temp)
                measured = probe(temp / 'master.mp4', count_frames=True)
                video = next((s for s in measured['streams'] if s['codec_type'] == 'video'), None)
                if not video or int(video.get('nb_read_frames', 0)) != metadata['frames'] or video['width'] != output['width'] or video['height'] != output['height'] or Fraction(video['avg_frame_rate']) != Fraction(output['fps']):
                    raise ValueError('Encoded artifact does not match the frame/dimension/rate contract')
                run([executable('ffmpeg'), '-v', 'error', '-xerror', '-nostdin', '-i', str(temp / 'master.mp4'), '-f', 'null', '-'], timeout=timeout)
                from .ingest import verify_sources
                verify_sources(root, state)
                destination = contained_path(root, f'output/{profile}.mp4', must_exist=False)
                if destination.exists():
                    history = contained_path(root, f'.reelsyntax/history/{job_id}.mp4', must_exist=False)
                    history.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, history)
                os.replace(temp / 'master.mp4', destination)
                if sound:
                    os.replace(temp / 'mix.wav', contained_path(root, f'output/{profile}-mix.wav', must_exist=False))
                    for stem_name in sound.get('stems', []):
                        os.replace(stem_temp / stem_name, contained_path(root, f'output/{profile}-{stem_name}', must_exist=False))

            snapshots = []
            for scene, directory in zip(plan['scenes'], directories):
                for frame in sorted({0, scene['duration_frames'] // 2, scene['duration_frames'] - 1}):
                    relative = f'review/{profile}-{scene["id"]}-{frame:06d}.png'
                    target = contained_path(root, relative, must_exist=False)
                    shutil.copy2(directory / f'{frame:06d}.png', target)
                    snapshots.append(relative)

            from PIL import Image, ImageOps
            thumbs = []
            for relative in snapshots:
                with Image.open(root / relative) as image:
                    thumbs.append(ImageOps.contain(image.convert('RGB'), (320, 180)))
            sheet = Image.new('RGB', (960, 180 * ((len(thumbs) + 2) // 3)), '#eee9df')
            for index, thumb in enumerate(thumbs):
                sheet.paste(thumb, ((index % 3) * 320, (index // 3) * 180))
            sheet_path = contained_path(root, f'review/{profile}-filmstrip.png', must_exist=False)
            sheet.save(sheet_path)

            hero_artifacts = {}
            if profile == 'hero':
                hero_scene = next((s for s in plan['scenes'] if resolved_engines[s['id']] == 'pillow' and s['recipe'] != 'layer-stack'), plan['scenes'][0])
                mid_f = hero_scene['duration_frames'] // 2
                if resolved_engines[hero_scene['id']] == 'pillow' and hero_scene['recipe'] != 'layer-stack':
                    hero_out = dict(output, reduced_motion=bool(reduced_motion))
                    if hero_scene['recipe'] in art_recipes.ART_RECIPES:
                        neutral_img, _ = art_recipes.draw_art_scene(hero_scene, mid_f, hero_out, plan['seed'], supersampling=2, look_mode='neutral', reduced_motion=bool(reduced_motion))
                        graded_img, _ = art_recipes.draw_art_scene(hero_scene, mid_f, hero_out, plan['seed'], supersampling=3, look_mode='agx', reduced_motion=bool(reduced_motion))
                    else:
                        neutral_img, _ = drawing.draw(hero_scene, mid_f, hero_out, plan['seed'], supersampling=2, look_mode='neutral')
                        graded_img, _ = drawing.draw(hero_scene, mid_f, hero_out, plan['seed'], supersampling=3, look_mode='agx')
                    ab_sheet = Image.new('RGB', (960, 270), '#14171c')
                    ab_sheet.paste(ImageOps.contain(neutral_img.convert('RGB'), (480, 270)), (0, 0))
                    ab_sheet.paste(ImageOps.contain(graded_img.convert('RGB'), (480, 270)), (480, 0))
                    ab_path = contained_path(root, 'review/hero-lookdev-ab.png', must_exist=False)
                    ab_sheet.save(ab_path)
                    hero_artifacts['lookdev_ab'] = ab_path.relative_to(root).as_posix()
                elif len(directories) >= 2:
                    quad_thumbs = []
                    for sc, sc_dir in zip(plan['scenes'][:4], directories[:4]):
                        mf = sc['duration_frames'] // 2
                        with Image.open(sc_dir / f'{mf:06d}.png') as sim:
                            quad_thumbs.append(ImageOps.contain(sim.convert('RGB'), (640, 360)))
                    rows_n = (len(quad_thumbs) + 1) // 2
                    shot_sheet = Image.new('RGB', (1280, 360 * rows_n), '#14171c')
                    for idx, qth in enumerate(quad_thumbs):
                        shot_sheet.paste(qth, ((idx % 2) * 640, (idx // 2) * 360))
                    shot_path = contained_path(root, 'review/hero-shot-study.png', must_exist=False)
                    shot_sheet.save(shot_path)
                    hero_artifacts['shot_study'] = shot_path.relative_to(root).as_posix()

                first_dir = directories[0]
                dur0 = plan['scenes'][0]['duration_frames']
                extrema_frames = sorted({0, dur0 // 4, dur0 // 2, (3 * dur0) // 4, dur0 - 1})
                ex_thumbs = []
                for ef in extrema_frames:
                    with Image.open(first_dir / f'{ef:06d}.png') as eim:
                        ex_thumbs.append(ImageOps.contain(eim.convert('RGB'), (240, 135)))
                ex_sheet = Image.new('RGB', (240 * len(ex_thumbs), 135), '#14171c')
                for idx, eth in enumerate(ex_thumbs):
                    ex_sheet.paste(eth, (idx * 240, 0))
                ex_path = contained_path(root, 'review/hero-motion-extrema.png', must_exist=False)
                ex_sheet.save(ex_path)
                hero_artifacts['motion_extrema'] = ex_path.relative_to(root).as_posix()

        state.update({
            'status': 'rendered',
            'elapsed_seconds': round(time.perf_counter() - started, 4),
            'environment': environment,
            'frames': metadata['frames'],
            'reduced_motion': bool(reduced_motion),
            'output_settings': output,
            'sound': sound,
            'fallbacks_used': fallbacks_used,
            'hero_evidence': hero_artifacts or None,
            'artifact': destination.relative_to(root).as_posix(),
            'artifact_sha256': file_digest(destination),
            'bytes': destination.stat().st_size,
            'snapshots': snapshots,
            'filmstrip': sheet_path.relative_to(root).as_posix(),
            'creative_review': 'required',
            'profile_note': f"Hero generated {', '.join(sorted(hero_artifacts))} sheets; human/host visual and playback review remain mandatory." if profile == 'hero' else None,
        })
        if 'attribution' in delivery:
            state['attribution'] = delivery['attribution']
        atomic_json(state_path, state)
        atomic_json(contained_path(root, f'output/{profile}-manifest.json', must_exist=False), state)
        if cache_budget_bytes is not None:
            from .cache import _prune_locked
            state['cache_pruning'] = _prune_locked(root, cache_budget_bytes, apply=True)
            atomic_json(state_path, state)
            atomic_json(contained_path(root, f'output/{profile}-manifest.json', must_exist=False), state)
        return state
    except BaseException as error:
        state.update({'status': 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', 'error': str(error)[:3000]})
        atomic_json(state_path, state)
        raise
    finally:
        mutex.unlink(missing_ok=True)
