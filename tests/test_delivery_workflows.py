import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ReelSyntax_Skills.tools.registry import ROOT, atomic_json, load_index
from ReelSyntax_Skills.tools.reindex import markdown_catalog
from reelsyntax.authoring import diagram
from reelsyntax.captions import caption_events
from reelsyntax.cli import execute, parser
from reelsyntax.interchange import export_project
from reelsyntax.project import initialize, load, starter, validate
from reelsyntax.schema import project_schema
from reelsyntax.shapes import SHAPES, validate_shapes
from reelsyntax.variants import aspect_size


def command(*args):
    return execute(parser().parse_args(list(map(str, args))))


class DeliveryTests(unittest.TestCase):
    def test_published_catalog_and_schema(self):
        rows = load_index()['skills']
        self.assertEqual((ROOT / 'CATALOG.md').read_text(encoding='utf-8'), markdown_catalog(rows))
        self.assertEqual(json.loads((ROOT.parent / 'docs/reel.schema.json').read_text()), project_schema())
        summary = f"{len(rows)} skills, {sum(r['status'] == 'validated' for r in rows)} validated"
        self.assertIn(summary, (ROOT.parent / 'README.md').read_text(encoding='utf-8'))

    def test_premiere_sequence_rates_tracks_and_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize(root)
            plan = load(root)[1]
            plan['output']['fps'] = '30000/1001'
            atomic_json(root / 'reel.json', plan)
            path = export_project(root, 'premiere', 'draft')['artifact']
            xml = ET.parse(root / path)
            self.assertEqual(xml.findtext('.//sequence/rate/ntsc'), 'TRUE')
            self.assertEqual(xml.findtext('.//sequence/rate/timebase'), '30')
            self.assertEqual(
                [c.findtext('start') for c in xml.findall('.//sequence/media/video/track/clipitem')],
                ['0', '90', '180'],
            )
            self.assertEqual(len(xml.findall('.//sequence/media/audio/track')), 2)
            self.assertEqual(xml.findtext('.//pathurl'), (root / 'output/draft.mp4').resolve().as_uri())

    def test_ratio_diagram_and_word_ranges(self):
        self.assertEqual(aspect_size(960, 540, '9:16'), (540, 960))
        for bad in ('0:0', 'nan', '4:-1'):
            with self.assertRaises(ValueError):
                aspect_size(960, 540, bad)
        nodes, edges = diagram('flowchart LR\nA["Source"] --> B --> C["Output"]')
        self.assertEqual(nodes['C'], 'Output')
        self.assertEqual(edges, [('A', 'B'), ('B', 'C')])
        with self.assertRaises(ValueError):
            list(caption_events(starter(), [{'start': 3, 'end': 1, 'text': 'one'}]))

    def test_shape_schema_rejects_unbounded_or_unknown_fields(self):
        for shape in (
            {'type': 'grid', 'x': 0, 'y': 0, 'w': 1, 'h': 1, 'rows': 2, 'columns': 100000},
            {'type': 'circle', 'cx': 0, 'cy': 0, 'r': -1},
            {'type': 'rect', 'side': 0.4},
        ):
            with self.assertRaises(ValueError):
                validate_shapes([shape])


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
class DrawingTests(unittest.TestCase):
    def test_all_primitives_render_at_two_sizes(self):
        from reelsyntax.drawing import draw

        samples = dict(
            cx=0.5,
            cy=0.5,
            r=0.25,
            x=0.2,
            y=0.2,
            w=0.6,
            h=0.6,
            radius=0.05,
            rows=5,
            columns=4,
            start_deg=0,
            sweep_deg=270,
            sides=5,
            points=[[0.1, 0.1], [0.3, 0.8], [0.7, 0.8], [0.9, 0.1]],
        )
        for kind, spec in SHAPES.items():
            shape = {'type': kind, **{key: samples[key] for key in spec}}
            if kind == 'arrow':
                shape['points'] = shape['points'][:2]
            shapes = [shape]
            if kind == 'mask':
                shapes.insert(0, dict(type='rect', x=0.1, y=0.1, w=0.8, h=0.8))
            plan = starter()
            scene = plan['scenes'][0]
            scene.update(recipe='shape-field', params={'shapes': shapes, 'background': '#ffffff'})
            validate(plan)
            for w, h in ((128, 72), (256, 144)):
                with self.subTest(kind=kind, w=w):
                    im, _ = draw(scene, 0, {'width': w, 'height': h}, 42)
                    self.assertGreater(len(im.getcolors(w * h)), 1)
                    self.assertEqual(im.tobytes(), draw(scene, 0, {'width': w, 'height': h}, 42)[0].tobytes())
        scene.update(
            params={'shapes': [dict(type='circle', cx=0.5, cy=0.5, r=0.2)]}, locked_regions=[[45, 20, 40, 30]]
        )
        with self.assertRaisesRegex(ValueError, 'locked region'):
            draw(scene, 0, {'width': 128, 'height': 72}, 42)

    def test_transition_endpoints_and_midpoints(self):
        from PIL import Image
        from reelsyntax.project import TRANSITIONS
        from reelsyntax.transitions import blend

        a, b = (Image.new('RGB', (24, 16), color) for color in ('red', 'blue'))
        for kind in TRANSITIONS - {'cut'}:
            with self.subTest(kind=kind):
                self.assertEqual(blend(a, b, kind, 0).tobytes(), a.tobytes())
                self.assertEqual(blend(a, b, kind, 1).tobytes(), b.tobytes())
                self.assertNotIn(blend(a, b, kind, 0.5).tobytes(), [a.tobytes(), b.tobytes()])


@unittest.skipUnless(os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1', 'Enable multimedia integration')
class MediaDeliveryTests(unittest.TestCase):
    def test_render_variants_export_and_quality(self):
        from reelsyntax.media import probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize(root)
            plan = load(root)[1]
            plan['output'].update(width=320, height=180, fps='24/1')
            plan['scenes'] = [
                {
                    'id': 'test',
                    'recipe': 'shape-field',
                    'engine': 'pillow',
                    'duration_frames': 8,
                    'params': {'shapes': [dict(type='star', cx=0.5, cy=0.5, r=0.25, sides=5)]},
                }
            ]
            plan.update(audio={'enabled': False, 'gain_db': -14, 'cues': []}, quality={})
            atomic_json(root / 'reel.json', plan)
            atomic_json(root / 'strings.de.json', {})
            atomic_json(root / 'jobs.json', [{'locale': 'de', 'aspect': '1:1', 'target': 'linkedin'}])
            job = command('render', root, '--queue', 'jobs.json')['deliveries'][0]
            variant = root / job['project']
            stream = probe(variant / job['artifact'], True)['streams'][0]
            self.assertEqual((stream['width'], stream['height'], stream['nb_read_frames']), (160, 160, '8'))
            self.assertEqual(stream['tags']['language'], 'deu')
            for fmt in ('poster', 'gif', 'webm', 'premiere', 'fcpxml'):
                item = command('export', variant, '--profile', 'draft', '--format', fmt, '--frame', '4')
                self.assertGreater((variant / item['artifact']).stat().st_size, 0)
            qc = command('qc', variant, '--html', '--loop')
            self.assertEqual(qc['technical_status'], 'pass')
            self.assertIn('data:image/png;base64,', (variant / qc['html']).read_text())
            self.assertIn('loop_picture', [c['id'] for c in qc['checks']])
