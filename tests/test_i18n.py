import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import load_index
from ReelSyntax_Skills.tools.route import route
from reelsyntax.lang import (
    detect_language,
    fallback_chain,
    fold_accents_for_match,
    load_locale_status,
    load_profile,
    locale_lower,
    locale_upper,
    pseudo_localize,
    resolve_ui_locale,
    scaffold_language,
    translate,
    validate_language,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ROWS = load_index()["skills"]


class InternationalizationFoundationTests(unittest.TestCase):
    def test_status_flags_remain_false_and_tier1_catalogs_validate(self) -> None:
        status = load_locale_status()
        for code in ("en", "tr", "de"):
            self.assertIn(code, status["locales"])
            self.assertEqual(status["locales"][code]["tier"], 1)
            self.assertIs(status["locales"][code]["verified_by_owner"], False)
            report = validate_language(code)
            self.assertTrue(report["valid"])
            self.assertIs(report["verified_by_owner"], False)
        self.assertTrue(validate_language("tr")["draft_translation"])
        self.assertTrue(validate_language("de")["draft_translation"])

    def test_bundled_package_data_matches_root_locales_and_profiles(self) -> None:
        root_locales = sorted((REPO_ROOT / "locales").glob("*.json"))
        bundled_locales = sorted((REPO_ROOT / "reelsyntax/data/locales").glob("*.json"))
        self.assertEqual([p.name for p in root_locales], [p.name for p in bundled_locales])
        for src, dst in zip(root_locales, bundled_locales):
            self.assertEqual(src.read_bytes(), dst.read_bytes(), f"Drifted {src.name}")

        root_profiles = sorted((REPO_ROOT / "lang-profiles").glob("*.json"))
        bundled_profiles = sorted((REPO_ROOT / "reelsyntax/data/lang_profiles").glob("*.json"))
        self.assertEqual([p.name for p in root_profiles], [p.name for p in bundled_profiles])
        for src, dst in zip(root_profiles, bundled_profiles):
            self.assertEqual(src.read_bytes(), dst.read_bytes(), f"Drifted {src.name}")

    def test_locale_aware_casing_for_turkish_and_german(self) -> None:
        self.assertEqual(locale_upper("istanbul", "tr"), "İSTANBUL")
        self.assertEqual(locale_upper("ışık", "tr"), "IŞIK")
        self.assertEqual(locale_upper("Straße", "de"), "STRASSE")
        self.assertEqual(locale_lower("İSTANBUL", "tr"), "istanbul")
        self.assertEqual(locale_lower("IŞIK", "tr"), "ışık")
        self.assertEqual(locale_lower("Straße", "de"), "straße")
        self.assertEqual(fold_accents_for_match("Straße ışık"), "strasse isik")

    def test_offline_language_detection_and_ui_locale_fallback(self) -> None:
        self.assertEqual(detect_language("5 odaklanma ipucu, sakin renkler ve hareketli yazı"), "tr")
        self.assertEqual(detect_language("Kurzes Video ohne Musik mit ruhigen Farben und Untertiteln"), "de")
        self.assertEqual(detect_language("Create a short vertical video with calm colors and captions"), "en")
        self.assertEqual(detect_language("مرحبا بالعالم"), "ar")
        self.assertEqual(detect_language("日本語のテスト"), "ja")

        self.assertEqual(fallback_chain("tr-TR"), ["tr-TR", "tr", "en"])
        self.assertEqual(fallback_chain("de-AT"), ["de-AT", "de", "en"])
        self.assertEqual(resolve_ui_locale(None, environ={"LANG": "de_DE.UTF-8"}), "de")
        self.assertEqual(translate("gate.action.approve", "tr-TR"), "Onayla")
        self.assertEqual(translate("gate.action.approve", "de-AT"), "Freigeben")
        self.assertIn("1 scene", translate("make.scenes_planned", "en", count=1, frames=30))
        self.assertIn("3 scenes", translate("make.scenes_planned", "en", count=3, frames=90))

        expanded = pseudo_localize("Review step '{step}': approve")
        self.assertIn("{step}", expanded)
        self.assertGreater(len(expanded), len("Review step '{step}': approve"))

    def test_scaffold_and_validate_new_language_via_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "locales").mkdir()
            (root / "lang-profiles").mkdir()
            for name in ("en.json", "status.json"):
                (root / "locales" / name).write_bytes((REPO_ROOT / "locales" / name).read_bytes())
            (root / "lang-profiles/en.json").write_bytes((REPO_ROOT / "lang-profiles/en.json").read_bytes())

            created = scaffold_language("fr", root=root)
            self.assertTrue(Path(created["profile"]).is_file())
            res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "lang", "validate", "fr", "--root", str(root), "--json"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)["result"]
            self.assertTrue(payload["valid"])
            self.assertFalse(payload["verified_by_owner"])

    def test_multilingual_negation_and_tier1_golden_routing(self) -> None:
        res_es = route("sin texto", ROWS)
        self.assertTrue(res_es["constraints"]["no_text"])
        res_fr = route("sans musique cinematic drone", ROWS)
        self.assertTrue(res_fr["constraints"]["no_music"])
        self.assertNotIn("cinematic-drone", [x["id"] for x in res_fr["selected"]])

        for code in ("en", "tr", "de"):
            golden = json.loads((REPO_ROOT / f"tests/i18n/golden/{code}.json").read_text(encoding="utf-8"))
            passed = 0
            for case in golden["cases"]:
                routed = route(case["query"], ROWS)
                selected_ids = {item["id"] for item in routed["selected"]}
                ok_pos = all(req in selected_ids for req in case["expected_any"])
                ok_neg = not bool(selected_ids & set(case["forbidden"]))
                if ok_pos and ok_neg:
                    passed += 1
            accuracy = passed / len(golden["cases"])
            self.assertGreaterEqual(accuracy, golden["min_accuracy"], f"Golden routing failed for {code}")

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow required")
    def test_tier1_profile_glyph_coverage(self) -> None:
        from reelsyntax.typography import glyph_audit

        for code in ("en", "tr", "de"):
            prof = load_profile(code)
            audit_res = glyph_audit(code)
            self.assertEqual(audit_res["sample"], prof["required_glyphs"])
            self.assertTrue(audit_res["ok"], f"Missing glyphs for {code}: {audit_res['missing_chars']}")


if __name__ == "__main__":
    unittest.main()
