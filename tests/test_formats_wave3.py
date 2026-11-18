import importlib.util
from pathlib import Path
import tempfile
from typing import Any
import unittest

from ReelSyntax_Skills.tools.registry import load_index, read_json
from reelsyntax import drawing
from reelsyntax.assets import audit_project_licenses
from reelsyntax.formats import FormatRunner, discover_formats, validate_format_directory
from reelsyntax.formats.installer import _audit_project_json_safety
from reelsyntax.make import make_video, step_project
from reelsyntax.media import executable
from reelsyntax.project import validate
from reelsyntax.quality import check, check_claims_sourced
from reelsyntax.render import render
from reelsyntax.skills import file_digest

HAS_PILLOW = importlib.util.find_spec("PIL") is not None
REPO_ROOT = Path(__file__).resolve().parents[1]
WAVE3_FORMATS = ("data-story", "news-ticker", "product-promo", "loop-art")


def _ffmpeg_ready() -> bool:
    if not HAS_PILLOW:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class _ClaimEmitterProvider:
    name = "mock_claim"

    def generate_json(self, system: str, user: str, schema: dict[str, Any], *, seed: int | None = None) -> dict[str, Any]:
        _ = (system, user, seed)
        props = schema.get("properties", {})
        if "hook" in props:
            return {"hook": "45% FASTER", "angle": "Cache wins", "summary": "Skip unchanged renders"}
        if "background" in props and "beats" not in props:
            return {"background": "#2b303a", "foreground": "#f4f6f9", "accent": "#5aa6b0"}
        return {
            "language": "en",
            "aspect": "9:16",
            "background": "#2b303a",
            "foreground": "#f4f6f9",
            "accent": "#5aa6b0",
            "beats": [
                {"id": "b1", "recipe": "data-horizon", "heading": "45% GAIN", "subheading": "Measured local cache.", "weight": 1},
                {"id": "b2", "recipe": "data-horizon", "heading": "3X SPEED", "subheading": "Repeatable run clock.", "weight": 1},
                {"id": "b3", "recipe": "kinetic-type", "heading": "SHIP CLEAN", "subheading": "Zero cloud cost.", "weight": 1},
            ],
        }


