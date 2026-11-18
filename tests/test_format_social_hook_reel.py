import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import load_index, read_json
from reelsyntax.formats import discover_formats, validate_format_directory
from reelsyntax.formats.installer import _audit_project_json_safety
from reelsyntax.make import make_video, step_project
from reelsyntax.media import executable
from reelsyntax.project import validate
from reelsyntax.quality import check
from reelsyntax.skills import file_digest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _ffmpeg_ready() -> bool:
    if importlib.util.find_spec("PIL") is None:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class SocialHookReelFormatTests(unittest.TestCase):
    def test_format_package_validates_and_bundled_mirror_matches(self) -> None:
        src_dir = REPO_ROOT / "formats/social-hook-reel"
        bundled_dir = REPO_ROOT / "reelsyntax/data/formats/social-hook-reel"
        validated = validate_format_directory(src_dir)
        self.assertTrue(validated["valid"])
        self.assertEqual(validated["id"], "social-hook-reel")

        catalog_ids = {row["id"] for row in load_index()["skills"]}
        for sid in validated["manifest"]["skills"]:
            self.assertIn(sid, catalog_ids)

        src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
        bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
        self.assertEqual(src_files, bundled_files)
        self.assertGreaterEqual(len(discover_formats()), 3)

    def test_skeleton_and_trilingual_examples_enforce_two_second_hook(self) -> None:
        base = REPO_ROOT / "formats/social-hook-reel"
        for rel in (
            "template/reel.skel.json",
            "examples/en/reel.json",
            "examples/tr/reel.json",
            "examples/de/reel.json",
        ):
            plan_path = base / rel
            _audit_project_json_safety(plan_path)
            doc = read_json(plan_path)
            meta = validate(doc)
            self.assertEqual(meta["scene_count"], 3)
            self.assertLessEqual(doc["scenes"][0]["duration_frames"], 60)

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for social-hook-reel live render")
    def test_make_social_hook_reel_caps_hook_and_passes_qc_in_en_tr_de(self) -> None:
        prompts = [
            ("en", "HOOK", "9s social hook reel: Stop guessing video render times"),
            ("tr", "DİKKAT", "9 saniye dikey kısa kanca videosu: Kurgu hızını ikiye katlayın"),
            ("de", "STOPP", "9 Sekunden vertikales Hook Reel: Nie wieder blind exportieren"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for lang_code, expected_kicker, prompt_text in prompts:
                with self.subTest(lang=lang_code):
                    pdir = root / f"hook-{lang_code}"
                    make_video(
                        prompt_text,
                        format_id="social-hook-reel",
                        out_dir=pdir,
                        provider_name="offline_rules",
                        video_lang=lang_code,
                        duration_sec=9,
                        yes=False,
                    )
                    for gated in ("idea", "script", "look", "frames", "pilot"):
                        step_project(pdir, gated, approve=True)
                    plan = read_json(pdir / "reel.json")
                    self.assertLessEqual(plan["scenes"][0]["duration_frames"], 60)
                    self.assertEqual(sum(s["duration_frames"] for s in plan["scenes"]), 9 * 30)
                    self.assertEqual(plan["scenes"][0]["params"].get("kicker"), expected_kicker)
                    self.assertEqual(plan["audio"]["cues"][0]["instrument"], "sub_impact")
                    self.assertEqual(check(pdir, profile="draft")["technical_status"], "pass")


if __name__ == "__main__":
    unittest.main()
