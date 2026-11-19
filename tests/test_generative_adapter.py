import base64
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

from ReelSyntax_Skills.tools.registry import atomic_json, read_json
from reelsyntax.assets import (
    audit_project_licenses,
    generate_media_asset,
    resolve_generative_policy,
)
from reelsyntax.cli import main as cli_main
from reelsyntax.config import load_config, render_starter_toml, validate_config_data
from reelsyntax.media import executable
from reelsyntax.project import initialize
from reelsyntax.quality import check_asset_licenses

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_png_bytes(width: int = 16, height: int = 16, rgb: tuple[int, int, int] = (48, 84, 120)) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _media_ready() -> bool:
    if importlib.util.find_spec("PIL") is None:
        return False
    try:
        return bool(executable("ffmpeg")) and bool(executable("ffprobe"))
    except ValueError:
        return False


class _MockGenerativeServer:
    def __init__(self, handler_fn):
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                outer.requests.append({"path": self.path, "body": body})
                status, headers, payload = handler_fn(self.path, body)
                self.send_response(status)
                for key, val in headers.items():
                    self.send_header(key, val)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}/generate", self.requests

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class GenerativeAdapterTests(unittest.TestCase):
    def test_disabled_by_default_everywhere_and_rejects_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "proj"
            initialize(proj)
            env = {"REELSYNTAX_USER_CONFIG": str(root / "missing-user.toml")}
            cfg = load_config(project=proj, environ=env, cwd=root)
            self.assertFalse(cfg.generative.enabled)
            self.assertEqual(cfg.generative.endpoint, "")
            self.assertEqual(cfg.generative.spdx, "User-Provided")
            self.assertIn("enabled = false", render_starter_toml())

            with self.assertRaisesRegex(ValueError, "disabled by default"):
                generate_media_asset(
                    proj,
                    "Calm architectural horizon",
                    endpoint="http://127.0.0.1:9/generate",
                    allow_network=True,
                    config=cfg,
                )
            self.assertFalse((proj / "assets").exists())

            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with patch.dict(os.environ, env, clear=False), patch("sys.stdout", out_buf), patch("sys.stderr", err_buf):
                rc = cli_main([
                    "assets",
                    "generate",
                    str(proj),
                    "Calm architectural horizon",
                    "--endpoint",
                    "http://127.0.0.1:9/generate",
                    "--allow-network",
                    "--json",
                ])
            self.assertEqual(rc, 2)
            self.assertIn("disabled by default", err_buf.getvalue())

    def test_opt_in_policy_enforces_endpoint_loopback_and_allow_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_no_ep = validate_config_data({"config_version": 1, "generative": {"enabled": True}})
            self.assertTrue(cfg_no_ep["generative"]["enabled"])

            proj = Path(tmp) / "proj"
            initialize(proj)
            (proj / "reelsyntax.toml").write_text('config_version = 1\n[generative]\nenabled = true\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "explicit .*endpoint"):
                resolve_generative_policy(project_dir=proj)

            (proj / "reelsyntax.toml").write_text(
                'config_version = 1\n[generative]\nenabled = true\nendpoint = "https://remote.example.invalid/gen"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "--allow-network"):
                resolve_generative_policy(project_dir=proj, allow_network=False)

            remote_ok = resolve_generative_policy(project_dir=proj, allow_network=True)
            self.assertTrue(remote_ok["allow_network"])
            self.assertFalse(remote_ok["loopback"])

            (proj / "reelsyntax.toml").write_text(
                'config_version = 1\n[generative]\nenabled = true\nendpoint = "http://127.0.0.1:9999/gen"\n',
                encoding="utf-8",
            )
            loopback_ok = resolve_generative_policy(project_dir=proj, allow_network=False)
            self.assertTrue(loopback_ok["loopback"])

            for bad in [
                {"generative": {"enabled": "true"}},
                {"generative": {"endpoint": "ftp://127.0.0.1/x"}},
                {"generative": {"spdx": "GPL-3.0-only"}},
                {"generative": {"timeout_sec": 0}},
                {"generative": {"unknown": 1}},
            ]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    validate_config_data(bad)

    def test_loopback_generation_stamps_provenance_and_passes_license_qc(self) -> None:
        png_data = make_png_bytes()

        def handler(path, body):
            payload = json.dumps({
                "data_base64": base64.b64encode(png_data).decode("ascii"),
                "mime_type": "image/png",
                "spdx": "CC0-1.0",
                "attribution": "Synthetic media via local adapter (disclosed)",
                "adapter": "local-test-stub",
                "generator": "test-image-stub",
            }).encode("utf-8")
            return 200, {"Content-Type": "application/json"}, payload

        with tempfile.TemporaryDirectory() as tmp, _MockGenerativeServer(handler) as (url, requests):
            proj = Path(tmp) / "proj"
            initialize(proj)
            (proj / "reelsyntax.toml").write_text(
                f'config_version = 1\n[generative]\nenabled = true\nendpoint = "{url}"\n',
                encoding="utf-8",
            )
            atomic_json(proj / "output/draft-manifest.json", {"schema_version": 1, "scenes": []})

            out_buf = io.StringIO()
            with patch("sys.stdout", out_buf):
                rc = cli_main([
                    "assets",
                    "generate",
                    str(proj),
                    "Slate architectural backdrop",
                    "--out",
                    "assets/generated/backdrop.png",
                    "--seed",
                    "77",
                    "--json",
                ])
            self.assertEqual(rc, 0, out_buf.getvalue())
            res = json.loads(out_buf.getvalue())["result"]
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["body"]["seed"], 77)
            self.assertEqual(res["path"], "assets/generated/backdrop.png")
            self.assertTrue((proj / "assets/generated/backdrop.png").is_file())

            prompt_doc = read_json(proj / "prompt.json")
            manifest_doc = read_json(proj / "manifest.json")
            draft_manifest = read_json(proj / "output/draft-manifest.json")
            for doc in (prompt_doc, manifest_doc, draft_manifest):
                self.assertTrue(doc["synthetic_origin"]["present"])
                self.assertEqual(doc["synthetic_origin"]["assets"][0]["path"], "assets/generated/backdrop.png")
                self.assertTrue(doc["synthetic_origin"]["assets"][0]["disclosed"])

            plan = read_json(proj / "reel.json")
            plan["audio"]["cues"] = []
            plan["quality"]["exceptions"] = {}
            plan["scenes"][0] = {
                "id": "synthetic-plate",
                "duration_frames": 30,
                "recipe": "layer-stack",
                "engine": "pillow",
                "params": {
                    "background": "#182028",
                    "layers": [
                        {"source": "assets/generated/backdrop.png", "x": 0, "y": 0, "width": 1080, "height": 1920},
                    ],
                },
            }
            atomic_json(proj / "reel.json", plan)

            audit = audit_project_licenses(proj)
            self.assertTrue(audit["ok"])
            self.assertEqual(audit["synthetic_assets"], ["assets/generated/backdrop.png"])
            qc_res = check_asset_licenses(proj, plan)
            self.assertEqual(qc_res["status"], "pass")
            self.assertEqual(qc_res["observed"]["synthetic_assets"], ["assets/generated/backdrop.png"])
            self.assertIn("(synthetic)", (proj / "LICENSES.md").read_text(encoding="utf-8"))

            ledger = read_json(proj / ".reelsyntax/asset-licenses.json")
            ledger["assets"]["assets/generated/backdrop.png"]["attribution"] = ""
            atomic_json(proj / ".reelsyntax/asset-licenses.json", ledger)
            qc_fail = check_asset_licenses(proj, plan)
            self.assertEqual(qc_fail["status"], "fail")
            self.assertEqual(qc_fail["observed"]["invalid"], ["assets/generated/backdrop.png"])

    def test_rejects_bad_paths_redirects_and_non_media_payloads(self) -> None:
        png_data = make_png_bytes()

        def handler(path, body):
            if path == "/redirect":
                return 302, {"Location": "http://169.254.169.254/latest"}, b""
            if path == "/html":
                return 200, {"Content-Type": "image/png"}, b"<html>not a png</html>"
            return 200, {"Content-Type": "image/png"}, png_data

        with tempfile.TemporaryDirectory() as tmp, _MockGenerativeServer(handler) as (url, _):
            base = url.rsplit("/", 1)[0]
            proj = Path(tmp) / "proj"
            initialize(proj)
            (proj / "reelsyntax.toml").write_text(
                f'config_version = 1\n[generative]\nenabled = true\nendpoint = "{base}/png"\n',
                encoding="utf-8",
            )
            for bad_dest in [
                "../escape.png",
                "/tmp/escape.png",
                "assets\\escape.png",
                "C:/escape.png",
                ".",
                ".reelsyntax/hidden.png",
                "output/draft.png",
                "reel.json",
                "assets/payload.py",
            ]:
                with self.subTest(bad_dest=bad_dest), self.assertRaises(ValueError):
                    generate_media_asset(proj, "Backdrop", dest_rel=bad_dest)

            with self.assertRaisesRegex(ValueError, "redirect"):
                generate_media_asset(proj, "Backdrop", endpoint=f"{base}/redirect")

            with self.assertRaisesRegex(ValueError, "do not match"):
                generate_media_asset(proj, "Backdrop", endpoint=f"{base}/html", dest_rel="assets/bad.png")

            for bad_ep in ["http://127.0.0.1:9/bad path", "http://127.0.0.1:9/\nX:1", "http://127.0.0.1:9/ok\n"]:
                out_buf = io.StringIO()
                err_buf = io.StringIO()
                with self.subTest(bad_ep=bad_ep), patch("sys.stdout", out_buf), patch("sys.stderr", err_buf):
                    rc = cli_main(["assets", "generate", str(proj), "Backdrop", "--endpoint", bad_ep, "--json"])
                self.assertEqual(rc, 2)
                self.assertIn("http(s) URL", err_buf.getvalue())

            with self.assertRaisesRegex(ValueError, "single-line"):
                generate_media_asset(proj, "Backdrop", attribution="line1\nline2", dest_rel="assets/bad2.png")

            with patch("urllib.request.build_opener") as mock_opener:
                mock_opener.return_value.open.side_effect = http.client.RemoteDisconnected("peer closed")
                with self.assertRaisesRegex(ValueError, "request failed"):
                    generate_media_asset(proj, "Backdrop", dest_rel="assets/bad3.png")

            outside = Path(tmp) / "outside"
            outside.mkdir()
            link = proj / "assets/link"
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                return
            with self.assertRaisesRegex(ValueError, "Symbolic links"):
                generate_media_asset(proj, "Backdrop", dest_rel="assets/link/evil.png")
            self.assertEqual(list(outside.iterdir()), [])

    def test_works_without_pillow_installed(self) -> None:
        script = (
            "import importlib.util, json, sys, tempfile\n"
            "from pathlib import Path\n"
            "sys.modules['PIL'] = None\n"
            "orig = importlib.util.find_spec\n"
            "importlib.util.find_spec = lambda n, *a, **k: None if n == 'PIL' or n.startswith('PIL.') else orig(n, *a, **k)\n"
            "from reelsyntax.assets import generate_media_asset\n"
            "from reelsyntax.config import load_config\n"
            "from reelsyntax.project import initialize\n"
            "proj = Path(tempfile.mkdtemp()) / 'p'\n"
            "initialize(proj)\n"
            "cfg = load_config(project=proj)\n"
            "err = ''\n"
            "try:\n"
            "    generate_media_asset(proj, 'Test', config=cfg)\n"
            "except ValueError as exc:\n"
            "    err = str(exc)\n"
            "print(json.dumps({'enabled': cfg.generative.enabled, 'err': err}))\n"
        )
        env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(REPO_ROOT), os.environ.get("PYTHONPATH", "")]))}
        res = subprocess.run([sys.executable, "-c", script], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertFalse(payload["enabled"])
        self.assertIn("disabled by default", payload["err"])

    @unittest.skipUnless(os.environ.get("REELSYNTAX_MEDIA_TESTS") == "1" and _media_ready(), "live media render disabled or FFmpeg/Pillow unavailable")
    def test_render_and_qc_stamp_synthetic_origin_in_manifests(self) -> None:
        from reelsyntax.quality import check as qc_check
        from reelsyntax.render import render

        png_data = make_png_bytes(64, 64, (72, 108, 144))

        def handler(path, body):
            return 200, {"Content-Type": "image/png"}, png_data

        with tempfile.TemporaryDirectory() as tmp, _MockGenerativeServer(handler) as (url, _):
            proj = Path(tmp) / "proj"
            initialize(proj)
            (proj / "reelsyntax.toml").write_text(
                f'config_version = 1\n[generative]\nenabled = true\nendpoint = "{url}"\n',
                encoding="utf-8",
            )
            gen = generate_media_asset(proj, "Slate backdrop", dest_rel="assets/generated/plate.png")
            plan = read_json(proj / "reel.json")
            plan["audio"]["enabled"] = False
            plan["audio"]["cues"] = []
            plan["quality"]["exceptions"] = {"freeze": [[0, 30]]}
            plan["scenes"] = [
                {
                    "id": "synthetic-bg",
                    "duration_frames": 30,
                    "recipe": "layer-stack",
                    "engine": "pillow",
                    "params": {
                        "background": "#2a3440",
                        "layers": [
                            {"source": gen["path"], "x": 0, "y": 0, "width": 1080, "height": 1920},
                        ],
                    },
                }
            ]
            atomic_json(proj / "reel.json", plan)

            rendered = render(proj, profile="draft")
            draft_manifest = read_json(proj / "output/draft-manifest.json")
            self.assertTrue(rendered["synthetic_origin"]["present"])
            self.assertTrue(draft_manifest["synthetic_origin"]["present"])
            self.assertEqual(draft_manifest["synthetic_origin"]["assets"][0]["path"], gen["path"])
            cache_key = draft_manifest["scenes"][0]["cache_key"]
            scene_manifest = read_json(proj / f".reelsyntax/cache/{cache_key}/manifest.json")
            self.assertTrue(scene_manifest["synthetic_origin"]["present"])

            qc_res = qc_check(proj, profile="draft")
            self.assertEqual(qc_res["technical_status"], "pass")
            asset_check = next(c for c in qc_res["checks"] if c["id"] == "asset_licenses")
            self.assertEqual(asset_check["status"], "pass")


if __name__ == "__main__":
    unittest.main()
