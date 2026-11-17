import re
from pathlib import Path
import shutil
import uuid

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, digest, read_json
from .project import load, validate
from .render import check_locks
from .skills import file_digest


def checkpoint(project, name):
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
        raise ValueError('Checkpoint name must be a lowercase hyphenated ID of at most 64 characters')
    root, plan, metadata = load(project)
    path = contained_path(root, f'.reelsyntax/checkpoints/{name}.json', must_exist=False)
    if path.exists():
        raise ValueError('Checkpoint already exists; choose a new name')
    atomic_json(path, {'schema_version': 1, 'plan': plan, 'sha256': metadata['plan_sha256']})
    return {'checkpoint': name, 'plan_sha256': metadata['plan_sha256']}


def restore(project, name):
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
        raise ValueError('Invalid checkpoint name')
    root = Path(project).resolve(strict=True)
    current = contained_path(root, 'reel.json')
    saved = read_json(contained_path(root, f'.reelsyntax/checkpoints/{name}.json'))
    validate(saved['plan'])
    if digest(canonical(saved['plan'])) != saved['sha256']:
        raise ValueError('Checkpoint digest mismatch')
    check_locks(root, saved['plan'])
    revision = uuid.uuid4().hex
    history = contained_path(root, f'.reelsyntax/revisions/{revision}.json', must_exist=False)
    original = contained_path(root, f'.reelsyntax/revisions/{revision}.reel.json', must_exist=False)
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(current, original)
    atomic_json(history, {'schema_version': 1, 'operation': 'restore', 'checkpoint': name,
                          'before_source': original.relative_to(root).as_posix(), 'before_source_sha256': file_digest(original),
                          'after_sha256': saved['sha256']})
    atomic_json(current, saved['plan'])
    return {'restored': name, 'revision': revision, 'plan_sha256': saved['sha256']}
