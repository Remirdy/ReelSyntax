from datetime import datetime, timezone
from pathlib import Path
import uuid

from ReelSyntax_Skills.tools.registry import ROOT, atomic_json, canonical, contained_path, digest, load_index, load_skill, read_json
from ReelSyntax_Skills.tools.route import route_task


def search(task: dict, project: str | Path | None = None, explain: bool = False) -> dict:
    task = dict(task)
    if project is not None:
        project = Path(project).resolve(strict=True)
        plan_path = contained_path(project, 'reel.json', must_exist=False)
        if plan_path.exists():
            from .project import load
            _, plan, _ = load(project)
            constraints = dict(plan.get('constraints', {}))
            supplied = task.get('constraints', {})
            if not isinstance(supplied, dict):
                raise ValueError('Routing constraints must be an object')
            for key, value in supplied.items():
                if constraints.get(key) and value is False:
                    raise ValueError('Routing task attempts to relax a saved project constraint: ' + key)
                constraints[key] = value
            task['constraints'] = constraints
    document = load_index()
    cache_key = digest(canonical({'registry': document['digest'], 'task': task, 'explain': explain, 'router_version': 3}))
    cached = None
    if project is not None:
        project = Path(project).resolve(strict=True)
        cached = contained_path(project, f'.reelsyntax/skills/cache/{cache_key}.json', must_exist=False)
        if cached.exists():
            result = read_json(cached)
            result['cache_hit'] = True
            result['index_maintenance_body_reads'] = document['maintenance_body_reads']
            return result
    result = route_task(task, document['skills'], include_diagnostics=explain)
    result['registry_digest'] = document['digest']
    result['index_maintenance_body_reads'] = document['maintenance_body_reads']
    result['cache_hit'] = False
    if cached is not None:
        atomic_json(cached, result)
    return result


def get_skill(sid, token_budget=6000, resource=None):
    document = load_index()
    row = next((row for row in document['skills'] if row['id'] == sid), None)
    if row is None:
        raise ValueError('Unknown skill ID: ' + sid)
    if resource is None:
        return {'id': sid, 'version': row['version'], 'sha256': row['sha256'], 'instructions': load_skill(row, token_budget=token_budget), 'resources': row.get('resources', []), 'skill_bodies_read': 1}
    if resource not in row.get('resources', []):
        raise ValueError('Resource is not declared for this skill')
    data = contained_path(ROOT, resource).read_bytes()
    if digest(data) != row.get('resource_sha256', {}).get(resource):
        raise ValueError('Resource changed; validate and reindex before loading')
    if (len(data) + 2) // 3 > token_budget:
        raise ValueError('Resource exceeds context budget')
    return {'id': sid, 'resource': resource, 'content': data.decode('utf-8'), 'skill_bodies_read': 0, 'executed': False}


def session_load(project, session, sid, token_budget=6000, resource=None):
    import re
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', session) or len(session) > 64:
        raise ValueError('Session must be a lowercase hyphenated ID of at most 64 characters')
    root = Path(project).resolve(strict=True)
    path = contained_path(root, f'.reelsyntax/skills/sessions/{session}.json', must_exist=False)
    mutex = contained_path(root, f'.reelsyntax/skills/sessions/{session}.lock', must_exist=False)
    mutex.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = mutex.open('x')
    except FileExistsError as error:
        raise ValueError('Session is busy; do not load concurrently into one session') from error
    try:
        handle.close()
        state = read_json(path) if path.exists() else {'budget': token_budget, 'charged_tokens': 0, 'loaded': []}
        if state['budget'] != token_budget or type(state['charged_tokens']) is not int or not 0 <= state['charged_tokens'] <= token_budget:
            raise ValueError('Session budget changed or state is invalid; use a new session ID')
        document = load_index()
        row = next((r for r in document['skills'] if r['id'] == sid), None)
        if row is None:
            raise ValueError('Unknown skill ID: ' + sid)
        version_key = f'{sid}:{row["sha256"]}:{resource or "body"}'
        if version_key in state['loaded']:
            return {'id': sid, 'already_loaded': True, 'skill_bodies_read': 0, 'charged_tokens': state['charged_tokens'], 'remaining_tokens': token_budget - state['charged_tokens']}
        remaining = token_budget - state['charged_tokens']
        if remaining <= 120:
            raise ValueError('Session context budget exhausted; retain a compact handoff before starting another session')
        result = get_skill(sid, remaining - 120, resource)
        content = result.get('instructions', result.get('content', ''))
        charge = (len(content.encode('utf-8')) + 2) // 3 + 120
        state['charged_tokens'] += charge
        state['loaded'].append(version_key)
        atomic_json(path, state)
        return {**result, 'charged_tokens': state['charged_tokens'], 'remaining_tokens': token_budget - state['charged_tokens'], 'session': session}
    finally:
        mutex.unlink(missing_ok=True)


def record_execution(project, sid, outcome, artifacts=()):
    document = load_index()
    row = next((row for row in document['skills'] if row['id'] == sid), None)
    if row is None or outcome not in {'success', 'failure', 'blocked'}:
        raise ValueError('Invalid skill ID or execution outcome')
    project = Path(project).resolve(strict=True)
    evidence = []
    for relative in artifacts:
        artifact = contained_path(project, relative)
        evidence.append({'path': relative, 'sha256': file_digest(artifact), 'bytes': artifact.stat().st_size})
    if outcome == 'success' and not evidence:
        raise ValueError('A reported success requires at least one existing artifact')
    execution_id = uuid.uuid4().hex
    event = {'schema_version': 1, 'execution_id': execution_id, 'skill_id': sid, 'version': row['version'],
             'skill_sha256': row['sha256'], 'registry_digest': document['digest'], 'outcome': outcome,
             'reported_at': datetime.now(timezone.utc).isoformat(), 'evidence': evidence,
             'evaluation_scope': 'caller-reported outcome; artifact existence and hashes checked, creative quality unverified'}
    target = contained_path(project, f'.reelsyntax/skills/executions/{execution_id}.json', must_exist=False)
    atomic_json(target, event)
    return event


def file_digest(path):
    import hashlib
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def effectiveness(project):
    root = Path(project).resolve(strict=True)
    directory = contained_path(root, '.reelsyntax/skills/executions', must_exist=False)
    summary = {}
    for path in sorted(directory.glob('*.json')):
        event = read_json(contained_path(root, path.relative_to(root).as_posix()))
        item = summary.setdefault(event['skill_id'], {'success': 0, 'failure': 0, 'blocked': 0})
        item[event['outcome']] += 1
    for value in summary.values():
        completed = value['success'] + value['failure']
        value['reported_success_rate'] = value['success'] / completed if completed else None
    return {'skills': summary, 'scope': 'caller-reported outcomes; no inferred aesthetic score'}
