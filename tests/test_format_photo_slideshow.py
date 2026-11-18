import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import load_index, read_json
from reelsyntax.assets import audit_project_licenses
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


class PhotoSlideshowFormatTests(unittest.TestCase):
    def test_format_package_validates_and_bundled_mirror_matches(self) -> None:
        src_dir = REPO_ROOT / "formats/photo-slideshow"
        bundled_dir = REPO_ROOT / "reelsyntax/data/formats/photo-slideshow"
        validated = validate_format_directory(src_dir)
        self.assertTrue(validated["valid"])
        self.assertEqual(validated["category"], "personal")

        catalog_ids = {row["id"] for row in load_index()["skills"]}
        for sid in validated["manifest"]["skills"]:
            self.assertIn(sid, catalog_ids)

        src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
        bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
        self.assertEqual(src_files, bundled_files)
        self.assertIn("photo-slideshow", {f["id"] for f in discover_formats()})

    def test_skeleton_and_trilingual_examples_validate(self) -> None:
        base = REPO_ROOT / "formats/photo-slideshow"
        for rel in (
            "template/reel.skel.json",
            "examples/en/reel.json",
            "examples/tr/reel.json",
            "examples/de/reel.json",
        ):
            plan_path = base / rel
            _audit_project_json_safety(plan_path)
            self.assertEqual(validate(read_json(plan_path))["scene_count"], 3)

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for photo-slideshow live render")
    def test_starter_plates_and_custom_user_photo_render_and_pass_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            for lang_code, prompt_text in (
                ("en", "6s photo slideshow of coastal autumn mornings"),
                ("tr", "6 saniye fotoğraf slayt gösterisi sahil sabahı"),
                ("de", "6 Sekunden Foto Diashow Herbst am Meer"),
            ):
                with self.subTest(mode="starter", lang=lang_code):
                    pdir = root / f"slides-{lang_code}"
                    make_video(
                        prompt_text,
                        format_id="photo-slideshow",
                        out_dir=pdir,
                        provider_name="offline_rules",
                        video_lang=lang_code,
                        duration_sec=6,
                        yes=False,
                    )
                    for gated in ("idea", "script", "look", "frames", "pilot"):
                        step_project(pdir, gated, approve=True)
                    plan = read_json(pdir / "reel.json")
                    self.assertTrue(any(s["recipe"] == "layer-stack" for s in plan["scenes"]))
                    lic_audit = audit_project_licenses(pdir)
                    self.assertTrue(lic_audit["ok"])
                    qc_res = check(pdir, profile="draft")
                    self.assertEqual(qc_res["technical_status"], "pass")

            from PIL import Image

            custom_dir = root / "custom-user-slides"
            (custom_dir / "assets").mkdir(parents=True, exist_ok=True)
            user_img = Image.new("RGB", (900, 900), "#4b6b88")
            user_img.save(custom_dir / "assets/harbor.png")

            make_video(
                "6s photo slideshow from harbor trip",
                format_id="photo-slideshow",
                out_dir=custom_dir,
                provider_name="offline_rules",
                duration_sec=6,
                yes=False,
            )
            for gated in ("idea", "script", "look", "frames", "pilot"):
                step_project(custom_dir, gated, approve=True)
            custom_plan = read_json(custom_dir / "reel.json")
            layer_scenes = [s for s in custom_plan["scenes"] if s["recipe"] == "layer-stack"]
            self.assertEqual(layer_scenes[0]["params"]["layers"][0]["source"], "assets/harbor.png")
            self.assertTrue(audit_project_licenses(custom_dir)["ok"])
            self.assertEqual(check(custom_dir, profile="draft")["technical_status"], "pass")


if __name__ == "__main__":
    unittest.main()
