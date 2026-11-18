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
    root.add_argument('--config', type=Path, help='Explicit reelsyntax.toml configuration file')
    commands = root.add_subparsers(dest='command', required=True)

    schema = commands.add_parser('schema', help='Print the editor JSON Schema')
    schema.add_argument('--kind', choices=['reel', 'config'], default='reel')
    schema.add_argument('--schema-version', type=int, default=1)
    schema.add_argument('--output', type=Path)

    migrate = commands.add_parser('migrate', help='Upgrade a legacy or unversioned reel.json to the current schema version')
    migrate.add_argument('project', type=Path)
    migrate.add_argument('--dry-run', action='store_true')
    migrate.add_argument('--remote-schema', action='store_true')
    migrate.add_argument('--json', action='store_true')

    cfg_cmd = commands.add_parser('config', help='Inspect, initialize, or validate reelsyntax.toml configuration')
    cfg_sub = cfg_cmd.add_subparsers(dest='action', required=True)
    cfg_show = cfg_sub.add_parser('show')
    cfg_show.add_argument('--project', type=Path)
    cfg_show.add_argument('--json', action='store_true')
    cfg_path = cfg_sub.add_parser('path')
    cfg_path.add_argument('--project', type=Path)
    cfg_path.add_argument('--json', action='store_true')
    cfg_init = cfg_sub.add_parser('init')
    cfg_init.add_argument('target', nargs='?', type=Path)
    cfg_init.add_argument('--user', action='store_true')
    cfg_init.add_argument('--force', action='store_true')
    cfg_init.add_argument('--json', action='store_true')
    cfg_val = cfg_sub.add_parser('validate')
    cfg_val.add_argument('path', nargs='?', type=Path)
    cfg_val.add_argument('--json', action='store_true')

    captions = commands.add_parser('captions').add_subparsers(dest='operation', required=True)
    burn = captions.add_parser('burn')
    burn.add_argument('project', type=Path)
    burn.add_argument('--profile', choices=['draft', 'production', 'hero'], default='draft')
    burn.add_argument('--style', choices=['plain', 'word-pop'], default='plain')
    burn.add_argument('--words', help='Project-relative JSON word timing table')
    glyphs = commands.add_parser('glyphs', help='Check glyph coverage for a locale sample')
    glyphs.add_argument('locale')
    glyphs.add_argument('--font', type=Path)
    watch = commands.add_parser('watch')
    watch.add_argument('project', type=Path)
    watch.add_argument('--once', action='store_true')
    watch.add_argument('--interval', type=float, default=1.0)
    for kind in ('readme', 'outline', 'mermaid'):
        source = commands.add_parser('from-' + kind)
        source.add_argument('source', type=Path)
        source.add_argument('--output', required=True, type=Path)
    composition = commands.add_parser('compose', help='Nest rendered child projects into a new timeline')
    composition.add_argument('children', type=Path, nargs='+')
    composition.add_argument('--profile', choices=['draft', 'production', 'hero'], default='draft')
    composition.add_argument('--output', type=Path, required=True)
    plugin = commands.add_parser('from-plugin')
    plugin.add_argument('name')
    plugin.add_argument('--params', type=Path)
    plugin.add_argument('--output', required=True, type=Path)
    plugin.add_argument('--allow-plugin', action='store_true')
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
    init.add_argument('--template', choices=['foundation', 'promo'], default='foundation')
    init.add_argument('--json', action='store_true')

    for name in ['validate', 'plan', 'status']:
        command = commands.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--json', action='store_true')

    for name in ['render', 'resume']:
        command = commands.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--profile', choices=['draft', 'production', 'hero'])
        if name == 'render':
            from .variants import TARGETS
            command.add_argument('--aspect', help='Comma-separated width:height ratios')
            command.add_argument('--target', choices=sorted(TARGETS))
            command.add_argument('--locale')
            command.add_argument('--set', action='append', default=[], metavar='SCENE.FIELD=TEXT')
            command.add_argument('--brand', help='Project-relative brand kit JSON')
            command.add_argument('--queue', help='Project-relative delivery jobs JSON')
        command.add_argument('--allow-browser-module', action='store_true')
        command.add_argument('--max-frames', type=int, default=18000)
        command.add_argument('--timeout', type=int, help='Per media process timeout in seconds')
        command.add_argument('--fallback', choices=['pillow', 'browser'], help='Graceful fallback engine when optional Blender is absent')
        command.add_argument('--cache-budget-mib', type=int, help='Prune unused scene caches after delivery; current delivery caches stay protected')
        command.add_argument('--json', action='store_true')

    psd_cmd = commands.add_parser('ingest-psd', help='Extract supported PSD raster layers through an existing optional local Node runtime')
    psd_cmd.add_argument('project', type=Path)
    psd_cmd.add_argument('--composite', action='store_true', help='Import supported pixel masks and blend modes')
    psd_cmd.add_argument('--source', required=True)
    psd_cmd.add_argument('--destination', required=True)

    cache_cmd = commands.add_parser('cache', help='Preview or apply LRU pruning of unreferenced scene caches')
    cache_cmd.add_argument('project', type=Path)
    cache_cmd.add_argument('--max-mib', type=int, required=True)
    cache_cmd.add_argument('--apply', action='store_true', help='Remove selected regenerable caches; default is dry-run')

    qc = commands.add_parser('qc')
    qc.add_argument('project', type=Path)
    qc.add_argument('--profile', choices=['draft', 'production', 'hero'])
    qc.add_argument('--loop', action='store_true')
    qc.add_argument('--html', action='store_true')
    audio = commands.add_parser('audio').add_subparsers(dest='operation', required=True)
    analyze = audio.add_parser('analyze', help='Find frame-aligned transients in a PCM WAV')
    analyze.add_argument('source', type=Path)
    analyze.add_argument('--fps', default='30/1')
    analyze.add_argument('--emit-cues', action='store_true')
    qc.add_argument('--json', action='store_true')

    snapshot = commands.add_parser('snapshot', help='Decode an actual rendered frame')
    snapshot.add_argument('project', type=Path)
    snapshot.add_argument('--frame', required=True, type=int)
    snapshot.add_argument('--profile', choices=['draft', 'production', 'hero'])

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
    export_cmd.add_argument('--format', required=True, choices=['otio', 'fcpxml', 'vtt', 'srt', 'svg', 'blender', 'premiere', 'gif', 'webm', 'poster'])
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
        action.add_argument('--host', choices=['codex', 'antigravity', 'claude', 'cursor', 'copilot'], required=True)
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


