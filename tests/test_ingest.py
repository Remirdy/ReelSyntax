import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.ingest import asset_hashes, verify_sources
from reelsyntax.media import probe, run
from reelsyntax.project import load, starter, validate
from reelsyntax.quality import check
from reelsyntax.render import render


def media_plan():
    plan = starter()
    plan['output'] = {'width': 320, 'height': 180, 'fps': '24/1'}
    plan['scenes'] = [
        {'id': 'layers', 'duration_frames': 12, 'recipe': 'layer-stack', 'engine': 'pillow', 'params': {'layers': [{'source': 'assets/red.png', 'x': 20, 'y': 20, 'width': 80, 'height': 80, 'opacity': 0.5}]}},
        {'id': 'clip', 'duration_frames': 12, 'recipe': 'footage', 'engine': 'ffmpeg', 'params': {'source': 'assets/source.mkv', 'in_frame': 3}},
    ]
    plan['audio'].update(cues=[], export_stems=True, tracks=[
        {'id': 'j-cut', 'source': 'assets/tone.wav', 'kind': 'effects', 'start_frame': 8, 'duration_frames': 16},
        {'id': 'l-cut', 'source': 'assets/tone.wav', 'kind': 'effects', 'start_frame': 0, 'duration_frames': 16, 'pan': -0.5},
    ])
    plan['quality']['exceptions'] = {'freeze': [[0, 12]]}
    return plan


class IngestTests(unittest.TestCase):
    def test_media_contract_rejects_escapes_ignored_fields_and_conflicts(self):
        plan = media_plan()
        self.assertEqual(validate(plan)['frames'], 24)
        changes = [
            lambda p: p['scenes'][1]['params'].update(source='../outside.mp4'),
            lambda p: p['scenes'][1]['params'].update(source='https://example.com/a.mp4'),
            lambda p: p['scenes'][1]['params'].update(source='output/hero.mp4'),
            lambda p: p['scenes'][1]['params'].update(source='.reelsyntax/cache/old/source.mp4'),
            lambda p: p['scenes'][1].update(engine='browser'),
            lambda p: p['scenes'][0]['params']['layers'][0].update(opacity=2),
            lambda p: p['scenes'][0]['params'].update(heading='ignored'),
            lambda p: p['audio']['tracks'][0].update(kind='music'),
            lambda p: p['audio'].update(enabled=False),
            lambda p: p['audio']['tracks'][0].update(start_frame=24),
        ]
        for change in changes:
            candidate = copy.deepcopy(plan)
            change(candidate)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(candidate)

    def test_source_integrity_records_and_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'assets').mkdir()
            for name in ('red.png', 'source.mkv', 'tone.wav'):
                (root / 'assets' / name).write_bytes(b'original')
            hashes = asset_hashes(root, media_plan())
            self.assertEqual(len(hashes), 3)
            verify_sources(root, {'source_assets': hashes})
            (root / 'assets/red.png').write_bytes(b'revised')
            with self.assertRaisesRegex(ValueError, 'Source asset changed'):
                verify_sources(root, {'source_assets': hashes})


