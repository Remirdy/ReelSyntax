from fractions import Fraction
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
from reelsyntax.prompt.compiler import (
    FLASH_SAFE_TRANSITIONS,
    WAVE_FORMAT_KICKERS,
    compile_storyboard_to_project,
    music_grid_frames,
    quantize_durations_to_grid,
    reweight_durations,
)
from reelsyntax.prompt.intent import parse_intent
from reelsyntax.prompt.providers.offline_rules import OfflineRulesProvider
from reelsyntax.prompt.storyboard import build_storyboard
from reelsyntax.quality import check, check_claims_sourced, check_reading_speed
from reelsyntax.skills import file_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
HAS_PILLOW = importlib.util.find_spec("PIL") is not None

WAVE2_FORMATS = ("explainer-slides", "lyric-video", "music-visualizer", "channel-intro")

REQUIRED_SKILLS = {
    "explainer-slides": {
        "educational-explainer",
        "microlearning-chunking",
        "procedural-broll-planner",
        "rhythm-density-map",
        "reading-speed-audit",
        "claims-must-be-sourced",
        "contrast-audit",
        "frame-clock",
    },
    "lyric-video": {
        "lyric-video",
        "burned-in-caption-styling",
        "bar-grid-music-alignment",
        "contrast-audit",
        "frame-clock",
        "orphan-widow-line-balance",
    },
    "music-visualizer": {
        "music-visualizer",
        "bar-grid-music-alignment",
        "flash-safety",
        "shader-loop-art",
        "frame-clock",
        "contrast-audit",
    },
    "channel-intro": {
        "end-card",
        "kinetic-layout-choreography",
        "sfx-layering-transient-tail",
        "easing-design",
        "frame-clock",
        "contrast-audit",
    },
}

PROMPTS = {
    "explainer-slides": {
        "en": ("Explainer lesson: How render caching saves time", 15),
        "tr": ("Konu anlatımı: Önbellek kurguyu nasıl hızlandırır", 15),
        "de": ("Erklärvideo: Wie Caching den Schnitt beschleunigt", 15),
    },
    "lyric-video": {
        "en": ("Lyric video: Lanterns drift over quiet water", 8),
        "tr": ("Şarkı sözü videosu: Fenerler sessiz suda süzülür", 8),
        "de": ("Liedtext Video: Laternen treiben über stilles Wasser", 8),
    },
    "music-visualizer": {
        "en": ("Music visualizer: Midnight pulse in deep blue", 8),
        "tr": ("Müzik görselleştirici: Gece yarısı nabzı", 8),
        "de": ("Musikvisualisierung: Mitternachtspuls in Tiefblau", 8),
    },
    "channel-intro": {
        "en": ("Channel intro: Studio Notes", 5),
        "tr": ("Kanal girişi: Stüdyo Notları", 5),
        "de": ("Kanal Intro: Studio Notizen", 5),
    },
}


def _ffmpeg_ready() -> bool:
    if not HAS_PILLOW:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


def _compile(fid: str, lang: str, prompt: str, duration: int, aspect: str | None = None) -> dict:
    intent = parse_intent(prompt, video_lang=lang, format_id=fid, duration_sec=duration, aspect=aspect)
    storyboard = build_storyboard(intent, OfflineRulesProvider(), seed=42)
    return compile_storyboard_to_project(storyboard, intent, project_id=f"{fid}-{lang}", seed=42)


