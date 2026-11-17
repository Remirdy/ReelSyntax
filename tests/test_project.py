import copy
from fractions import Fraction
import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import atomic_json
from reelsyntax.project import initialize, load, starter, validate
from reelsyntax.render import check_locks, lock, output_settings
from reelsyntax.revisions import checkpoint, restore
from reelsyntax.skills import search
from reelsyntax.sound import synthesize


class ProjectTests(unittest.TestCase):
    def test_aperture_recipe_requires_native_engine_and_valid_shot(self):
        plan = starter()
        plan['scenes'][0].update(recipe='aperture', engine='blender', params={'shot': 'hero'})
        self.assertEqual(validate(plan)['scene_count'], len(plan['scenes']))
        for mutation in [lambda scene: scene.update(engine='pillow'), lambda scene: scene['params'].update(shot='unknown'), lambda scene: scene['params'].update(heading='Overlay')]:
            candidate = copy.deepcopy(plan)
            mutation(candidate['scenes'][0])
            with self.assertRaises(ValueError):
                validate(candidate)

    def test_rational_timeline_and_round_trip(self):
        plan = starter()
        plan['output']['fps'] = '30000/1001'
        metadata = validate(plan)
        self.assertEqual(metadata['duration'], str(Fraction(240 * 1001, 30000)))
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            self.assertEqual(load(tmp)[1], starter())
            with self.assertRaises(ValueError):
                initialize(tmp)

    def test_invalid_plans_and_constraints(self):
        changes = [lambda p: p.update(schema_version=2), lambda p: p.update(unknown=True),
                   lambda p: p['output'].update(fps='29.97'), lambda p: p['output'].update(width=961),
                   lambda p: p['scenes'][1].update(id='form'), lambda p: p['scenes'][0].update(duration_frames=-1),
                   lambda p: p['scenes'][0].update(engine='blender'), lambda p: p['constraints'].update(no_text=True),
                   lambda p: p['constraints'].update(no_audio=True), lambda p: p['audio']['cues'][0].update(frame=240),
                   lambda p: p['quality'].update(exceptions={'freeze': [[0,241]]}), lambda p: p['audio'].update(gain_db=float('nan'))]
        for change in changes:
            plan = starter()
            change(plan)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(plan)

    def test_draft_preserves_aspect(self):
        for width, height in [(960,540),(962,542),(1080,1920),(66,64)]:
            plan = starter()
            plan['output'].update(width=width,height=height)
            settings = output_settings(plan,'draft')
            self.assertEqual(Fraction(width,height),Fraction(settings['width'],settings['height']))
            self.assertEqual(settings['width'] % 2,0)
            self.assertEqual(settings['height'] % 2,0)

    def test_scene_lock_rejects_shift_and_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            lock(tmp,['time'])
            root, plan, _ = load(tmp)
            plan['scenes'][0]['duration_frames'] -= 1
            with self.assertRaisesRegex(ValueError, 'Approved scene changed'):
                check_locks(root,plan)
            plan = starter()
            plan['scenes'][1]['params']['heading'] = 'CHANGED'
            with self.assertRaises(ValueError):
                check_locks(root,plan)

    def test_checkpoints_restore_as_new_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            checkpoint(tmp,'first')
            with self.assertRaises(ValueError):
                checkpoint(tmp,'first')
            root, plan, _ = load(tmp)
            plan['scenes'][0]['params']['heading'] = 'EDIT'
            atomic_json(root/'reel.json',plan)
            result = restore(tmp,'first')
            self.assertEqual(load(tmp)[1],starter())
            self.assertTrue((root/f'.reelsyntax/revisions/{result["revision"]}.json').is_file())

    def test_restore_recovers_invalid_source_without_losing_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            checkpoint(tmp, 'valid-source')
            current = Path(tmp, 'reel.json')
            damaged = b'invalid source, keep these edits\xff'
            current.write_bytes(damaged)
            result = restore(tmp, 'valid-source')
            self.assertEqual(load(tmp)[1], starter())
            self.assertEqual(Path(tmp, f'.reelsyntax/revisions/{result["revision"]}.reel.json').read_bytes(), damaged)

    def test_project_constraints_survive_stage_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            initialize(tmp)
            result = search({'intent':'orbit camera','stage':'render'},tmp)
            self.assertTrue(result['constraints']['camera_locked'])
            self.assertNotIn('orbit-camera',[x['id'] for x in result['selected']])
            with self.assertRaises(ValueError):
                search({'intent':'x','constraints':{'camera_locked':False}},tmp)

    def test_audio_sample_count_and_determinism(self):
        import wave
        with tempfile.TemporaryDirectory() as tmp:
            plan = starter()
            plan['output']['fps'] = '30000/1001'
            plan['scenes'] = [dict(plan['scenes'][0],duration_frames=3)]
            plan['audio']['cues'] = [{'frame':0,'frequency':330,'duration_frames':3}]
            a,b=Path(tmp,'a.wav'),Path(tmp,'b.wav')
            result = synthesize(a,plan)
            synthesize(b,plan)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(result['samples'],4805)
            self.assertLess(result['sample_peak_dbfs'],-6)
            with wave.open(str(a)) as stream:
                self.assertEqual(stream.getnframes(),4805)
                self.assertEqual(stream.getnchannels(),2)

    @unittest.skipUnless(importlib.util.find_spec('PIL'),'Pillow optional dependency unavailable')
    def test_real_frames_seek_and_layout_failure(self):
        from reelsyntax.drawing import draw
        plan = starter()
        first,_ = draw(plan['scenes'][0],0,plan['output'],42)
        middle,_ = draw(plan['scenes'][0],45,plan['output'],42)
        again,_ = draw(plan['scenes'][0],0,plan['output'],42)
        self.assertEqual(first.tobytes(),again.tobytes())
        self.assertNotEqual(first.tobytes(),middle.tobytes())
        scene = copy.deepcopy(plan['scenes'][0])
        scene['params']['heading'] = 'A very long heading that cannot fit its assigned region'
        with self.assertRaisesRegex(ValueError,'safe layout region'):
            draw(scene,0,plan['output'],42)


if __name__ == '__main__':
    unittest.main()
