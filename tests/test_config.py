import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reelsyntax.config import (
    config_context,
    load_config,
    render_starter_toml,
    user_config_path,
    validate_config_data,
    write_starter_config,
)
from reelsyntax.media import executable
from reelsyntax.schema import config_schema

REPO_ROOT = Path(__file__).resolve().parents[1]


class ConfigTomlTests(unittest.TestCase):
    def test_default_config_values_and_starter_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            u_cfg = Path(tmp) / "user.toml"
            cfg = load_config(environ={"REELSYNTAX_USER_CONFIG": str(u_cfg)}, cwd=Path(tmp))
            self.assertEqual(cfg.config_version, 1)
            self.assertEqual(cfg.general.ui_lang, "auto")
            self.assertEqual(cfg.general.video_lang, "auto")
            self.assertFalse(cfg.general.allow_network)
            self.assertFalse(cfg.general.attribution)
            self.assertEqual(cfg.provider.name, "offline_rules")
            self.assertEqual(cfg.provider.max_repairs, 3)
            self.assertEqual(cfg.render.default_profile, "draft")
            self.assertEqual(cfg.sources, ())

            written = write_starter_config(Path(tmp))
            self.assertTrue(written.is_file())
            self.assertNotIn("#", render_starter_toml())
            loaded = load_config(config_file=written, environ={"REELSYNTAX_USER_CONFIG": str(u_cfg)}, cwd=Path(tmp))
            self.assertEqual(loaded.sources, (str(written.resolve()),))
            with self.assertRaisesRegex(ValueError, "already exists"):
                write_starter_config(Path(tmp))
            overwritten = write_starter_config(Path(tmp), force=True)
            self.assertEqual(overwritten, written)

    def test_precedence_env_beats_project_beats_user_beats_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            u_file = root / "user-config.toml"
            p_dir = root / "proj"
            p_dir.mkdir()
            p_file = p_dir / "reelsyntax.toml"

            u_file.write_text(
                'config_version = 1\n[general]\nui_lang = "tr"\nvideo_lang = "tr"\n[provider]\nname = "ollama"\nmodel = "qwen-small"\n[render]\ndefault_profile = "production"\n',
                encoding="utf-8",
            )
            p_file.write_text(
                'config_version = 1\n[general]\nvideo_lang = "de"\nattribution = true\n[render]\ndefault_profile = "hero"\ncache_budget_mib = 512\n',
                encoding="utf-8",
            )
            env = {
                "REELSYNTAX_USER_CONFIG": str(u_file),
                "REELSYNTAX_PROVIDER": "openai_compat",
                "REELSYNTAX_ENDPOINT": "http://127.0.0.1:11434/v1",
                "REELSYNTAX_ALLOW_NETWORK": "true",
            }
            resolved = load_config(project=p_dir, environ=env, cwd=root)
            self.assertEqual(resolved.general.ui_lang, "tr")
            self.assertEqual(resolved.general.video_lang, "de")
            self.assertTrue(resolved.general.allow_network)
            self.assertTrue(resolved.general.attribution)
            self.assertEqual(resolved.provider.name, "openai_compat")
            self.assertEqual(resolved.provider.model, "qwen-small")
            self.assertEqual(resolved.provider.endpoint, "http://127.0.0.1:11434/v1")
            self.assertEqual(resolved.render.default_profile, "hero")
            self.assertEqual(resolved.render.cache_budget_mib, 512)
            self.assertEqual(len(resolved.sources), 3)

    def test_validation_rejects_unknown_keys_bad_types_and_unsafe_endpoints(self) -> None:
        bad_cases = [
            {"config_version": 2},
            {"unknown_section": {}},
            {"general": {"unknown_key": True}},
            {"general": {"allow_network": "yes"}},
            {"general": {"ui_lang": "invalid_lang_!"}},
            {"provider": {"name": "unknown_llm"}},
            {"provider": {"endpoint": "file:///etc/passwd"}},
            {"provider": {"max_repairs": 5}},
            {"render": {"default_profile": "ultra"}},
            {"render": {"timeout_sec": 0}},
            {"paths": {"ffmpeg": "relative/ffmpeg"}},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_config_data(bad)

    def test_os_user_config_paths(self) -> None:
        win = user_config_path({"APPDATA": "C:/Users/demo/AppData/Roaming"}, platform_name="win32")
        self.assertEqual(win.as_posix(), "C:/Users/demo/AppData/Roaming/reelsyntax/config.toml")
        xdg = user_config_path({"XDG_CONFIG_HOME": "/tmp/xdg"}, platform_name="linux")
        self.assertEqual(xdg.as_posix(), "/tmp/xdg/reelsyntax/config.toml")

    def test_media_executable_reads_paths_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            fake_bin.write_text("#!/bin/sh\necho ffmpeg\n", encoding="utf-8")
            fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IXUSR)
            cfg_path = Path(tmp) / "reelsyntax.toml"
            escaped_bin = str(fake_bin.resolve()).replace("\\", "\\\\")
            cfg_path.write_text(
                f'config_version = 1\n[paths]\nffmpeg = "{escaped_bin}"\n',
                encoding="utf-8",
            )
            clean_env = {k: v for k, v in os.environ.items() if k != "REELSYNTAX_FFMPEG"}
            with patch.dict(os.environ, clean_env, clear=True), config_context(cfg_path):
                self.assertEqual(Path(executable("ffmpeg")).resolve(), fake_bin.resolve())

    def test_cli_config_commands_and_published_schema(self) -> None:
        published = json.loads((REPO_ROOT / "docs/config.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(published, config_schema())
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "REELSYNTAX_USER_CONFIG": str(Path(tmp) / "user.toml")}
            init_res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "config", "init", tmp, "--json"],
                capture_output=True,
                text=True,
                env=env,
                timeout=20,
                check=False,
            )
            self.assertEqual(init_res.returncode, 0, init_res.stderr)
            created_path = Path(json.loads(init_res.stdout)["result"]["path"])
            self.assertTrue(created_path.is_file())

            val_res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "config", "validate", str(created_path), "--json"],
                capture_output=True,
                text=True,
                env=env,
                timeout=20,
                check=False,
            )
            self.assertEqual(val_res.returncode, 0, val_res.stderr)
            self.assertTrue(json.loads(val_res.stdout)["result"]["valid"])

            show_res = subprocess.run(
                [sys.executable, "-m", "reelsyntax", "--config", str(created_path), "config", "show", "--json"],
                capture_output=True,
                text=True,
                env=env,
                timeout=20,
                check=False,
            )
            self.assertEqual(show_res.returncode, 0, show_res.stderr)
            payload = json.loads(show_res.stdout)["result"]
            self.assertEqual(payload["provider"]["name"], "offline_rules")
            self.assertIn(str(created_path.resolve()), payload["sources"])


if __name__ == "__main__":
    unittest.main()