class Wave2FormatPackageTests(unittest.TestCase):
    def test_packages_validate_mirror_and_wire_catalog_skills(self) -> None:
        catalog_ids = {row["id"] for row in load_index()["skills"]}
        discovered = {f["id"] for f in discover_formats()}
        for fid in WAVE2_FORMATS:
            with self.subTest(format_id=fid):
                src_dir = REPO_ROOT / "formats" / fid
                bundled_dir = REPO_ROOT / "reelsyntax/data/formats" / fid
                validated = validate_format_directory(src_dir)
                self.assertTrue(validated["valid"])
                self.assertEqual(validated["id"], fid)
                self.assertIn(fid, discovered)
                self.assertEqual(get_format(fid)["version"], "1.0.0")
                skills = set(validated["manifest"]["skills"])
                self.assertLessEqual(REQUIRED_SKILLS[fid], skills)
                self.assertLessEqual(skills, catalog_ids)
                self.assertEqual(set(validated["manifest"]["aspect"]), {"16:9", "9:16", "1:1", "4:5"})
                src_files = {p.relative_to(src_dir).as_posix(): file_digest(p) for p in src_dir.rglob("*") if p.is_file()}
                bundled_files = {p.relative_to(bundled_dir).as_posix(): file_digest(p) for p in bundled_dir.rglob("*") if p.is_file()}
                self.assertEqual(src_files, bundled_files)
                for lang in ("en", "tr", "de"):
                    self.assertIn(f"examples/{lang}/reel.json", src_files)
                    self.assertIn(f"references/{lang}.json", src_files)

    def test_manifest_contracts(self) -> None:
        intro = get_format("channel-intro")
        self.assertEqual(intro["duration_sec"], {"min": 4, "max": 15})
        self.assertEqual(intro["aspect"][0], "16:9")
        self.assertEqual(get_format("explainer-slides")["aspect"][0], "16:9")
        self.assertIn("claims-must-be-sourced", get_format("explainer-slides")["qc_rules"])
        self.assertIn("flash-safety", get_format("music-visualizer")["qc_rules"])
        for fid in ("explainer-slides", "lyric-video", "channel-intro"):
            self.assertIn("reading-speed", get_format(fid)["qc_rules"])

    def test_format_docs_cover_rights_flash_and_claims_boundaries(self) -> None:
        lyric_doc = (REPO_ROOT / "formats/lyric-video/FORMAT.md").read_text(encoding="utf-8")
        self.assertIn("Lyrics rights boundary", lyric_doc)
        self.assertIn("original, brand-free demo verse", lyric_doc)
        visual_doc = (REPO_ROOT / "formats/music-visualizer/FORMAT.md").read_text(encoding="utf-8")
        self.assertIn("3 Hz", visual_doc)
        explainer_doc = (REPO_ROOT / "formats/explainer-slides/FORMAT.md").read_text(encoding="utf-8")
        self.assertIn("claims-must-be-sourced", explainer_doc)
        intro_doc = (REPO_ROOT / "formats/channel-intro/FORMAT.md").read_text(encoding="utf-8")
        self.assertIn("4–15 s", intro_doc)

    def test_examples_and_templates_are_safe_readable_and_grid_aligned(self) -> None:
        beat, bar = music_grid_frames("30/1")
        for fid in WAVE2_FORMATS:
            base = REPO_ROOT / "formats" / fid
            for rel in ("template/reel.skel.json", "examples/en/reel.json", "examples/tr/reel.json", "examples/de/reel.json"):
                with self.subTest(format_id=fid, plan=rel):
                    plan_path = base / rel
                    _audit_project_json_safety(plan_path)
                    doc = read_json(plan_path)
                    meta = validate(doc)
                    self.assertEqual(meta["scene_count"], 3)
                    self.assertEqual(check_reading_speed(doc)["status"], "pass")
                    self.assertEqual(check_claims_sourced(base, doc, {"claims-must-be-sourced"})["status"], "pass")
                    durations = [s["duration_frames"] for s in doc["scenes"]]
                    total = sum(durations)
                    for scene in doc["scenes"]:
                        self.assertLessEqual(len(scene["params"]["heading"]), 10)
                    if fid == "lyric-video":
                        self.assertTrue(all(d % beat == 0 for d in durations))
                    if fid == "music-visualizer":
                        self.assertTrue(all(d % bar == 0 for d in durations))
                        self.assertTrue(all(s.get("transition", {}).get("type", "cut") in FLASH_SAFE_TRANSITIONS for s in doc["scenes"]))
                        self.assertEqual([c["frame"] for c in doc["audio"]["cues"]], list(range(0, total, bar)))
                    if fid == "channel-intro":
                        self.assertTrue(4 * 30 <= total <= 15 * 30)
                        self.assertNotIn("subheading", doc["scenes"][0]["params"])
                        self.assertNotIn("subheading", doc["scenes"][-1]["params"])


