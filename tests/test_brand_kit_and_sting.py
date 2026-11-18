from fractions import Fraction
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ReelSyntax_Skills.tools.registry import read_json
from reelsyntax.brand import (
    STING_GROUND_HEX,
    STING_INK_HEX,
    STING_SUBTITLES,
    append_closing_sting,
    apply_brand_kit,
    brand_kit_schema,
    init_brand_kit,
    load_brand_kit,
    localized_sting_subtitle,
    resolve_attribution,
    sting_duration_frames,
    validate_brand_kit,
)
from reelsyntax.cli import main as cli_main
from reelsyntax.completion import generate_completion
from reelsyntax.make import make_video, step_project
from reelsyntax.media import executable
from reelsyntax.project import initialize, load, starter, validate
from reelsyntax.quality import check
from reelsyntax.render import lock, render

HAS_PILLOW = importlib.util.find_spec("PIL") is not None


def _ffmpeg_ready() -> bool:
    if not HAS_PILLOW:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class BrandKitTests(unittest.TestCase):
    def test_brand_kit_init_validate_contrast_floors_and_apply(self) -> None:
        schema = brand_kit_schema()
        self.assertEqual(schema["title"], "ReelSyntax brand kit")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "proj"
            initialize(proj)
            created = init_brand_kit(proj, name="Nordic Press", background="#1f2430", foreground="#f8fafc", accent="#38bdf8")
            self.assertTrue(created["valid"])
            self.assertGreaterEqual(created["contrast"]["foreground_ratio"], 4.5)
            kit_path = Path(created["path"])
            self.assertTrue(kit_path.is_file())

            loaded = load_brand_kit(kit_path, project_root=proj)
            self.assertEqual(loaded.name, "Nordic Press")

            with self.assertRaisesRegex(ValueError, "contrast ratio"):
                validate_brand_kit({"background": "#22262e", "foreground": "#464d59", "accent": "#38bdf8"})
            with self.assertRaisesRegex(ValueError, "accent contrast ratio"):
                validate_brand_kit({"background": "#1f2430", "foreground": "#f8fafc", "accent": "#282e3b"})
            with self.assertRaisesRegex(ValueError, "project-relative asset path"):
                validate_brand_kit({"font": "../escape.ttf"})
            with self.assertRaisesRegex(ValueError, "brand.mark.preset"):
                validate_brand_kit({"mark": {"preset": "unknown"}})

            plan = load(proj)[1]
            updated = apply_brand_kit(plan, loaded, project_root=proj)
            for scene in updated["scenes"]:
                self.assertEqual(scene["params"]["background"], "#1f2430")
                self.assertEqual(scene["params"]["foreground"], "#f8fafc")
                self.assertEqual(scene["params"]["accent"], "#38bdf8")

            lock(proj, [plan["scenes"][0]["id"]])
            bad_kit = proj / "locked-change.json"
            init_brand_kit(bad_kit, name="Shift", background="#24303a", foreground="#f8fafc", accent="#38bdf8")
            with self.assertRaisesRegex(ValueError, "Approved scene changed"):
                from reelsyntax.brand import apply_brand_kit_to_project

                apply_brand_kit_to_project(proj, bad_kit)

    def test_cli_brand_init_validate_apply_and_completion(self) -> None:
        script = generate_completion("bash")
        self.assertIn("brand", script)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "film"
            initialize(proj)
            kit_file = proj / "brand.json"

            buf_init = io.StringIO()
            with patch("sys.stdout", buf_init):
                rc = cli_main([
                    "brand", "init", str(kit_file),
                    "--name", "Craft Lab",
                    "--background", "#202736",
                    "--foreground", "#f5f7fa",
                    "--accent", "#e8a33d",
                    "--json",
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf_init.getvalue())["result"]["valid"])

            buf_val = io.StringIO()
            with patch("sys.stdout", buf_val):
                rc_val = cli_main(["brand", "validate", str(kit_file), "--project", str(proj), "--json"])
            self.assertEqual(rc_val, 0)
            self.assertGreaterEqual(json.loads(buf_val.getvalue())["result"]["contrast"]["foreground_ratio"], 4.5)

            buf_apply = io.StringIO()
            with patch("sys.stdout", buf_apply):
                rc_apply = cli_main(["brand", "apply", str(proj), str(kit_file), "--json"])
            self.assertEqual(rc_apply, 0)
            self.assertTrue(json.loads(buf_apply.getvalue())["result"]["applied"])
            applied_plan = read_json(proj / "reel.json")
            self.assertEqual(applied_plan["scenes"][0]["params"]["background"], "#202736")
            self.assertEqual(applied_plan["scenes"][0]["params"]["accent"], "#e8a33d")


