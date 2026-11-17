#!/usr/bin/env python3
import csv
import os
from pathlib import Path
import tempfile

if __package__:
    from .registry import ROOT, contained_path, rebuild as build_registry
else:
    from registry import ROOT, contained_path, rebuild as build_registry


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
    if not quiet:
        print(f"Indexed {len(rows)} unique skills; digest {document['digest']}")
    return document


if __name__ == '__main__':
    rebuild()
