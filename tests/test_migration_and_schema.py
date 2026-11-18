import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reelsyntax.migration import migrate_plan, migrate_project, normalize_fps_value
from reelsyntax.project import initialize, load
from reelsyntax.schema import (
    CONFIG_V1_SCHEMA_URL,
    REEL_V1_SCHEMA_URL,
    config_schema,
    project_schema,
    schema_for,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class SchemaAndMigrationTests(unittest.TestCase):
    def test_published_versioned_schemas_match_generators(self) -> None:
        reel = project_schema()
        cfg = config_schema()
        self.assertEqual(reel["$id"], REEL_V1_SCHEMA_URL)
        self.assertEqual(cfg["$id"], CONFIG_V1_SCHEMA_URL)
        for rel in ("docs/reel.schema.json", "docs/schemas/reel.v1.schema.json"):
            self.assertEqual(json.loads((REPO_ROOT / rel).read_text(encoding="utf-8")), reel)
        for rel in ("docs/config.schema.json", "docs/schemas/config.v1.schema.json"):
            self.assertEqual(json.loads((REPO_ROOT / rel).read_text(encoding="utf-8")), cfg)
        with self.assertRaisesRegex(ValueError, "Unsupported schema version"):
            schema_for("reel", 2)

    def test_fps_normalization_handles_integers_ntsc_floats_and_rationals(self) -> None:
        self.assertEqual(normalize_fps_value(24), "24/1")
        self.assertEqual(normalize_fps_value("30"), "30/1")
        self.assertEqual(normalize_fps_value(29.97), "30000/1001")
        self.assertEqual(normalize_fps_value("23.976"), "24000/1001")
        self.assertEqual(normalize_fps_value("59.94"), "60000/1001")
        self.assertEqual(normalize_fps_value("24/1"), "24/1")
        with self.assertRaises(ValueError):
            normalize_fps_value("invalid")

    def test_migrate_legacy_project_dry_run_backup_and_idempotency(self) -> None:
        legacy_plan = {
            "id": "legacy-cut",
            "seed": 7,
            "output": {"width": 1280, "height": 720, "fps": 29.97},
            "scenes": [
                {
                    "id": "intro",
                    "duration_sec": 2.0,
                    "recipe": "title",
                    "engine": "pillow",
                    "params": {"title": "OPEN", "subtitle": "Legacy fields"},
                }
            ],
            "audio": {"enabled": True, "volume_db": -16},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reel_file = root / "reel.json"
            original_raw = json.dumps(legacy_plan, indent=2) + "\n"
            reel_file.write_text(original_raw, encoding="utf-8")

            preview = migrate_project(root, dry_run=True)
            self.assertTrue(preview["changed"])
            self.assertTrue(preview["dry_run"])
            self.assertEqual(preview["from_version"], 0)
            self.assertEqual(preview["to_version"], 1)
            self.assertEqual(reel_file.read_text(encoding="utf-8"), original_raw)
            self.assertFalse((root / ".reelsyntax/migrations").exists())

            applied = migrate_project(root, dry_run=False)
            self.assertTrue(applied["changed"])
            self.assertIsNotNone(applied["backup"])
            self.assertTrue((root / applied["backup"]).is_file())
            self.assertEqual((root / applied["backup"]).read_text(encoding="utf-8"), original_raw)
            self.assertTrue((root / "reel.schema.json").is_file())

            _, loaded_plan, meta = load(root)
            self.assertEqual(loaded_plan["schema_version"], 1)
            self.assertEqual(loaded_plan["output"]["fps"], "30000/1001")
            self.assertEqual(loaded_plan["scenes"][0]["duration_frames"], 60)
            self.assertEqual(loaded_plan["scenes"][0]["params"]["heading"], "OPEN")
            self.assertEqual(loaded_plan["audio"]["gain_db"], -16)
            self.assertEqual(meta["frames"], 60)

            second = migrate_project(root)
            self.assertFalse(second["changed"])
            self.assertIsNone(second["backup"])

    def test_migrate_rejects_future_schema_version_and_cli_round_trip(self) -> None:
        with self.assertRaisesRegex(ValueError, "supports up to version 1"):
            migrate_plan(
                {
                    "schema_version": 99,
                    "id": "future",
                    "seed": 1,
                    "output": {"width": 960, "height": 540, "fps": "30/1"},
                    "scenes": [],
                }
            )
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "fresh"
            initialize(proj)
            res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "migrate", str(proj), "--remote-schema", "--json"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)["result"]
            self.assertTrue(payload["changed"])
            updated = json.loads((proj / "reel.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["$schema"], REEL_V1_SCHEMA_URL)


if __name__ == "__main__":
    unittest.main()
