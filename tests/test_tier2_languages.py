import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unicodedata
import unittest

from ReelSyntax_Skills.tools.registry import load_index
from ReelSyntax_Skills.tools.route import route
from reelsyntax.lang import (
    SUPPORTED_LOCALES,
    TIER2_LOCALES,
    detect_language,
    fallback_chain,
    fold_accents_for_match,
    load_catalog,
    load_locale_status,
    load_profile,
    locale_lower,
    locale_title,
    locale_upper,
    resolve_ui_locale,
    translate,
    validate_language,
)
from reelsyntax.make import make_video
from reelsyntax.quality import check_reading_speed
from reelsyntax.ui.server import available_locales, ui_strings

REPO_ROOT = Path(__file__).resolve().parents[1]
ROWS = load_index()['skills']


class Tier2LanguagesTests(unittest.TestCase):
    def test_tier2_catalogs_status_and_key_parity_without_owner_verification(self) -> None:
        self.assertEqual(TIER2_LOCALES, ('es', 'fr', 'pt'))
        self.assertEqual(SUPPORTED_LOCALES, ('en', 'tr', 'de', 'es', 'fr', 'pt'))
        status = load_locale_status()
        en_cat = load_catalog('en')
        for code in TIER2_LOCALES:
            meta = status['locales'][code]
            self.assertEqual(meta['tier'], 2)
            self.assertIs(meta['verified_by_owner'], False)
            self.assertIsNone(meta['verified_at'])
            report = validate_language(code)
            self.assertTrue(report['valid'])
            self.assertTrue(report['draft_translation'])
            self.assertIs(report['verified_by_owner'], False)
            self.assertEqual(report['keys'], len(en_cat))
            cat = load_catalog(code)
            self.assertEqual(set(cat), set(en_cat))

    def test_bundled_data_matches_root_for_all_locales_and_profiles(self) -> None:
        for code in TIER2_LOCALES:
            root_loc = REPO_ROOT / f'locales/{code}.json'
            pkg_loc = REPO_ROOT / f'reelsyntax/data/locales/{code}.json'
            self.assertEqual(root_loc.read_bytes(), pkg_loc.read_bytes())

            root_prof = REPO_ROOT / f'lang-profiles/{code}.json'
            pkg_prof = REPO_ROOT / f'reelsyntax/data/lang_profiles/{code}.json'
            self.assertEqual(root_prof.read_bytes(), pkg_prof.read_bytes())

        self.assertEqual(
            (REPO_ROOT / 'locales/status.json').read_bytes(),
            (REPO_ROOT / 'reelsyntax/data/locales/status.json').read_bytes(),
        )

    def test_profiles_cps_nfc_casing_and_detection_for_es_fr_pt(self) -> None:
        expected_cps = {'es': 19, 'fr': 18, 'pt': 19}
        for code, cps in expected_cps.items():
            prof = load_profile(code)
            self.assertEqual(prof['tier'], 2)
            self.assertEqual(prof['caption']['max_cps'], cps)

        nfd_sample = unicodedata.normalize('NFD', 'éêçñãõ')
        for code in TIER2_LOCALES:
            up = locale_upper(nfd_sample, code)
            lo = locale_lower(up, code)
            ti = locale_title(nfd_sample, code)
            self.assertTrue(unicodedata.is_normalized('NFC', up))
            self.assertTrue(unicodedata.is_normalized('NFC', lo))
            self.assertTrue(unicodedata.is_normalized('NFC', ti))
            self.assertEqual(up, 'ÉÊÇÑÃÕ')
            self.assertEqual(lo, 'éêçñãõ')
        self.assertEqual(fold_accents_for_match('café ação mañanero'), 'cafe acao mananero')

        self.assertEqual(detect_language('Consejos rápidos con colores tranquilos sin música'), 'es')
        self.assertEqual(detect_language('Courte vidéo avec sous-titres sans musique et couleurs calmes'), 'fr')
        self.assertEqual(detect_language('Dicas rápidas com legendas sem música e cores calmas'), 'pt')

        self.assertEqual(fallback_chain('es-MX'), ['es-MX', 'es', 'en'])
        self.assertEqual(fallback_chain('fr-CA'), ['fr-CA', 'fr', 'en'])
        self.assertEqual(fallback_chain('pt-BR'), ['pt-BR', 'pt', 'en'])
        self.assertEqual(resolve_ui_locale(None, environ={'LANG': 'pt_BR.UTF-8'}), 'pt')
        self.assertEqual(translate('gate.action.approve', 'es-ES'), 'Aprobar')
        self.assertEqual(translate('gate.action.approve', 'fr-FR'), 'Approuver')
        self.assertEqual(translate('gate.action.approve', 'pt-BR'), 'Aprovar')

    def test_ui_locales_reading_speed_cli_and_dry_run_make(self) -> None:
        ui_codes = {row['code'] for row in available_locales()}
        self.assertTrue({'en', 'tr', 'de', 'es', 'fr', 'pt'}.issubset(ui_codes))
        for code in TIER2_LOCALES:
            strings = ui_strings(code)
            self.assertIn('ui.nav.projects', strings)
            self.assertIn('ui.make.create', strings)

        for iso3, expected_loc in (('spa', 'es'), ('fra', 'fr'), ('por', 'pt')):
            plan = {
                'output': {'width': 1080, 'height': 1920, 'fps': '30/1'},
                'delivery': {'language': iso3},
                'scenes': [{'id': 's1', 'duration_frames': 90, 'params': {'heading': 'OK', 'subheading': 'Texto claro y breve.'}}],
            }
            res = check_reading_speed(plan, {'reading-speed'})
            self.assertEqual(res['status'], 'pass')
            self.assertIn(f'locale {expected_loc}', res['expected'])

            dry = make_video(
                'Dicas rápidas' if expected_loc == 'pt' else ('Consejos rápidos' if expected_loc == 'es' else 'Conseils rapides'),
                video_lang=expected_loc,
                provider_name='offline_rules',
                dry_run=True,
            )
            self.assertEqual(dry['languages']['video_lang'], expected_loc)

        cli_res = subprocess.run(
            [sys.executable, '-m', 'reelsyntax', 'lang', 'validate', '--json'],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(cli_res.returncode, 0, cli_res.stderr)
        payload = json.loads(cli_res.stdout)['result']
        self.assertGreaterEqual(payload['validated_count'], 6)

    def test_tier2_golden_routing(self) -> None:
        for code in TIER2_LOCALES:
            golden = json.loads((REPO_ROOT / f'tests/i18n/golden/{code}.json').read_text(encoding='utf-8'))
            passed = 0
            for case in golden['cases']:
                routed = route(case['query'], ROWS)
                selected_ids = {item['id'] for item in routed['selected']}
                ok_pos = all(req in selected_ids for req in case['expected_any'])
                ok_neg = not bool(selected_ids & set(case['forbidden']))
                if ok_pos and ok_neg:
                    passed += 1
            accuracy = passed / len(golden['cases'])
            self.assertGreaterEqual(accuracy, golden['min_accuracy'], f'Golden routing failed for {code}')

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
    def test_tier2_profile_glyph_coverage(self) -> None:
        from reelsyntax.typography import glyph_audit

        for code in TIER2_LOCALES:
            prof = load_profile(code)
            audit_res = glyph_audit(code)
            self.assertEqual(audit_res['sample'], prof['required_glyphs'])
            self.assertTrue(audit_res['ok'], f'Missing glyphs for {code}: {audit_res["missing_chars"]}')


if __name__ == '__main__':
    unittest.main()
