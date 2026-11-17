import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def build(wheel, destination):
    manifest = {
        'manifest_version': '0.3',
        'name': 'reelsyntax',
        'display_name': 'ReelSyntax',
        'version': '0.1.0',
        'description': 'Local skill routing and project tools for video production.',
        'author': {'name': 'Remirdy', 'url': 'https://github.com/Remirdy'},
        'license': 'MIT',
        'homepage': 'https://github.com/Remirdy/ReelSyntax',
        'user_config': {
            'workspace': {
                'type': 'directory',
                'title': 'Project workspace',
                'description': 'Select the directory containing your ReelSyntax projects.',
                'required': True,
            }
        },
        'server': {
            'type': 'python',
            'entry_point': 'server/main.py',
            'mcp_config': {
                'command': 'python3',
                'args': ['${__dirname}/server/main.py', 'mcp', '--workspace', '${user_config.workspace}'],
                'platform_overrides': {'win32': {'command': 'python'}},
            },
        },
        'compatibility': {'platforms': ['darwin', 'linux', 'win32'], 'runtimes': {'python': '>=3.11'}},
    }
    with ZipFile(wheel) as package, ZipFile(destination, 'w', ZIP_DEFLATED) as bundle:
        for path in package.namelist():
            if path.startswith(('reelsyntax/', 'ReelSyntax_Skills/')):
                bundle.writestr('server/' + path, package.read(path))
        bundle.writestr('manifest.json', json.dumps(manifest, indent=2))
        bundle.writestr('server/main.py', 'from reelsyntax.cli import main\n\nraise SystemExit(main())\n')
        bundle.write(ROOT / 'LICENSE', 'LICENSE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('wheel', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.wheel, args.output)
