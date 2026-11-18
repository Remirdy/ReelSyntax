import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.release_prepare import (
    extract_changelog_section,
    is_prerelease_version,
    stamp_server_json,
    verify_release_metadata,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleasePipelineTests(unittest.TestCase):
    def test_repository_release_metadata_is_synchronized(self) -> None:
        report = verify_release_metadata(REPO_ROOT, tag="v0.1.0")
        self.assertEqual(report["version"], "0.1.0")
        self.assertFalse(report["prerelease"])
        self.assertGreater(int(report["notes_length"]), 50)
        with self.assertRaisesRegex(ValueError, "does not match package version"):
            verify_release_metadata(REPO_ROOT, tag="v9.9.9")

    def test_prerelease_detection_and_changelog_extraction(self) -> None:
        self.assertFalse(is_prerelease_version("v0.1.0"))
        self.assertFalse(is_prerelease_version("1.2.3"))
        self.assertTrue(is_prerelease_version("v0.2.0-rc.1"))
        self.assertTrue(is_prerelease_version("0.2.0-beta.2"))
        self.assertTrue(is_prerelease_version("v1.0.0rc1"))
        with self.assertRaises(ValueError):
            is_prerelease_version("not-a-semver")

        sample = "# Changelog\n\n## [Unreleased]\n\n- Next\n\n## [0.2.0] — 2026-12-01\n\n### Added\n\n- Feature A\n\n## [0.1.0] — 2026-11-18\n\n- Initial\n"
        notes = extract_changelog_section(sample, "v0.2.0")
        self.assertIn("- Feature A", notes)
        self.assertNotIn("Initial", notes)

    def test_stamp_server_json_replaces_mcpb_sha256_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mcpb = Path(tmp) / "reelsyntax.mcpb"
            payload = b"deterministic-mcpb-archive-bytes"
            mcpb.write_bytes(payload)
            out_json = Path(tmp) / "server.stamped.json"
            result = stamp_server_json(mcpb, REPO_ROOT / "server.json", out_json)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(result["fileSha256"], expected)
            stamped = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(stamped["packages"][0]["fileSha256"], expected)


if __name__ == "__main__":
    unittest.main()