def config_command(args):
    from .config import (
        CONFIG_FILENAME,
        discover_project_config,
        load_config,
        read_toml_file,
        user_config_path,
        write_starter_config,
    )

    if args.action == 'show':
        return load_config(config_file=getattr(args, 'config', None), project=args.project).to_dict()
    if args.action == 'path':
        u_path = user_config_path()
        p_path = discover_project_config(project=args.project)
        return {
            'user_config': str(u_path),
            'user_exists': u_path.is_file(),
            'project_config': str(p_path) if p_path else None,
            'project_exists': p_path is not None and p_path.is_file(),
        }
    if args.action == 'init':
        written = write_starter_config(args.target, user_scope=args.user, force=args.force)
        return {'path': str(written), 'created': True}
    if args.action == 'validate':
        target = args.path or getattr(args, 'config', None) or (Path.cwd() / CONFIG_FILENAME)
        normalized = read_toml_file(target)
        return {'path': str(Path(target).resolve()), 'valid': True, 'config_version': normalized['config_version']}
    raise ValueError('Unsupported config action')


def execute(args):
    from .config import config_context, load_config

    project_hint = getattr(args, 'project', None)
    with config_context(getattr(args, 'config', None), project_hint):
        return _execute_with_config(args, load_config)


def _execute_with_config(args, load_config):
    from . import project
    if args.command == 'config':
        return config_command(args)
    if args.command == 'migrate':
        from .migration import migrate_project
        return migrate_project(args.project, dry_run=args.dry_run, remote_schema=args.remote_schema)
    if args.command == 'skills':
        return skill_command(args)
    if args.command == 'captions':
        from .captions import burn
        return burn(args.project, args.profile, args.style, args.words)
    if args.command == 'glyphs':
        from .typography import glyph_audit
        return glyph_audit(args.locale, args.font)
    if args.command == 'watch':
        from .authoring import watch
        return watch(args.project, args.once, args.interval)
    if args.command == 'compose':
        from .authoring import compose
        return compose(args.children, args.profile, args.output)
    if args.command == 'from-plugin':
        from .authoring import plugin_project
        return plugin_project(args.name, args.params, args.output, args.allow_plugin)
    if args.command.startswith('from-'):
        from .authoring import from_source
        return from_source(args.command[5:], args.source, args.output)
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
        return project.initialize(args.project, template=args.template)
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
        cfg = load_config()
        profile = args.profile or cfg.render.default_profile
        timeout = args.timeout if args.timeout is not None else cfg.render.timeout_sec
        if not 1 <= timeout <= 3600:
            raise ValueError('Timeout must be between 1 and 3600 seconds')
        budget_mib = args.cache_budget_mib if args.cache_budget_mib is not None else (cfg.render.cache_budget_mib or None)
        budget = budget_mib * 1024 * 1024 if budget_mib is not None else None
        if args.command == 'render' and any((args.aspect, args.target, args.locale, args.set, args.brand, args.queue)):
            from .variants import render_variants
            args.profile = profile
            return render_variants(args, dict(profile=profile, max_frames=args.max_frames, timeout=timeout,
                                              fallback_engine=args.fallback, cache_budget_bytes=budget, allow_browser_module=args.allow_browser_module))
        return render(args.project, profile, args.max_frames, timeout, recover=args.command == 'resume', fallback_engine=args.fallback, cache_budget_bytes=budget, allow_browser_module=args.allow_browser_module)

    if args.command == 'cache':
        from .cache import prune_cache
        return prune_cache(args.project, args.max_mib * 1024 * 1024, apply=args.apply)

    if args.command == 'ingest-psd':
        from .psd import ingest_psd
        return ingest_psd(args.project, args.source, args.destination, composite=args.composite)
    if args.command == 'audio':
        from .review import audio_onsets
        return audio_onsets(args.source, args.fps, args.emit_cues)
    if args.command == 'qc':
        from .quality import check
        profile = args.profile or load_config().render.default_profile
        return check(args.project, profile, loop=args.loop, html=args.html)
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
        profile = args.profile or load_config().render.default_profile
        root, _, metadata = project.load(args.project)
        if not 0 <= args.frame < metadata['frames']:
            raise ValueError('Frame is outside the timeline')
        artifact = contained_path(root, f'output/{profile}.mp4')
        target = contained_path(root, f'review/{profile}-decoded-{args.frame:06d}.png', must_exist=False)
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
        if args.command == 'schema':
            from .schema import schema_for
            payload = schema_for(args.kind, args.schema_version)
            document = json.dumps(payload, indent=2, ensure_ascii=False)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(document + '\n', encoding='utf-8')
            else:
                print(document)
            return 0
        if args.command == 'mcp':
            from .config import config_context
            from .mcp_server import serve_stdio
            with config_context(args.config, args.workspace):
                return serve_stdio(workspace=args.workspace)
        result = execute(args)
        ok = result.get('technical_status') not in {'fail', 'blocked', 'review'}
        if result.get('unfulfilled_explicit_ids'):
            ok = False
        if args.command == 'skills' and args.action == 'test':
            ok = result['hard_constraint_violation_rate'] == 0
        if args.command == 'doctor' and not args.json:
            for name, tool in result['tools'].items():
                detail = tool.get('version') or tool.get('diagnostic') or ('available' if tool['available'] else 'unavailable')
                print(f'{name:15} {detail}')
            return 0
        print(json.dumps({'ok': ok, 'command': args.command, 'result': result}, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if ok else 2
    except KeyboardInterrupt:
        print(json.dumps({'ok': False, 'command': args.command, 'errors': [{'code': 'interrupted', 'message': 'Operation interrupted; completed scene caches are retained.'}]}), file=sys.stderr)
        return 130
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired, ZeroDivisionError) as error:
        print(json.dumps({'ok': False, 'command': args.command, 'errors': [{'code': 'operation_failed', 'message': str(error)}]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