@unittest.skipUnless(os.environ.get('REELSYNTAX_MEDIA_TESTS') == '1' and importlib.util.find_spec('PIL'), 'Enable actual media tests with Pillow and FFmpeg')
class IngestMediaTests(unittest.TestCase):
    def test_psd_extract_preserves_order_alpha_source_and_rejects_unsupported_blend(self):
        import json
        from PIL import Image
        from reelsyntax.gateway import resolve_integration
        from reelsyntax.ingest import render_layers
        from reelsyntax.psd import ingest_psd
        runtime = resolve_integration('after-effects')
        if not runtime['mcp_server_ready']:
            self.skipTest('Optional PSD Node runtime unavailable')
        js = r"""
const {createRequire}=require('module');const fs=require('fs');
const local=createRequire(process.argv[1]+'/package.json');const {writePsdBuffer}=local('ag-psd');
function pixels(w,h,r,g,b){const data=new Uint8ClampedArray(w*h*4);for(let i=0;i<data.length;i+=4){data[i]=r;data[i+1]=g;data[i+2]=b;data[i+3]=255;}return {width:w,height:h,data};}
const layers=[{name:'Bottom',top:0,left:0,imageData:pixels(80,80,240,0,0)},{name:'Top',top:20,left:20,opacity:0.5,blendMode:process.argv[3],imageData:pixels(40,40,0,0,240)}];
fs.writeFileSync(process.argv[2],writePsdBuffer({width:320,height:180,children:layers},{generateThumbnail:false}));
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from reelsyntax.project import initialize
            initialize(root)
            source = root / 'design.psd'
            run([runtime['command'][0], '-e', js, runtime['cwd'], str(source), 'normal'])
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = ingest_psd(root, 'design.psd', 'assets/layers')
            self.assertEqual(result['layers'], 2)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            data = json.loads((root / result['artifact']).read_text())
            scene = {'id': 'design', 'recipe': 'layer-stack', 'engine': 'pillow', 'duration_frames': 1, 'params': data['params']}
            output = root / 'frames'
            output.mkdir()
            render_layers(root, scene, media_plan()['output'], media_plan()['output'], output)
            with Image.open(output / '000000.png') as image:
                pixel = image.getpixel((30, 30))
                self.assertLess(max(abs(a - b) for a, b in zip(pixel, (120, 0, 120))), 2)
            with self.assertRaisesRegex(ValueError, 'new directory'):
                ingest_psd(root, 'design.psd', 'assets/layers')
            run([runtime['command'][0], '-e', js, runtime['cwd'], str(source), 'multiply'])
            with self.assertRaisesRegex(ValueError, 'Unsupported PSD compositing'):
                ingest_psd(root, 'design.psd', 'assets/unsupported')
            self.assertFalse((root / 'assets/unsupported').exists())

    def fixture(self, root):
        from PIL import Image
        from reelsyntax.media import executable, run
        assets = root / 'assets'
        assets.mkdir()
        Image.new('RGBA', (80, 80), (240, 0, 0, 255)).save(assets / 'red.png')
        frames = assets / 'source-frames'
        frames.mkdir()
        for frame in range(18):
            Image.new('RGB', (160, 90), (frame * 12, 30, 60)).save(frames / f'{frame:06d}.png')
        run([executable('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-framerate', '24', '-i', str(frames / '%06d.png'), '-c:v', 'ffv1', '-pix_fmt', 'bgr0', str(assets / 'source.mkv')])
        with wave.open(str(assets / 'tone.wav'), 'wb') as audio:
            audio.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            audio.writeframes(struct.pack('<hh', 2000, 2000) * 48000)
        atomic_json(root / 'reel.json', media_plan())

    def test_real_trim_layers_j_l_cuts_stems_and_selective_cache(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            result = render(root, 'hero')
            video = next(s for s in probe(root / result['artifact'], True)['streams'] if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_read_frames']), 24)
            layer_cache = root / '.reelsyntax/cache' / result['scenes'][0]['cache_key']
            clip_cache = root / '.reelsyntax/cache' / result['scenes'][1]['cache_key']
            with Image.open(layer_cache / '000000.png') as image:
                self.assertEqual(image.getpixel((30, 30)), (120, 0, 0))
            with Image.open(clip_cache / '000000.png') as image:
                pixel = image.getpixel((100, 60))
                self.assertLess(max(abs(a - b) for a, b in zip(pixel, (36, 30, 60))), 3)
            for name, start, end in [('j-cut', 8, 24), ('l-cut', 0, 16)]:
                with wave.open(str(root / f'output/hero-stem-source-{name}.wav'), 'rb') as audio:
                    samples = audio.readframes(audio.getnframes())
                self.assertTrue(all(v == 0 for v in samples[:start * 2000 * 4]))
                self.assertNotEqual(samples[start * 2000 * 4:(start + 1) * 2000 * 4], bytes(2000 * 4))
                self.assertTrue(all(v == 0 for v in samples[end * 2000 * 4:]))
            Image.new('RGBA', (80, 80), (0, 240, 0, 255)).save(root / 'assets/red.png')
            with self.assertRaisesRegex(ValueError, 'Source asset changed'):
                check(root, 'hero')
            revised = render(root, 'hero')
            self.assertEqual([s['cache_hit'] for s in revised['scenes']], [False, True])
            plan = load(root)[1]
            plan['scenes'][1]['params']['in_frame'] = 17
            atomic_json(root / 'reel.json', plan)
            before = (root / revised['artifact']).read_bytes()
            with self.assertRaisesRegex(ValueError, 'too short'):
                render(root, 'hero')
            self.assertEqual((root / revised['artifact']).read_bytes(), before)

    def test_short_source_audio_refuses_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            plan = load(root)[1]
            plan['audio']['tracks'][0]['in_frame'] = 23
            atomic_json(root / 'reel.json', plan)
            with self.assertRaisesRegex(ValueError, 'too short'):
                render(root)
            self.assertFalse((root / 'output/draft.mp4').exists())

    def test_fractional_rate_audio_uses_exact_endpoint_sample_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            plan = load(root)[1]
            plan['output']['fps'] = '30000/1001'
            plan['audio']['tracks'] = [dict(plan['audio']['tracks'][0], start_frame=1, duration_frames=1)]
            atomic_json(root / 'reel.json', plan)
            result = render(root, 'draft')
            self.assertEqual(result['sound']['samples'], 38439)
            with wave.open(str(root / 'output/draft-stem-source-j-cut.wav'), 'rb') as audio:
                samples = audio.readframes(audio.getnframes())
            self.assertEqual(samples[:1602 * 4], bytes(1602 * 4))
            self.assertNotEqual(samples[1602 * 4:3203 * 4], bytes(1601 * 4))
            self.assertEqual(samples[3203 * 4:], bytes(len(samples) - 3203 * 4))

    def test_indirect_media_and_disguised_playlist_are_not_opened(self):
        from reelsyntax.media import local_input_args
        with self.assertRaisesRegex(ValueError, 'playlists'):
            local_input_args('assets/remote.m3u8')
        with tempfile.TemporaryDirectory() as tmp:
            disguised = Path(tmp, 'disguised.mp4')
            disguised.write_text('#EXTM3U\n#EXTINF:1\nhttps://example.com/segment.ts\n')
            with self.assertRaisesRegex(ValueError, 'failed'):
                probe(disguised, safe_input=True)
