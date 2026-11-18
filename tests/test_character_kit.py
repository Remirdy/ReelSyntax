import importlib.util
import math
from pathlib import Path
import tempfile
from typing import Any
import unittest

from reelsyntax.audio.voice_fx import synthesize_retro_dialogue_chirps
from reelsyntax.character import (
    CHARACTER_PRESETS,
    EXPRESSIONS,
    MOUTH_LEVELS,
    blink_aperture,
    build_blender_character,
    build_character_mesh_data,
    build_mouth_envelope,
    expression_parameters,
    get_character_preset,
    is_blinking,
    list_character_presets,
    oklch_to_hex,
)
from reelsyntax.project import starter, validate
from reelsyntax.quality import check_mouth_sync

HAS_PILLOW = importlib.util.find_spec('PIL') is not None


class _FakeInput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.default_value = None


class _FakeNode:
    def __init__(self, node_type: str) -> None:
        self.type = node_type
        self.inputs: dict[str, _FakeInput] = {
            'Base Color': _FakeInput('Base Color'),
            'Roughness': _FakeInput('Roughness'),
            'Metallic': _FakeInput('Metallic'),
        }


class _FakeNodeTree:
    def __init__(self) -> None:
        self.nodes = [_FakeNode('BSDF_PRINCIPLED')]


class _FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.use_nodes = False
        self.node_tree = _FakeNodeTree()


class _FakePoly:
    def __init__(self, indices: tuple[int, ...]) -> None:
        self.vertices = indices
        self.use_smooth = True
        self.material_index = 0


class _FakeMesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.vertices: list[tuple[float, float, float]] = []
        self.polygons: list[_FakePoly] = []
        self.materials: list[_FakeMaterial] = []

    def from_pydata(self, verts: list[tuple[float, float, float]], edges: list[Any], faces: list[tuple[int, ...]]) -> None:
        _ = edges
        self.vertices = list(verts)
        self.polygons = [_FakePoly(tuple(f)) for f in faces]

    def update(self) -> None:
        return None


class _FakeObject:
    def __init__(self, name: str, data: _FakeMesh) -> None:
        self.name = name
        self.data = data


class _FakeRegistry:
    def __init__(self, ctor) -> None:
        self._ctor = ctor
        self._items: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        return self._items.get(name)

    def new(self, name: str, data: Any = None) -> Any:
        obj = self._ctor(name) if data is None else self._ctor(name, data)
        self._items[name] = obj
        return obj


class _FakeCollectionObjects:
    def __init__(self) -> None:
        self.linked: list[Any] = []

    def link(self, obj: Any) -> None:
        self.linked.append(obj)


class _FakeCollection:
    def __init__(self) -> None:
        self.objects = _FakeCollectionObjects()


class _FakeScene:
    def __init__(self) -> None:
        self.collection = _FakeCollection()


class _FakeContext:
    def __init__(self) -> None:
        self.scene = _FakeScene()


class _FakeData:
    def __init__(self) -> None:
        self.meshes = _FakeRegistry(_FakeMesh)
        self.materials = _FakeRegistry(_FakeMaterial)
        self.objects = _FakeRegistry(_FakeObject)


class _FakeBpy:
    def __init__(self) -> None:
        self.data = _FakeData()
        self.context = _FakeContext()


