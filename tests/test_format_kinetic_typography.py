import importlib.util
from pathlib import Path
import tempfile
import unittest

from ReelSyntax_Skills.tools.registry import load_index, read_json
from reelsyntax.formats import discover_formats, get_format, validate_format_directory
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


class KineticTypographyFormatTests(unittest.TestCase):
    def test_format_package_validates_skills_exist_and_bundled_mirror_matches(self) -> None:
        src_dir = REPO_ROOT / "formats/kinetic-typography"
        bundled_dir = REPO_ROOT / "reelsyntax/data/formats/kinetic-typography"

        validated = validate_format_directory(src_dir)
        self.assertTrue(validated["valid"])
        self.assertEqual(validated["id"], "kinetic-typography")

        catalog_ids = {row["id"] for row in load_index()["skills"]}
        for sid in validated["manifest"]["skills"]:
            self.assertIn(sid, catalog_ids)

        src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
        bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
        self.assertEqual(src_files, bundled_files)

        discovered_ids = {fmt["id"] for fmt in discover_formats()}
        self.assertIn("kinetic-typography", discovered_ids)
        self.assertEqual(get_format("kinetic-typography")["version"], "1.0.0")

    def test_skeleton_and_trilingual_examples_pass_project_and_safety_validation(self) -> None:
        base = REPO_ROOT / "formats/kinetic-typography"
        for rel in (
            "template/reel.skel.json",
            "examples/en/reel.json",
            "examples/tr/reel.json",
            "examples/de/reel.json",
        ):
            plan_path = base / rel
            _audit_project_json_safety(plan_path)
            meta = validate(read_json(plan_path))
            self.assertEqual(meta["scene_count"], 3)

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for trilingual kinetic-typography render")
    def test_make_kinetic_typography_renders_and_passes_qc_in_en_tr_de(self) -> None:
        prompts = [
            ("en", "6s vertical kinetic quote: Ship clean deterministic frames every day"),
            ("tr", "6 saniye dikey kinetik tipografi alıntı: Her karede net ve sade ritim"),
            ("de", "6 Sekunden vertikales Typografie Zitat: Klare Struktur und ruhiger Fokus"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for lang_code, prompt_text in prompts:
                with self.subTest(lang=lang_code):
                    proj_dir = root / f"kt-{lang_code}"
                    make_video(
                        prompt_text,
                        format_id="kinetic-typography",
                        out_dir=proj_dir,
                        provider_name="offline_rules",
                        video_lang=lang_code,
                        duration_sec=6,
                        yes=False,
                    )
                    for gated in ("idea", "script", "look", "frames", "pilot"):
                        step_project(proj_dir, gated, approve=True)
                    plan = read_json(proj_dir / "reel.json")
                    self.assertEqual(plan["scenes"][0]["recipe"], "kinetic-type")
                    self.assertEqual(plan["scenes"][0]["params"].get("kicker"), "01")
                    self.assertTrue((proj_dir / "output/draft.mp4").is_file())
                    qc_res = check(proj_dir, profile="draft")
                    self.assertEqual(qc_res["technical_status"], "pass")


if __name__ == "__main__":
    unittest.main()
