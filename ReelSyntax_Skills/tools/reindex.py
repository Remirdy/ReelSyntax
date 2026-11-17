#!/usr/bin/env python3
import csv
from pathlib import Path

if __package__:
    from .registry import rebuild as build_registry
else:
    from registry import rebuild as build_registry


def rebuild():
    document = build_registry()
    rows = document['skills']
    target = Path(__file__).resolve().parents[1] / 'registry/catalog.csv'
    with target.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(['id', 'category', 'stage', 'aliases', 'description', 'requires', 'status', 'path'])
        for row in rows:
            writer.writerow([row['id'], row['category'], row['stage'], ', '.join(row['aliases']), row['description'], ', '.join(row['requires']), row['status'], row['path']])
    print(f"Indexed {len(rows)} unique skills; digest {document['digest']}")
    return document


if __name__ == '__main__':
    rebuild()