class Wave3FormatsTests(unittest.TestCase):
    def test_packages_validate_skills_exist_and_bundled_mirrors_match(self) -> None:
        catalog_ids = {row["id"] for row in load_index()["skills"]}
        discovered_ids = {fmt["id"] for fmt in discover_formats()}
        for fid in WAVE3_FORMATS:
            with self.subTest(format_id=fid):
                src_dir = REPO_ROOT / "formats" / fid
                bundled_dir = REPO_ROOT / "reelsyntax/data/formats" / fid
                validated = validate_format_directory(src_dir)
                self.assertTrue(validated["valid"])
                self.assertEqual(validated["id"], fid)
                self.assertIn(fid, discovered_ids)
                for sid in validated["manifest"]["skills"]:
                    self.assertIn(sid, catalog_ids)
                src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
                bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
                self.assertEqual(src_files, bundled_files)

    def test_skeletons_and_trilingual_examples_validate(self) -> None:
        for fid in WAVE3_FORMATS:
            base = REPO_ROOT / "formats" / fid
            for rel in (
                "template/reel.skel.json",
                "examples/en/reel.json",
                "examples/tr/reel.json",
                "examples/de/reel.json",
            ):
                with self.subTest(format_id=fid, rel=rel):
                    plan_path = base / rel
                    _audit_project_json_safety(plan_path)
                    meta = validate(read_json(plan_path))
                    self.assertGreaterEqual(meta["scene_count"], 1)

    def test_offline_dry_run_and_brief_compilation_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fid, prompt_text in (
                ("data-story", "6s data story comparing cold and cached builds"),
                ("news-ticker", "6s news ticker: Local cache ready, zero cloud calls"),
                ("product-promo", "6s product launch promo for fast offline video engine"),
                ("loop-art", "6s seamless loop art with calm harmonic waves"),
            ):
                with self.subTest(format_id=fid):
                    pdir = root / fid
                    res = make_video(
                        prompt_text,
                        format_id=fid,
                        out_dir=pdir,
                        provider_name="offline_rules",
                        duration_sec=6,
                        yes=True,
                        dry_run_render=True,
                    )
                    self.assertEqual(res["status"], "completed")
                    plan = read_json(pdir / "reel.json")
                    validate(plan)
                    if fid == "data-story":
                        self.assertTrue(any(s["recipe"] == "data-horizon" for s in plan["scenes"]))
                        self.assertEqual(check_claims_sourced(pdir, plan, {"claims-must-be-sourced"})["status"], "pass")
                    elif fid == "news-ticker":
                        self.assertTrue(all(s["recipe"] == "news-ticker" for s in plan["scenes"]))
                    elif fid == "product-promo":
                        self.assertLessEqual(plan["scenes"][0]["duration_frames"], 60)
                        self.assertTrue((pdir / ".reelsyntax/asset-licenses.json").is_file())
                    elif fid == "loop-art":
                        self.assertEqual(len(plan["scenes"]), 1)
                        self.assertEqual(plan["scenes"][0]["recipe"], "loop-art")

            claim_dir = root / "ds-claim-brief"
            runner = FormatRunner.from_id("data-story", _ClaimEmitterProvider(), dry_run_render=True)
            runner.initialize_project(claim_dir, "6s data story, 45% faster rebuilds", duration_sec=6)
            done = runner.run(claim_dir, auto_approve=True)
            self.assertEqual(done["status"], "completed")
            claim_plan = read_json(claim_dir / "reel.json")
            self.assertEqual(check_claims_sourced(claim_dir, claim_plan, {"claims-must-be-sourced"})["status"], "pass")
            self.assertTrue(read_json(claim_dir / "prompt.json").get("sources"))

    @unittest.skipUnless(HAS_PILLOW, "Pillow required for news-ticker and loop-art frame checks")
    def test_news_ticker_reduced_motion_pagination_safe_zone_and_loop_art_seam(self) -> None:
        from PIL import Image, ImageChops, ImageStat

        ticker_plan = read_json(REPO_ROOT / "formats/news-ticker/examples/en/reel.json")
        ticker_scene = ticker_plan["scenes"][0]
        vert_out = {"width": 540, "height": 960, "fps": "30/1"}

        norm_0, bounds_0 = drawing.draw(ticker_scene, 0, {**vert_out, "reduced_motion": False}, 42, supersampling=1)
        norm_1, _ = drawing.draw(ticker_scene, 1, {**vert_out, "reduced_motion": False}, 42, supersampling=1)
        self.assertNotEqual(norm_0.tobytes(), norm_1.tobytes())
        for entry in bounds_0:
            self.assertLessEqual(entry["bounds"][3], vert_out["height"] * 0.82)

        rm_0, rm_bounds = drawing.draw(ticker_scene, 0, {**vert_out, "reduced_motion": True}, 42, supersampling=1)
        rm_1, _ = drawing.draw(ticker_scene, 10, {**vert_out, "reduced_motion": True}, 42, supersampling=1)
        rm_p2, _ = drawing.draw(ticker_scene, 60, {**vert_out, "reduced_motion": True}, 42, supersampling=1)
        self.assertEqual(rm_0.tobytes(), rm_1.tobytes())
        self.assertNotEqual(rm_0.tobytes(), rm_p2.tobytes())
        for entry in rm_bounds:
            self.assertLessEqual(entry["bounds"][3], vert_out["height"] * 0.82)

        loop_plan = read_json(REPO_ROOT / "formats/loop-art/examples/en/reel.json")
        loop_scene = loop_plan["scenes"][0]
        sq_out = {"width": 540, "height": 540, "fps": "30/1"}
        img_first, _ = drawing.draw(loop_scene, 0, sq_out, 42, supersampling=1)
        img_last, _ = drawing.draw(loop_scene, loop_scene["duration_frames"] - 1, sq_out, 42, supersampling=1)
        self.assertNotEqual(img_first.tobytes(), img_last.tobytes())
        small_a = img_first.convert("RGB").resize((16, 9), Image.Resampling.BOX)
        small_b = img_last.convert("RGB").resize((16, 9), Image.Resampling.BOX)
        delta = sum(ImageStat.Stat(ImageChops.difference(small_a, small_b)).mean) / 3.0
        self.assertGreater(delta, 0.0)
        self.assertLessEqual(delta, 8.0)

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for wave3 live render tests")
    def test_trilingual_live_make_and_qc_pass_across_all_four_formats(self) -> None:
        cases = {
            "data-story": [
                ("en", "6s data story comparing cold and cached builds"),
                ("tr", "6 saniye veri grafiği karşılaştırma akışı"),
                ("de", "6 Sekunden Daten Grafik Vergleich lokal"),
            ],
            "news-ticker": [
                ("en", "6s news ticker briefing: Local queue green, cache synced"),
                ("tr", "6 saniye haber bandı duyuru: Yerel kuyruk temiz, çıktı hazır"),
                ("de", "6 Sekunden Nachrichten Ticker: Lokaler Bau bereit, Cache aktiv"),
            ],
            "product-promo": [
                ("en", "6s product promo for offline motion render"),
                ("tr", "6 saniye ürün tanıtımı yerel video motoru"),
                ("de", "6 Sekunden Produkt Promo für lokalen Schnitt"),
            ],
            "loop-art": [
                ("en", "6s seamless loop art with harmonic motion"),
                ("tr", "6 saniye soyut döngü kesintisiz hareket"),
                ("de", "6 Sekunden Endlosschleife harmonische Welle"),
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fid, prompts in cases.items():
                for lang_code, prompt_text in prompts:
                    with self.subTest(format_id=fid, lang=lang_code):
                        pdir = root / f"{fid}-{lang_code}"
                        make_video(
                            prompt_text,
                            format_id=fid,
                            out_dir=pdir,
                            provider_name="offline_rules",
                            video_lang=lang_code,
                            duration_sec=6,
                            yes=False,
                        )
                        for gated in ("idea", "script", "look", "frames", "pilot"):
                            step_project(pdir, gated, approve=True)
                        qc_res = check(pdir, profile="draft", loop=(fid == "loop-art"))
                        self.assertEqual(qc_res["technical_status"], "pass", qc_res["checks"])
                        if fid == "loop-art":
                            loop_check = next(c for c in qc_res["checks"] if c["id"] == "loop_picture")
                            self.assertEqual(loop_check["status"], "pass")
                            flash_check = next(c for c in qc_res["checks"] if c["id"] == "flash_screening")
                            self.assertEqual(flash_check["status"], "pass")

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for wave3 special pipeline tests")
    def test_special_pipelines_claims_reduced_motion_and_product_asset_ledger(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            ds_dir = root / "ds-claims"
            make_video(
                "6s data chart: 45% faster builds without external ledger",
                format_id="data-story",
                out_dir=ds_dir,
                provider_name="offline_rules",
                duration_sec=6,
                yes=False,
            )
            for gated in ("idea", "script", "look", "frames", "pilot"):
                step_project(ds_dir, gated, approve=True)
            ds_qc = check(ds_dir, profile="draft")
            self.assertEqual(ds_qc["technical_status"], "pass", ds_qc["checks"])
            self.assertEqual(next(c for c in ds_qc["checks"] if c["id"] == "claims_sourced")["status"], "pass")

            nt_dir = root / "nt-rm"
            make_video(
                "6s news ticker: Local cache active, zero network calls",
                format_id="news-ticker",
                out_dir=nt_dir,
                provider_name="offline_rules",
                duration_sec=6,
                yes=False,
            )
            for gated in ("idea", "script", "look", "frames", "pilot"):
                step_project(nt_dir, gated, approve=True)
            rm_state = render(nt_dir, profile="draft", reduced_motion=True)
            self.assertTrue(rm_state["reduced_motion"])
            nt_qc = check(nt_dir, profile="draft")
            self.assertEqual(nt_qc["technical_status"], "pass", nt_qc["checks"])
            self.assertEqual(next(c for c in nt_qc["checks"] if c["id"] == "vertical_safe_zones")["status"], "pass")

            promo_dir = root / "promo-asset"
            (promo_dir / "assets").mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (900, 900), "#3c5a78").save(promo_dir / "assets/product.png")
            make_video(
                "6s product promo showcasing studio box",
                format_id="product-promo",
                out_dir=promo_dir,
                provider_name="offline_rules",
                duration_sec=6,
                yes=False,
            )
            for gated in ("idea", "script", "look", "frames", "pilot"):
                step_project(promo_dir, gated, approve=True)
            promo_plan = read_json(promo_dir / "reel.json")
            self.assertEqual(promo_plan["scenes"][1]["recipe"], "layer-stack")
            self.assertTrue(audit_project_licenses(promo_dir)["ok"])
            promo_qc = check(promo_dir, profile="draft")
            self.assertEqual(promo_qc["technical_status"], "pass", promo_qc["checks"])
            self.assertEqual(next(c for c in promo_qc["checks"] if c["id"] == "asset_licenses")["status"], "pass")
            self.assertEqual(next(c for c in promo_qc["checks"] if c["id"] == "opening_hook")["status"], "pass")


if __name__ == "__main__":
    unittest.main()
