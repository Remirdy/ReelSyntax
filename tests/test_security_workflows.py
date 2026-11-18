from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s@]+)@([0-9a-f]{40})\s*$", re.MULTILINE)


class SecurityWorkflowTests(unittest.TestCase):
    def test_security_workflow_defines_codeql_pip_audit_and_license_gate(self) -> None:
        sec_path = REPO_ROOT / ".github/workflows/security.yml"
        self.assertTrue(sec_path.is_file())
        text = sec_path.read_text(encoding="utf-8")
        self.assertIn("codeql:", text)
        self.assertIn("pip-audit:", text)
        self.assertIn("dependency-review:", text)
        self.assertIn("AGPL-3.0", text)
        self.assertIn("permissions:\n  contents: read", text)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                self.assertIsNotNone(
                    PINNED_USES_RE.match(line),
                    f"Action reference must be pinned to a 40-char commit SHA: {line}",
                )

    def test_dependabot_config_limits_open_prs_and_groups_updates(self) -> None:
        dep_text = (REPO_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("package-ecosystem: github-actions", dep_text)
        self.assertIn("package-ecosystem: pip", dep_text)
        self.assertIn("open-pull-requests-limit: 5", dep_text)
        self.assertIn("groups:", dep_text)


if __name__ == "__main__":
    unittest.main()
