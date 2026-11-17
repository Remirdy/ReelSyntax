from fractions import Fraction
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.camera import Camera3D
from reelsyntax.diff import compare_profiles
from reelsyntax.gateway import build_handoff_package, discover_blender_binary
from reelsyntax.interchange import export_project
from reelsyntax.motion import spring_damper, verlet_ribbon
from reelsyntax.palette import agx_tonemap_linear, contrast_ratio, hex_to_linear, hex_to_rgb, mix_oklab
from reelsyntax.project import initialize, load, validate
from reelsyntax.quality import check as qc_check
from reelsyntax.render import lock, render
from reelsyntax.sound import synthesize
from reelsyntax.typography import check_glyph_coverage, resolve_font

MEDIA = os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1'


class ProductionLibrariesUnitTests(unittest.TestCase):
    def test_oklab_agx_and_wcag_contrast(self):
        self.assertGreater(contrast_ratio(hex_to_rgb('#f2ede4'), hex_to_rgb('#14171c')), 12.0)
        mid = mix_oklab('#bb5537', '#355f65', 0.5)
        self.assertTrue(all(0 <= c <= 255 for c in mid))
        bright = agx_tonemap_linear(tuple(c * 8.0 for c in hex_to_linear('#ff5522')))
        self.assertTrue(all(0.0 <= c <= 1.0 for c in bright))
        self.assertGreater(min(bright), 0.15)

    def test_spring_verlet_and_camera_rig_determinism(self):
        self.assertAlmostEqual(spring_damper(0.0, zeta=1.0, omega=5.0), 0.0, places=6)
        self.assertGreater(spring_damper(2.0, zeta=1.0, omega=5.0), 0.99)
        anchor = lambda t: (100.0 + 20.0 * (1.0 if t > 0.1 else 0.0), 40.0)
        pts_a = verlet_ribbon(anchor, segments=6, segment_length=15.0, frame=24, fps=24.0)
        pts_b = verlet_ribbon(anchor, segments=6, segment_length=15.0, frame=24, fps=24.0)
        self.assertEqual(pts_a, pts_b)

        scene = {'id': 'shot', 'duration_frames': 48, 'camera': {'preset': 'dolly_zoom', 'focal_mm': 50.0, 'position': [0.0, -5.0, 0.0], 'target': [0.0, 0.0, 0.0]}}
        c0 = Camera3D.from_scene(scene, 0, 24.0, 42, camera_locked=False)
        c1 = Camera3D.from_scene(scene, 47, 24.0, 42, camera_locked=False)
        p0 = c0.project((0.5, 0.0, 0.0), 960, 540)
        p1 = c1.project((0.5, 0.0, 0.0), 960, 540)
        self.assertAlmostEqual(p0[0], p1[0], delta=1.5)
        with self.assertRaisesRegex(ValueError, 'camera_locked'):
            Camera3D.from_scene(scene, 10, 24.0, 42, camera_locked=True)

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Optional Pillow dependency is required for glyph rasterization')
    def test_turkish_glyph_coverage(self):
        font = resolve_font(24, bold=False)
        cov = check_glyph_coverage('ÇĞİÖŞÜçğıöşü FORM 01', font)
        self.assertTrue(cov['ok'], cov)

    def test_multi_stem_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = {
                'schema_version': 1,
                'id': 'audio-stems',
                'seed': 7,
                'output': {'width': 320, 'height': 180, 'fps': '24/1'},
                'scenes': [{'id': 'a', 'duration_frames': 24, 'recipe': 'prism-monolith', 'engine': 'pillow', 'params': {'heading': 'SES'}}],
                'audio': {
                    'enabled': True,
                    'gain_db': -14,
                    'export_stems': True,
                    'cues': [
                        {'frame': 0, 'frequency': 90, 'duration_frames': 12, 'instrument': 'sub_impact', 'pan': -0.3},
                        {'frame': 12, 'frequency': 330, 'duration_frames': 10, 'instrument': 'harmonic_pluck', 'pan': 0.4},
                    ],
                },
            }
            validate(plan)
            stem_dir = Path(tmp, 'stems')
            info = synthesize(Path(tmp, 'mix.wav'), plan, stem_dir=stem_dir)
            self.assertEqual(sorted(info['stems']), ['stem-harmonic_pluck.wav', 'stem-sub_impact.wav'])
            self.assertTrue((stem_dir / 'stem-sub_impact.wav').is_file())

    def test_otio_fcpxml_vtt_srt_and_svg_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            otio_res = export_project(tmp, 'otio')
            otio_doc = json.loads((Path(tmp) / otio_res['artifact']).read_text())
            self.assertEqual(otio_doc['OTIO_SCHEMA'], 'Timeline.1')
            self.assertEqual(len(otio_doc['tracks']['children'][0]['children']), 3)

            fcp_res = export_project(tmp, 'fcpxml')
            xml_text = (Path(tmp) / fcp_res['artifact']).read_text()
            root = ET.fromstring(xml_text.replace('<!DOCTYPE fcpxml>\n', ''))
            self.assertEqual(root.attrib['version'], '1.10')

            vtt_res = export_project(tmp, 'vtt')
            self.assertTrue((Path(tmp) / vtt_res['artifact']).read_text().startswith('WEBVTT'))

            srt_res = export_project(tmp, 'srt')
            self.assertIn('00:00:00,000 --> 00:00:03,000', (Path(tmp) / srt_res['artifact']).read_text())

            svg_res = export_project(tmp, 'svg', frame=15)
            self.assertIn('<svg', (Path(tmp) / svg_res['artifact']).read_text())

    def test_aperture_svg_export_and_multi_camera_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            aperture_plan = {
                'schema_version': 1,
                'id': 'aperture-test',
                'seed': 108,
                'output': {'width': 640, 'height': 360, 'fps': '24/1'},
                'constraints': {'offline': True, 'no_paid_services': True, 'no_text': True},
                'scenes': [
                    {'id': 'macro', 'duration_frames': 12, 'recipe': 'aperture', 'engine': 'blender', 'camera': {'preset': 'dolly_in', 'focal_mm': 85}, 'params': {'shot': 'macro'}},
                    {'id': 'hero', 'duration_frames': 12, 'recipe': 'aperture', 'engine': 'blender', 'camera': {'preset': 'dolly_in', 'focal_mm': 57}, 'params': {'shot': 'hero'}},
                ],
                'audio': {'enabled': False, 'gain_db': -14, 'cues': []},
            }
            atomic_json(Path(tmp, 'reel.json'), aperture_plan)
            svg_res = export_project(tmp, 'svg', frame=6)
            svg_text = (Path(tmp) / svg_res['artifact']).read_text()
            self.assertIn('<polyline', svg_text)
            handoff = build_handoff_package(tmp, verify_jsx=False)
            manifest = json.loads(Path(handoff['manifest']).read_text())
            self.assertEqual(len(manifest['scene_cameras']), 2)
            self.assertNotEqual(manifest['scene_cameras'][0]['camera_3d']['zoom_pixels'], manifest['scene_cameras'][1]['camera_3d']['zoom_pixels'])
            jsx_text = Path(handoff['jsx_script']).read_text()
            self.assertIn('KeyframeInterpolationType.HOLD', jsx_text)