class CharacterKitTests(unittest.TestCase):
    def test_presets_oklch_palettes_and_distinct_rigs(self) -> None:
        presets = list_character_presets()
        self.assertIn('scout', presets)
        self.assertIn('archivist', presets)
        self.assertGreaterEqual(len(presets), 2)

        for pid in presets:
            spec = get_character_preset(pid)
            self.assertEqual(spec['id'], pid)
            for role, vals in spec['oklch'].items():
                self.assertEqual(spec['palette'][role], oklch_to_hex(*vals))
                self.assertRegex(spec['palette'][role], r'^#[0-9a-f]{6}$')

        scout_mesh = build_character_mesh_data('scout')
        archivist_mesh = build_character_mesh_data('archivist')
        self.assertNotEqual(scout_mesh['materials']['primary'], archivist_mesh['materials']['primary'])
        self.assertNotEqual(len(scout_mesh['vertices']), len(archivist_mesh['vertices']))
        self.assertGreater(len(scout_mesh['faces']), 20)
        self.assertGreater(len(archivist_mesh['faces']), 20)

    def test_expressions_and_staggered_blink_cycles(self) -> None:
        for expr in EXPRESSIONS:
            params = expression_parameters(expr)
            self.assertIn('brow_tilt', params)
            self.assertIn('eye_scale_y', params)
            mesh = build_character_mesh_data('scout', expression=expr, mouth_open=0.35)
            self.assertEqual(mesh['expression'], expr)

        neutral = build_character_mesh_data('scout', expression='neutral')
        surprised = build_character_mesh_data('scout', expression='surprised')
        focused = build_character_mesh_data('scout', expression='focused')
        self.assertNotEqual(neutral['vertices'], surprised['vertices'])
        self.assertNotEqual(focused['vertices'], surprised['vertices'])

        scout = CHARACTER_PRESETS['scout']
        archivist = CHARACTER_PRESETS['archivist']
        simultaneous_blinks = [
            f
            for f in range(300)
            if is_blinking(f, blink_period=scout['blink_period'], blink_offset=scout['blink_offset'], blink_duration=scout['blink_duration'])
            and is_blinking(f, blink_period=archivist['blink_period'], blink_offset=archivist['blink_offset'], blink_duration=archivist['blink_duration'])
        ]
        self.assertEqual(simultaneous_blinks, [])
        self.assertTrue(any(blink_aperture(f, blink_period=scout['blink_period'], blink_offset=scout['blink_offset'], blink_duration=scout['blink_duration']) == 0.0 for f in range(120)))

    def test_mouth_envelope_from_duration_samples_and_wav(self) -> None:
        env_dur = build_mouth_envelope(4.0, '30/1', speech_text='Signal locked in sector four.', seed=11)
        self.assertEqual(len(env_dur), 120)
        self.assertTrue(all(v in MOUTH_LEVELS for v in env_dur))
        self.assertEqual(env_dur[0], 0.0)
        self.assertEqual(env_dur[-1], 0.0)
        self.assertGreater(max(env_dur), 0.35)

        sr = 48000
        frame_samples = sr // 30
        silent = [0.0] * frame_samples
        mid_tone = [0.16 * math.sin(math.tau * 220.0 * i / sr) for i in range(frame_samples)]
        loud_tone = [0.70 * math.sin(math.tau * 220.0 * i / sr) for i in range(frame_samples)]
        env_seq = build_mouth_envelope(silent + mid_tone + loud_tone + silent, '30/1', sample_rate=sr)
        self.assertEqual(len(env_seq), 4)
        self.assertEqual(env_seq[0], 0.0)
        self.assertEqual(env_seq[3], 0.0)
        self.assertGreater(env_seq[2], env_seq[1])

        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / 'chirp.wav'
            synthesize_retro_dialogue_chirps(wav_path, 'Relay online and ready.', duration_sec=3.0, base_pitch_hz=250.0, seed=7)
            env_wav = build_mouth_envelope(wav_path, '30/1', duration_frames=90)
            self.assertEqual(len(env_wav), 90)
            self.assertTrue(all(v in MOUTH_LEVELS for v in env_wav))
            self.assertGreater(sum(1 for v in env_wav if v > 0.0), 10)
            self.assertEqual(check_mouth_sync({'scenes': [{'id': 'a', 'duration_frames': 90, 'params': {'mouth_envelope': env_wav}}]})['status'], 'pass')

    def test_project_validation_and_optional_bpy_helper(self) -> None:
        plan = starter()
        plan['scenes'] = [
            {
                'id': 'scout-talk',
                'duration_frames': 60,
                'recipe': 'character-stage',
                'engine': 'pillow',
                'params': {
                    'character': 'scout',
                    'expression': 'focused',
                    'shot_role': 'speaker_a',
                    'character_pos': 'left',
                    'speaker': 'SCOUT',
                    'dialogue': 'Telemetry link restored on channel two.',
                    'mouth_envelope': build_mouth_envelope(2.0, '30/1', duration_frames=60),
                    'background': '#2b303a',
                    'foreground': '#f2f5f9',
                    'accent': '#4c8b93',
                },
            }
        ]
        plan['audio'] = {'enabled': False, 'gain_db': -14, 'cues': []}
        plan['quality'] = {}
        meta = validate(plan)
        self.assertEqual(meta['frames'], 60)

        bad_plan = starter()
        bad_plan['scenes'][0].update(
            recipe='character-stage',
            params={'character': 'scout', 'expression': 'unknown-mood'},
        )
        with self.assertRaises(ValueError):
            validate(bad_plan)

        fake_bpy = _FakeBpy()
        obj = build_blender_character('archivist', expression='happy', mouth_open=0.75, blink_open=1.0, bpy_module=fake_bpy)
        self.assertIsNotNone(obj)
        self.assertIn(obj, fake_bpy.context.scene.collection.objects.linked)
        self.assertTrue(all(poly.use_smooth is False for poly in obj.data.polygons))
        self.assertGreaterEqual(len(obj.data.materials), 4)

    @unittest.skipUnless(HAS_PILLOW, 'Pillow required for procedural character rendering tests')
    def test_pillow_procedural_renderer_expressions_mouth_blink_and_hud_safe_zones(self) -> None:
        from reelsyntax import drawing

        scene = {
            'id': 'talk',
            'duration_frames': 120,
            'recipe': 'character-stage',
            'engine': 'pillow',
            'params': {
                'character': 'scout',
                'partner_character': 'archivist',
                'expression': 'happy',
                'shot_role': 'speaker_a',
                'character_pos': 'left',
                'speaker': 'SCOUT',
                'dialogue': 'Sensors confirm the beacon locked in cleanly.',
                'mouth_envelope': [0.0 if i < 10 else 0.75 for i in range(120)],
                'background': '#2b303a',
                'foreground': '#f2f5f9',
                'accent': '#4cc3c9',
            },
        }
        for w, h in ((960, 540), (540, 960)):
            with self.subTest(size=(w, h)):
                output = {'width': w, 'height': h, 'fps': '30/1', 'original_size': (w, h)}
                im_closed, bounds = drawing.draw(scene, 0, output, 42, supersampling=1)
                im_open, _ = drawing.draw(scene, 15, output, 42, supersampling=1)
                self.assertEqual(im_closed.size, (w, h))
                self.assertNotEqual(im_closed.tobytes(), im_open.tobytes())
                self.assertEqual(im_closed.tobytes(), drawing.draw(scene, 0, output, 42, supersampling=1)[0].tobytes())
                self.assertTrue(len(bounds) >= 2)
                for entry in bounds:
                    x0, y0, x1, y1 = entry['bounds']
                    self.assertGreaterEqual(x0, w * 0.04)
                    self.assertLessEqual(x1, w * 0.96)
                    self.assertGreaterEqual(y0, h * 0.60)
                    self.assertLessEqual(y1, h * 0.82)

        duo_scene = {
            'id': 'duo',
            'duration_frames': 90,
            'recipe': 'character-stage',
            'engine': 'pillow',
            'params': {
                'character': 'scout',
                'partner_character': 'archivist',
                'expression': 'neutral',
                'partner_expression': 'focused',
                'shot_role': 'two_shot',
                'character_pos': 'duo',
                'speaker': 'ARCHIVIST',
                'dialogue': 'Both consoles agree on the trajectory.',
                'background': '#2b303a',
                'foreground': '#f2f5f9',
                'accent': '#e08646',
            },
        }
        im_duo, _ = drawing.draw(duo_scene, 45, {'width': 960, 'height': 540, 'fps': '30/1'}, 42)
        self.assertGreater(len(im_duo.getcolors(960 * 540) or [(1, 2), (2, 3)]), 1)


if __name__ == '__main__':
    unittest.main()
