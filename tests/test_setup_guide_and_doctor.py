import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from reelsyntax.cli import main as cli_main
from reelsyntax.media import DOCTOR_REMEDIATION_GUIDES, SETUP_GUIDE_BASE_URL, doctor, redact_diagnostic_payload

REPO_ROOT = Path(__file__).resolve().parents[1]


def _markdown_heading_slugs(md_text: str) -> set[str]:
    slugs: set[str] = set()
    for line in md_text.splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not m:
            continue
        raw = re.sub(r"`([^`]*)`", r"\1", m.group(1))
        slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
        if slug:
            slugs.add(slug)
    return slugs


class SetupGuideAndDoctorTests(unittest.TestCase):
    def test_getting_started_exists_in_mkdocs_and_has_all_remediation_anchors(self) -> None:
        guide_path = REPO_ROOT / "docs/getting-started.md"
        self.assertTrue(guide_path.is_file())
        guide_text = guide_path.read_text(encoding="utf-8")
        slugs = _markdown_heading_slugs(guide_text)

        for entry in DOCTOR_REMEDIATION_GUIDES.values():
            self.assertTrue(entry["doc_url"].startswith(SETUP_GUIDE_BASE_URL))
            anchor = entry["doc_url"].split("#", 1)[1]
            self.assertIn(anchor, slugs, f"Missing heading anchor #{anchor} in docs/getting-started.md")

        mkdocs_text = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("getting-started.md", mkdocs_text)

    def test_redact_diagnostic_payload_masks_paths_and_credentials(self) -> None:
        sample = {
            "ffmpeg_path": "/Users/alice/tools/ffmpeg",
            "linux_path": "/home/bob/.local/bin/ffprobe",
            "win_path": r"C:\Users\charlie\AppData\Local\Programs\Blender Foundation\blender.exe",
            "endpoint": "https://admin:supersecret@gateway.example.invalid/v1?api_key=sk-12345&model=fast",
        }
        redacted = redact_diagnostic_payload(sample, home_dir="/Users/alice")
        self.assertEqual(redacted["ffmpeg_path"], "<USER_HOME>/tools/ffmpeg")
        self.assertEqual(redacted["linux_path"], "<USER_HOME>/.local/bin/ffprobe")
        self.assertIn("<USER_HOME>", redacted["win_path"])
        self.assertNotIn("charlie", redacted["win_path"])
        self.assertNotIn("supersecret", redacted["endpoint"])
        self.assertNotIn("sk-12345", redacted["endpoint"])
        self.assertIn("<REDACTED>", redacted["endpoint"])

    def test_doctor_remediation_when_media_tools_unavailable(self) -> None:
        with patch("reelsyntax.media.executable", side_effect=ValueError("binary missing")):
            rep = doctor(probe_blender_headless=False, redact=False)
        self.assertFalse(rep["tools"]["ffmpeg"]["available"])
        self.assertIn("guide", rep["tools"]["ffmpeg"])
        self.assertFalse(rep["render_available"])
        remediated_tools = {item["tool"] for item in rep["remediation"]}
        self.assertIn("ffmpeg", remediated_tools)
        self.assertIn("ffprobe", remediated_tools)

    def test_cli_doctor_report_and_mocked_blender_headless_probe(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cli_main(["doctor", "--report", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())["result"]
        self.assertTrue(payload["redacted"])
        self.assertIn("providers", payload)
        self.assertEqual(payload["setup_guide"], SETUP_GUIDE_BASE_URL)
        self.assertNotIn(str(Path.home()), json.dumps(payload))

        with patch("reelsyntax.gateway.discover_blender_binary", return_value={"available": True, "binary": "/fake/blender", "version": "Blender 4.2.0"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "REELSYNTAX_BLENDER_OK 4.2.0\n"
                mock_run.return_value.stderr = ""
                rep = doctor(probe_blender_headless=True)
        self.assertEqual(rep["tools"]["blender"]["headless_probe"], "pass")
        self.assertEqual(rep["tools"]["blender"]["bpy_version"], "4.2.0")


if __name__ == "__main__":
    unittest.main()