@unittest.skipUnless(MEDIA, 'Set REELSYNTAX_MEDIA_TESTS=1 for full render, Hero lookdev, ROI lock, diff, and Blender CLI tests')
class ProductionMediaPipelineTests(unittest.TestCase):
    def test_hero_render_transitions_roi_locks_diff_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = {
                'schema_version': 1,
                'id': 'hero-pipeline',
                'seed': 19,
                'output': {'width': 320, 'height': 180, 'fps': '24/1'},
                'constraints': {'offline': True, 'no_paid_services': True, 'camera_locked': False},
                'camera': {'preset': 'dolly_in', 'focal_mm': 52.0},
                'scenes': [
                    {
                        'id': 'monolith',
                        'duration_frames': 16,
                        'recipe': 'prism-monolith',
                        'engine': 'pillow',
                        'camera': {'preset': 'dolly_in', 'focal_mm': 52.0},
                        'params': {'kicker': '01 / OPTICS', 'heading': 'MONOLITH', 'subheading': 'Türkçe ışık ve derinlik.', 'background': '#14171c', 'foreground': '#ede8de', 'accent': '#c8643b'},
                    },
                    {
                        'id': 'hud',
                        'duration_frames': 16,
                        'recipe': 'hud-lock',
                        'engine': 'pillow',
                        'transition': {'type': 'cross_dissolve', 'duration_frames': 4},
                        'locked_regions': [[0, 152, 320, 28]],
                        'params': {'heading': 'HUD', 'subheading': 'Protected lower region.', 'background': '#eee9df', 'foreground': '#222629', 'accent': '#355f65'},
                    },
                ],
                'audio': {
                    'enabled': True,
                    'gain_db': -14,
                    'export_stems': True,
                    'cues': [
                        {'frame': 0, 'frequency': 110, 'duration_frames': 8, 'instrument': 'sub_impact'},
                        {'frame': 16, 'frequency': 330, 'duration_frames': 8, 'instrument': 'harmonic_pluck'},
                    ],
                },
                'quality': {'exceptions': {'silence': [[8, 16], [24, 32]]}},
            }
            atomic_json(Path(tmp, 'reel.json'), plan)
            draft_state = render(tmp, 'draft')
            hero_state = render(tmp, 'hero')
            self.assertEqual(hero_state['frames'], 32)
            self.assertTrue((Path(tmp) / hero_state['hero_evidence']['lookdev_ab']).is_file())
            self.assertTrue((Path(tmp) / hero_state['hero_evidence']['motion_extrema']).is_file())

            lock(tmp, ['hud'], roi_profile='hero')
            qc = qc_check(tmp, 'hero')
            self.assertEqual(qc['technical_status'], 'pass', qc['checks'])
            self.assertEqual(next(c for c in qc['checks'] if c['id'] == 'roi_locks')['status'], 'pass')

            # Modify upper accent in hud while keeping lower bar foreground/background intact -> ROI lock stays green!
            plan['scenes'][1]['params']['accent'] = '#bb5537'
            atomic_json(Path(tmp, 'reel.json'), plan)
            render(tmp, 'hero')
            qc_after = qc_check(tmp, 'hero')
            self.assertEqual(next(c for c in qc_after['checks'] if c['id'] == 'roi_locks')['status'], 'pass')

            diff_rep = compare_profiles(tmp, 'draft', 'hero')
            self.assertTrue((Path(tmp) / diff_rep['diff_contact_sheet']).is_file())

            handoff_rep = build_handoff_package(tmp, verify_jsx=False)
            self.assertTrue(Path(handoff_rep['manifest']).is_file())

    def test_blender_engine_fallback_and_live_headless_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = {
                'schema_version': 1,
                'id': 'blender-shot',
                'seed': 11,
                'output': {'width': 320, 'height': 180, 'fps': '24/1'},
                'scenes': [{
                    'id': 'stage',
                    'duration_frames': 4,
                    'recipe': 'prism-monolith',
                    'engine': 'blender',
                    'camera': {'preset': 'orbit', 'focal_mm': 50.0},
                    'params': {'heading': '3D', 'background': '#16191e', 'foreground': '#ece8df', 'accent': '#c8643b'},
                }],
                'audio': {'enabled': False, 'gain_db': -14, 'cues': []},
            }
            atomic_json(Path(tmp, 'reel.json'), plan)

            # First verify graceful fallback when Blender is forced unavailable.
            old = os.environ.get('REELSYNTAX_BLENDER')
            os.environ['REELSYNTAX_BLENDER'] = '/nonexistent/blender'
            try:
                # discover_blender_binary checks PATH/Applications too, so test explicit fallback helper when binary is absent via mock.
                from unittest.mock import patch
                with patch('reelsyntax.gateway.discover_blender_binary', return_value={'available': False, 'binary': None, 'version': None}):
                    with self.assertRaisesRegex(ValueError, '--fallback'):
                        render(tmp, 'draft')
                    fb_state = render(tmp, 'draft', fallback_engine='pillow')
                    self.assertEqual(fb_state['scenes'][0]['engine_used'], 'pillow')
                    self.assertEqual(len(fb_state['fallbacks_used']), 1)
            finally:
                if old is None:
                    os.environ.pop('REELSYNTAX_BLENDER', None)
                else:
                    os.environ['REELSYNTAX_BLENDER'] = old

            # Now run real headless Blender 5.x render if installed on this machine!
            bl = discover_blender_binary()
            if bl['available']:
                live_state = render(tmp, 'production', timeout=180)
                self.assertEqual(live_state['scenes'][0]['engine_used'], 'blender')
                self.assertIn('Blender', live_state['environment']['blender'])


if __name__ == '__main__':
    unittest.main()
