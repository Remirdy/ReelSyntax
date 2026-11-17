import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.browser import BrowserRenderer
from reelsyntax.media import probe
from reelsyntax.project import starter, validate
from reelsyntax.render import render


class WebglTests(unittest.TestCase):
    def test_shader_contract_rejects_substitution_and_ignored_controls(self):
        plan = starter()
        plan['scenes'] = [{'id': 'shader', 'recipe': 'shader-sculpture', 'engine': 'browser', 'duration_frames': 24, 'params': {}}]
        plan['audio'].update(enabled=False, cues=[])
        plan['quality']['exceptions'] = {}
        validate(plan)
        for mutation in [lambda s: s.update(engine='pillow'), lambda s: s['params'].update(heading='ignored'), lambda s: s.update(camera={'focal_mm': 50})]:
            candidate = copy.deepcopy(plan)
            mutation(candidate['scenes'][0])
            with self.assertRaises(ValueError):
                validate(candidate)

    @unittest.skipUnless(os.environ.get('REELSYNTAX_BROWSER_TESTS') == '1' and os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1' and importlib.util.find_spec('PIL'), 'Enable browser/media tests with optional Chromium tools')
    def test_actual_shader_seek_canvas_switch_and_encoded_output(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = starter()
            plan['output'] = {'width': 320, 'height': 180, 'fps': '24/1'}
            shader = {'id': 'shader', 'recipe': 'shader-sculpture', 'engine': 'browser', 'duration_frames': 12, 'params': {}}
            plain = dict(plan['scenes'][0], params={})
            with BrowserRenderer(timeout=15) as browser:
                info = browser.require_webgl()
                self.assertIn('WebGL 2.0', info['version'])
                self.assertTrue(info['renderer'])
                browser.draw(plain, 0, plan['output'], 108, root / 'plain.png')
                for frame, name in [(0, 'first'), (6, 'middle'), (0, 'again')]:
                    browser.draw(shader, frame, plan['output'], 108, root / f'{name}.png')
                browser.draw(plain, 0, plan['output'], 108, root / 'plain-again.png')
            self.assertEqual((root / 'first.png').read_bytes(), (root / 'again.png').read_bytes())
            self.assertNotEqual((root / 'first.png').read_bytes(), (root / 'middle.png').read_bytes())
            self.assertEqual((root / 'plain.png').read_bytes(), (root / 'plain-again.png').read_bytes())
            with Image.open(root / 'first.png') as image:
                self.assertEqual(image.size, (320, 180))
                extrema = image.convert('L').getextrema()
                self.assertGreater(extrema[1] - extrema[0], 40)
            plan['scenes'] = [shader]
            plan['audio'].update(enabled=False, cues=[])
            plan['quality']['exceptions'] = {}
            atomic_json(root / 'reel.json', plan)
            result = render(root, 'production')
            video = next(s for s in probe(root / result['artifact'], True)['streams'] if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_read_frames']), 12)
            self.assertEqual(result['environment']['webgl']['renderer'], info['renderer'])
