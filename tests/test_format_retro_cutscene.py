import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import load_index, read_json
from reelsyntax.assets import audit_project_licenses
from reelsyntax.formats import discover_formats, get_format, validate_format_directory
from reelsyntax.formats.installer import _audit_project_json_safety
from reelsyntax.make import make_video, step_project
from reelsyntax.media import executable
from reelsyntax.project import validate
from reelsyntax.quality import check, check_mouth_sync, check_reading_speed
from reelsyntax.skills import file_digest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ffmpeg_ready() -> bool:
    if importlib.util.find_spec('PIL') is None:
        return False
    try:
        return bool(executable('ffmpeg')) and bool(executable('ffprobe'))
    except ValueError:
        return False


class RetroLowpolyCutsceneFormatTests(unittest.TestCase):
    def test_format_package_validates_skills_and_bundled_mirror_matches(self) -> None:
        src_dir = REPO_ROOT / 'formats/retro-lowpoly-cutscene'
        bundled_dir = REPO_ROOT / 'reelsyntax/data/formats/retro-lowpoly-cutscene'
        validated = validate_format_directory(src_dir)
        self.assertTrue(validated['valid'])
        self.assertEqual(validated['id'], 'retro-lowpoly-cutscene')
        self.assertEqual(validated['manifest']['duration_sec'], {'min': 18, 'max': 45})

        required_skills = {
            'retro-cutscene-directing',
            'low-poly-style',
            'lip-sync',
            'voice-fx-flat-synth',
            'eyeline-headroom-grammar',
            'content-policy-boundaries',
            'frame-clock',
        }
        self.assertTrue(required_skills.issubset(set(validated['manifest']['skills'])))
        catalog_ids = {row['id'] for row in load_index()['skills']}
        for sid in validated['manifest']['skills']:
            self.assertIn(sid, catalog_ids)

        src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob('*') if p.is_file()}
        bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob('*') if p.is_file()}
        self.assertEqual(src_files, bundled_files)
        self.assertIn('retro-lowpoly-cutscene', {f['id'] for f in discover_formats()})
        self.assertEqual(get_format('retro-lowpoly-cutscene')['version'], '1.0.0')

    def test_skeleton_and_trilingual_examples_validate_and_pass_sync_and_cps(self) -> None:
        base = REPO_ROOT / 'formats/retro-lowpoly-cutscene'
        for rel in (
            'template/reel.skel.json',
            'examples/en/reel.json',
            'examples/tr/reel.json',
            'examples/de/reel.json',
        ):
            plan_path = base / rel
            _audit_project_json_safety(plan_path)
            doc = read_json(plan_path)
            meta = validate(doc)
            self.assertEqual(meta['scene_count'], 5)
            self.assertEqual(meta['frames'], 24 * 30)
            self.assertEqual(check_reading_speed(doc, {'reading-speed'})['status'], 'pass')
            self.assertEqual(check_mouth_sync(doc)['status'], 'pass')

    def test_dry_run_defaults_to_24s_and_gated_script_generates_audio_sync_without_pillow(self) -> None:
        dry = make_video(
            'Low-poly cutscene at the orbital beacon station',
            provider_name='offline_rules',
            dry_run=True,
        )
        self.assertEqual(dry['format_id'], 'retro-lowpoly-cutscene')
        self.assertEqual(dry['budget']['duration_sec'], 24.0)
        self.assertEqual(dry['budget']['frames'], 24 * 30)
        self.assertEqual(dry['budget']['scenes'], 5)

        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / 'offline-cutscene'
            make_video(
                '9:16 24s low-poly cutscene between Scout and Archivist',
                format_id='retro-lowpoly-cutscene',
                out_dir=pdir,
                provider_name='offline_rules',
                yes=False,
                dry_run_render=True,
            )
            step_project(pdir, 'idea', approve=True, dry_run_render=True)
            plan = read_json(pdir / 'reel.json')
            self.assertEqual(len(plan['scenes']), 5)
            self.assertTrue(any(isinstance(s['params'].get('mouth_envelope'), list) for s in plan['scenes']))
            self.assertTrue(len(plan['audio'].get('tracks', [])) >= 2)
            self.assertTrue(audit_project_licenses(pdir)['ok'])
            self.assertEqual(check_mouth_sync(plan)['status'], 'pass')
            self.assertEqual(check_reading_speed(plan, {'reading-speed'})['status'], 'pass')

    @unittest.skipUnless(_ffmpeg_ready(), 'FFmpeg, FFprobe, and Pillow required for live cutscene render')
    def test_make_retro_lowpoly_cutscene_renders_and_passes_qc_in_en_tr_de(self) -> None:
        cases = [
            ('en', '16:9', '18s low-poly cutscene at the orbital relay deck'),
            ('tr', '9:16', '18 saniye dikey düşük poligon ara sahne gözlem kulesi'),
            ('de', '16:9', '18 Sekunden Low-Poly Zwischensequenz im Signalturm'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for lang_code, aspect_ratio, prompt_text in cases:
                with self.subTest(lang=lang_code, aspect=aspect_ratio):
                    pdir = root / f'cutscene-{lang_code}'
                    make_video(
                        prompt_text,
                        format_id='retro-lowpoly-cutscene',
                        out_dir=pdir,
                        provider_name='offline_rules',
                        video_lang=lang_code,
                        aspect=aspect_ratio,
                        duration_sec=18,
                        yes=False,
                    )
                    for gated in ('idea', 'script', 'look', 'frames', 'pilot'):
                        step_project(pdir, gated, approve=True)

                    self.assertTrue((pdir / 'output/draft.mp4').is_file())
                    qc_res = check(pdir, profile='draft')
                    self.assertEqual(qc_res['technical_status'], 'pass', qc_res)
                    checks_by_id = {c['id']: c for c in qc_res['checks']}
                    self.assertEqual(checks_by_id['mouth_sync']['status'], 'pass')
                    self.assertEqual(checks_by_id['reading_speed']['status'], 'pass')
                    self.assertEqual(checks_by_id['typography_contrast']['status'], 'pass')
                    self.assertEqual(checks_by_id['glyph_coverage']['status'], 'pass')
                    self.assertEqual(checks_by_id['asset_licenses']['status'], 'pass')
                    if aspect_ratio == '9:16':
                        self.assertEqual(checks_by_id['vertical_safe_zones']['status'], 'pass')

                    draft_manifest = read_json(pdir / 'output/draft-manifest.json')
                    draft_h = float(draft_manifest['output_settings']['height'])
                    for s_entry in draft_manifest['scenes']:
                        c_doc = read_json(pdir / f".reelsyntax/cache/{s_entry['cache_key']}/manifest.json")
                        for sample in c_doc.get('layout_samples', []):
                            for item in sample.get('text', []):
                                self.assertLessEqual(item['bounds'][3], draft_h * 0.82)


if __name__ == '__main__':
    unittest.main()