class AttributionAndStingTests(unittest.TestCase):
    def test_rational_sting_duration_and_localized_subtitles(self) -> None:
        self.assertEqual(sting_duration_frames("30/1"), 54)
        self.assertEqual(sting_duration_frames("24/1"), 43)
        self.assertEqual(sting_duration_frames("60/1"), 108)
        self.assertEqual(sting_duration_frames(Fraction(30000, 1001)), 54)

        self.assertEqual(localized_sting_subtitle("en"), "Built with ReelSyntax")
        self.assertEqual(localized_sting_subtitle("tr"), "ReelSyntax ile üretildi")
        self.assertEqual(localized_sting_subtitle("de"), "Erstellt mit ReelSyntax")
        self.assertEqual(localized_sting_subtitle("tur"), STING_SUBTITLES["tr"])

    def test_attribution_off_appends_zero_scenes_frames_or_marks(self) -> None:
        self.assertFalse(resolve_attribution(None, False))
        self.assertFalse(resolve_attribution(False, True))
        self.assertFalse(resolve_attribution("off", True))
        self.assertTrue(resolve_attribution("on", False))
        with self.assertRaises(ValueError):
            resolve_attribution("maybe", False)

        base = starter()
        off_plan = append_closing_sting(base, attribution=False, video_lang="en")
        self.assertEqual(off_plan, base)
        self.assertEqual(len(off_plan["scenes"]), len(base["scenes"]))
        self.assertNotIn("delivery", off_plan)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_file = root / "reelsyntax.toml"
            cfg_file.write_text("config_version = 1\n[general]\nattribution = true\n", encoding="utf-8")

            off_dir = root / "off-proj"
            on_dir = root / "on-proj"
            buf_off = io.StringIO()
            with patch("sys.stdout", buf_off):
                rc_off = cli_main([
                    "--config", str(cfg_file),
                    "make", "9s kinetic quote: Clean frames",
                    "--format", "kinetic-typography",
                    "--out", str(off_dir),
                    "--attribution", "off",
                    "--dry-run", "--json",
                ])
            self.assertEqual(rc_off, 0)
            off_res = json.loads(buf_off.getvalue())["result"]
            self.assertFalse(off_res["attribution"])
            self.assertEqual(off_res["budget"]["frames"], 9 * 30)

            buf_on = io.StringIO()
            with patch("sys.stdout", buf_on):
                rc_on = cli_main([
                    "make", "9s kinetic quote: Clean frames",
                    "--format", "kinetic-typography",
                    "--out", str(on_dir),
                    "--attribution", "on",
                    "--dry-run", "--json",
                ])
            self.assertEqual(rc_on, 0)
            on_res = json.loads(buf_on.getvalue())["result"]
            self.assertTrue(on_res["attribution"])
            self.assertEqual(on_res["budget"]["frames"], 9 * 30 + 54)

    def test_loop_preserving_attribution_keeps_zero_appended_scenes(self) -> None:
        base = starter()
        loop_plan = append_closing_sting(base, attribution=True, video_lang="de", loop=True)
        self.assertEqual(len(loop_plan["scenes"]), len(base["scenes"]))
        self.assertEqual(sum(s["duration_frames"] for s in loop_plan["scenes"]), sum(s["duration_frames"] for s in base["scenes"]))
        self.assertEqual(loop_plan["delivery"]["attribution"], "metadata-only-loop")

        loop_art_plan = append_closing_sting(base, attribution=True, video_lang="en", format_id="loop-art")
        self.assertEqual(len(loop_art_plan["scenes"]), len(base["scenes"]))
        self.assertEqual(loop_art_plan["delivery"]["attribution"], "metadata-only-loop")

    def test_sting_audio_chime_and_no_audio_constraint(self) -> None:
        base = starter()
        base["constraints"]["no_music"] = False
        on_plan = append_closing_sting(base, attribution=True, video_lang="tr")
        validate(on_plan)
        sting = on_plan["scenes"][-1]
        self.assertEqual(sting["recipe"], "brand-sting")
        self.assertEqual(sting["duration_frames"], 54)
        self.assertEqual(sting["params"]["background"], STING_GROUND_HEX)
        self.assertEqual(sting["params"]["foreground"], STING_INK_HEX)
        self.assertEqual(sting["params"]["heading"], "Remirdy")
        self.assertEqual(sting["params"]["subheading"], "ReelSyntax ile üretildi")
        chime = on_plan["audio"]["cues"][-1]
        self.assertEqual(chime["instrument"], "warm_pad")
        self.assertEqual(chime["frequency"], 440)
        self.assertAlmostEqual(on_plan["audio"]["gain_db"] + chime["gain_offset_db"], -18.0, places=3)

        no_music_base = starter()
        no_music_on = append_closing_sting(no_music_base, attribution=True, video_lang="en")
        self.assertEqual(len(no_music_on["audio"]["cues"]), len(no_music_base["audio"]["cues"]))

        silent_base = starter()
        silent_base["constraints"]["no_audio"] = True
        silent_base["audio"] = {"enabled": False, "gain_db": -14, "cues": []}
        silent_on = append_closing_sting(silent_base, attribution=True, video_lang="en")
        self.assertEqual(silent_on["audio"]["cues"], [])
        self.assertEqual(silent_on["scenes"][-1]["recipe"], "brand-sting")

    @unittest.skipUnless(HAS_PILLOW, "Pillow required for sting frame rendering tests")
    def test_sting_frame_render_and_reduced_motion_fade(self) -> None:
        from reelsyntax import drawing

        plan = append_closing_sting(starter(), attribution=True, video_lang="en")
        sting = plan["scenes"][-1]
        out = {"width": 640, "height": 360, "fps": "30/1"}

        img_a, bounds_a = drawing.draw(sting, 27, out, 42, supersampling=1)
        img_b, _ = drawing.draw(sting, 27, out, 42, supersampling=1)
        self.assertEqual(img_a.tobytes(), img_b.tobytes())
        self.assertEqual([b["field"] for b in bounds_a], ["heading", "subheading"])

        rm_f0, _ = drawing.draw(sting, 0, out, 42, supersampling=1, reduced_motion=True)
        rm_f8, _ = drawing.draw(sting, 8, out, 42, supersampling=1, reduced_motion=True)
        self.assertEqual(len(rm_f0.getcolors(640 * 360)), 1)
        self.assertGreater(len(rm_f8.getcolors(640 * 360)), 1)
        self.assertEqual(rm_f8.tobytes(), drawing.draw(sting, 40, out, 42, supersampling=1, reduced_motion=True)[0].tobytes())

    @unittest.skipUnless(_ffmpeg_ready(), "Pillow, FFmpeg, and FFprobe required for brand sting live render and QC")
    def test_live_attribution_off_on_and_reduced_motion_pass_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            off_dir = root / "unbranded"
            make_video(
                "6s vertical kinetic reel: Clean renders locally",
                format_id="kinetic-typography",
                out_dir=off_dir,
                provider_name="offline_rules",
                video_lang="en",
                duration_sec=6,
                attribution="off",
                yes=False,
            )
            for gated in ("idea", "script", "look", "frames", "pilot"):
                step_project(off_dir, gated, approve=True)
            off_plan = read_json(off_dir / "reel.json")
            self.assertEqual(sum(s["duration_frames"] for s in off_plan["scenes"]), 180)
            self.assertNotIn("brand-sting", [s["recipe"] for s in off_plan["scenes"]])
            off_manifest = read_json(off_dir / "output/draft-manifest.json")
            self.assertNotIn("attribution", off_manifest)
            self.assertEqual(check(off_dir, profile="draft")["technical_status"], "pass")

            for lang_code, expected_sub in (
                ("en", "Built with ReelSyntax"),
                ("tr", "ReelSyntax ile üretildi"),
                ("de", "Erstellt mit ReelSyntax"),
            ):
                with self.subTest(lang=lang_code):
                    on_dir = root / f"branded-{lang_code}"
                    make_video(
                        "6s vertical kinetic reel: Clean renders locally",
                        format_id="kinetic-typography",
                        out_dir=on_dir,
                        provider_name="offline_rules",
                        video_lang=lang_code,
                        duration_sec=6,
                        attribution="on",
                        yes=False,
                    )
                    for gated in ("idea", "script", "look", "frames", "pilot"):
                        step_project(on_dir, gated, approve=True)
                    on_plan = read_json(on_dir / "reel.json")
                    self.assertEqual(sum(s["duration_frames"] for s in on_plan["scenes"]), 180 + 54)
                    self.assertEqual(on_plan["scenes"][-1]["recipe"], "brand-sting")
                    self.assertEqual(on_plan["scenes"][-1]["params"]["subheading"], expected_sub)
                    on_manifest = read_json(on_dir / "output/draft-manifest.json")
                    self.assertEqual(on_manifest["attribution"], "remirdy-sting-v1")
                    qc_res = check(on_dir, profile="draft")
                    self.assertEqual(qc_res["technical_status"], "pass")
                    by_id = {c["id"]: c["status"] for c in qc_res["checks"]}
                    self.assertEqual(by_id["black"], "pass")
                    self.assertEqual(by_id["typography_contrast"], "pass")
                    self.assertEqual(by_id["frame_cadence"], "pass")
                    if lang_code == "en":
                        render(on_dir, profile="draft", reduced_motion=True)
                        rm_qc = check(on_dir, profile="draft")
                        self.assertEqual(rm_qc["technical_status"], "pass")


if __name__ == "__main__":
    unittest.main()
