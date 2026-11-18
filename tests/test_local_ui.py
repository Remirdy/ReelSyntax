import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from reelsyntax.cli import main as cli_main
from reelsyntax.cli import parser as cli_parser
from reelsyntax.lang.catalog import load_catalog
from reelsyntax.ui import CSRF_HEADER, create_server, is_loopback_host, validate_bind_host
from reelsyntax.ui.server import UI_ASSET_DIR, StudioServer

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT = "12s vertical reel with 3 beats on reproducible video pipelines"


class RunningStudio:
    def __init__(self, workspace: Path, **kwargs: object) -> None:
        self.server = create_server(workspace, port=0, **kwargs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "RunningStudio":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    @property
    def port(self) -> int:
        return self.server.studio.port

    @property
    def token(self) -> str:
        return self.server.studio.csrf_token

    def request(
        self,
        method: str,
        path: str,
        body: object = None,
        headers: dict[str, str] | None = None,
        raw: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        try:
            payload = raw
            send_headers = dict(headers or {})
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                send_headers.setdefault("Content-Type", "application/json")
            conn.request(method, path, body=payload, headers=send_headers)
            response = conn.getresponse()
            data = response.read()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, data
        finally:
            conn.close()

    def get_json(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
        status, _, data = self.request("GET", path, headers=headers)
        return status, json.loads(data.decode("utf-8"))

    def post_json(self, path: str, body: object, token: str | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
        send = dict(headers or {})
        if token is None:
            send[CSRF_HEADER] = self.token
        elif token:
            send[CSRF_HEADER] = token
        status, _, data = self.request("POST", path, body=body, headers=send)
        return status, json.loads(data.decode("utf-8"))


def write_fake_project(root: Path) -> None:
    (root / "output").mkdir(parents=True)
    (root / "review").mkdir()
    (root / ".formats/snapshots").mkdir(parents=True)
    (root / ".reelsyntax").mkdir()
    (root / "reel.json").write_text(json.dumps({
        "id": "fake-project",
        "output": {"width": 1080, "height": 1920, "fps": "30/1"},
        "scenes": [
            {"id": "beat-1", "engine": "pillow", "recipe": "title-card", "duration_frames": 30,
             "params": {"heading": "Hello", "subheading": "World", "background": "#101010", "foreground": "#f0f0f0", "accent": "#3080c0"}},
            {"id": "beat-2", "engine": "pillow", "recipe": "title-card", "duration_frames": 45, "params": {"heading": "Two"}},
        ],
    }), encoding="utf-8")
    (root / ".reelsyntax/scene-locks.json").write_text(json.dumps({"beat-2": {"locked": True}}), encoding="utf-8")
    (root / "output/draft.mp4").write_bytes(bytes(range(256)) * 8)
    (root / ".formats/snapshots/beat-1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (root / "review/draft-qc.json").write_text(json.dumps({
        "schema_version": 1,
        "profile": "draft",
        "technical_status": "review",
        "release_status": "requires creative/audio review",
        "checks": [
            {"id": "decode", "status": "pass", "observed": {"frames": 75}, "expected": "decodable"},
            {"id": "contrast", "status": "review", "observed": "4.2:1", "expected": ">= 4.5:1"},
        ],
    }), encoding="utf-8")
    (root / ".reelsyntax/state.json").write_text("{}", encoding="utf-8")
    (root / "notes.txt").write_text("private", encoding="utf-8")


class BindGuardTests(unittest.TestCase):
    def test_loopback_detection_and_non_loopback_guard(self) -> None:
        for host in ("127.0.0.1", "localhost", "::1", "[::1]", "127.0.0.2"):
            self.assertTrue(is_loopback_host(host), host)
            self.assertTrue(validate_bind_host(host))
        for host in ("0.0.0.0", "192.168.1.20", "example.com", "::"):
            self.assertFalse(is_loopback_host(host), host)
            with self.assertRaisesRegex(ValueError, "allow-non-loopback"):
                validate_bind_host(host)
            self.assertEqual(validate_bind_host(host, allow_non_loopback=True), host)
        for bad in ("", "   ", "127.0.0.1 evil"):
            with self.assertRaises(ValueError):
                validate_bind_host(bad, allow_non_loopback=True)

    def test_create_server_rejects_non_loopback_and_bad_port(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "non-loopback"):
                create_server(tmp, host="0.0.0.0", port=0)
            with self.assertRaises(ValueError):
                create_server(tmp, port=70000)
            with self.assertRaises(OSError):
                create_server(Path(tmp) / "missing", port=0)

    def test_cli_rejects_non_loopback_host_without_opt_in(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli_main(["ui", "--host", "0.0.0.0", "--port", "0", "--no-open"])
        self.assertEqual(code, 2)
        payload = json.loads(err.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("non-loopback", payload["errors"][0]["message"])

    def test_cli_parser_and_serve_startup_banner(self) -> None:
        args = cli_parser().parse_args(["ui", "--no-open", "--port", "0", "--project", "."])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertTrue(args.no_open)
        self.assertFalse(args.allow_non_loopback)
        self.assertEqual(args.port, 0)
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with patch.object(StudioServer, "serve_forever", side_effect=KeyboardInterrupt), \
                    patch("webbrowser.open") as opener, contextlib.redirect_stdout(out):
                code = cli_main(["--ui-lang", "tr", "ui", "--port", "0", "--no-open", "--project", tmp])
            self.assertEqual(code, 0)
            opener.assert_not_called()
            banner = json.loads(out.getvalue().strip().splitlines()[0])
            self.assertTrue(banner["ok"])
            self.assertEqual(banner["command"], "ui")
            self.assertTrue(banner["result"]["url"].startswith("http://127.0.0.1:"))
            self.assertTrue(banner["result"]["loopback"])
            self.assertEqual(banner["result"]["locale"], "tr")


class StudioHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name).resolve()
        self.studio = RunningStudio(self.workspace)
        self.studio.__enter__()

    def tearDown(self) -> None:
        self.studio.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_index_serves_csp_security_headers_and_injected_token(self) -> None:
        status, headers, body = self.studio.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/html; charset=utf-8")
        csp = headers["content-security-policy"]
        for directive in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'self'", "frame-ancestors 'none'"):
            self.assertIn(directive, csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["x-frame-options"], "DENY")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        self.assertEqual(headers["cache-control"], "no-store")
        page = body.decode("utf-8")
        self.assertIn(f'<meta name="reelsyntax-csrf" content="{self.studio.token}">', page)
        self.assertNotIn("__REELSYNTAX_", page)
        self.assertIn('<script src="/static/app.js" defer></script>', page)
        self.assertGreaterEqual(len(self.studio.token), 32)

    def test_static_assets_are_self_contained_offline_and_accessible(self) -> None:
        for route, ctype in (("/static/app.js", "text/javascript"), ("/static/app.css", "text/css")):
            status, headers, body = self.studio.request("GET", route)
            self.assertEqual(status, 200)
            self.assertTrue(headers["content-type"].startswith(ctype))
            text = body.decode("utf-8")
            for forbidden in ("http://", "https://", "@import", "googleapis", "cdn", "analytics", "innerHTML", "eval("):
                self.assertNotIn(forbidden, text, f"{route} contains {forbidden}")
        css = (UI_ASSET_DIR / "app.css").read_text(encoding="utf-8")
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn(":focus-visible", css)
        page = (UI_ASSET_DIR / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertIn('role="status"', page)
        self.assertIn('class="skip-link"', page)
        status, _, _ = self.studio.request("GET", "/static/../server.py")
        self.assertEqual(status, 404)

    def test_session_localizes_ui_strings_for_en_tr_de(self) -> None:
        expected = {"en": "Projects", "tr": "Projeler", "de": "Projekte"}
        for code, label in expected.items():
            status, payload = self.studio.get_json(f"/api/session?lang={code}")
            self.assertEqual(status, 200)
            result = payload["result"]
            self.assertEqual(result["locale"], code)
            self.assertEqual(result["strings"]["ui.nav.projects"], label)
            self.assertEqual(result["csrf_token"], self.studio.token)
            self.assertEqual(result["csrf_header"], CSRF_HEADER)
            self.assertTrue(result["offline"])
            self.assertEqual({entry["code"] for entry in result["locales"]} >= {"en", "tr", "de"}, True)
        status, payload = self.studio.get_json("/api/session?lang=xx")
        self.assertEqual(payload["result"]["locale"], "en")

    def test_every_ui_key_used_by_assets_exists_in_all_catalogs(self) -> None:
        sources = (UI_ASSET_DIR / "index.html").read_text(encoding="utf-8") + (UI_ASSET_DIR / "app.js").read_text(encoding="utf-8")
        keys: set[str] = set()
        for quote in ('"', "'"):
            for chunk in sources.split(quote + "ui.")[1:]:
                end = chunk.find(quote)
                keys.add("ui." + chunk[:end])
        self.assertGreater(len(keys), 40)
        for code in ("en", "tr", "de"):
            catalog = load_catalog(code)
            missing = sorted(k for k in keys if k not in catalog)
            self.assertEqual(missing, [], f"{code} missing {missing}")

    def test_foreign_host_header_is_rejected(self) -> None:
        status, payload = self.studio.get_json("/api/formats", headers={"Host": f"evil.example:{self.studio.port}"})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        status, _ = self.studio.get_json("/api/formats", headers={"Host": f"localhost:{self.studio.port}"})
        self.assertEqual(status, 200)

    def test_mutations_require_csrf_same_origin_and_json(self) -> None:
        body = {"project": ".", "instruction": "heading: Nope"}
        status, payload = self.studio.post_json("/api/revise", body, token="")
        self.assertEqual(status, 403)
        self.assertIn("CSRF", payload["error"])
        status, _ = self.studio.post_json("/api/revise", body, token="not-the-token")
        self.assertEqual(status, 403)
        status, _ = self.studio.post_json("/api/make", {"prompt": PROMPT}, token="")
        self.assertEqual(status, 403)
        status, _ = self.studio.post_json("/api/step", {"project": ".", "step_id": "idea", "action": "approve"}, token="")
        self.assertEqual(status, 403)
        status, payload = self.studio.post_json("/api/revise", body, headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)
        self.assertIn("Cross-origin", payload["error"])
        status, _ = self.studio.post_json("/api/revise", body, headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)
        status, _, _ = self.studio.request("POST", "/api/revise", raw=b"instruction=x", headers={
            "Content-Type": "application/x-www-form-urlencoded", CSRF_HEADER: self.studio.token})
        self.assertEqual(status, 415)
        status, _, _ = self.studio.request("POST", "/api/revise", raw=b"{" + b" " * 70_000 + b"}", headers={
            "Content-Type": "application/json", CSRF_HEADER: self.studio.token})
        self.assertEqual(status, 413)
        status, _, _ = self.studio.request("POST", "/api/revise", raw=b"[1, 2]", headers={
            "Content-Type": "application/json", CSRF_HEADER: self.studio.token})
        self.assertEqual(status, 400)
        status, _ = self.studio.post_json("/api/unknown", body)
        self.assertEqual(status, 404)
        status, _, _ = self.studio.request("PUT", "/api/revise", body=body, headers={CSRF_HEADER: self.studio.token})
        self.assertEqual(status, 405)
        status, _, _ = self.studio.request("DELETE", "/api/project?project=.")
        self.assertEqual(status, 405)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_format_list_endpoint_exposes_metadata(self) -> None:
        status, payload = self.studio.get_json("/api/formats")
        self.assertEqual(status, 200)
        rows = {row["id"]: row for row in payload["result"]["formats"]}
        self.assertEqual(payload["result"]["total"], len(rows))
        for fid in ("kinetic-typography", "photo-slideshow", "social-hook-reel", "prompt-direct"):
            self.assertIn(fid, rows)
        social = rows["social-hook-reel"]
        for key in ("version", "title", "category", "aspect", "duration_sec", "needs", "engines", "languages", "steps"):
            self.assertIn(key, social)
        self.assertIn("min", social["duration_sec"])
        self.assertTrue(any(step.get("gate") == "approve" for step in social["steps"]))
        self.assertTrue(rows["prompt-direct"]["builtin"] or rows["prompt-direct"]["steps"])
        self.assertNotIn("path", social)

    def test_project_path_traversal_and_unknown_projects_are_rejected(self) -> None:
        outside = self.workspace.parent
        for bad in ("../" + outside.name, "/etc", "..", "a\\b", "C:/Windows"):
            status, _ = self.studio.get_json("/api/project?project=" + bad.replace("\\", "%5C"))
            self.assertEqual(status, 400, bad)
        status, _ = self.studio.get_json("/api/project?project=missing")
        self.assertEqual(status, 404)
        status, _ = self.studio.get_json("/api/project")
        self.assertEqual(status, 400)
        status, _ = self.studio.post_json("/api/revise", {"project": "../x", "instruction": "heading: Y"})
        self.assertEqual(status, 400)

    def test_media_endpoint_serves_allowlisted_files_with_ranges(self) -> None:
        project = self.workspace / "fake"
        write_fake_project(project)
        video = (project / "output/draft.mp4").read_bytes()
        base = "/api/media?project=fake&path="
        status, headers, body = self.studio.request("GET", base + "output/draft.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "video/mp4")
        self.assertEqual(headers["accept-ranges"], "bytes")
        self.assertEqual(body, video)
        status, headers, body = self.studio.request("GET", base + "output/draft.mp4", headers={"Range": "bytes=10-19"})
        self.assertEqual(status, 206)
        self.assertEqual(headers["content-range"], f"bytes 10-19/{len(video)}")
        self.assertEqual(body, video[10:20])
        status, headers, body = self.studio.request("GET", base + "output/draft.mp4", headers={"Range": "bytes=-5"})
        self.assertEqual(status, 206)
        self.assertEqual(body, video[-5:])
        status, headers, body = self.studio.request("GET", base + "output/draft.mp4", headers={"Range": "bytes=2040-"})
        self.assertEqual(status, 206)
        self.assertEqual(body, video[2040:])
        status, headers, _ = self.studio.request("GET", base + "output/draft.mp4", headers={"Range": "bytes=99999-100000"})
        self.assertEqual(status, 416)
        self.assertEqual(headers["content-range"], f"bytes */{len(video)}")
        status, headers, body = self.studio.request("GET", base + ".formats/snapshots/beat-1.png")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "image/png")
        status, headers, _ = self.studio.request("GET", base + "reel.json")
        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("application/json"))
        status, _, _ = self.studio.request("GET", base + "review/draft-qc.json")
        self.assertEqual(status, 200)
        for bad in ("../fake/reel.json", "%2Fetc%2Fpasswd", "output/..%2F..%2Freel.json", "output%5Cdraft.mp4", "C:%2Fwin.ini", ""):
            status, _, _ = self.studio.request("GET", base + bad)
            self.assertEqual(status, 400, bad)
        for forbidden in (".reelsyntax/state.json", "notes.txt", ".reelsyntax/scene-locks.json", "reel.schema.json"):
            status, _, _ = self.studio.request("GET", base + forbidden)
            self.assertEqual(status, 403, forbidden)
        status, _, _ = self.studio.request("GET", base + "output/missing.mp4")
        self.assertEqual(status, 404)
        status, _, _ = self.studio.request("GET", "/api/media?project=..%2F&path=reel.json")
        self.assertEqual(status, 400)
        secret = self.workspace.parent / f"{self.workspace.name}-secret.mp4"
        secret.write_bytes(b"secret")
        try:
            try:
                os.symlink(secret, project / "output/link.mp4")
            except (OSError, NotImplementedError):
                self.skipTest("Symbolic links are unavailable on this platform")
            status, _, body = self.studio.request("GET", base + "output/link.mp4")
            self.assertEqual(status, 400)
            self.assertNotIn(b"secret", body)
        finally:
            secret.unlink()

    def test_project_inspection_reports_timeline_snapshots_videos_and_qc(self) -> None:
        write_fake_project(self.workspace / "fake")
        status, payload = self.studio.get_json("/api/projects")
        self.assertEqual(status, 200)
        self.assertEqual([p["path"] for p in payload["result"]["projects"]], ["fake"])
        status, payload = self.studio.get_json("/api/project?project=fake")
        self.assertEqual(status, 200)
        detail = payload["result"]
        self.assertEqual(detail["timeline"]["id"], "fake-project")
        self.assertEqual(detail["timeline"]["frames"], 75)
        scenes = detail["timeline"]["scenes"]
        self.assertEqual(scenes[1]["frame_range"], [30, 75])
        self.assertEqual(scenes[0]["colors"], ["#101010", "#f0f0f0", "#3080c0"])
        self.assertFalse(scenes[0]["locked"])
        self.assertTrue(scenes[1]["locked"])
        self.assertEqual(detail["snapshots"], [".formats/snapshots/beat-1.png"])
        self.assertEqual(detail["videos"], [{"path": "output/draft.mp4", "bytes": 2048}])
        self.assertEqual(detail["qc"][0]["profile"], "draft")
        self.assertEqual(detail["qc"][0]["technical_status"], "review")
        self.assertEqual([c["id"] for c in detail["qc"][0]["checks"]], ["decode", "contrast"])
        self.assertIsNone(detail["workflow"])

    def test_make_step_and_revise_flow_offline(self) -> None:
        status, payload = self.studio.post_json("/api/make", {"prompt": PROMPT, "dry_run": True, "aspect": "9:16"})
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["result"]["dry_run"])
        self.assertIn("estimated_draft_sec", payload["result"]["budget"])
        self.assertFalse((self.workspace / "out").exists())

        for bad in ({"prompt": ""}, {"prompt": PROMPT, "aspect": "2:1"}, {"prompt": PROMPT, "format_id": "../x"},
                    {"prompt": PROMPT, "name": "../evil"}, {"prompt": PROMPT, "duration": "ten"},
                    {"prompt": PROMPT, "dry_run": "yes"}, {"prompt": PROMPT, "lang": "english!"}):
            status, _ = self.studio.post_json("/api/make", bad)
            self.assertEqual(status, 400, bad)
        self.assertFalse((self.workspace / "out").exists())

        status, payload = self.studio.post_json("/api/make", {"prompt": PROMPT, "name": "demo", "seed": 7})
        self.assertEqual(status, 200, payload)
        made = payload["result"]
        self.assertEqual(made["project"], "out/demo")
        self.assertEqual(made["status"], "awaiting_approval")
        self.assertEqual(made["pending_gate"], "idea")
        self.assertEqual(made["seed"], 7)
        self.assertNotIn("next_actions", made)
        status, payload = self.studio.post_json("/api/make", {"prompt": PROMPT, "name": "demo"})
        self.assertEqual(status, 409)

        status, payload = self.studio.get_json("/api/projects")
        self.assertIn("out/demo", [p["path"] for p in payload["result"]["projects"]])

        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "idea", "action": "fly"})
        self.assertEqual(status, 400)
        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "nope", "action": "approve"})
        self.assertEqual(status, 400)
        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "idea", "action": "edit"})
        self.assertEqual(status, 400)
        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "idea", "action": "approve"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["pending_gate"], "script")
        self.assertIn("idea", payload["result"]["approvals"])

        status, payload = self.studio.get_json("/api/project?project=out/demo")
        detail = payload["result"]
        steps = {s["id"]: s for s in detail["workflow"]["steps"]}
        self.assertTrue(steps["idea"]["approved"])
        self.assertTrue(steps["script"]["pending"])
        self.assertFalse(steps["look"]["completed"])
        self.assertGreaterEqual(len(detail["timeline"]["scenes"]), 2)
        self.assertEqual(detail["prompt"]["text"].split()[0], "12s")
        first_scene = detail["timeline"]["scenes"][0]["id"]

        status, payload = self.studio.post_json("/api/revise", {"project": "out/demo", "instruction": "heading: Studio Title", "scene": first_scene})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["changed_scenes"], [first_scene])
        plan = json.loads((self.workspace / "out/demo/reel.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["scenes"][0]["params"]["heading"], "Studio Title")
        status, payload = self.studio.post_json("/api/revise", {"project": "out/demo", "instruction": "heading: X", "scene": "missing-scene"})
        self.assertEqual(status, 400)
        status, payload = self.studio.post_json("/api/revise", {"project": "out/demo", "instruction": "x", "render": "yes"})
        self.assertEqual(status, 400)

        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "script", "action": "back"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["status"], "awaiting_approval")

        status, payload = self.studio.post_json("/api/step", {
            "project": "out/demo",
            "step_id": "idea",
            "action": "edit",
            "instruction": "Focus on deterministic builds",
        })
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["status"], "awaiting_approval")
        self.assertEqual(payload["result"]["pending_gate"], "idea")

        status, payload = self.studio.post_json("/api/step", {"project": "out/demo", "step_id": "idea", "action": "approve"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["pending_gate"], "script")


class ZeroPillowTests(unittest.TestCase):
    def test_studio_flow_runs_without_pillow(self) -> None:
        code = "\n".join([
            "import json, sys, tempfile, threading, http.client",
            "sys.modules['PIL'] = None",
            "from reelsyntax.ui import create_server, CSRF_HEADER",
            "tmp = tempfile.mkdtemp()",
            "srv = create_server(tmp, port=0)",
            "threading.Thread(target=srv.serve_forever, daemon=True).start()",
            "def call(method, path, body=None):",
            "    conn = http.client.HTTPConnection('127.0.0.1', srv.studio.port, timeout=120)",
            "    headers = {CSRF_HEADER: srv.studio.csrf_token, 'Content-Type': 'application/json'}",
            "    conn.request(method, path, body=None if body is None else json.dumps(body), headers=headers)",
            "    res = conn.getresponse()",
            "    data = json.loads(res.read())",
            "    conn.close()",
            "    return res.status, data",
            "out = {}",
            "out['formats'] = call('GET', '/api/formats')[0]",
            "out['make'] = call('POST', '/api/make', {'prompt': " + repr(PROMPT) + ", 'name': 'nopil'})[0]",
            "out['approve'] = call('POST', '/api/step', {'project': 'out/nopil', 'step_id': 'idea', 'action': 'approve'})[0]",
            "out['revise'] = call('POST', '/api/revise', {'project': 'out/nopil', 'instruction': 'scene 1 heading: Plain'})[0]",
            "out['detail'] = call('GET', '/api/project?project=out/nopil')[0]",
            "out['pil_blocked'] = sys.modules.get('PIL', 1) is None",
            "srv.shutdown()",
            "srv.server_close()",
            "print(json.dumps(out))",
        ])
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result, {"formats": 200, "make": 200, "approve": 200, "revise": 200, "detail": 200, "pil_blocked": True})


if __name__ == "__main__":
    unittest.main()
