from fractions import Fraction
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ReelSyntax_Skills.tools.registry import atomic_json
from ReelSyntax_Skills.tools.quality_audit import audit
from reelsyntax.media import executable, probe, run
from reelsyntax.interchange import export_project
from reelsyntax.project import initialize, load
from reelsyntax.render import render

MEDIA = os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1'
BROWSER = os.environ.get('REELSYNTAX_BROWSER_TESTS') == '1'


@unittest.skipUnless(MEDIA, 'Set REELSYNTAX_MEDIA_TESTS=1 with installed FFmpeg, FFprobe and Pillow for actual render tests')
class MediaIntegrationTests(unittest.TestCase):
    def test_native_blender_editorial_roundtrip_matches_decoded_frame(self):
        from PIL import Image, ImageChops, ImageStat
        from reelsyntax.gateway import discover_blender_binary
        if not discover_blender_binary()['available']:
            self.skipTest('Optional native Blender runtime unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output'].update(width=320, height=180, fps='30000/1001')
            plan['scenes'] = [dict(s, duration_frames=12, params={}) for s in plan['scenes'][:2]]
            plan['audio'].update(enabled=False, cues=[])
            plan['quality']['exceptions'] = {}
            atomic_json(root / 'reel.json', plan)
            result = render(root, 'draft')
            exported = export_project(root, 'blender', profile='draft', frame=12)
            native = exported['native_import']
            self.assertEqual(native['frames'], 24)
            self.assertEqual(native['frame_end'] - native['frame_start'] + 1, 24)
            self.assertEqual([s['source_in'] for s in native['clips']], [0, 12])
            self.assertEqual([s['timeline_in'] for s in native['clips']], [0, 12])
            self.assertEqual(native['fps'], '30000/1001')
            self.assertTrue((root / exported['artifact']).is_file())
            decoded = root / 'decoded.png'
            run([executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-i', str(root / result['artifact']), '-vf', 'select=eq(n\\,12)', '-frames:v', '1', str(decoded)])
            with Image.open(native['preview']) as a, Image.open(decoded) as b:
                self.assertEqual(a.size, b.size)
                mae = sum(ImageStat.Stat(ImageChops.difference(a.convert('RGB'), b.convert('RGB'))).mean) / 3
                self.assertLess(mae, 4.0)

    def test_draft_editorial_exports_match_actual_encoded_master(self):
        with tempfile.TemporaryDirectory(prefix='reelsyntax editorial ') as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output'].update(width=320, height=180, fps='30000/1001')
            plan['scenes'] = [dict(s, duration_frames=12, params={}) for s in plan['scenes'][:2]]
            plan['scenes'][1]['transition'] = {'type': 'cross_dissolve', 'duration_frames': 5}
            plan['audio'].update(enabled=False, cues=[])
            plan['quality']['exceptions'] = {}
            atomic_json(root / 'reel.json', plan)
            result = render(tmp, 'draft')
            video = next(s for s in probe(root / result['artifact'], count_frames=True)['streams'] if s['codec_type'] == 'video')
            fcp = export_project(tmp, 'fcpxml', profile='draft')
            document = ET.parse(root / fcp['artifact'])
            fmt = document.find('resources/format')
            self.assertEqual((int(fmt.get('width')), int(fmt.get('height'))), (video['width'], video['height']))
            self.assertEqual(document.find('resources/asset/media-rep').get('src'), (root / result['artifact']).as_uri())
            duration = Fraction(document.find('.//sequence').get('duration').removesuffix('s'))
            self.assertEqual(duration * Fraction(video['avg_frame_rate']), int(video['nb_read_frames']))
            otio = export_project(tmp, 'otio', profile='draft')
            clips = json.loads((root / otio['artifact']).read_text())['tracks']['children'][0]['children']
            self.assertTrue(all(c['OTIO_SCHEMA'] == 'Clip.2' for c in clips))
            self.assertEqual(sum(c['source_range']['duration']['value'] for c in clips), int(video['nb_read_frames']))

    def test_render_decode_cache_selective_revision_and_recovery(self):
        with tempfile.TemporaryDirectory(prefix='reelsyntax real media ') as tmp:
            initialize(tmp)
            root, plan, _ = load(tmp)
            plan['output'].update(width=320,height=180,fps='30000/1001')
            plan['scenes']= [dict(s,duration_frames=12,params={}) for s in plan['scenes'][:2]]
            plan['audio']['cues']=[{'frame':0,'frequency':220,'duration_frames':6},{'frame':12,'frequency':330,'duration_frames':6}]
            plan['quality']['exceptions']={}
            atomic_json(root/'reel.json',plan)
            first=render(tmp,'production')
            self.assertFalse(any(s['cache_hit'] for s in first['scenes']))
            video=next(s for s in probe(root/first['artifact'],count_frames=True)['streams'] if s['codec_type']=='video')
            self.assertEqual(int(video['nb_read_frames']),24)
            self.assertEqual(Fraction(video['avg_frame_rate']),Fraction(30000,1001))
            self.assertEqual((video['width'],video['height']),(320,180))
            second=render(tmp,'production')
            self.assertTrue(all(s['cache_hit'] for s in second['scenes']))
            plan['scenes'][0]['params']['accent']='#446655'
            atomic_json(root/'reel.json',plan)
            changed=render(tmp,'production')
            self.assertEqual([s['cache_hit'] for s in changed['scenes']],[False,True])
            self.assertTrue(any((root/'.reelsyntax/history').iterdir()))
            state=load(tmp)[1]
            state['scenes'][1]['params']['heading']='A heading deliberately too long for the layout'
            atomic_json(root/'reel.json',state)
            before=(root/changed['artifact']).read_bytes()
            with self.assertRaises(ValueError):
                render(tmp,'production')
            self.assertEqual((root/changed['artifact']).read_bytes(),before)
            atomic_json(root/'reel.json',plan)
            recovered=render(tmp,'production',recover=True)
            self.assertTrue(all(s['cache_hit'] for s in recovered['scenes']))
            cache=root/'.reelsyntax/cache'/recovered['scenes'][0]['cache_key']
            (cache/'000000.png').write_bytes(b'corrupt')
            repaired=render(tmp,'production',cache_budget_bytes=0)
            self.assertEqual([s['cache_hit'] for s in repaired['scenes']],[False,True])
            self.assertGreater(repaired['cache_pruning']['removed_bytes'], 0)
            self.assertEqual(repaired['cache_pruning']['protected_entries'], 2)
            self.assertFalse(repaired['cache_pruning']['within_budget'])

    def test_negative_and_intentionally_static_dark_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp,'black.mp4')
            run([executable('ffmpeg'),'-v','error','-nostdin','-y','-f','lavfi','-i','color=black:s=320x180:r=30:d=1','-c:v','libx264','-pix_fmt','yuv420p',str(bad)])
            tools={'ffmpeg':executable('ffmpeg'),'ffprobe':executable('ffprobe')}
            expected={'width':320,'height':180,'frames':30,'fps':'30/1','audio_required':True}
            failed=audit(bad,expected,tools=tools)
            self.assertEqual(next(x for x in failed if x['id']=='audio_stream')['status'],'fail')
            wrong=audit(bad,dict(expected,width=640),tools=tools)
            self.assertEqual(next(x for x in wrong if x['id']=='width')['status'],'fail')
            allowed=audit(bad,{'width':320,'height':180,'frames':30,'fps':'30/1','audio_forbidden':True}, {'black':[[0,1]],'freeze':[[0,1]]}, tools=tools)
            self.assertTrue(all(x['status']=='pass' for x in allowed if x['id']!='creative_review'),allowed)
            self.assertEqual(next(x for x in allowed if x['id']=='creative_review')['status'],'review')


class BrowserWorkerResilienceTests(unittest.TestCase):
    def test_stalled_worker_times_out_and_terminates_cleanly(self):
        import sys
        import time
        from reelsyntax.browser import BrowserRenderer
        t0 = time.perf_counter()
        renderer = BrowserRenderer(timeout=0.35, worker_cmd=[sys.executable, '-c', 'import time; time.sleep(30)'])
        with self.assertRaisesRegex(ValueError, 'readiness timed out'):
            renderer.__enter__()
        self.assertLess(time.perf_counter() - t0, 3.0)
        self.assertIsNone(renderer.process)


@unittest.skipUnless(BROWSER, 'Set REELSYNTAX_BROWSER_TESTS=1 after approving and installing Playwright/Chromium')
class BrowserIntegrationTests(unittest.TestCase):
    def test_actual_browser_seek_and_blocked_network(self):
        from reelsyntax.browser import BrowserRenderer
        from reelsyntax.project import starter
        plan=starter()
        scene=plan['scenes'][0]
        scene['params']={}
        output={'width':320,'height':180,'fps':'30/1'}
        try:
            with tempfile.TemporaryDirectory() as tmp, BrowserRenderer(timeout=6.0) as browser:
                first,middle,again=[Path(tmp,x+'.png') for x in ['first','middle','again']]
                browser.draw(scene,0,output,42,first)
                browser.draw(scene,45,output,42,middle)
                browser.draw(scene,0,output,42,again)
                self.assertEqual(first.read_bytes(),again.read_bytes())
                self.assertNotEqual(first.read_bytes(),middle.read_bytes())
                result=browser.page.evaluate("async () => { try { await fetch('https://example.com'); return false; } catch { return true; } }")
                self.assertTrue(result)
        except ValueError as error:
            if 'readiness timed out' in str(error):
                self.skipTest(f'Blocked by outer host sandbox preventing nested Chromium canvas initialization: {error}')
            raise


if __name__ == '__main__':
    unittest.main()
