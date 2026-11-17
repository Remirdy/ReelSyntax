import copy
import re
import shutil
import uuid

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json
from .project import fields, integer, load, project_mutex, validate
from .render import check_locks
from .skills import file_digest


def _ranges(plan):
    result = {}
    cursor = 0
    for scene in plan['scenes']:
        result[scene['id']] = {'start_frame': cursor, 'end_frame': cursor + scene['duration_frames']}
        cursor += scene['duration_frames']
    return result


def _find(scenes, scene_id):
    if not isinstance(scene_id, str):
        raise ValueError('scene_id must be a string')
    for index, scene in enumerate(scenes):
        if scene['id'] == scene_id:
            return index
    raise ValueError('Unknown scene: ' + scene_id)


def _follow_audio(before, after):
    old, new = _ranges(before), _ranges(after)
    def mapped(frame):
        sid, span = next((sid, span) for sid, span in old.items() if span['start_frame'] <= frame < span['end_frame'])
        offset = frame - span['start_frame']
        if sid not in new or offset >= new[sid]['end_frame'] - new[sid]['start_frame']:
            raise ValueError(f'Audio anchor in removed/shortened scene {sid}; revise audio explicitly or use absolute audio timing')
        return new[sid]['start_frame'] + offset
    for cue in after['audio']['cues']:
        cue['frame'] = mapped(cue['frame'])
    for track in after['audio'].get('tracks', []):
        track['start_frame'] = mapped(track['start_frame'])


def prepare_edit(plan, operations, audio_mode='absolute'):
    validate(plan)
    if audio_mode not in {'absolute', 'follow-scenes'}:
        raise ValueError('audio_mode must be absolute or follow-scenes')
    if not isinstance(operations, list) or not 1 <= len(operations) <= 128:
        raise ValueError('Expected 1–128 edit operations')
    candidate = copy.deepcopy(plan)
    scenes = candidate['scenes']
    for operation in operations:
        if not isinstance(operation, dict) or not isinstance(operation.get('type'), str):
            raise ValueError('Each edit operation needs a type')
        kind = operation['type']
        if kind == 'insert':
            fields(operation, {'type', 'scene', 'at_index'}, {'type', 'scene', 'at_index'}, 'insert')
            integer(operation['at_index'], 0, len(scenes), 'insert.at_index')
            scene = operation['scene']
            if not isinstance(scene, dict) or 'id' not in scene:
                raise ValueError('insert.scene must include an id')
            if any(s['id'] == scene['id'] for s in scenes):
                raise ValueError('insert.scene.id already exists')
            scenes.insert(operation['at_index'], copy.deepcopy(scene))
            continue
        if kind == 'move':
            fields(operation, {'type', 'scene_id', 'to_index'}, {'type', 'scene_id', 'to_index'}, 'move')
            index = _find(scenes, operation['scene_id'])
            integer(operation['to_index'], 0, len(scenes) - 1, 'move.to_index')
            scenes.insert(operation['to_index'], scenes.pop(index))
        elif kind == 'duplicate':
            fields(operation, {'type', 'scene_id', 'new_id', 'at_index'}, {'type', 'scene_id', 'new_id'}, 'duplicate')
            index = _find(scenes, operation['scene_id'])
            target = operation.get('at_index', index + 1)
            integer(target, 0, len(scenes), 'duplicate.at_index')
            if any(s['id'] == operation['new_id'] for s in scenes):
                raise ValueError('duplicate.new_id already exists')
            scene = copy.deepcopy(scenes[index])
            scene['id'] = operation['new_id']
            scenes.insert(target, scene)
        elif kind == 'remove':
            fields(operation, {'type', 'scene_id'}, {'type', 'scene_id'}, 'remove')
            scenes.pop(_find(scenes, operation['scene_id']))
        elif kind == 'update':
            fields(operation, {'type', 'scene_id', 'changes'}, {'type', 'scene_id', 'changes'}, 'update')
            changes = operation['changes']
            fields(changes, {'duration_frames', 'recipe', 'engine', 'params', 'camera', 'transition', 'locked_regions'}, set(), 'update.changes')
            if not changes:
                raise ValueError('update.changes cannot be empty')
            scenes[_find(scenes, operation['scene_id'])].update(copy.deepcopy(changes))
        else:
            raise ValueError('Unsupported edit operation: ' + kind)
    structural = copy.deepcopy(candidate)
    structural['audio'] = {'enabled': False, 'gain_db': plan['audio']['gain_db'], 'cues': []}
    structural['quality'] = {'exceptions': {}}
    validate(structural)
    if audio_mode == 'follow-scenes':
        _follow_audio(plan, candidate)
    invalidated = []
    if candidate != plan and candidate.get('quality', {}).get('exceptions'):
        invalidated = [name for name, ranges in candidate['quality']['exceptions'].items() if ranges]
        candidate['quality']['exceptions'] = {}
    metadata = validate(candidate)
    before_ranges, after_ranges = _ranges(plan), _ranges(candidate)
    before_scenes = {s['id']: s for s in plan['scenes']}
    after_scenes = {s['id']: s for s in candidate['scenes']}
    affected = [
        {'scene_id': sid, 'before': before_ranges.get(sid), 'after': after_ranges.get(sid)}
        for sid in dict.fromkeys([*before_ranges, *after_ranges])
        if before_ranges.get(sid) != after_ranges.get(sid) or before_scenes.get(sid) != after_scenes.get(sid)
    ]
    return candidate, {
        'before_sha256': validate(plan)['plan_sha256'], 'after_sha256': metadata['plan_sha256'],
        'before_frames': sum(s['duration_frames'] for s in plan['scenes']), 'after_frames': metadata['frames'],
        'duration_rational': metadata['duration'], 'audio_mode': audio_mode,
        'affected_scenes': affected, 'invalidated_quality_exceptions': invalidated,
        'audio_cue_frames': [c['frame'] for c in candidate['audio']['cues']],
        'audio_track_frames': {t['id']: t['start_frame'] for t in candidate['audio'].get('tracks', [])},
    }


