from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from reelsyntax.gateway import blender_binary_candidates, discover_blender_binary
from reelsyntax.media import _terminate_process_tree, executable, standard_media_candidates


class CrossPlatformBinaryTests(unittest.TestCase):
    def test_standard_media_candidates_cover_windows_macos_and_linux(self) -> None:
        win = standard_media_candidates(
            "ffmpeg",
            platform_name="win32",
            environ={"LOCALAPPDATA": "C:/Users/demo/AppData/Local", "USERPROFILE": "C:/Users/demo"},
        )
        self.assertIn(Path("C:/Users/demo/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"), win)
        self.assertIn(Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"), win)

        mac = standard_media_candidates("ffprobe", platform_name="darwin", environ={})
        self.assertIn(Path("/opt/homebrew/bin/ffprobe"), mac)

        lin = standard_media_candidates("ffmpeg", platform_name="linux", environ={})
        self.assertIn(Path("/usr/bin/ffmpeg"), lin)
        self.assertIn(Path("/snap/bin/ffmpeg"), lin)

    def test_executable_falls_back_to_standard_candidates_when_path_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            win_bin = Path(tmp) / "ffmpeg.exe"
            win_bin.write_bytes(b"MZ")
            with patch("reelsyntax.media.standard_media_candidates", return_value=[win_bin]):
                resolved = executable("ffmpeg", platform_name="win32", environ={"PATH": ""})
            self.assertEqual(Path(resolved), win_bin)

            posix_bin = Path(tmp) / "ffprobe"
            posix_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            posix_bin.chmod(posix_bin.stat().st_mode | stat.S_IXUSR)
            with patch("reelsyntax.media.standard_media_candidates", return_value=[posix_bin]):
                resolved_posix = executable("ffprobe", platform_name="linux", environ={"PATH": ""})
            self.assertEqual(Path(resolved_posix), posix_bin)

    def test_blender_discovery_across_simulated_os_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "Program Files"
            bl_dir = pf / "Blender Foundation/Blender 5.1"
            bl_dir.mkdir(parents=True)
            bl_exe = bl_dir / "blender.exe"
            bl_exe.write_bytes(b"MZ")
            env = {"ProgramFiles": str(pf), "PATH": ""}
            cands = blender_binary_candidates(platform_name="win32", environ=env)
            self.assertIn(bl_exe, cands)
            with patch("reelsyntax.gateway.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Blender 5.1.2\n")
                info = discover_blender_binary(platform_name="win32", environ=env)
            self.assertTrue(info["available"])
            self.assertEqual(Path(info["binary"]), bl_exe)
            self.assertEqual(info["version"], "Blender 5.1.2")

    def test_windows_process_tree_termination_invokes_taskkill(self) -> None:
        fake_proc = MagicMock()
        fake_proc.pid = 43210
        with patch("reelsyntax.media.os.name", "nt"), patch("reelsyntax.media.subprocess.run") as mock_run:
            _terminate_process_tree(fake_proc)
        mock_run.assert_called_once()
        called_args = mock_run.call_args[0][0]
        self.assertEqual(called_args, ["taskkill", "/F", "/T", "/PID", "43210"])
        fake_proc.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
