import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import atomic_json, read_json
from reelsyntax.media import executable
from reelsyntax.project import initialize
from reelsyntax.quality import (
    check,
    check_claims_sourced,
    check_mouth_sync,
    check_opening_hook_window,
    check_reading_speed,
    check_vertical_safe_zones,
)
from reelsyntax.render import apply_reduced_motion_scenes, render


def _render_ready() -> bool:
    if importlib.util.find_spec("PIL") is None:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class QcExtensionsTests(unittest.TestCase):
    def test_reading_speed_passes_comfortable_pace_and_flags_extreme_cps(self) -> None:
        good_plan = {
            "output": {"width": 1080, "height": 1920, "fps": "30/1"},
            "delivery": {"language": "eng"},
            "scenes": [
                {"id": "s1", "duration_frames": 60, "params": {"heading": "CLEAN", "subheading": "Easy to read line."}}
            ],
        }
        self.assertEqual(check_reading_speed(good_plan)["status"], "pass")

        fast_plan = {
            "output": {"width": 1080, "height": 1920, "fps": "30/1"},
            "delivery": {"language": "deu"},
            "scenes": [
                {
                    "id": "s1",
                    "duration_frames": 15,
                    "params": {
                        "heading": "EXTREM SCHNELLE ZEILE",
                        "subheading": "Unlesbare Informationsdichte innerhalb einer halben Sekunde.",
                    },
                }
            ],
        }
        self.assertEqual(check_reading_speed(fast_plan)["status"], "fail")

    def test_opening_hook_and_claims_sourced_rules(self) -> None:
        slow_hook = {
            "output": {"fps": "30/1"},
            "scenes": [{"id": "intro", "duration_frames": 120, "recipe": "kinetic-type", "params": {"heading": "WAIT"}}],
        }
        self.assertEqual(check_opening_hook_window(slow_hook, set())["status"], "not-applicable")
        self.assertEqual(check_opening_hook_window(slow_hook, {"opening-hook"})["status"], "fail")

        fast_hook = {
            "output": {"fps": "30/1"},
            "scenes": [{"id": "hook", "duration_frames": 54, "recipe": "prism-monolith", "params": {"kicker": "HOOK", "heading": "NOW"}}],
        }
        self.assertEqual(check_opening_hook_window(fast_hook, {"opening-hook"})["status"], "pass")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promo_plan = {
                "scenes": [
                    {"id": "claim", "duration_frames": 60, "params": {"heading": "98% FASTER", "subheading": "3x output"}}
                ]
            }
            self.assertEqual(check_claims_sourced(root, promo_plan, {"claims-must-be-sourced"})["status"], "fail")
            atomic_json(root / "sources.json", [{"claim": "98% FASTER", "source": "Local benchmark 2026-11"}])
            self.assertEqual(check_claims_sourced(root, promo_plan, {"claims-must-be-sourced"})["status"], "pass")

    def test_mouth_sync_and_reduced_motion_scene_transform(self) -> None:
        bad_mouth = {"scenes": [{"id": "talk", "duration_frames": 60, "params": {"mouth_envelope": [0.1] * 20}}]}
        self.assertEqual(check_mouth_sync(bad_mouth)["status"], "fail")
        ok_mouth = {"scenes": [{"id": "talk", "duration_frames": 60, "params": {"mouth_envelope": [0.1] * 60}}]}
        self.assertEqual(check_mouth_sync(ok_mouth)["status"], "pass")

        raw_scenes = [
            {"id": "a", "duration_frames": 30, "camera": {"preset": "dolly_zoom", "focal_mm": 35.0}},
            {"id": "b", "duration_frames": 30, "transition": {"type": "glitch", "duration_frames": 6}},
        ]
        calmed = apply_reduced_motion_scenes(raw_scenes)
        self.assertEqual(calmed[0]["camera"]["preset"], "locked")
        self.assertEqual(calmed[1]["transition"]["type"], "cut")

    def test_vertical_safe_zones_detects_edge_clipping_in_cached_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache_dir = root / ".reelsyntax/cache/key1"
            cache_dir.mkdir(parents=True)
            atomic_json(
                cache_dir / "manifest.json",
                {"layout_samples": [{"frame": 0, "text": [{"field": "heading", "bounds": [2.0, 10.0, 539.0, 955.0]}]}]},
            )
            plan = {"output": {"width": 540, "height": 960}}
            manifest = {"output_settings": {"width": 540, "height": 960}, "scenes": [{"id": "s1", "cache_key": "key1"}]}
            self.assertEqual(check_vertical_safe_zones(root, plan, manifest)["status"], "fail")

    @unittest.skipUnless(_render_ready(), "Pillow and FFmpeg required for reduced-motion live render")
    def test_live_reduced_motion_render_and_extended_qc_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "rm-film"
            initialize(proj)
            plan = read_json(proj / "reel.json")
            plan["scenes"][1]["transition"] = {"type": "glitch", "duration_frames": 6}
            atomic_json(proj / "reel.json", plan)

            state = render(proj, profile="draft", reduced_motion=True)
            self.assertTrue(state["reduced_motion"])
            qc_res = check(proj, profile="draft")
            self.assertEqual(qc_res["technical_status"], "pass")
            check_ids = {c["id"] for c in qc_res["checks"]}
            self.assertIn("reading_speed", check_ids)
            self.assertIn("vertical_safe_zones", check_ids)


if __name__ == "__main__":
    unittest.main()