class Wave2CompilerTests(unittest.TestCase):
    def test_grid_helpers_preserve_totals(self) -> None:
        self.assertEqual(music_grid_frames("30/1"), (15, 60))
        self.assertEqual(music_grid_frames("24/1"), (12, 48))
        for durations in ([120, 120, 120], [101, 137, 122], [80, 80, 80, 80], [13, 14, 15]):
            for unit in (15, 60):
                out = quantize_durations_to_grid(durations, unit)
                self.assertEqual(sum(out), sum(durations))
                self.assertEqual(len(out), len(durations))
                self.assertTrue(all(d >= 12 for d in out))
                if sum(durations) // unit >= len(durations):
                    self.assertTrue(all(d % unit == 0 for d in out[:-1]))
        self.assertEqual(sum(reweight_durations([150, 150, 150], [3, 5, 4])), 450)
        self.assertEqual(reweight_durations([150, 150], [1, 2, 3]), [150, 150])

    def test_keyword_routing_selects_wave2_formats(self) -> None:
        cases = {
            "A lesson explainer about compilers": "explainer-slides",
            "lyric video for my own song": "lyric-video",
            "Şarkı sözleri için sade video": "lyric-video",
            "spectrum visualizer for a synth loop": "music-visualizer",
            "Müzik görselleştirici siyahsız dalga": "music-visualizer",
            "Musikvisualisierung im Takt": "music-visualizer",
            "channel intro for a woodworking studio": "channel-intro",
            "Kanal girişi: Atölye Notları": "channel-intro",
            "Vorspann für meinen Kanal": "channel-intro",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(parse_intent(prompt).format_hint, expected)

    def test_constraints_and_all_aspects_compile_cleanly(self) -> None:
        for fid in WAVE2_FORMATS:
            for aspect in ("16:9", "9:16", "1:1", "4:5"):
                with self.subTest(format_id=fid, aspect=aspect):
                    prompt, duration = PROMPTS[fid]["en"]
                    plan = _compile(fid, "en", f"{prompt}, no text, no audio, locked camera", duration, aspect=aspect)
                    validate(plan)
                    self.assertFalse(plan["audio"]["enabled"])
                    self.assertEqual(plan["audio"]["cues"], [])
                    for scene in plan["scenes"]:
                        self.assertNotIn("heading", scene["params"])
                        self.assertNotIn("subheading", scene["params"])
                        self.assertNotIn("kicker", scene["params"])
                        self.assertNotIn("camera", scene)

    @unittest.skipUnless(HAS_PILLOW, "Pillow required for example frame draw bounds check")
    def test_examples_draw_within_safe_bounds(self) -> None:
        from reelsyntax import drawing

        for fid in WAVE2_FORMATS:
            for lang in ("en", "tr", "de"):
                doc = read_json(REPO_ROOT / "formats" / fid / "examples" / lang / "reel.json")
                out = {"width": doc["output"]["width"] // 2, "height": doc["output"]["height"] // 2, "fps": doc["output"]["fps"]}
                for scene in doc["scenes"]:
                    with self.subTest(format_id=fid, lang=lang, scene=scene["id"]):
                        img, bounds = drawing.draw(scene, scene["duration_frames"] // 2, out, doc["seed"], supersampling=1)
                        self.assertEqual(img.size, (out["width"], out["height"]))
                        for entry in bounds:
                            x0, y0, x1, y1 = entry["bounds"]
                            self.assertGreaterEqual(x0, out["width"] * 0.05)
                            self.assertLessEqual(x1, out["width"] * 0.52)
                            self.assertGreaterEqual(y0, out["height"] * 0.12)
                            self.assertLessEqual(y1, out["height"] * 0.82)

    def test_offline_compile_structure_in_en_tr_de(self) -> None:
        beat, bar = music_grid_frames("30/1")
        for fid, langs in PROMPTS.items():
            for lang, (prompt, duration) in langs.items():
                with self.subTest(format_id=fid, lang=lang):
                    plan = _compile(fid, lang, prompt, duration)
                    validate(plan)
                    scenes = plan["scenes"]
                    durations = [s["duration_frames"] for s in scenes]
                    total = sum(durations)
                    self.assertEqual(total, duration * 30)
                    self.assertEqual(check_reading_speed(plan)["status"], "pass")
                    kickers = [s["params"].get("kicker") for s in scenes]
                    table = WAVE_FORMAT_KICKERS[fid]
                    if fid == "explainer-slides":
                        self.assertEqual(kickers[0], f"{table['chapter'][lang]} 01/{len(scenes):02d}")
                        self.assertEqual(kickers[-1], table["recap"][lang])
                        self.assertEqual(scenes[0]["recipe"], "kinetic-type")
                        self.assertTrue(all(s["recipe"] == "assembly" for s in scenes[1:-1]))
                        self.assertGreater(durations[1], durations[0])
                    elif fid == "lyric-video":
                        self.assertEqual(kickers[0], f"{table['line'][lang]} 01")
                        self.assertTrue(all(d % beat == 0 for d in durations))
                        self.assertEqual([c["frame"] for c in plan["audio"]["cues"]], [sum(durations[:i]) for i in range(len(scenes))])
                    elif fid == "music-visualizer":
                        self.assertTrue(all(d % bar == 0 for d in durations))
                        self.assertEqual([s["recipe"] for s in scenes[:2]], ["signal", "rings"])
                        self.assertEqual(kickers[0], f"{table['bar'][lang]} 01")
                        self.assertTrue(all(s.get("transition", {}).get("type", "cut") in FLASH_SAFE_TRANSITIONS for s in scenes))
                        cue_frames = [c["frame"] for c in plan["audio"]["cues"]]
                        self.assertEqual(cue_frames, list(range(0, total, bar)))
                        fps = float(Fraction(plan["output"]["fps"]))
                        self.assertLess(fps / min(b - a for a, b in zip(cue_frames, cue_frames[1:])), 3.0)
                        self.assertLess(1.4 * fps / min(durations), 3.0)
                    elif fid == "channel-intro":
                        self.assertEqual(kickers, [table["open"][lang], table["body"][lang], table["close"][lang]])
                        self.assertEqual(scenes[0]["recipe"], "prism-monolith")
                        self.assertNotIn("subheading", scenes[0]["params"])
                        self.assertNotIn("subheading", scenes[-1]["params"])
                        self.assertEqual(plan["audio"]["cues"][0]["instrument"], "harmonic_pluck")
                        self.assertEqual(plan["audio"]["cues"][-1]["instrument"], "warm_pad")
                    silence = plan["quality"]["exceptions"]["silence"]
                    for cue in plan["audio"]["cues"]:
                        onset = cue["frame"]
                        self.assertFalse(any(a <= onset < b for a, b in silence))

    def test_channel_intro_minimum_and_maximum_lengths_stay_readable(self) -> None:
        for duration in (4, 15):
            for lang, (prompt, _) in PROMPTS["channel-intro"].items():
                with self.subTest(duration=duration, lang=lang):
                    plan = _compile("channel-intro", lang, prompt, duration, aspect="16:9")
                    self.assertEqual(sum(s["duration_frames"] for s in plan["scenes"]), duration * 30)
                    self.assertEqual(check_reading_speed(plan)["status"], "pass")

    def test_dry_run_make_budgets_each_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for fid in WAVE2_FORMATS:
                with self.subTest(format_id=fid):
                    prompt, duration = PROMPTS[fid]["en"]
                    res = make_video(
                        prompt,
                        format_id=fid,
                        out_dir=Path(tmp) / fid,
                        provider_name="offline_rules",
                        video_lang="en",
                        duration_sec=duration,
                        dry_run=True,
                    )
                    self.assertEqual(res["format_id"], fid)
                    self.assertEqual(res["budget"]["frames"], duration * 30)


@unittest.skipUnless(_ffmpeg_ready(), "Pillow, FFmpeg, and FFprobe required for wave 2 format live renders")
class Wave2LiveRenderTests(unittest.TestCase):
    def test_make_renders_and_passes_qc_in_en_tr_de(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fid, langs in PROMPTS.items():
                for lang, (prompt, duration) in langs.items():
                    with self.subTest(format_id=fid, lang=lang):
                        pdir = root / f"{fid}-{lang}"
                        make_video(
                            prompt,
                            format_id=fid,
                            out_dir=pdir,
                            provider_name="offline_rules",
                            video_lang=lang,
                            duration_sec=duration,
                            yes=False,
                        )
                        for gated in ("idea", "script", "look", "frames", "pilot"):
                            step_project(pdir, gated, approve=True)
                        plan = read_json(pdir / "reel.json")
                        self.assertEqual(sum(s["duration_frames"] for s in plan["scenes"]), duration * 30)
                        report = check(pdir, profile="draft")
                        failing = [c for c in report["checks"] if c["status"] not in {"pass", "not-applicable", "measured"} and c["id"] not in {"creative_review", "cue_sync", "glyph_integrity"}]
                        self.assertEqual(report["technical_status"], "pass", failing)


if __name__ == "__main__":
    unittest.main()
