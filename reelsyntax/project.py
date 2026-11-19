from fractions import Fraction
import math
from pathlib import Path
import re

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json

from .contracts import Project, ProjectMetadata

RECIPES = {'rings', 'assembly', 'signal', 'title', 'prism-monolith', 'cinematic-3d', 'stepped-clay', 'paper-cutout', 'kinetic-type', 'data-horizon', 'hud-lock', 'aperture', 'cassette', 'footage', 'layer-stack', 'shader-sculpture', 'custom-shader', 'three-scene', 'shape-field', 'news-ticker', 'loop-art', 'character-stage'}
RECIPES_3D = {'prism-monolith', 'cinematic-3d', 'stepped-clay', 'paper-cutout', 'aperture', 'cassette', 'character-stage'}
ENGINES = {'pillow', 'browser', 'blender', 'ffmpeg'}
CAMERA_PRESETS = {'locked', 'dolly_in', 'orbit', 'crane_rise', 'dolly_zoom'}
TRANSITIONS = {'cut', 'cross_dissolve', 'fade_black', 'wipe_left', 'slide_left', 'slide_right', 'fade_white', 'radial', 'glitch'}
INSTRUMENTS = {'sine', 'sub_impact', 'harmonic_pluck', 'warm_pad', 'whoosh', 'click_transient'}
CONSTRAINTS = {'no_text', 'no_audio', 'no_voice', 'no_music', 'camera_locked', 'offline', 'no_paid_services'}


def fields(value, allowed, required, location):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError(f'{location}: unexpected or missing fields')


def integer(value, low, high, location):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{location}: expected integer in [{low}, {high}]')


def number(value, low, high, location):
    if type(value) not in {int, float} or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{location}: expected finite number in [{low}, {high}]')


def text(value, location, maximum=120):
    if not isinstance(value, str) or len(value) > maximum or any(ord(x) < 32 for x in value):
        raise ValueError(f'{location}: invalid text or length exceeds {maximum}')


def color(value, location):
    if not isinstance(value, str) or not re.fullmatch('#[0-9a-fA-F]{6}', value):
        raise ValueError(f'{location}: expected #RRGGBB')


def asset_path(value, location):
    if (not isinstance(value, str) or not value or len(value) > 512
            or Path(value).is_absolute() or '\\' in value or ':' in value
            or '..' in Path(value).parts or any(ord(c) < 32 for c in value)):
        raise ValueError(f'{location}: expected a project-relative asset path')
    parts = Path(value).parts
    if parts and (parts[0] in {'output', 'review', '.git'} or parts[0] == '.reelsyntax' and (len(parts) < 2 or parts[1] != 'inputs')):
        raise ValueError(f'{location}: copy source media into assets or .reelsyntax/inputs; managed output/cache paths are not sources')


def _validate_camera(cam, camera_locked: bool, location: str):
    fields(cam, {'preset', 'focal_mm', 'position', 'target'}, set(), location)
    preset = cam.get('preset', 'locked')
    if not isinstance(preset, str) or preset not in CAMERA_PRESETS:
        raise ValueError(f'{location}.preset: unsupported camera preset')
    if camera_locked and preset != 'locked':
        raise ValueError(f'{location}.preset: camera_locked forbids moving preset {preset}')
    if 'focal_mm' in cam:
        number(cam['focal_mm'], 12.0, 200.0, f'{location}.focal_mm')
    for vec_key in ('position', 'target'):
        if vec_key in cam:
            vec = cam[vec_key]
            if not isinstance(vec, list) or len(vec) != 3:
                raise ValueError(f'{location}.{vec_key}: expected [x, y, z]')
            for c in vec:
                number(c, -1000.0, 1000.0, f'{location}.{vec_key}')


