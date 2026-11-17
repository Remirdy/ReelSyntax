#!/usr/bin/env python3
from collections import Counter
import csv
import os
from pathlib import Path
import tempfile

if __package__:
    from .registry import ROOT, contained_path, rebuild as build_registry
else:
    from registry import ROOT, contained_path, rebuild as build_registry


CATEGORY_NAMES = {
    "art": "Art direction, composition and design",
    "audio": "Sound design, recording and mixing",
    "camera": "Camera and cinematography",
    "capture": "Browser, software capture and product demonstrations",
    "character": "Character production and animation",
    "data": "Educational, scientific and data visualizations",
    "delivery": "Export, interoperability and deliverables",
    "direction": "Creative direction and production planning",
    "editing": "Editing and temporal assembly",
    "engines": "Engine adapters and authoring",
    "formats": "Genre workflows and creative formats",
    "graphics": "2D graphics and vector animation",
    "ingest": "Asset ingestion, research, rights and source management",
    "lighting": "Lighting, staging and environment",
    "modeling": "3D modeling, materials and assets",
    "motion": "Motion principles and temporal design",
    "music": "Music and procedural audio composition",
    "qa": "Quality, compliance and restoration",
    "render": "Render orchestration and performance",
    "skills": "Skill engineering, agent interoperability and development",
    "story": "Narrative, writing and storyboards",
    "transitions": "Transition and shot recipes",
    "typography": "Typography, captions and visual text",
    "vfx": "Visual effects and compositing",
    "workflow": "Project intelligence and batch workflows"
}


def markdown_catalog(rows):
    categories = Counter(row['category'] for row in rows)
    statuses = Counter(row['status'] for row in rows)
    lines = ['# ReelSyntax skill catalog', '', f'{len(rows)} skills across {len(categories)} categories. '
             + ', '.join(f'{count} {status}' for status, count in sorted(statuses.items())) + '.', '',
             '| Category | Skills |', '| --- | ---: |']
    for category, count in sorted(categories.items()):
        lines.append(f'| {category} | {count} |')
    for category, count in sorted(categories.items()):
        title = CATEGORY_NAMES.get(category, category.capitalize())
        lines.extend(['', f'## {title} (`{category}`, {count})', '',
                      '| Skill | Status | Search phrases | Scope |', '| --- | --- | --- | --- |'])
        for row in rows:
            if row['category'] == category:
                description = row['description'].replace('|', '&#124;')
                aliases = ', '.join(row['aliases']).replace('|', '&#124;')
                lines.append(f"| [{row['id']}]({row['path']}) | {row['status']} | {aliases} | {description} |")
    return '\n'.join(lines) + '\n'


def rebuild(quiet=False, root=ROOT):
    document = build_registry(root)
    rows = document['skills']
    target = contained_path(root, 'registry/catalog.csv', must_exist=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8-sig', dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream)
            writer.writerow(['id', 'category', 'stage', 'aliases', 'description', 'requires', 'status', 'path'])
            for row in rows:
                writer.writerow([row['id'], row['category'], row['stage'], ', '.join(row['aliases']), row['description'], ', '.join(row['requires']), row['status'], row['path']])
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    catalog = contained_path(root, 'CATALOG.md', must_exist=False)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=catalog.parent, delete=False) as stream:
        stream.write(markdown_catalog(rows))
    os.chmod(stream.name, 0o644)
    os.replace(stream.name, catalog)
    readme = contained_path(root, 'README.md', must_exist=False)
    if readme.exists():
        prefix, marker, _ = readme.read_text(encoding='utf-8').partition('\n## Category distribution\n')
        if marker:
            counts = sorted(Counter(row['category'] for row in rows).items())
            chart = '\n'.join(f'{name:12} {count:2}  ' + '▇' * count for name, count in counts)
            readme.write_text(prefix + marker + '\n```text\n' + chart + '\n```\n', encoding='utf-8')
    if not quiet:
        print(f"Indexed {len(rows)} unique skills; digest {document['digest']}")
    return document


if __name__ == '__main__':
    rebuild()