def _expected(metadata, expected):
    if expected is not None and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or metadata['plan_sha256'] != expected):
        raise ValueError('Project differs from expected plan hash; refresh the edit preview')


def _write_edit(root, before, after, operations, audio_mode, undo_of=None):
    before_hash, after_hash = digest(canonical(before)), digest(canonical(after))
    if before_hash == after_hash:
        return None
    if load(root)[2]['plan_sha256'] != before_hash:
        raise ValueError('Project changed while preparing edit; retry from a fresh preview')
    revision = uuid.uuid4().hex
    relative = f'.reelsyntax/edits/{revision}'
    backup = contained_path(root, relative + '.source.json', must_exist=False)
    journal = contained_path(root, relative + '.json', must_exist=False)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(contained_path(root, 'reel.json'), backup)
    if digest(canonical(read_json(backup))) != before_hash:
        raise ValueError('Project changed while saving the edit backup')
    atomic_json(journal, {
        'schema_version': 1, 'operation': 'scene-edit', 'before_plan': before, 'after_plan': after,
        'before_sha256': before_hash, 'after_sha256': after_hash, 'audio_mode': audio_mode,
        'operations': operations, 'undo_of': undo_of,
        'original_source': backup.relative_to(root).as_posix(), 'original_sha256': file_digest(backup),
    })
    if load(root)[2]['plan_sha256'] != before_hash:
        raise ValueError('Project changed before edit commit; source backup retained')
    atomic_json(contained_path(root, 'reel.json'), after)
    return revision


def edit_project(project, operations, apply=False, audio_mode='absolute', expected_plan=None):
    root, plan, metadata = load(project)
    if apply:
        with project_mutex(root):
            _, plan, metadata = load(root)
            _expected(metadata, expected_plan)
            candidate, report = prepare_edit(plan, operations, audio_mode)
            check_locks(root, candidate)
            revision = _write_edit(root, plan, candidate, operations, audio_mode)
            return dict(report, status='applied' if revision else 'unchanged', revision=revision)
    _expected(metadata, expected_plan)
    candidate, report = prepare_edit(plan, operations, audio_mode)
    check_locks(root, candidate)
    return dict(report, status='preview', revision=None)


def undo_edit(project, revision, apply=False, expected_plan=None):
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{32}', revision):
        raise ValueError('Invalid edit revision ID')
    root, _, _ = load(project)
    def prepared():
        _, current, metadata = load(root)
        _expected(metadata, expected_plan)
        record = read_json(contained_path(root, f'.reelsyntax/edits/{revision}.json'))
        if not isinstance(record, dict) or record.get('schema_version') != 1 or record.get('operation') != 'scene-edit':
            raise ValueError('Unsupported edit journal')
        fields(record, {'schema_version', 'operation', 'before_plan', 'after_plan', 'before_sha256', 'after_sha256', 'audio_mode', 'operations', 'undo_of', 'original_source', 'original_sha256'}, {'before_plan', 'after_plan', 'before_sha256', 'after_sha256', 'original_source', 'original_sha256'}, 'edit journal')
        for side in ('before', 'after'):
            validate(record[side + '_plan'])
            if digest(canonical(record[side + '_plan'])) != record[side + '_sha256']:
                raise ValueError('Edit journal integrity mismatch')
        if file_digest(contained_path(root, record['original_source'])) != record['original_sha256']:
            raise ValueError('Original edit source backup integrity mismatch')
        if metadata['plan_sha256'] != record['after_sha256']:
            raise ValueError('Project changed after this edit; reconcile later changes before undo')
        target = record['before_plan']
        check_locks(root, target)
        return current, target, {
            'before_sha256': metadata['plan_sha256'], 'after_sha256': record['before_sha256'],
            'before_frames': metadata['frames'], 'after_frames': validate(target)['frames'], 'undo_of': revision,
        }
    if apply:
        with project_mutex(root):
            current, target, report = prepared()
            saved = _write_edit(root, current, target, [{'type': 'undo', 'revision': revision}], 'snapshot', undo_of=revision)
            return dict(report, status='applied', revision=saved)
    _, _, report = prepared()
    return dict(report, status='preview', revision=None)
