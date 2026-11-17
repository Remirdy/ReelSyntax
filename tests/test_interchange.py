import json
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.interchange import export_project
from reelsyntax.project import initialize, load


class InterchangeTests(unittest.TestCase):
    def test_draft_format_matches_renderer_and_uses_absolute_media_uri(self):
        with tempfile.TemporaryDirectory(prefix='film export ') as tmp:
            initialize(tmp)
            result = export_project(tmp, 'fcpxml', profile='draft')
            document = ET.parse(Path(tmp, result['artifact']))
            fmt = document.find('resources/format')
            self.assertEqual((fmt.get('width'), fmt.get('height')), ('480', '270'))
            uri = document.find('resources/asset/media-rep').get('src')
            self.assertEqual(uri, Path(tmp, 'output/draft.mp4').resolve().as_uri())

    def test_flattened_otio_keeps_baked_transitions_as_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['scenes'][1]['transition'] = {'type': 'cross_dissolve', 'duration_frames': 11}
            atomic_json(root / 'reel.json', plan)
            result = export_project(tmp, 'otio')
            document = json.loads(Path(tmp, result['artifact']).read_text())
            clips = document['tracks']['children'][0]['children']
            self.assertEqual([c['OTIO_SCHEMA'] for c in clips], ['Clip.2'] * 3)
            self.assertEqual(clips[1]['metadata']['baked_transition'], plan['scenes'][1]['transition'])
            self.assertEqual(sum(c['source_range']['duration']['value'] for c in clips), 240)

    def test_otio_audio_uses_embedded_mix_when_sidecar_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            result = export_project(tmp, 'otio')
            document = json.loads(Path(tmp, result['artifact']).read_text())
            tracks = document['tracks']['children']
            picture = tracks[0]['children'][0]['media_reference']['target_url']
            audio = tracks[1]['children'][0]['media_reference']['target_url']
            self.assertEqual(audio, picture)
            Path(tmp, 'output/production-mix.wav').write_bytes(b'local-sidecar')
            result = export_project(tmp, 'otio')
            document = json.loads(Path(tmp, result['artifact']).read_text())
            audio = document['tracks']['children'][1]['children'][0]['media_reference']['target_url']
            self.assertTrue(audio.endswith('/production-mix.wav'))

    def test_fcpxml_markers_use_source_coordinates_at_fractional_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output']['fps'] = '30000/1001'
            atomic_json(root / 'reel.json', plan)
            result = export_project(tmp, 'fcpxml')
            document = ET.parse(root / result['artifact'])
            clips = document.findall('.//spine/asset-clip')
            self.assertEqual(clips[1].get('start'), '90090/30000s')
            self.assertEqual(clips[1].find('marker').get('start'), clips[1].get('start'))
            self.assertEqual(clips[1].find('marker').get('duration'), '1001/30000s')

    def test_otio_markers_stay_inside_trimmed_source_at_fractional_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output']['fps'] = '30000/1001'
            atomic_json(root / 'reel.json', plan)
            result = export_project(tmp, 'otio')
            document = json.loads((root / result['artifact']).read_text())
            clips = document['tracks']['children'][0]['children']
            for clip in clips:
                source = clip['source_range']
                marked = clip['markers'][0]['marked_range']
                self.assertEqual(marked['start_time']['value'], source['start_time']['value'])
                self.assertLessEqual(marked['duration']['value'], source['duration']['value'])
                self.assertEqual(source['start_time']['rate'], float(Fraction(30000, 1001)))

    def test_svg_rejects_frames_outside_timeline_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            target = Path(tmp, 'output/story.svg')
            for frame in (-1, 240, 1000, 1.5, True):
                with self.subTest(frame=frame), self.assertRaisesRegex(ValueError, 'frame'):
                    export_project(tmp, 'svg', output_path=target, frame=frame)
                self.assertFalse(target.exists())
            result = export_project(tmp, 'svg', output_path=target, frame=239)
            self.assertGreater(result['bytes'], 0)

    def test_export_rejects_unknown_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            with self.assertRaisesRegex(ValueError, 'profile'):
                export_project(tmp, 'otio', profile='other')

    def test_editorial_export_rejects_stale_render_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, metadata = load(tmp)
            (root / 'output').mkdir()
            atomic_json(root / 'output/draft-manifest.json', {
                'plan_sha256': metadata['plan_sha256'], 'profile': 'draft',
                'frames': metadata['frames'],
                'output_settings': {'width': 480, 'height': 270, 'fps': '30/1'},
            })
            export_project(tmp, 'fcpxml', profile='draft')
            plan['scenes'][0]['params']['heading'] = 'REVISED'
            atomic_json(root / 'reel.json', plan)
            for fmt in ('fcpxml', 'otio'):
                with self.subTest(fmt=fmt), self.assertRaisesRegex(ValueError, 'render.*current plan'):
                    export_project(tmp, fmt, profile='draft')


if __name__ == '__main__':
    unittest.main()
