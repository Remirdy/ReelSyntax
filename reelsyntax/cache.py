from pathlib import Path
import re
import shutil

from ReelSyntax_Skills.tools.registry import contained_path, read_json
from .project import load, project_mutex


def _cache_inventory(root):
    protected = set()
    for relative in ['.reelsyntax/state.json', *(f'output/{p}-manifest.json' for p in ('draft', 'production', 'hero'))]:
        path = contained_path(root, relative, must_exist=False)
        if path.exists():
            record = read_json(path)
            if not isinstance(record, dict) or not isinstance(record.get('scenes', []), list):
                raise ValueError(f'Invalid cache reference record: {relative}')
            for scene in record.get('scenes', []):
                if not isinstance(scene, dict) or not re.fullmatch('[0-9a-f]{64}', str(scene.get('cache_key', ''))):
                    raise ValueError(f'Invalid scene cache reference: {relative}')
                protected.add(scene['cache_key'])
    base = contained_path(root, '.reelsyntax/cache', must_exist=False)
    entries, ignored = [], []
    if not base.exists():
        return entries, ignored
    for path in sorted(base.iterdir()):
        if path.is_symlink():
            raise ValueError('Cache inventory refuses symbolic links: ' + path.name)
        if not path.is_dir() or not re.fullmatch('[0-9a-f]{64}', path.name):
            ignored.append(path.name)
            continue
        manifest = path / 'manifest.json'
        if not manifest.is_file() or manifest.is_symlink():
            ignored.append(path.name)
            continue
        record = read_json(manifest)
        if not isinstance(record, dict) or record.get('key') != path.name:
            ignored.append(path.name)
            continue
        size = 0
        for child in path.rglob('*'):
            if child.is_symlink():
                raise ValueError('Cache inventory refuses symbolic links: ' + str(child.relative_to(base)))
            if child.is_file():
                size += child.stat().st_size
        entries.append({'key': path.name, 'bytes': size, 'last_used_ns': path.stat().st_mtime_ns, 'protected': path.name in protected})
    return entries, ignored


def _prune_locked(root: Path, max_bytes: int, apply: bool = False) -> dict:
    if type(max_bytes) is not int or max_bytes < 0:
        raise ValueError('max_bytes must be a nonnegative integer')
    entries, ignored = _cache_inventory(root)
    before = sum(e['bytes'] for e in entries)
    remaining = before
    selected = []
    for entry in sorted(entries, key=lambda e: (e['last_used_ns'], e['key'])):
        if remaining <= max_bytes:
            break
        if not entry['protected']:
            selected.append(entry)
            remaining -= entry['bytes']
    removed = 0
    if apply:
        for entry in selected:
            directory = contained_path(root, '.reelsyntax/cache/' + entry['key'], must_exist=False)
            shutil.rmtree(directory)
            removed += entry['bytes']
    return {
        'dry_run': not apply, 'max_bytes': max_bytes, 'before_bytes': before,
        'projected_bytes': remaining, 'removed_bytes': removed,
        'within_budget': remaining <= max_bytes, 'protected_entries': sum(e['protected'] for e in entries),
        'selected': selected, 'ignored': ignored,
        'scope': 'recognized scene caches only; current delivery/state references are protected',
    }


def prune_cache(project, max_bytes: int, apply: bool = False) -> dict:
    root, _, _ = load(project)
    with project_mutex(root):
        return _prune_locked(root, max_bytes, apply)
