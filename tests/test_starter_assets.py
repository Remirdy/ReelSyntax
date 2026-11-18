import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from ReelSyntax_Skills.tools.registry import atomic_json, read_json
from reelsyntax.assets import (
    APPROVED_SPDX_LICENSES,
    audit_project_licenses,
    list_starter_assets,
    materialize_starter_asset,
    materialize_starter_pack,
    register_local_asset,
    resolve_project_asset,
    validate_license_entry,
    verify_open_catalog_candidate,
)
from reelsyntax.cli import main as cli_main
from reelsyntax.project import initialize
from reelsyntax.skills import file_digest


class StarterAssetsAndLicenseTests(unittest.TestCase):
    def test_starter_catalog_has_approved_licenses_across_kinds(self) -> None:
        all_assets = list_starter_assets()
        self.assertGreaterEqual(len(all_assets), 10)
        kinds = {item["kind"] for item in all_assets}
        self.assertEqual(kinds, {"music", "sfx", "palette", "graphic", "font_preset"})
        for item in all_assets:
            self.assertIn(item["spdx"], APPROVED_SPDX_LICENSES)

    def test_materialize_starter_pack_is_deterministic_and_writes_licenses_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "run1"
            p2 = Path(tmp) / "run2"
            res1 = materialize_starter_pack(
                p1,
                asset_ids=["ambient-focus-bed", "soft-whoosh", "photo-plate-warm"],
                duration_sec=2.0,
                seed=101,
            )
            res2 = materialize_starter_pack(
                p2,
                asset_ids=["ambient-focus-bed", "soft-whoosh", "photo-plate-warm"],
                duration_sec=2.0,
                seed=101,
            )
            self.assertEqual(res1["materialized_count"], 3)
            self.assertEqual(res2["materialized_count"], 3)

            wav1 = p1 / "assets/starter/music/ambient-focus-bed.wav"
            wav2 = p2 / "assets/starter/music/ambient-focus-bed.wav"
            self.assertEqual(file_digest(wav1), file_digest(wav2))
            with wave.open(str(wav1), "rb") as wf:
                self.assertEqual(wf.getframerate(), 48000)
                self.assertEqual(wf.getnchannels(), 2)
                self.assertEqual(wf.getnframes(), 96000)

            lic_md = (p1 / "LICENSES.md").read_text(encoding="utf-8")
            self.assertIn("ambient-focus-bed.wav", lic_md)
            self.assertIn("CC0-1.0", lic_md)

    def test_license_policy_rejects_copyleft_unattributed_cc_by_and_network_without_opt_in(self) -> None:
        with self.assertRaisesRegex(ValueError, "Disallowed or unknown"):
            validate_license_entry({
                "path": "assets/song.wav",
                "spdx": "GPL-3.0-only",
                "sha256": "a" * 64,
            })

        with self.assertRaisesRegex(ValueError, "requires non-empty"):
            validate_license_entry({
                "path": "assets/loop.wav",
                "spdx": "CC-BY-4.0",
                "author": "",
                "attribution": "",
                "sha256": "b" * 64,
            })

        with self.assertRaisesRegex(ValueError, "disabled by default"):
            verify_open_catalog_candidate(
                {"url": "https://example.invalid/track.wav", "spdx": "CC0-1.0"},
                allow_network=False,
            )

    def test_audit_detects_missing_or_tampered_assets_and_passes_when_registered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "film"
            initialize(proj)

            mat = materialize_starter_asset(proj, "crisp-click", seed=12)
            plan = read_json(proj / "reel.json")
            plan["constraints"]["no_music"] = False
            plan["audio"]["tracks"] = [
                {
                    "id": "click-fx",
                    "source": mat["path"],
                    "kind": "effects",
                    "start_frame": 0,
                    "duration_frames": 5,
                }
            ]
            atomic_json(proj / "reel.json", plan)

            audit_ok = audit_project_licenses(proj)
            self.assertTrue(audit_ok["ok"])
            self.assertEqual(audit_ok["technical_status"], "pass")

            unlicensed = proj / "assets/unregistered.wav"
            unlicensed.parent.mkdir(parents=True, exist_ok=True)
            unlicensed.write_bytes((proj / mat["path"]).read_bytes())
            plan["audio"]["tracks"].append({
                "id": "mystery-fx",
                "source": "assets/unregistered.wav",
                "kind": "effects",
                "start_frame": 10,
                "duration_frames": 5,
            })
            atomic_json(proj / "reel.json", plan)

            err_buf = io.StringIO()
            out_buf = io.StringIO()
            with patch("sys.stdout", out_buf), patch("sys.stderr", err_buf):
                rc_fail = cli_main(["assets", "licenses", str(proj), "--json"])
            self.assertEqual(rc_fail, 2)
            fail_res = json.loads(out_buf.getvalue())["result"]
            self.assertEqual(fail_res["missing_licenses"], ["assets/unregistered.wav"])

            register_local_asset(proj, unlicensed, dest_rel="assets/unregistered.wav", spdx="CC-BY-4.0", author="Studio Composer")
            pass_buf = io.StringIO()
            with patch("sys.stdout", pass_buf):
                rc_pass = cli_main(["assets", "licenses", str(proj), "--write", "--json"])
            self.assertEqual(rc_pass, 0)
            self.assertTrue((proj / "LICENSES.md").is_file())

    def test_resolver_orders_project_local_then_user_local_then_starter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "proj"
            proj.mkdir()

            res_starter = resolve_project_asset(proj, "starter:soft-whoosh", seed=9)
            self.assertEqual(res_starter["source_kind"], "starter_procedural")

            ext = root / "external-note.txt"
            ext.write_text("sample", encoding="utf-8")
            res_user = resolve_project_asset(proj, str(ext))
            self.assertEqual(res_user["source_kind"], "user_local")
            self.assertEqual(res_user["path"], "assets/external-note.txt")

            res_local = resolve_project_asset(proj, "assets/external-note.txt")
            self.assertEqual(res_local["source_kind"], "project_local")


if __name__ == "__main__":
    unittest.main()
