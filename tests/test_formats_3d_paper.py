import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ReelSyntax_Skills.tools.registry import atomic_json, load_index, read_json
from reelsyntax import art_recipes
from reelsyntax.blender_engine import (
    build_blender_scene_payload,
    probe_blender_scene_support,
    render_blender_scene,
)
from reelsyntax.formats import discover_formats, get_format, validate_format_directory
from reelsyntax.formats.installer import _audit_project_json_safety
from reelsyntax.gateway import discover_blender_binary
from reelsyntax.make import make_video, select_format_manifest, step_project
from reelsyntax.media import executable
from reelsyntax.project import validate
from reelsyntax.prompt import parse_intent
from reelsyntax.quality import check
from reelsyntax.render import render
from reelsyntax.skills import file_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
HAS_PILLOW = importlib.util.find_spec("PIL") is not None


def _ffmpeg_ready() -> bool:
    if not HAS_PILLOW:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class Formats3DAndPaperTests(unittest.TestCase):
    def test_format_packages_validate_skills_exist_and_bundled_mirrors_match(self) -> None:
        catalog_ids = {row["id"] for row in load_index()["skills"]}
        discovered = {fmt["id"]: fmt for fmt in discover_formats()}
        expected_meta = {
            "cinematic-3d": ("art", ("blender", "pillow", "ffmpeg"), ("16:9", "9:16", "1:1")),
            "stepped-clay-look": ("art", ("blender", "pillow", "ffmpeg"), ("16:9", "9:16", "1:1", "4:5")),
            "paper-cutout": ("art", ("pillow", "ffmpeg", "blender"), ("9:16", "1:1", "16:9", "4:5")),
        }
        for fid, (cat, engines, aspects) in expected_meta.items():
            with self.subTest(format_id=fid):
                src_dir = REPO_ROOT / "formats" / fid
                bundled_dir = REPO_ROOT / "reelsyntax/data/formats" / fid
                validated = validate_format_directory(src_dir)
                self.assertTrue(validated["valid"])
                self.assertEqual(validated["category"], cat)
                manifest = validated["manifest"]
                self.assertEqual(tuple(manifest["engines"]), engines)
                self.assertEqual(tuple(manifest["aspect"]), aspects)
                for sid in manifest["skills"]:
                    self.assertIn(sid, catalog_ids)
                src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
                bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
                self.assertEqual(src_files, bundled_files)
                self.assertIn(fid, discovered)
                self.assertEqual(get_format(fid)["id"], fid)

    def test_skeleton_and_trilingual_examples_pass_safety_and_validation(self) -> None:
        expected_recipes = {
            "cinematic-3d": "cinematic-3d",
            "stepped-clay-look": "stepped-clay",
            "paper-cutout": "paper-cutout",
        }
        for fid, recipe in expected_recipes.items():
            base = REPO_ROOT / "formats" / fid
            for rel in (
                "template/reel.skel.json",
                "examples/en/reel.json",
                "examples/tr/reel.json",
                "examples/de/reel.json",
            ):
                with self.subTest(format_id=fid, path=rel):
                    plan_path = base / rel
                    _audit_project_json_safety(plan_path)
                    doc = read_json(plan_path)
                    meta = validate(doc)
                    self.assertEqual(meta["scene_count"], 3)
                    self.assertEqual(doc["scenes"][0]["recipe"], recipe)

    def test_multilingual_prompt_routing_and_blender_probing(self) -> None:
        cases = [
            ("16:9 cinematic 3d monolith lighting study", "cinematic-3d", "16:9"),
            ("sinematik 3b monolit ışık çalışması 16:9", "cinematic-3d", "16:9"),
            ("stepped clay sculpture showcase", "stepped-clay-look", "9:16"),
            ("kademeli kil heykel sahnesi", "stepped-clay-look", "9:16"),
            ("gestufter Knetanimation Look", "stepped-clay-look", "9:16"),
            ("paper cutout layered 2.5d silhouettes", "paper-cutout", "9:16"),
            ("kağıt kesme katmanlı derinlik", "paper-cutout", "9:16"),
            ("Scherenschnitt Papierschnitt 2.5D", "paper-cutout", "9:16"),
        ]
        for prompt_text, expected_fmt, expected_aspect in cases:
            with self.subTest(prompt=prompt_text):
                intent = parse_intent(prompt_text)
                self.assertEqual(intent.format_hint, expected_fmt)
                selected = select_format_manifest(intent)
                self.assertEqual(selected["id"], expected_fmt)
                self.assertIn(expected_aspect, selected["aspect"])

        sample_scene = {
            "id": "clay",
            "duration_frames": 24,
            "recipe": "stepped-clay",
            "engine": "blender",
            "camera": {"preset": "orbit", "focal_mm": 52.0},
            "params": {"heading": "CLAY", "background": "#292421", "foreground": "#f4ede3", "accent": "#df7c52"},
        }
        with patch("reelsyntax.blender_engine.discover_blender_binary", return_value={"available": False, "binary": None, "version": None}):
            probe_off = probe_blender_scene_support(sample_scene)
            self.assertFalse(probe_off["blender_available"])
            self.assertTrue(probe_off["pillow_fallback_available"])
            self.assertEqual(probe_off["recommended_engine"], "pillow")
        with patch("reelsyntax.blender_engine.discover_blender_binary", return_value={"available": True, "binary": "/fake/blender", "version": "Blender 4.2.0"}):
            probe_on = probe_blender_scene_support(sample_scene)
            self.assertTrue(probe_on["blender_available"])
            self.assertTrue(probe_on["native_bpy_supported"])
            self.assertEqual(probe_on["recommended_engine"], "blender")

        payload = build_blender_scene_payload(
            sample_scene,
            {"width": 640, "height": 360, "fps": "24/1"},
            "draft",
            Path("/tmp/unused"),
            reduced_motion=True,
        )
        self.assertEqual(payload["pose_step"], 2)
        self.assertEqual(payload["dof_fstop"], 5.6)
        self.assertTrue(payload["reduced_motion"])
        self.assertEqual(payload["camera_preset"], "locked")

    def test_zero_pillow_offline_make_and_step_gates(self) -> None:
        code = "\n".join([
            "import json, sys, tempfile",
            "from pathlib import Path",
            "sys.modules['PIL'] = None",
            "from reelsyntax.make import make_video, step_project",
            "from reelsyntax.blender_engine import probe_blender_scene_support",
            "root = Path(tempfile.mkdtemp())",
            "out = {}",
            "for fid in ('cinematic-3d', 'stepped-clay-look', 'paper-cutout'):",
            "    dry = make_video(f'6s {fid} demo', format_id=fid, provider_name='offline_rules', dry_run=True)",
            "    pdir = root / fid",
            "    make_video(f'6s {fid} demo', format_id=fid, out_dir=pdir, provider_name='offline_rules', duration_sec=6, yes=False)",
            "    step_project(pdir, 'idea', approve=True)",
            "    st = step_project(pdir, 'script', approve=True)",
            "    out[fid] = {'dry_scenes': dry['plan_summary']['scene_count'], 'gate': st['pending_gate']}",
            "out['probe'] = probe_blender_scene_support({'recipe': 'paper-cutout'})['pillow_fallback_available']",
            "print(json.dumps(out))",
        ])
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        res = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(res["probe"])
        for fid in ("cinematic-3d", "stepped-clay-look", "paper-cutout"):
            self.assertGreaterEqual(res[fid]["dry_scenes"], 2)
            self.assertEqual(res[fid]["gate"], "look")

    @unittest.skipUnless(HAS_PILLOW, "Pillow required for stepped-clay and paper-cutout frame assertions")
    def test_stepped_clay_quantization_and_paper_cutout_reduced_motion(self) -> None:
        out = {"width": 480, "height": 270, "fps": "30/1"}
        clay_scene = {
            "id": "clay",
            "duration_frames": 30,
            "recipe": "stepped-clay",
            "engine": "pillow",
            "camera": {"preset": "locked", "focal_mm": 52.0},
            "params": {"background": "#292421", "foreground": "#f4ede3", "accent": "#df7c52"},
        }
        f0 = art_recipes._draw_stepped_clay(clay_scene, 0, 480, 270, 30.0, 42, "#292421", "#f4ede3", "#df7c52", "agx", 0.0, False)
        f2 = art_recipes._draw_stepped_clay(clay_scene, 2, 480, 270, 30.0, 42, "#292421", "#f4ede3", "#df7c52", "agx", 0.0, False)
        f3 = art_recipes._draw_stepped_clay(clay_scene, 3, 480, 270, 30.0, 42, "#292421", "#f4ede3", "#df7c52", "agx", 0.0, False)
        self.assertEqual(f0.tobytes(), f2.tobytes())
        self.assertNotEqual(f0.tobytes(), f3.tobytes())

        paper_scene = {
            "id": "paper",
            "duration_frames": 60,
            "recipe": "paper-cutout",
            "engine": "pillow",
            "camera": {"preset": "dolly_in", "focal_mm": 50.0},
            "params": {"background": "#eee6d8", "foreground": "#22252a", "accent": "#b84f32"},
        }
        p10 = art_recipes._draw_paper_cutout(paper_scene, 10, 480, 270, 42, "#eee6d8", "#22252a", "#b84f32", False)
        p25 = art_recipes._draw_paper_cutout(paper_scene, 25, 480, 270, 42, "#eee6d8", "#22252a", "#b84f32", False)
        self.assertNotEqual(p10.tobytes(), p25.tobytes())

        r20 = art_recipes._draw_paper_cutout(paper_scene, 20, 480, 270, 42, "#eee6d8", "#22252a", "#b84f32", True)
        r40 = art_recipes._draw_paper_cutout(paper_scene, 40, 480, 270, 42, "#eee6d8", "#22252a", "#b84f32", True)
        self.assertEqual(r20.tobytes(), r40.tobytes())
        full_img, _ = art_recipes.draw_art_scene(paper_scene, 20, out, 42, reduced_motion=True)
        self.assertEqual(full_img.size, (480, 270))

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for live render and QC verification")
    def test_make_render_and_qc_pass_in_en_tr_de_and_reduced_motion(self) -> None:
        cases = [
            ("cinematic-3d", "en", "16:9", "6s 16:9 cinematic 3d monolith lighting study"),
            ("cinematic-3d", "tr", "16:9", "6 saniye 16:9 sinematik 3b monolit ışık sahnesi"),
            ("cinematic-3d", "de", "16:9", "6 Sekunden 16:9 kinoreife 3D Monolith Lichtstudie"),
            ("stepped-clay-look", "en", "9:16", "6s 9:16 stepped clay sculpture showcase"),
            ("stepped-clay-look", "tr", "9:16", "6 saniye 9:16 kademeli kil heykel sahnesi"),
            ("stepped-clay-look", "de", "9:16", "6 Sekunden 9:16 Knetanimation Skulptur"),
            ("paper-cutout", "en", "9:16", "6s 9:16 paper cutout layered shadow story"),
            ("paper-cutout", "tr", "9:16", "6 saniye 9:16 kağıt kesme katmanlı hikaye"),
            ("paper-cutout", "de", "9:16", "6 Sekunden 9:16 Scherenschnitt Ebenen"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fid, lang_code, aspect, prompt_text in cases:
                with self.subTest(format_id=fid, lang=lang_code):
                    pdir = root / f"{fid}-{lang_code}"
                    make_video(
                        prompt_text,
                        format_id=fid,
                        out_dir=pdir,
                        provider_name="offline_rules",
                        video_lang=lang_code,
                        aspect=aspect,
                        duration_sec=6,
                        yes=False,
                    )
                    for gated in ("idea", "script", "look", "frames", "pilot"):
                        step_project(pdir, gated, approve=True)
                    qc_res = check(pdir, profile="draft")
                    self.assertEqual(qc_res["technical_status"], "pass", qc_res)

            for rm_fid in ("paper-cutout", "stepped-clay-look"):
                rm_dir = root / f"rm-{rm_fid}"
                make_video(
                    f"6s 9:16 {rm_fid} calm study",
                    format_id=rm_fid,
                    out_dir=rm_dir,
                    provider_name="offline_rules",
                    duration_sec=6,
                    yes=False,
                )
                for gated in ("idea", "script", "look"):
                    step_project(rm_dir, gated, approve=True)
                render(rm_dir, profile="draft", reduced_motion=True)
                self.assertEqual(check(rm_dir, profile="draft")["technical_status"], "pass")

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for Blender fallback QC test")
    def test_blender_scenes_fallback_cleanly_to_pillow_and_pass_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {
                "schema_version": 1,
                "id": "blender-fallback-art",
                "seed": 7,
                "output": {"width": 640, "height": 360, "fps": "24/1"},
                "scenes": [
                    {
                        "id": "s1",
                        "duration_frames": 24,
                        "recipe": "cinematic-3d",
                        "engine": "blender",
                        "camera": {"preset": "orbit", "focal_mm": 50.0},
                        "params": {"kicker": "01", "heading": "STUDIO", "background": "#232834", "foreground": "#f4f6f9", "accent": "#5eb8c4"},
                    },
                    {
                        "id": "s2",
                        "duration_frames": 24,
                        "recipe": "stepped-clay",
                        "engine": "blender",
                        "camera": {"preset": "dolly_in", "focal_mm": 52.0},
                        "params": {"kicker": "02", "heading": "CLAY", "background": "#292421", "foreground": "#f4ede3", "accent": "#df7c52"},
                    },
                    {
                        "id": "s3",
                        "duration_frames": 24,
                        "recipe": "paper-cutout",
                        "engine": "blender",
                        "camera": {"preset": "dolly_in", "focal_mm": 50.0},
                        "params": {"kicker": "03", "heading": "PAPER", "background": "#eee6d8", "foreground": "#22252a", "accent": "#b84f32"},
                    },
                ],
                "audio": {"enabled": False, "gain_db": -14, "cues": []},
                "quality": {"exceptions": {"freeze": [[0, 72]]}},
            }
            atomic_json(root / "reel.json", plan)
            with patch("reelsyntax.gateway.discover_blender_binary", return_value={"available": False, "binary": None, "version": None}):
                state = render(root, profile="draft", fallback_engine="pillow")
            self.assertEqual(len(state["fallbacks_used"]), 3)
            self.assertEqual(check(root, profile="draft")["technical_status"], "pass")

            if discover_blender_binary()["available"]:
                with tempfile.TemporaryDirectory() as bl_tmp:
                    one_scene = {
                        "id": "clay-live",
                        "duration_frames": 2,
                        "recipe": "stepped-clay",
                        "engine": "blender",
                        "camera": {"preset": "locked", "focal_mm": 52.0},
                        "params": {"kicker": "01", "heading": "CLAY", "background": "#292421", "foreground": "#f4ede3", "accent": "#df7c52"},
                    }
                    ev, lay = render_blender_scene(one_scene, {"width": 320, "height": 180, "fps": "24/1"}, "draft", Path(bl_tmp), timeout=120)
                    self.assertIn("Blender", ev["blender_version"])
                    self.assertTrue((Path(bl_tmp) / "000001.png").is_file())
                    self.assertGreaterEqual(len(lay), 2)


if __name__ == "__main__":
    unittest.main()
