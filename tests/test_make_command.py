import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ReelSyntax_Skills.tools.registry import read_json
from reelsyntax.cli import main as cli_main
from reelsyntax.completion import generate_completion
from reelsyntax.formats import scaffold_format
from reelsyntax.make import make_video, resume_format_project, revise_project, step_project
from reelsyntax.media import executable
from reelsyntax.render import check_locks, lock


def _ffmpeg_ready() -> bool:
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class MakeCommandTests(unittest.TestCase):
    def test_dry_run_estimates_budget_without_creating_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            non_existent_out = Path(tmp) / "should-not-exist"
            res = make_video(
                "Create a 12s vertical kinetic reel about deterministic builds",
                out_dir=non_existent_out,
                provider_name="offline_rules",
                seed=77,
                dry_run=True,
            )
            self.assertTrue(res["dry_run"])
            self.assertFalse(non_existent_out.exists())
            self.assertFalse(res["attribution"])
            self.assertGreaterEqual(res["budget"]["scenes"], 2)
            self.assertEqual(res["budget"]["frames"], 12 * 30)
            self.assertEqual(res["budget"]["production_resolution"], [1080, 1920])
            self.assertIn("idea", res["budget"]["approval_gates"])

    def test_cli_dry_run_and_multilingual_prompt_provenance(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cli_main([
                "make",
                "10 saniyelik dikey tipografi videosu: Yerel kurgu hızı",
                "--provider",
                "offline_rules",
                "--dry-run",
                "--attribution",
                "--json",
            ])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())["result"]
        self.assertTrue(payload["dry_run"])
        self.assertTrue(payload["attribution"])
        self.assertEqual(payload["languages"]["video_lang"], "tr")

    def test_make_gates_step_approve_edit_back_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fmt_root = root / "formats"
            scaffold_format("custom-kinetic", category="social", base_dir=fmt_root)
            proj_dir = root / "proj"

            started = make_video(
                "12s vertical reel on clean architecture",
                format_id="custom-kinetic",
                out_dir=proj_dir,
                provider_name="offline_rules",
                seed=19,
                extra_format_roots=(fmt_root,),
                dry_run_render=True,
            )
            self.assertEqual(started["status"], "awaiting_approval")
            self.assertEqual(started["pending_gate"], "idea")

            prov = read_json(proj_dir / "prompt.json")
            self.assertEqual(prov["format_id"], "custom-kinetic")
            self.assertEqual(prov["provider"], "offline_rules")
            self.assertFalse(prov["attribution"])

            with self.assertRaisesRegex(ValueError, "Current gate is 'idea'"):
                step_project(
                    proj_dir,
                    "script",
                    approve=True,
                    extra_format_roots=(fmt_root,),
                    dry_run_render=True,
                )

            after_idea = step_project(
                proj_dir,
                "idea",
                approve=True,
                extra_format_roots=(fmt_root,),
                dry_run_render=True,
            )
            self.assertEqual(after_idea["pending_gate"], "script")
            self.assertTrue((proj_dir / "reel.json").is_file())

            edited = step_project(
                proj_dir,
                "script",
                edit="emphasize cache determinism",
                extra_format_roots=(fmt_root,),
                dry_run_render=True,
            )
            self.assertEqual(edited["pending_gate"], "script")
            prov_after_edit = read_json(proj_dir / "prompt.json")
            self.assertEqual(len(prov_after_edit["revisions"]), 1)
            self.assertEqual(prov_after_edit["revisions"][0]["kind"], "step_edit")

            backed = step_project(
                proj_dir,
                "script",
                back=True,
                extra_format_roots=(fmt_root,),
                dry_run_render=True,
            )
            self.assertEqual(backed["pending_gate"], "idea")

            (proj_dir / ".reelsyntax").mkdir(parents=True, exist_ok=True)
            (proj_dir / ".reelsyntax/render.lock").write_text("stale", encoding="utf-8")
            completed = resume_format_project(
                proj_dir,
                yes=True,
                extra_format_roots=(fmt_root,),
                dry_run_render=True,
            )
            self.assertEqual(completed["status"], "completed")
            self.assertFalse((proj_dir / ".reelsyntax/render.lock").exists())

    def test_revise_creates_checkpoint_preserves_locks_and_updates_only_targeted_scene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "revise-proj"
            make_video(
                "12s vertical reel with 3 beats on reproducible video pipelines",
                out_dir=proj_dir,
                provider_name="offline_rules",
                yes=True,
                dry_run_render=True,
            )
            before_plan = read_json(proj_dir / "reel.json")
            self.assertGreaterEqual(len(before_plan["scenes"]), 2)
            first_id = before_plan["scenes"][0]["id"]
            second_id = before_plan["scenes"][1]["id"]

            lock(proj_dir, [first_id])

            with self.assertRaisesRegex(ValueError, "locked"):
                revise_project(proj_dir, "heading: Illegal Change", scene_id=first_id)

            rev = revise_project(proj_dir, "scene 2 heading: Cache Hits")
            self.assertEqual(rev["changed_scenes"], [second_id])
            self.assertIn(first_id, rev["preserved_scenes"])
            self.assertTrue((proj_dir / f".reelsyntax/checkpoints/{rev['checkpoint']}.json").is_file())

            after_plan = read_json(proj_dir / "reel.json")
            self.assertEqual(before_plan["scenes"][0], after_plan["scenes"][0])
            self.assertEqual(after_plan["scenes"][1]["params"]["heading"], "Cache Hits")
            check_locks(proj_dir, after_plan)

            prov = read_json(proj_dir / "prompt.json")
            self.assertTrue(any(r["kind"] == "revise" for r in prov["revisions"]))

    @unittest.skipUnless(_ffmpeg_ready(), "FFmpeg and FFprobe required for end-to-end make render")
    def test_make_yes_and_revise_render_selective_cache_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fmt_root = root / "formats"
            scaffold_format("fast-draft-reel", category="social", base_dir=fmt_root)
            fjson_path = fmt_root / "fast-draft-reel/format.json"
            fjson = read_json(fjson_path)
            fjson["steps"] = [s for s in fjson["steps"] if s.get("profile") != "hero"]
            (fjson_path).write_text(json.dumps(fjson, indent=2) + "\n", encoding="utf-8")

            proj_dir = root / "live-make"
            res = make_video(
                "4s vertical reel on fast local motion graphics",
                format_id="fast-draft-reel",
                out_dir=proj_dir,
                provider_name="offline_rules",
                duration_sec=4,
                yes=True,
                extra_format_roots=(fmt_root,),
            )
            self.assertEqual(res["status"], "completed")
            self.assertTrue((proj_dir / "output/draft.mp4").is_file())
            self.assertEqual(res["completed_steps"]["qc"]["technical_status"], "pass")

            plan = read_json(proj_dir / "reel.json")
            self.assertGreaterEqual(len(plan["scenes"]), 2)
            first_sid = plan["scenes"][0]["id"]
            second_sid = plan["scenes"][1]["id"]

            rev = revise_project(
                proj_dir,
                f"{second_sid} heading: Fast Rebuild",
                scene_id=second_sid,
                render_after=True,
                profile="draft",
            )
            self.assertIn(first_sid, rev["render"]["cache_hits"])
            self.assertEqual(rev["render"]["rendered_scenes"], [second_sid])
            shutil.rmtree(proj_dir, ignore_errors=True)

    def test_shell_completion_scripts_for_all_shells(self) -> None:
        for shell in ("bash", "zsh", "fish", "powershell"):
            script = generate_completion(shell)
            self.assertIn("make", script)
            self.assertIn("revise", script)
            self.assertIn("formats", script)
            self.assertIn("dry-run", script)

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cli_main(["completion", "zsh"])
        self.assertEqual(rc, 0)
        self.assertIn("compdef _reelsyntax reelsyntax", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
