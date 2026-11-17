import json
import os
from pathlib import Path
import tempfile

from .gateway import discover_blender_binary
from .media import run


def export_blender_timeline(target, timeline, frame=0, timeout=180):
    binary = discover_blender_binary()
    if not binary['available']:
        raise ValueError('Native editorial export requires a separately installed Blender executable')
    with tempfile.TemporaryDirectory(prefix='vse-', dir=target.parent) as tmp:
        temp = Path(tmp)
        cfg = {
            'timeline': timeline, 'preview_frame': frame,
            'destination': str(temp / 'timeline.blend'), 'preview': str(temp / 'preview.png'), 'report': str(temp / 'report.json'),
        }
        config = temp / 'config.json'
        config.write_text(json.dumps(cfg), encoding='utf-8')
        run([binary['binary'], '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(Path(__file__).with_name('blender_editorial.py')), '--', str(config)], timeout=timeout)
        report = json.loads((temp / 'report.json').read_text(encoding='utf-8'))
        preview = target.with_suffix('.png')
        os.replace(temp / 'timeline.blend', target)
        os.replace(temp / 'preview.png', preview)
        report['preview'] = str(preview)
    return report
