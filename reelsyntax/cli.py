import argparse
import json
from pathlib import Path
import subprocess
import sys

from ReelSyntax_Skills.tools.registry import STAGES, contained_path, load_index, read_json
from . import __version__


def parser():
    root = argparse.ArgumentParser(prog='reelsyntax', description='Local skill routing, unified MCP gateway, and deterministic video production.')
    root.add_argument('--version', action='version', version=__version__)
    commands = root.add_subparsers(dest='command', required=True)

    doctor = commands.add_parser('doctor', help='Report installed media and first-party MCP dependencies without installing anything')
    doctor.add_argument('--json', action='store_true')

    integrations_cmd = commands.add_parser('integrations', help='Inspect first-party BlenderMCP and AfterEffectsMCP submodule and runtime status')
    integrations_cmd.add_argument('--json', action='store_true')

    caps_cmd = commands.add_parser('capabilities', help='Discover or search namespaced first-party MCP gateway capabilities')
    caps_cmd.add_argument('--refresh', action='store_true', help='Re-introspect live MCP servers and refresh capability registry')
    caps_cmd.add_argument('--query', default='', help='Optional intent query to filter capabilities progressively')
    caps_cmd.add_argument('--namespace', choices=['blender', 'after_effects'])
    caps_cmd.add_argument('--stage', choices=sorted(STAGES))
    caps_cmd.add_argument('--limit', type=int, default=12)
    caps_cmd.add_argument('--json', action='store_true')

    install_cmd = commands.add_parser('install', help='Initialize or reuse optional first-party MCP integrations')
    install_cmd.add_argument('target', nargs='?', choices=['blender', 'after-effects'])
    install_cmd.add_argument('--all', action='store_true', dest='install_all')
    install_cmd.add_argument('--dry-run', action='store_true')
    install_cmd.add_argument('--json', action='store_true')

    update_cmd = commands.add_parser('update', help='Check or synchronize first-party MCP submodules with schema validation and rollback')
    update_cmd.add_argument('target', nargs='?', default='all', choices=['all', 'blender', 'after-effects'])
    update_cmd.add_argument('--apply', action='store_true', help='Apply validated upstream submodule update instead of check-only')
    update_cmd.add_argument('--rollback', action='store_true', help='Roll submodule back to last known working commit')
    update_cmd.add_argument('--json', action='store_true')

    mcp = commands.add_parser('mcp', help='Start the Unified MCP Gateway stdio server')
    mcp.add_argument('--workspace', type=Path, default=Path.cwd(), help='Authorized project root; defaults to the current directory')

    init = commands.add_parser('init', help='Create a procedural motion project in a new or empty directory')
    init.add_argument('project', type=Path)
    init.add_argument('--json', action='store_true')

    for name in ['validate', 'plan', 'status']:
        command = commands.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--json', action='store_true')

    for name in ['render', 'resume']:
        command = commands.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--profile', choices=['draft', 'production', 'hero'], default='draft')
        command.add_argument('--max-frames', type=int, default=18000)
        command.add_argument('--timeout', type=int, default=180, help='Per media process timeout in seconds')
        command.add_argument('--fallback', choices=['pillow', 'browser'], help='Graceful fallback engine when optional Blender is absent')
        command.add_argument('--cache-budget-mib', type=int, help='Prune unused scene caches after delivery; current delivery caches stay protected')
        command.add_argument('--json', action='store_true')

    psd_cmd = commands.add_parser('ingest-psd', help='Extract supported PSD raster layers through an existing optional local Node runtime')
    psd_cmd.add_argument('project', type=Path)
    psd_cmd.add_argument('--source', required=True)
    psd_cmd.add_argument('--destination', required=True)

    cache_cmd = commands.add_parser('cache', help='Preview or apply LRU pruning of unreferenced scene caches')
    cache_cmd.add_argument('project', type=Path)
    cache_cmd.add_argument('--max-mib', type=int, required=True)
    cache_cmd.add_argument('--apply', action='store_true', help='Remove selected regenerable caches; default is dry-run')

    qc = commands.add_parser('qc')
    qc.add_argument('project', type=Path)
    qc.add_argument('--profile', choices=['draft', 'production', 'hero'], default='draft')
    qc.add_argument('--json', action='store_true')

    snapshot = commands.add_parser('snapshot', help='Decode an actual rendered frame')
    snapshot.add_argument('project', type=Path)
    snapshot.add_argument('--frame', required=True, type=int)
    snapshot.add_argument('--profile', choices=['draft', 'production', 'hero'], default='draft')

    lock = commands.add_parser('lock', help='Protect specified scene sources, timing, or rendered ROI pixel regions')
    lock.add_argument('project', type=Path)
    lock.add_argument('--scene', action='append', required=True)
    lock.add_argument('--roi-profile', choices=['draft', 'production', 'hero'], help='Lock declared scene locked_regions pixels for profile')

    for name in ['checkpoint', 'restore']:
        command = commands.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--name', required=True)

    diff_cmd = commands.add_parser('diff', help='Compare two rendered profiles and emit pixel/loudness delta metrics')
    diff_cmd.add_argument('project', type=Path)
    diff_cmd.add_argument('--base', choices=['draft', 'production', 'hero'], default='draft')
    diff_cmd.add_argument('--target', choices=['draft', 'production', 'hero'], default='production')
    diff_cmd.add_argument('--json', action='store_true')

    export_cmd = commands.add_parser('export', help='Export OTIO, FCPXML, WebVTT, SRT, or SVG editorial artifacts')
    export_cmd.add_argument('project', type=Path)
    export_cmd.add_argument('--format', required=True, choices=['otio', 'fcpxml', 'vtt', 'srt', 'svg', 'blender'])
    export_cmd.add_argument('--profile', choices=['draft', 'production', 'hero'], default='production')
    export_cmd.add_argument('--output', type=Path)
    export_cmd.add_argument('--frame', type=int, default=0)
    export_cmd.add_argument('--json', action='store_true')

    handoff_cmd = commands.add_parser('handoff', help='Generate coordinated BlenderMCP and AfterEffectsMCP interchange package')
    handoff_cmd.add_argument('project', type=Path)
    handoff_cmd.add_argument('--output', type=Path)
    handoff_cmd.add_argument('--no-jsx-check', action='store_true')
    handoff_cmd.add_argument('--json', action='store_true')

    skills = commands.add_parser('skills', help='Metadata discovery, explicit loading and local execution evidence')
    actions = skills.add_subparsers(dest='action', required=True)
    for name in ['search', 'explain']:
        action = actions.add_parser(name)
        action.add_argument('query', nargs='?', default='')
        action.add_argument('--task', type=Path, help='Structured task envelope JSON')
        action.add_argument('--stage', choices=sorted(STAGES))
        action.add_argument('--category', action='append', default=[])
        action.add_argument('--include', action='append', default=[])
        action.add_argument('--exclude', action='append', default=[])
        action.add_argument('--available', help='Comma-separated verified capability allowlist')
        action.add_argument('--limit', type=int, default=6)
        action.add_argument('--context-budget', type=int, default=6000)
        action.add_argument('--word-budget', type=int, default=2400)
        action.add_argument('--project', type=Path, help='Explicit opt-in local route cache')
        action.add_argument('--json', action='store_true')
    get = actions.add_parser('load', help='Explicitly load one hash-checked instruction body or resource')
    get.add_argument('id')
    get.add_argument('--context-budget', type=int, default=6000)
    get.add_argument('--resource')
    get.add_argument('--project', type=Path)
    get.add_argument('--session', help='Explicit context session with cumulative budget and duplicate-load suppression')
    listing = actions.add_parser('list', help='Bounded metadata listing')
    listing.add_argument('--category', required=True)
    listing.add_argument('--limit', type=int, default=6)
    listing.add_argument('--offset', type=int, default=0)
    for name in ['validate', 'reindex', 'test']:
        actions.add_parser(name)
    for name in ['install', 'uninstall']:
        action = actions.add_parser(name)
        action.add_argument('project', type=Path)
        action.add_argument('--host', choices=['codex', 'antigravity', 'claude', 'cursor'], required=True)
    record = actions.add_parser('record', help='Record a caller-reported outcome and hash real artifact evidence')
    record.add_argument('project', type=Path)
    record.add_argument('--skill', required=True)
    record.add_argument('--outcome', choices=['success', 'failure', 'blocked'], required=True)
    record.add_argument('--artifact', action='append', default=[])
    stats = actions.add_parser('effectiveness')
    stats.add_argument('project', type=Path)
    return root