def validate(plan: Project) -> ProjectMetadata:
    fields(
        plan,
        {'$schema', 'schema_version', 'id', 'seed', 'output', 'constraints', 'camera', 'scenes', 'audio', 'quality', 'delivery'},
        {'schema_version', 'id', 'seed', 'output', 'scenes', 'audio'},
        'project',
    )
    if '$schema' in plan:
        text(plan['$schema'], '$schema', 512)
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('schema_version: only version 1 is supported')
    if not isinstance(plan['id'], str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', plan['id']) or len(plan['id']) > 64:
        raise ValueError('id: expected lowercase hyphenated ID, maximum 64 characters')
    integer(plan['seed'], 0, 2**32 - 1, 'seed')
    output = plan['output']
    fields(output, {'width', 'height', 'fps'}, {'width', 'height', 'fps'}, 'output')
    for dimension in ['width', 'height']:
        integer(output[dimension], 64, 7680, 'output.' + dimension)
        if output[dimension] % 2:
            raise ValueError(f'output.{dimension}: H.264 yuv420p requires even dimensions')
    if not isinstance(output['fps'], str) or not re.fullmatch(r'[1-9][0-9]*/[1-9][0-9]*', output['fps']):
        raise ValueError('output.fps: expected rational string such as 30000/1001')
    fps = Fraction(output['fps'])
    if not 1 <= fps <= 120:
        raise ValueError('output.fps: supported range is 1–120')
    delivery = plan.get('delivery', {})
    fields(delivery, {'target', 'language', 'font', 'logo', 'margin'}, set(), 'delivery')
    if 'target' in delivery:
        from .variants import TARGETS
        if delivery['target'] not in TARGETS:
            raise ValueError('Unknown delivery target')
    if 'language' in delivery and not re.fullmatch('[a-z]{3}', delivery['language']):
        raise ValueError('delivery.language: expected a three-letter language code')
    number(delivery.get('margin', 0), 0, 0.25, 'delivery.margin')
    for key in ('font', 'logo'):
        if key in delivery:
            asset_path(delivery[key], 'delivery.' + key)
    constraints = plan.get('constraints', {})
    fields(constraints, CONSTRAINTS, set(), 'constraints')
    if any(type(v) is not bool for v in constraints.values()):
        raise ValueError('constraints: values must be booleans')
    if 'camera' in plan:
        _validate_camera(plan['camera'], bool(constraints.get('camera_locked')), 'project.camera')

    scenes = plan['scenes']
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 1000:
        raise ValueError('scenes: expected 1–1000 scenes')
    known = set()
    for scene in scenes:
        fields(
            scene,
            {'id', 'duration_frames', 'recipe', 'engine', 'params', 'camera', 'transition', 'locked_regions'},
            {'id', 'duration_frames', 'recipe', 'engine', 'params'},
            'scene',
        )
        sid = scene['id']
        if not isinstance(sid, str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', sid) or len(sid) > 64 or sid in known:
            raise ValueError('scene.id: invalid or duplicate scene ID')
        known.add(sid)
        integer(scene['duration_frames'], 1, 10_000_000, sid + '.duration_frames')
        if not isinstance(scene['recipe'], str) or scene['recipe'] not in RECIPES or not isinstance(scene['engine'], str) or scene['engine'] not in ENGINES:
            raise ValueError(sid + ': unsupported recipe or engine')
        if scene['engine'] == 'blender' and scene['recipe'] not in RECIPES_3D:
            raise ValueError(f'{sid}: blender engine requires a 3D recipe ({sorted(RECIPES_3D)})')
        params = scene['params']
        fields(params, {'heading', 'subheading', 'kicker', 'background', 'foreground', 'accent', 'series', 'font_mode', 'shot', 'samples', 'source', 'in_frame', 'layers', 'shapes', 'speed', 'hdr_to_sdr', 'fragment_file', 'module_file', 'character', 'partner_character', 'expression', 'partner_expression', 'mouth_envelope', 'speaker', 'dialogue', 'shot_role', 'character_pos', 'blink_offset'}, set(), sid + '.params')
        for key, value in params.items():
            if key in {'heading', 'subheading', 'kicker'}:
                text(value, sid + '.' + key)
                if constraints.get('no_text') and value:
                    raise ValueError('no_text conflicts with scene typography: ' + sid)
            elif key in {'background', 'foreground', 'accent'}:
                color(value, sid + '.' + key)
            elif key == 'series':
                if not isinstance(value, list) or not 2 <= len(value) <= 64:
                    raise ValueError(f'{sid}.series: expected 2–64 numeric values')
                for v in value:
                    number(v, -1_000_000.0, 1_000_000.0, f'{sid}.series')
            elif key == 'font_mode':
                if value not in {'default', 'system'}:
                    raise ValueError(f'{sid}.font_mode: expected default or system')
        char_keys = {'character', 'partner_character', 'expression', 'partner_expression', 'mouth_envelope', 'speaker', 'dialogue', 'shot_role', 'character_pos', 'blink_offset'}
        if scene['recipe'] == 'character-stage':
            from .character import CHARACTER_POSITIONS, CHARACTER_PRESETS, EXPRESSIONS, SHOT_ROLES
            for c_key in ('character', 'partner_character'):
                if c_key in params and params[c_key] not in CHARACTER_PRESETS:
                    raise ValueError(f'{sid}.{c_key}: unsupported character preset')
            for e_key in ('expression', 'partner_expression'):
                if e_key in params and params[e_key] not in EXPRESSIONS:
                    raise ValueError(f'{sid}.{e_key}: unsupported expression')
            if 'shot_role' in params and params['shot_role'] not in SHOT_ROLES:
                raise ValueError(f'{sid}.shot_role: unsupported shot role')
            if 'character_pos' in params and params['character_pos'] not in CHARACTER_POSITIONS:
                raise ValueError(f'{sid}.character_pos: unsupported character position')
            if 'blink_offset' in params:
                integer(params['blink_offset'], 0, 10000, f'{sid}.blink_offset')
            if 'speaker' in params:
                text(params['speaker'], f'{sid}.speaker', 48)
                if constraints.get('no_text') and params['speaker']:
                    raise ValueError('no_text conflicts with scene speaker label: ' + sid)
            if 'dialogue' in params:
                text(params['dialogue'], f'{sid}.dialogue', 160)
                if constraints.get('no_text') and params['dialogue']:
                    raise ValueError('no_text conflicts with scene dialogue: ' + sid)
            if 'mouth_envelope' in params:
                env = params['mouth_envelope']
                if not isinstance(env, list) or not 1 <= len(env) <= 10000:
                    raise ValueError(f'{sid}.mouth_envelope: expected 1–10000 samples')
                for v in env:
                    number(v, 0.0, 1.0, f'{sid}.mouth_envelope')
        elif char_keys.intersection(params):
            raise ValueError(f'{sid}: character fields require the character-stage recipe')
        native_shots = {'aperture': ('macro', 'iris', 'assembly', 'hero'), 'cassette': ('label', 'drive', 'edge', 'hero')}
        recipe = scene['recipe']
        if recipe in native_shots:
            if scene['engine'] != 'blender':
                raise ValueError(f'{sid}: {recipe} requires the native Blender renderer')
            if any(params.get(key) for key in ('heading', 'subheading', 'kicker')):
                raise ValueError(f'{sid}: {recipe} does not support typography overlays')
            if recipe == 'cassette' and (constraints.get('no_text') or constraints.get('camera_locked') or scene.get('camera') or plan.get('camera')):
                raise ValueError(f'{sid}: cassette uses printed labeling and authored camera paths')
        if 'shot' in params and params['shot'] not in native_shots.get(recipe, ()):
            raise ValueError(f'{sid}.shot: expected a native {recipe} shot')
        if 'samples' in params:
            if recipe not in native_shots:
                raise ValueError(f'{sid}.samples: expected a native product recipe')
            integer(params['samples'], 8, 256, f'{sid}.samples')
        if scene['recipe'] == 'footage' or scene['engine'] == 'ffmpeg':
            if scene['recipe'] != 'footage' or scene['engine'] != 'ffmpeg':
                raise ValueError(f'{sid}: footage requires engine ffmpeg')
            fields(params, {'source', 'in_frame', 'background', 'speed', 'hdr_to_sdr'}, {'source'}, f'{sid}.params')
            asset_path(params['source'], f'{sid}.source')
            number(params.get('speed', 1), 0.05, 16, sid + '.speed')
            if type(params.get('hdr_to_sdr', False)) is not bool:
                raise ValueError('hdr_to_sdr must be boolean')
            integer(params.get('in_frame', 0), 0, 10_000_000, f'{sid}.in_frame')
        elif {'source', 'in_frame', 'speed', 'hdr_to_sdr'}.intersection(params):
            raise ValueError(f'{sid}: source/in_frame require the footage recipe')
        if scene['recipe'] == 'shape-field':
            from .shapes import validate_shapes
            if scene['engine'] != 'pillow':
                raise ValueError(f'{sid}: shape-field requires pillow')
            fields(params, {'shapes', 'background'}, {'shapes'}, f'{sid}.params')
            validate_shapes(params['shapes'])
        elif 'shapes' in params:
            raise ValueError(f'{sid}: shapes require the shape-field recipe')
        if scene['recipe'] == 'layer-stack':
            if scene['engine'] != 'pillow':
                raise ValueError(f'{sid}: layer-stack requires engine pillow')
            fields(params, {'layers', 'background'}, {'layers'}, f'{sid}.params')
            if not isinstance(params['layers'], list) or not 1 <= len(params['layers']) <= 128:
                raise ValueError(f'{sid}.layers: expected 1–128 raster layers')
            for layer in params['layers']:
                fields(layer, {'source', 'name', 'x', 'y', 'width', 'height', 'opacity', 'blend'}, {'source'}, f'{sid}.layer')
                if layer.get('blend', 'normal') not in ('normal', 'multiply', 'screen', 'overlay'):
                    raise ValueError('Unsupported raster blend mode')
                asset_path(layer['source'], f'{sid}.layer.source')
                for key in ('x', 'y'):
                    integer(layer.get(key, 0), -16384, 16384, f'{sid}.layer.{key}')
                for key in ('width', 'height'):
                    if key in layer:
                        integer(layer[key], 1, 16384, f'{sid}.layer.{key}')
                number(layer.get('opacity', 1.0), 0.0, 1.0, f'{sid}.layer.opacity')
                if 'name' in layer:
                    text(layer['name'], f'{sid}.layer.name')
        elif 'layers' in params:
            raise ValueError(f'{sid}: layers require the layer-stack recipe')
        if scene['recipe'] in {'footage', 'layer-stack'} and scene.get('camera', plan.get('camera', {})):
            raise ValueError(f'{sid}: media recipes do not support camera configuration')
        custom = {'custom-shader': 'fragment_file', 'three-scene': 'module_file'}
        if scene['recipe'] in custom:
            key = custom[scene['recipe']]
            fields(params, {key, 'background', 'foreground', 'accent'}, {key}, f'{sid}.params')
            asset_path(params[key], sid + '.' + key)
            if scene['engine'] != 'browser':
                raise ValueError(f'{sid}: a custom WebGL scene requires the browser')
        elif {'fragment_file', 'module_file'}.intersection(params):
            raise ValueError('WebGL source paths require a custom browser recipe')
        if scene['recipe'] == 'shader-sculpture':
            if scene['engine'] != 'browser':
                raise ValueError(f'{sid}: shader-sculpture requires the browser WebGL2 renderer')
            fields(params, {'background', 'foreground', 'accent'}, set(), f'{sid}.params')
            cam = scene.get('camera', plan.get('camera', {}))
            if set(cam) - {'preset'} or cam.get('preset', 'locked') != 'locked':
                raise ValueError(f'{sid}: shader-sculpture supports its fixed studio camera only')
        if 'camera' in scene:
            _validate_camera(scene['camera'], bool(constraints.get('camera_locked')), f'{sid}.camera')
        if 'transition' in scene:
            tr = scene['transition']
            fields(tr, {'type', 'duration_frames'}, {'type'}, f'{sid}.transition')
            if tr['type'] not in TRANSITIONS:
                raise ValueError(f'{sid}.transition: unsupported transition')
            if 'duration_frames' in tr:
                integer(tr['duration_frames'], 1, max(1, scene['duration_frames'] // 2), f'{sid}.transition.duration_frames')
        if 'locked_regions' in scene:
            regs = scene['locked_regions']
            if not isinstance(regs, list) or len(regs) > 16:
                raise ValueError(f'{sid}.locked_regions: expected at most 16 regions')
            for reg in regs:
                if not isinstance(reg, list) or len(reg) != 4:
                    raise ValueError(f'{sid}.locked_regions: expected [x, y, width, height]')
                integer(reg[0], 0, output['width'] - 2, f'{sid}.locked_regions.x')
                integer(reg[1], 0, output['height'] - 2, f'{sid}.locked_regions.y')
                integer(reg[2], 2, output['width'] - reg[0], f'{sid}.locked_regions.width')
                integer(reg[3], 2, output['height'] - reg[1], f'{sid}.locked_regions.height')

    audio = plan['audio']
    fields(audio, {'enabled', 'gain_db', 'cues', 'export_stems', 'tracks'}, {'enabled', 'gain_db', 'cues'}, 'audio')
    if type(audio['enabled']) is not bool or type(audio['gain_db']) not in {float, int} or not math.isfinite(audio['gain_db']) or not -60 <= audio['gain_db'] <= -6:
        raise ValueError('audio: enabled must be boolean and gain_db must be between -60 and -6')
    if 'export_stems' in audio and type(audio['export_stems']) is not bool:
        raise ValueError('audio.export_stems: must be boolean')
    if constraints.get('no_audio') and audio['enabled']:
        raise ValueError('no_audio conflicts with enabled audio')
    if not isinstance(audio['cues'], list) or len(audio['cues']) > 10000:
        raise ValueError('audio.cues: expected at most 10000 cues')
    total = sum(s['duration_frames'] for s in scenes)
    tracks = audio.get('tracks', [])
    if not isinstance(tracks, list) or len(tracks) > 16:
        raise ValueError('audio.tracks: expected at most 16 source tracks')
    track_ids = set()
    for track in tracks:
        fields(track, {'id', 'source', 'kind', 'start_frame', 'in_frame', 'duration_frames', 'gain_db', 'pan', 'fade_in_frames', 'fade_out_frames'}, {'id', 'source', 'kind', 'start_frame', 'duration_frames'}, 'audio.track')
        tid = track['id']
        if not isinstance(tid, str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', tid) or len(tid) > 64 or tid in track_ids:
            raise ValueError('audio.track.id: expected a unique lowercase hyphenated ID')
        track_ids.add(tid)
        asset_path(track['source'], 'audio.track.source')
        if track['kind'] not in ('voice', 'music', 'effects'):
            raise ValueError('audio.track.kind: expected voice, music or effects')
        if constraints.get('no_voice') and track['kind'] == 'voice' or constraints.get('no_music') and track['kind'] == 'music':
            raise ValueError('audio.track.kind conflicts with project constraints')
        integer(track['start_frame'], 0, total - 1, 'audio.track.start_frame')
        integer(track.get('in_frame', 0), 0, 10_000_000, 'audio.track.in_frame')
        integer(track['duration_frames'], 1, total - track['start_frame'], 'audio.track.duration_frames')
        number(track.get('gain_db', 0), -60, 12, 'audio.track.gain_db')
        number(track.get('pan', 0), -1, 1, 'audio.track.pan')
        for key in ('fade_in_frames', 'fade_out_frames'):
            integer(track.get(key, 0), 0, track['duration_frames'], 'audio.track.' + key)
    for cue in audio['cues']:
        fields(cue, {'frame', 'frequency', 'duration_frames', 'instrument', 'pan', 'gain_offset_db'}, {'frame', 'frequency', 'duration_frames'}, 'audio.cue')
        integer(cue['frame'], 0, total - 1, 'cue.frame')
        integer(cue['frequency'], 30, 8000, 'cue.frequency')
        integer(cue['duration_frames'], 1, total - cue['frame'], 'cue.duration_frames')
        if 'instrument' in cue and cue['instrument'] not in INSTRUMENTS:
            raise ValueError('cue.instrument: unsupported procedural instrument')
        if 'pan' in cue:
            number(cue['pan'], -1.0, 1.0, 'cue.pan')
        if 'gain_offset_db' in cue:
            number(cue['gain_offset_db'], -24.0, 6.0, 'cue.gain_offset_db')
    if not audio['enabled'] and (audio['cues'] or tracks):
        raise ValueError('Disabled audio cannot contain cues or tracks')
    quality = plan.get('quality', {})
    fields(quality, {'exceptions'}, set(), 'quality')
    exceptions = quality.get('exceptions', {})
    fields(exceptions, {'black', 'freeze', 'silence'}, set(), 'quality.exceptions')
    for key, ranges in exceptions.items():
        if not isinstance(ranges, list):
            raise ValueError('quality.exceptions must contain frame interval arrays')
        for interval in ranges:
            if not isinstance(interval, list) or len(interval) != 2:
                raise ValueError('Exception interval must be [start_frame, end_frame)')
            integer(interval[0], 0, total - 1, key + '.start')
            integer(interval[1], interval[0] + 1, total, key + '.end')
    return {'scene_count': len(scenes), 'frames': total, 'fps': str(fps), 'duration': str(Fraction(total, 1) / fps), 'plan_sha256': digest(canonical(plan))}


def load(project: str | Path) -> tuple[Path, Project, ProjectMetadata]:
    root = Path(project).resolve(strict=True)
    plan = read_json(contained_path(root, 'reel.json'), max_bytes=2_000_000)
    return root, plan, validate(plan)


def initialize(project, template='foundation'):
    root = Path(project).absolute()
    if root.is_symlink() or root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('init requires a new or empty directory')
    root.mkdir(parents=True, exist_ok=True)
    from .schema import project_schema
    plan = starter()
    if template == 'promo':
        for scene, heading in zip(plan['scenes'], ['INTRO', 'DETAIL', 'CLOSE']):
            scene['params'].update(heading=heading, subheading='')
    atomic_json(root / 'reel.schema.json', project_schema())
    atomic_json(root / 'reel.json', plan)
    return {'project': str(root), **validate(plan)}


def starter() -> Project:
    return {
        '$schema': './reel.schema.json',
        'schema_version': 1,
        'id': 'motion-study',
        'seed': 42,
        'output': {'width': 960, 'height': 540, 'fps': '30/1'},
        'constraints': {'offline': True, 'no_paid_services': True, 'camera_locked': True, 'no_voice': True, 'no_music': True},
        'scenes': [
            {'id': 'form', 'duration_frames': 90, 'recipe': 'assembly', 'engine': 'pillow', 'params': {'heading': 'FORM', 'subheading': 'Parts find their place.', 'accent': '#bb5537'}},
            {'id': 'time', 'duration_frames': 90, 'recipe': 'rings', 'engine': 'pillow', 'params': {'heading': 'TIME', 'subheading': 'Motion finds its rhythm.', 'accent': '#355f65'}},
            {'id': 'signal', 'duration_frames': 60, 'recipe': 'signal', 'engine': 'pillow', 'params': {'heading': 'SIGNAL', 'subheading': 'Every frame has a purpose.', 'accent': '#bb5537'}},
        ],
        'audio': {'enabled': True, 'gain_db': -14, 'cues': [{'frame': 0, 'frequency': 220, 'duration_frames': 15}, {'frame': 90, 'frequency': 330, 'duration_frames': 15}, {'frame': 180, 'frequency': 440, 'duration_frames': 15}]},
        'quality': {'exceptions': {'freeze': [[65, 90]], 'silence': [[15, 90], [105, 180], [195, 240]]}},
    }
