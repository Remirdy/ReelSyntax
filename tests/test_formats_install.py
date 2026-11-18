import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

from ReelSyntax_Skills.tools.registry import atomic_json, read_json
from reelsyntax.cli import main as cli_main
from reelsyntax.formats import (
    install_format,
    is_remote_git_source,
    list_installed_formats,
    scaffold_format,
    uninstall_format,
    validate_format_directory,
)


class FormatInstallerTests(unittest.TestCase):
    def test_remote_git_source_detection(self) -> None:
        self.assertTrue(is_remote_git_source("https://example.invalid/org/format.git"))
        self.assertTrue(is_remote_git_source("git@example.invalid:org/format.git"))
        self.assertTrue(is_remote_git_source("ssh://git@example.invalid/org/format.git"))
        self.assertTrue(is_remote_git_source("git://example.invalid/org/format.git"))
        self.assertFalse(is_remote_git_source("/tmp/local-format"))
        self.assertFalse(is_remote_git_source("./relative-format"))

    def test_remote_url_rejected_without_allow_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "--allow-network"):
                install_format(
                    "https://example.invalid/community/demo-format.git",
                    allow_network=False,
                    install_root=Path(tmp) / "installed",
                )

    def test_install_from_local_directory_force_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_parent = root / "src"
            scaffold_format("community-card", category="social", base_dir=src_parent)
            src_dir = src_parent / "community-card"
            install_root = root / "user-formats"

            result = install_format(str(src_dir), install_root=install_root)
            self.assertTrue(result["installed"])
            self.assertEqual(result["id"], "community-card")
            self.assertIsNone(result["commit_sha"])
            self.assertEqual(len(result["package_sha256"]), 64)

            installed_dir = install_root / "community-card"
            validated = validate_format_directory(installed_dir)
            self.assertTrue(validated["valid"])

            with self.assertRaisesRegex(ValueError, "already installed"):
                install_format(str(src_dir), install_root=install_root)

            replaced = install_format(str(src_dir), force=True, install_root=install_root)
            self.assertEqual(replaced["package_sha256"], result["package_sha256"])

            rows = list_installed_formats(install_root=install_root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "community-card")

            removed = uninstall_format("community-card", install_root=install_root)
            self.assertTrue(removed["uninstalled"])
            self.assertEqual(list_installed_formats(install_root=install_root), [])

    def test_install_from_local_git_repository_with_subdir_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_dir = root / "pack-repo"
            formats_sub = repo_dir / "packs"
            scaffold_format("git-hosted-reel", category="creator", base_dir=formats_sub)

            git_env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "Test Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Test Fixture",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            }
            subprocess.run(["git", "init", "-b", "main", str(repo_dir)], env=git_env, check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo_dir), "add", "."], env=git_env, check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "commit", "-m", "feat: add format fixture"],
                env=git_env,
                check=True,
                capture_output=True,
            )
            head_sha = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                env=git_env,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            install_root = root / "installed"
            res = install_format(
                str(repo_dir),
                subdir="packs/git-hosted-reel",
                ref="main",
                install_root=install_root,
            )
            self.assertEqual(res["id"], "git-hosted-reel")
            self.assertEqual(res["commit_sha"], head_sha)
            installed_pkg = install_root / "git-hosted-reel"
            self.assertFalse((installed_pkg / ".git").exists())
            receipt = read_json(installed_pkg / ".install-receipt.json")
            self.assertEqual(receipt["commit_sha"], head_sha)
            self.assertEqual(receipt["subdir"], "packs/git-hosted-reel")

    def test_install_from_zip_and_reject_zip_slip_or_zip_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_parent = root / "src"
            scaffold_format("zip-bundle-demo", category="education", base_dir=src_parent)
            pkg_dir = src_parent / "zip-bundle-demo"

            good_zip = root / "good.zip"
            with ZipFile(good_zip, "w") as zf:
                for file_path in sorted(pkg_dir.rglob("*")):
                    if file_path.is_file():
                        arcname = f"zip-bundle-demo/{file_path.relative_to(pkg_dir).as_posix()}"
                        zf.write(file_path, arcname)

            install_root = root / "installed"
            res = install_format(str(good_zip), install_root=install_root)
            self.assertEqual(res["id"], "zip-bundle-demo")

            traversal_zip = root / "traversal.zip"
            with ZipFile(traversal_zip, "w") as zf:
                zf.writestr("../escaped.json", "{}")
            with self.assertRaisesRegex(ValueError, "path traversal"):
                install_format(str(traversal_zip), install_root=install_root)

            symlink_zip = root / "symlink.zip"
            with ZipFile(symlink_zip, "w") as zf:
                sym = ZipInfo("zip-bundle-demo/link.txt")
                sym.external_attr = (0o120777 << 16)
                zf.writestr(sym, "/etc/hosts")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                install_format(str(symlink_zip), install_root=install_root)

    def test_rejects_executable_files_unsafe_recipes_and_external_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_root = root / "installed"

            py_parent = root / "bad-code"
            scaffold_format("bad-code-fmt", category="social", base_dir=py_parent)
            (py_parent / "bad-code-fmt/helper.py").write_text("x = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbidden executable/code file"):
                install_format(str(py_parent / "bad-code-fmt"), install_root=install_root)

            recipe_parent = root / "bad-recipe"
            scaffold_format("bad-recipe-fmt", category="art", base_dir=recipe_parent)
            skel_path = recipe_parent / "bad-recipe-fmt/template/reel.skel.json"
            skel = read_json(skel_path)
            skel["scenes"][0]["recipe"] = "three-scene"
            atomic_json(skel_path, skel)
            with self.assertRaisesRegex(ValueError, "cannot use executable recipe"):
                install_format(str(recipe_parent / "bad-recipe-fmt"), install_root=install_root)

            ext_parent = root / "bad-url"
            scaffold_format("bad-url-fmt", category="music", base_dir=ext_parent)
            ext_skel_path = ext_parent / "bad-url-fmt/template/reel.skel.json"
            ext_skel = read_json(ext_skel_path)
            ext_skel["audio"]["tracks"] = [{"source": "https://example.invalid/audio.mp3"}]
            atomic_json(ext_skel_path, ext_skel)
            with self.assertRaisesRegex(ValueError, "unsafe audio track source"):
                install_format(str(ext_parent / "bad-url-fmt"), install_root=install_root)

    def test_cli_formats_install_list_validate_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_parent = root / "src"
            scaffold_format("cli-installed-reel", category="personal", base_dir=src_parent)
            user_formats = root / "user-formats"

            with patch.dict(os.environ, {"REELSYNTAX_FORMATS_DIR": str(user_formats)}):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    rc = cli_main(["formats", "install", str(src_parent / "cli-installed-reel"), "--json"])
                self.assertEqual(rc, 0)
                installed_payload = json.loads(buf.getvalue())["result"]
                self.assertEqual(installed_payload["id"], "cli-installed-reel")

                list_buf = io.StringIO()
                with patch("sys.stdout", list_buf):
                    rc_list = cli_main(["formats", "installed", "--json"])
                self.assertEqual(rc_list, 0)
                listed = json.loads(list_buf.getvalue())["result"]
                self.assertEqual(listed["total"], 1)

                val_buf = io.StringIO()
                with patch("sys.stdout", val_buf):
                    rc_val = cli_main(["formats", "validate", "cli-installed-reel", "--json"])
                self.assertEqual(rc_val, 0)
                self.assertTrue(json.loads(val_buf.getvalue())["result"]["valid"])

                rm_buf = io.StringIO()
                with patch("sys.stdout", rm_buf):
                    rc_rm = cli_main(["formats", "uninstall", "cli-installed-reel", "--json"])
                self.assertEqual(rc_rm, 0)
                self.assertTrue(json.loads(rm_buf.getvalue())["result"]["uninstalled"])


if __name__ == "__main__":
    unittest.main()