def skill_command(args):
    from . import skills
    if args.action in {'search', 'explain'}:
        if args.task:
            task = read_json(args.task, max_bytes=64000)
        else:
            task = {
                'intent': args.query, 'include': args.include, 'exclude': args.exclude, 'categories': args.category,
                'max_skills': args.limit, 'context_budget': args.context_budget, 'word_budget': args.word_budget,
            }
            if args.stage:
                task['stage'] = args.stage
            if args.available is not None:
                task['capabilities'] = [x.strip() for x in args.available.split(',') if x.strip()]
        return skills.search(task, args.project, explain=(args.action == 'explain'))
    if args.action == 'load':
        if not 1 <= args.context_budget <= 64000:
            raise ValueError('Context budget must be between 1 and 64000')
        if bool(args.project) != bool(args.session):
            raise ValueError('--project and --session must be supplied together for cumulative loading')
        if args.project:
            return skills.session_load(args.project, args.session, args.id, args.context_budget, args.resource)
        return skills.get_skill(args.id, args.context_budget, args.resource)
    if args.action == 'list':
        if not 1 <= args.limit <= 20 or args.offset < 0:
            raise ValueError('Invalid listing limit or offset')
        rows = load_index()['skills']
        if args.category not in {r['category'] for r in rows}:
            raise ValueError('Unknown category')
        rows = [r for r in rows if r['category'] == args.category]
        return {'total': len(rows), 'skills': [{key: row[key] for key in ['id', 'description', 'stage', 'status', 'version']} for row in rows[args.offset:args.offset + args.limit]], 'skill_bodies_read': 0}
    if args.action in {'validate', 'reindex'}:
        if args.action == 'reindex':
            from ReelSyntax_Skills.tools.reindex import rebuild as rebuild_catalog
            document = rebuild_catalog(quiet=True)
        else:
            document = load_index()
        return {'skills': len(document['skills']), 'digest': document['digest'], 'schema_version': document['schema_version']}
    if args.action == 'test':
        from .evaluation import evaluate
        return evaluate()
    if args.action in {'install', 'uninstall'}:
        from . import hosts
        return getattr(hosts, args.action)(args.project, args.host)
    if args.action == 'record':
        return skills.record_execution(args.project, args.skill, args.outcome, args.artifact)
    if args.action == 'effectiveness':
        return skills.effectiveness(args.project)
    raise ValueError('Unsupported skill action')


