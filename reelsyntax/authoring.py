import html
from importlib.metadata import entry_points
from pathlib import Path
import re
import tempfile
import textwrap
import time

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json
from .project import load, starter, validate


def create_project(destination, produce):
    from .schema import project_schema

    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new project directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        root = Path(tmp) / 'project'
        root.mkdir()
        plan = produce(root)
        validate(plan)
        plan['$schema'] = './reel.schema.json'
        atomic_json(root / 'reel.schema.json', project_schema())
        atomic_json(root / 'reel.json', plan)
        root.rename(destination)
    return {'project': str(destination), **validate(plan)}


def plugin_project(name, params, destination, authorized):
    if not authorized:
        raise ValueError(
            'Loading an installed recipe executes its Python code. Select --allow-plugin explicitly.'
        )
    matches = list(entry_points(group='reelsyntax.recipes', name=name))
    if len(matches) != 1:
        raise ValueError('Expected one installed reelsyntax.recipes entry point named ' + name)
    values = read_json(params, max_bytes=64000) if params else {}
    return create_project(destination, lambda root: matches[0].load()(values, root))


def markdown_cards(source):
    cards = []
    heading, body = '', []
    in_code = False
    for line in source.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith('#'):
            if heading or body:
                cards.append((heading, ' '.join(body)))
            heading, body = line.lstrip('# ').strip(), []
        elif line.strip():
            body.append(line.strip().removeprefix('- '))
    if heading or body:
        cards.append((heading, ' '.join(body)))
    return cards


def diagram(source):
    node = r'([a-zA-Z_][\w-]*)(?:\["?([^\]"\n]+)"?\])?'
    lines = [
        line.strip().rstrip(';')
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith('%%')
    ]
    if not lines or not re.fullmatch(r'(?:flowchart|graph) (?:LR|TD|TB)', lines[0]):
        raise ValueError('Expected a Mermaid LR/TD/TB flowchart')
    nodes, edges = {}, []
    for line in lines[1:]:
        previous = None
        for part in line.split('-->'):
            part = part.strip()
            match = re.fullmatch(node, part)
            if not match:
                raise ValueError('Unsupported Mermaid expression: ' + part)
            key, label = match.groups()
            nodes.setdefault(key, key)
            if label:
                nodes[key] = label
            if previous:
                edges.append((previous, key))
            previous = key
    if not 1 <= len(nodes) <= 12:
        raise ValueError('Expected 1–12 diagram nodes')
    return nodes, edges


