from pathlib import Path
import sys

from ReelSyntax_Skills.tools.registry import ROOT, atomic_json, contained_path, digest, read_json

HOST_PATHS = {
    'codex': '.agents/skills',
    'antigravity': '.agents/skills',
    'claude': '.claude/skills',
    'cursor': '.cursor/skills',
}


def install(project, host):
    root = Path(project).resolve(strict=True)
    if not root.is_dir() or host not in HOST_PATHS:
        raise ValueError('Invalid project or unsupported host')
    directory = f'{HOST_PATHS[host]}/reelsyntax-router'
    target = contained_path(root, directory + '/SKILL.md', must_exist=False)
    receipt = contained_path(root, directory + '/installation.json', must_exist=False)
    launcher = contained_path(root, directory + '/route.py', must_exist=False)
    source = (ROOT / '.agents/skills/reelsyntax-router/SKILL.md').read_text(encoding='utf-8')
    content = source + '\n## Installed checkout\n\nUse the adjacent `route.py` launcher with the configured Python interpreter. It resolves the pack without scanning the library. Reinstall after moving the checkout.\n'
    script = 'import runpy\nimport sys\nfrom pathlib import Path\n' + 'pack = Path(' + repr(str(ROOT)) + ')\n' + "sys.path.insert(0, str(pack.parent))\nrunpy.run_path(str(pack / 'tools/route.py'), run_name='__main__')\n"
    files = {'SKILL.md': content.encode(), 'route.py': script.encode()}
    if receipt.exists():
        previous = read_json(receipt)
        compatible_hosts = {k for k, v in HOST_PATHS.items() if v == HOST_PATHS[host]}
        if previous.get('owner') != 'reelsyntax' or previous.get('host') not in compatible_hosts:
            raise ValueError('Unrecognized installation receipt')
        for name in files:
            file = contained_path(root, directory + '/' + name)
            if digest(file.read_bytes()) != previous.get('files', {}).get(name):
                raise ValueError('Installed router was modified; preserve it before updating')
    elif target.exists() or launcher.exists() or target.parent.exists():
        raise ValueError('Existing router directory is not owned by ReelSyntax')
    target.parent.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        file = contained_path(root, directory + '/' + name, must_exist=False)
        file.write_bytes(data)
    atomic_json(receipt, {'owner': 'reelsyntax', 'schema_version': 1, 'host': host, 'files': {name: digest(data) for name, data in files.items()}})
    return {'installed': directory, 'host': host, 'native_skills_installed': 1, 'host_activation': 'unverified', 'python': Path(sys.executable).name}


def uninstall(project, host):
    root = Path(project).resolve(strict=True)
    if host not in HOST_PATHS:
        raise ValueError('Unsupported host')
    directory = f'{HOST_PATHS[host]}/reelsyntax-router'
    receipt = contained_path(root, directory + '/installation.json')
    record = read_json(receipt)
    compatible_hosts = {k for k, v in HOST_PATHS.items() if v == HOST_PATHS[host]}
    if record.get('owner') != 'reelsyntax' or record.get('host') not in compatible_hosts or set(record.get('files', {})) != {'SKILL.md', 'route.py'}:
        raise ValueError('Invalid installation receipt')
    files = [contained_path(root, directory + '/' + name) for name in record['files']]
    for file in files:
        if digest(file.read_bytes()) != record['files'][file.name]:
            raise ValueError('Installed router was modified; refusing to remove it')
    for file in files:
        file.unlink()
    receipt.unlink()
    if not any(receipt.parent.iterdir()):
        receipt.parent.rmdir()
    return {'removed': directory, 'host': host}