def execute(args):
    from . import project
    if args.command == 'skills':
        return skill_command(args)
    if args.command == 'doctor':
        from .media import doctor
        return doctor()
    if args.command == 'integrations':
        from .gateway import McpGateway
        with McpGateway() as gw:
            return gw.status()
    if args.command == 'capabilities':
        from .gateway import McpGateway
        with McpGateway() as gw:
            if args.query or args.namespace or args.stage:
                return gw.search_tools(args.query, namespace=args.namespace, stage=args.stage, limit=min(25, max(1, args.limit)), refresh=args.refresh)
            snap = gw.load_catalog(refresh=args.refresh)
            return {
                'refreshed_at': snap.get('refreshed_at'),
                'digest': snap.get('digest'),
                'total_tools': snap.get('total_tools'),
                'servers': snap.get('servers'),
                'changes_since_previous': snap.get('changes_since_previous'),
                'sample_tools': [
                    {k: t[k] for k in ('id', 'stage', 'summary', 'compatible_skills')}
                    for t in snap.get('tools', [])[:max(1, min(25, args.limit))]
                ],
                'full_schemas_exposed': 0,
            }
    if args.command == 'install':
        from .gateway import install_integration
        if bool(args.install_all) == bool(args.target):
            raise ValueError("Specify either a target ('blender' or 'after-effects') or '--all'")
        return install_integration('all' if args.install_all else args.target, dry_run=args.dry_run)
    if args.command == 'update':
        from .gateway import update_integrations
        return update_integrations(args.target, check_only=(not args.apply and not args.rollback), rollback=args.rollback)
    if args.command == 'init':
        return project.initialize(args.project)
    if args.command in {'validate', 'plan', 'status'}:
        root, plan, metadata = project.load(args.project)
        if args.command == 'validate':
            return metadata
        if args.command == 'status':
            path = contained_path(root, '.reelsyntax/state.json', must_exist=False)
            return read_json(path) if path.exists() else {'status': 'not-rendered', **metadata}
        start, scenes = 0, []
        for scene in plan['scenes']:
            scenes.append({'id': scene['id'], 'engine': scene['engine'], 'recipe': scene['recipe'], 'frame_range': [start, start + scene['duration_frames']]})
            start += scene['duration_frames']
        return {**metadata, 'scenes': scenes, 'constraints': plan.get('constraints', {}), 'network': 'no render networking is implemented'}
    if args.command in {'render', 'resume'}:
        from .render import render
        if not 1 <= args.timeout <= 3600:
            raise ValueError('Timeout must be between 1 and 3600 seconds')
        budget = args.cache_budget_mib * 1024 * 1024 if args.cache_budget_mib is not None else None
        return render(args.project, args.profile, args.max_frames, args.timeout, recover=args.command == 'resume', fallback_engine=args.fallback, cache_budget_bytes=budget)

    if args.command == 'cache':
        from .cache import prune_cache
        return prune_cache(args.project, args.max_mib * 1024 * 1024, apply=args.apply)

    if args.command == 'ingest-psd':
        from .psd import ingest_psd
        return ingest_psd(args.project, args.source, args.destination)
    if args.command == 'qc':
        from .quality import check
        return check(args.project, args.profile)
    if args.command == 'lock':
        from .render import lock
        return lock(args.project, args.scene, roi_profile=args.roi_profile)
    if args.command in {'checkpoint', 'restore'}:
        from . import revisions
        return getattr(revisions, args.command)(args.project, args.name)
    if args.command == 'diff':
        from .diff import compare_profiles
        return compare_profiles(args.project, args.base, args.target)
    if args.command == 'export':
        from .interchange import export_project
        return export_project(args.project, args.format, args.profile, args.output, args.frame)
    if args.command == 'handoff':
        from .gateway import build_handoff_package
        return build_handoff_package(args.project, args.output, verify_jsx=not args.no_jsx_check)
    if args.command == 'snapshot':
        from .media import executable, run
        root, _, metadata = project.load(args.project)
        if not 0 <= args.frame < metadata['frames']:
            raise ValueError('Frame is outside the timeline')
        artifact = contained_path(root, f'output/{args.profile}.mp4')
        target = contained_path(root, f'review/{args.profile}-decoded-{args.frame:06d}.png', must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        run([executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-i', str(artifact), '-vf', f'select=eq(n\\,{args.frame})', '-frames:v', '1', str(target)])
        if not target.is_file():
            raise ValueError('Frame decoder produced no artifact')
        return {'artifact': target.relative_to(root).as_posix(), 'frame': args.frame, 'source': artifact.relative_to(root).as_posix()}
    raise ValueError('Unsupported command')


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    try:
        if args.command == 'mcp':
            from .mcp_server import serve_stdio
            return serve_stdio(workspace=args.workspace)
        result = execute(args)
        ok = result.get('technical_status') not in {'fail', 'blocked', 'review'}
        if result.get('unfulfilled_explicit_ids'):
            ok = False
        if args.command == 'skills' and args.action == 'test':
            ok = result['hard_constraint_violation_rate'] == 0
        print(json.dumps({'ok': ok, 'command': args.command, 'result': result}, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if ok else 2
    except KeyboardInterrupt:
        print(json.dumps({'ok': False, 'command': args.command, 'errors': [{'code': 'interrupted', 'message': 'Operation interrupted; completed scene caches are retained.'}]}), file=sys.stderr)
        return 130
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'ok': False, 'command': args.command, 'errors': [{'code': 'operation_failed', 'message': str(error)}]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