def from_source(kind, source, destination):
    from PIL import Image, ImageDraw
    from .typography import resolve_font

    if source.stat().st_size > 1024 * 1024:
        raise ValueError('Input exceeds 1 MiB')
    content = source.read_text(encoding='utf-8')

    def produce(root):
        plan = starter()
        plan.update(id='diagram-study' if kind == 'mermaid' else 'reading-study', scenes=[])
        plan['output'].update(width=960, height=540, fps='24/1')
        plan['audio'] = {'enabled': False, 'gain_db': -14, 'cues': []}
        assets = root / 'assets'
        assets.mkdir()
        font = resolve_font(24)
        title = resolve_font(35, bold=True)
        if kind == 'mermaid':
            nodes, edges = diagram(content)
            positions = {key: (65 + (i % 3) * 305, 62 + (i // 3) * 117) for i, key in enumerate(nodes)}
            pages = list(nodes)
        else:
            pages = []
            for heading, text in markdown_cards(content):
                words = textwrap.wrap(text, width=54) or ['']
                for i in range(0, len(words), 6):
                    pages.append((heading, words[i : i + 6]))
        if not 1 <= len(pages) <= 200:
            raise ValueError('Expected 1–200 cards')
        for index, page in enumerate(pages):
            image = Image.new('RGB', (960, 540), '#f3f0e9')
            draw = ImageDraw.Draw(image)
            if kind == 'mermaid':
                for a, b in edges:
                    x, y = positions[a]
                    u, v = positions[b]
                    draw.line((x + 95, y + 28, u + 95, v + 28), fill='#627b80', width=3)
                for key, label in nodes.items():
                    x, y = positions[key]
                    draw.rounded_rectangle(
                        (x, y, x + 206, y + 60), radius=8, fill='#b4d5cf' if key == page else '#ddd8cf'
                    )
                    if draw.textlength(label, font=font) > 190:
                        raise ValueError('Diagram label exceeds card width: ' + label)
                    draw.text((x + 103, y + 30), label, font=font, fill='#1c2929', anchor='mm')
            else:
                heading, lines = page
                heading_lines = textwrap.wrap(heading, width=36)
                if len(heading_lines) > 2:
                    raise ValueError('Heading exceeds the two-line title area')
                for i, line in enumerate(heading_lines):
                    draw.text((64, 48 + 44 * i), line, font=title, fill='#233438')
                for i, line in enumerate(lines):
                    if draw.textlength(line, font=font) > 830:
                        raise ValueError('Text exceeds card width')
                    draw.text((65, 166 + 42 * i), line, font=font, fill='#263a3c')
            name = f'card-{index + 1:03d}'
            relative = f'assets/{name}.png'
            image.save(root / relative)
            scene = {
                'id': name,
                'duration_frames': 60,
                'recipe': 'layer-stack',
                'engine': 'pillow',
                'params': {'layers': [{'source': relative}]},
            }
            if index:
                scene['transition'] = {'type': 'cross_dissolve', 'duration_frames': 6}
            plan['scenes'].append(scene)
        plan['quality'] = {'exceptions': {'freeze': [[0, len(pages) * 60]]}}
        return plan

    return create_project(destination, produce)


def watch(project, once=False, interval=1.0):
    from .ingest import asset_hashes
    from .render import render

    if not 0.2 <= interval <= 60:
        raise ValueError('Polling interval must be between 0.2 and 60 seconds')
    last = None
    while True:
        try:
            root, plan, metadata = load(project)
            state = (metadata['plan_sha256'], asset_hashes(root, plan))
            if state != last:
                render(root, profile='draft')
                page = contained_path(root, 'review/preview.html', must_exist=False)
                title = html.escape(plan['id'])
                page.write_text(
                    f'<!doctype html><meta charset="utf-8"><title>{title}</title><h1>{title}</h1><video controls src="../output/draft.mp4"></video>',
                    encoding='utf-8',
                )
                last = state
            if once:
                return {'preview': str(page)}
        except (OSError, ValueError) as error:
            if once:
                raise
            import sys

            print(str(error), file=sys.stderr, flush=True)
        time.sleep(interval)


def compose(children, profile, destination):
    import shutil
    from .ingest import verify_sources
    from .skills import file_digest

    def produce(root):
        result = starter()
        result.update(id='composition', scenes=[], quality={})
        result['audio'] = {'enabled': False, 'gain_db': -6, 'tracks': [], 'cues': []}
        assets = root / 'assets'
        assets.mkdir()
        cursor = 0
        for i, child in enumerate(children):
            directory, plan, metadata = load(child)
            record = read_json(contained_path(directory, f'output/{profile}-manifest.json'))
            verify_sources(directory, record)
            if record['plan_sha256'] != metadata['plan_sha256']:
                raise ValueError('Render the current child composition before nesting it')
            if i and plan['output']['fps'] != result['output']['fps']:
                raise ValueError('Child compositions must use the same frame rate')
            name = f'section-{i + 1}'
            target = assets / (name + '.mp4')
            shutil.copyfile(contained_path(directory, record['artifact']), target)
            if file_digest(target) != record['artifact_sha256']:
                raise ValueError('Nested master differs from its approved render')
            result['output'] = dict(record['output_settings']) if not i else result['output']
            relative = target.relative_to(root).as_posix()
            duration = metadata['frames']
            result['scenes'].append(
                {
                    'id': name,
                    'recipe': 'footage',
                    'engine': 'ffmpeg',
                    'duration_frames': duration,
                    'params': {'source': relative},
                }
            )
            if plan['audio']['enabled']:
                result['audio']['enabled'] = True
                result['audio']['tracks'].append(
                    {
                        'id': name,
                        'kind': 'effects',
                        'source': relative,
                        'start_frame': cursor,
                        'duration_frames': duration,
                        'gain_db': 6,
                    }
                )
            for kind, ranges in plan.get('quality', {}).get('exceptions', {}).items():
                result['quality'].setdefault('exceptions', {}).setdefault(kind, []).extend(
                    [[a + cursor, b + cursor] for a, b in ranges]
                )
            cursor += duration
        return result

    return create_project(destination, produce)
