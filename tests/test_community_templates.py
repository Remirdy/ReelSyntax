from pathlib import Path
import unittest

from tools.sync_labels import load_labels, sync_labels

REPO_ROOT = Path(__file__).resolve().parents[1]


class CommunityTemplateTests(unittest.TestCase):
    def test_issue_templates_and_contact_routing_exist(self) -> None:
        issue_dir = REPO_ROOT / ".github/ISSUE_TEMPLATE"
        for name in ("bug.yml", "feature.yml", "skill.yml", "format.yml", "language.yml", "config.yml"):
            path = issue_dir / name
            self.assertTrue(path.is_file(), f"Missing {name}")
            content = path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 80)

        cfg = (issue_dir / "config.yml").read_text(encoding="utf-8")
        self.assertIn("blank_issues_enabled: false", cfg)
        self.assertIn("/discussions", cfg)
        self.assertIn("/security/advisories/new", cfg)

    def test_labels_catalog_and_dry_run_sync(self) -> None:
        labels = load_labels()
        names = {item["name"] for item in labels}
        for expected in ("good first issue", "help wanted", "format", "i18n", "skills", "render", "qc", "security"):
            self.assertIn(expected, names)
        preview = sync_labels(apply=False)
        self.assertEqual(preview["mode"], "dry-run")
        self.assertEqual(preview["count"], len(labels))


if __name__ == "__main__":
    unittest.main()
