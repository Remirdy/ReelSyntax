import argparse
import json
from pathlib import Path
import re
import subprocess

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, digest, read_json
from .gateway import INTEGRATIONS, REPO_ROOT, _parse_semver, _read_package_version, diff_capability_snapshots, summarize_tool_entry


def static_extract_submodule_tools(target: str, sub_root: Path) -> list[dict]:
    entries = []
    if target == 'after-effects':
        index_ts = sub_root / 'src/index.ts'
        if index_ts.is_file():
            text = index_ts.read_text(encoding='utf-8', errors='replace')
            for match in re.finditer(r'server\.tool\(\s*"([^"]+)"\s*,\s*(?:"([^"]*)"|([a-zA-Z0-9_$.]+))', text):
                name, desc = match.group(1), match.group(2) or ''
                entries.append(summarize_tool_entry('after_effects', {'name': name, 'description': desc, 'inputSchema': {'type': 'object', 'properties': {}}}))
    elif target == 'blender':
        tools_dir = sub_root / 'server/tools'
        if tools_dir.is_dir():
            seen = set()
            for py_file in sorted(tools_dir.glob('*.py')):
                text = py_file.read_text(encoding='utf-8', errors='replace')
                for match in re.finditer(r'@mcp\.tool\([^)]*\)\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\(([^)]*)\)(?:\s*->[^:]+)?:\s*(?:"""([^"]*?)""")?', text, flags=re.S):
                    name, sig, doc = match.group(1), match.group(2), (match.group(3) or '').strip()
                    if name in seen:
                        continue
                    seen.add(name)
                    props, req = {}, []
                    for param in [p.strip() for p in sig.split(',') if p.strip()]:
                        p_name = param.split(':')[0].split('=')[0].strip()
                        if not p_name or p_name in {'self', 'ctx'}:
                            continue
                        props[p_name] = {'type': 'string'}
                        if '=' not in param:
                            req.append(p_name)
                    entries.append(summarize_tool_entry('blender', {'name': name, 'description': doc, 'inputSchema': {'type': 'object', 'properties': props, 'required': req}}))
    entries.sort(key=lambda x: x['id'])
    return entries


def evaluate_submodule_candidate(target: str, repo_root: Path = REPO_ROOT, baseline_path: Path | None = None) -> dict:
    spec = INTEGRATIONS[target]
    sub_dir = repo_root / spec['submodule_path']
    pkg_ver = _read_package_version(target, sub_dir)
    if pkg_ver is None:
        return {'ok': False, 'target': target, 'error': f"Missing or invalid manifest in {spec['submodule_path']}"}
    version_ok = _parse_semver(pkg_ver) >= spec['min_version']
    tools = static_extract_submodule_tools(target, sub_dir)
    current_snap = {
        'target': target,
        'package_version': pkg_ver,
        'tool_count': len(tools),
        'digest': digest(canonical([{'id': t['id'], 'schema_sha256': t['schema_sha256']} for t in tools])),
        'tools': tools,
    }
    prev_snap = read_json(baseline_path) if baseline_path and baseline_path.is_file() else None
    diff = diff_capability_snapshots(prev_snap, current_snap) if prev_snap else None
    ok = version_ok and len(tools) > 0
    return {
        'ok': ok,
        'target': target,
        'repository': spec['repo'],
        'package_version': pkg_ver,
        'min_compatible_version': '.'.join(map(str, spec['min_version'])),
        'version_compatible': version_ok,
        'extracted_tool_count': len(tools),
        'snapshot_digest': current_snap['digest'],
        'schema_diff': diff,
        'snapshot': current_snap,
    }


def format_markdown_summary(report: dict, commit_sha: str, latest_tag: str | None = None) -> str:
    lines = [
        f"### Submodule Synchronization Audit: `{report['repository']}`",
        '',
        f"- **Target**: `{report['target']}`",
        f"- **Candidate Commit**: `{commit_sha}`",
        f"- **Latest Release Tag**: `{latest_tag or 'none'}`",
        f"- **Package Version**: `{report.get('package_version')}` (min `{report.get('min_compatible_version')}`)",
        f"- **Extracted MCP Tools**: `{report.get('extracted_tool_count', 0)}`",
        f"- **Compatibility Gate**: `{'PASS' if report.get('ok') else 'FAIL'}`",
    ]
    diff = report.get('schema_diff')
    if diff:
        lines.extend([
            '',
            '#### Capability & Schema Delta',
            f"- Added tools: **{diff['added_count']}**",
            f"- Modified tools: **{diff['modified_count']}**",
            f"- Removed tools: **{diff['removed_count']}**",
            f"- Breaking changes: **{diff['breaking_count']}** (`backward_compatible={diff['backward_compatible']}`)",
            f"- Affected ReelSyntax skills: `{', '.join(diff['affected_skills']) or 'none'}`",
        ])
        if diff['added']:
            lines.append(f"- New IDs (up to 15): `{', '.join(diff['added'][:15])}`")
        if diff['breaking']:
            lines.append(f"- Breaking details: `{json.dumps(diff['breaking'][:5], ensure_ascii=False)}`")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit submodule MCP compatibility and schema changes.')
    parser.add_argument('--target', choices=sorted(INTEGRATIONS), required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--write-snapshot', type=Path)
    parser.add_argument('--markdown-out', type=Path)
    parser.add_argument('--commit-sha', default='HEAD')
    parser.add_argument('--release-tag', default='')
    args = parser.parse_args(argv)

    report = evaluate_submodule_candidate(args.target, REPO_ROOT, args.baseline)
    if args.write_snapshot and 'snapshot' in report:
        atomic_json(args.write_snapshot, report['snapshot'])
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(format_markdown_summary(report, args.commit_sha, args.release_tag or None), encoding='utf-8')
    summary = {k: v for k, v in report.items() if k != 'snapshot'}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report.get('ok') else 2


if __name__ == '__main__':
    raise SystemExit(main())
