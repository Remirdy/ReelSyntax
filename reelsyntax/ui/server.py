from dataclasses import dataclass, field
import hmac
import html
import ipaddress
import json
from pathlib import Path
import re
import secrets
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
import webbrowser

from ReelSyntax_Skills.tools.registry import contained_path, read_json

from .. import __version__

UI_ASSET_DIR = Path(__file__).resolve().parents[1] / "data/ui"
STATIC_ROUTES: dict[str, tuple[str, str]] = {
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
}
CSRF_HEADER = "X-ReelSyntax-CSRF"
CSRF_META_PLACEHOLDER = "__REELSYNTAX_CSRF__"
LANG_PLACEHOLDER = "__REELSYNTAX_LANG__"
MAX_BODY_BYTES = 65_536
MAX_PROJECTS = 200
STREAM_CHUNK = 65_536
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cache-Control": "no-store",
}
MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".json": "application/json; charset=utf-8",
    ".vtt": "text/vtt; charset=utf-8",
    ".srt": "text/plain; charset=utf-8",
}
MEDIA_PREFIXES = ("output/", "review/", ".formats/snapshots/", ".formats/pilot/output/")
MEDIA_ROOT_FILES = frozenset({"reel.json", "prompt.json"})
SKIPPED_DIR_NAMES = frozenset({"node_modules", "__pycache__", "build", "dist", "integrations", "site-packages"})
UI_KEY_PREFIXES = ("app.", "ui.", "gate.action.", "make.step.", "qc.status.", "i18n.")
STEP_ACTIONS = frozenset({"approve", "edit", "back", "run"})
ASPECTS = ("9:16", "1:1", "16:9", "4:5")
PROFILES = ("draft", "production", "hero")
FOLDER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
STEP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SCENE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class StudioHttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class StudioState:
    workspace: Path
    csrf_token: str
    locale: str
    bind_host: str
    port: int
    allow_non_loopback: bool = False
    config_file: Path | None = None
    extra_format_roots: tuple[Path, ...] = ()
    dry_run_render: bool = False
    quiet: bool = True
    operation_lock: threading.Lock = field(default_factory=threading.Lock)

    def allowed_host_headers(self) -> frozenset[str]:
        names = {"127.0.0.1", "localhost", "[::1]"}
        bare = self.bind_host.strip("[]")
        names.add(f"[{bare}]" if ":" in bare else bare)
        allowed = {f"{name}:{self.port}" for name in names}
        if self.port == 80:
            allowed |= names
        return frozenset(value.lower() for value in allowed)


def is_loopback_host(host: str) -> bool:
    candidate = host.strip().strip("[]").lower()
    if candidate == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def validate_bind_host(host: str, allow_non_loopback: bool = False) -> str:
    if not isinstance(host, str) or not host.strip() or any(ch.isspace() for ch in host) or len(host) > 255:
        raise ValueError("Expected a nonempty host name or IP address")
    if is_loopback_host(host):
        return host.strip()
    if not allow_non_loopback:
        raise ValueError(
            f"Refusing to bind non-loopback host {host!r}; the studio is local-only by default "
            "(pass --allow-non-loopback to expose it on your network)"
        )
    return host.strip()


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


def _safe_text(value: Any, limit: int = 240) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _read_json_file(path: Path, max_bytes: int = 1_048_576) -> Any:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return read_json(path, max_bytes=max_bytes)
    except (ValueError, OSError):
        return None


def _is_project_dir(path: Path) -> bool:
    if not path.is_dir() or path.is_symlink():
        return False
    for marker in ("reel.json", ".formats/state.json"):
        try:
            if contained_path(path, marker, must_exist=False).is_file():
                return True
        except ValueError:
            continue
    return False


def resolve_project(state: StudioState, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise StudioHttpError(400, "Expected a project path relative to the studio workspace")
    if relative == ".":
        root = state.workspace
    else:
        try:
            root = contained_path(state.workspace, relative, must_exist=False)
        except ValueError as error:
            raise StudioHttpError(400, str(error)) from error
    if not _is_project_dir(root):
        raise StudioHttpError(404, "Unknown project")
    return root


def project_label(state: StudioState, root: Path) -> str:
    if root == state.workspace:
        return "."
    return root.relative_to(state.workspace).as_posix()


def discover_projects(state: StudioState) -> list[dict[str, Any]]:
    found: list[Path] = []
    if _is_project_dir(state.workspace):
        found.append(state.workspace)
    frontier = [state.workspace]
    for _depth in range(2):
        next_frontier: list[Path] = []
        for parent in frontier:
            try:
                children = sorted(parent.iterdir(), key=lambda p: p.name)
            except OSError:
                continue
            for child in children:
                if child.name.startswith(".") or child.name in SKIPPED_DIR_NAMES:
                    continue
                if child.is_symlink() or not child.is_dir():
                    continue
                if _is_project_dir(child):
                    found.append(child)
                else:
                    next_frontier.append(child)
                if len(found) >= MAX_PROJECTS:
                    break
        frontier = next_frontier
    return [project_summary(state, root) for root in found[:MAX_PROJECTS]]


def project_summary(state: StudioState, root: Path) -> dict[str, Any]:
    plan = _read_json_file(root / "reel.json")
    runner_state = _read_json_file(root / ".formats/state.json")
    summary: dict[str, Any] = {
        "path": project_label(state, root),
        "name": root.name,
        "id": plan.get("id") if isinstance(plan, dict) else None,
        "format_id": None,
        "status": "timeline" if isinstance(plan, dict) else "unknown",
        "pending_gate": None,
        "updated_at": None,
    }
    if isinstance(runner_state, dict):
        summary["format_id"] = runner_state.get("format_id")
        summary["status"] = runner_state.get("status")
        summary["pending_gate"] = runner_state.get("pending_gate")
        summary["updated_at"] = runner_state.get("updated_at")
    return summary


def _listing(root: Path, relative_dir: str, suffixes: tuple[str, ...]) -> list[str]:
    try:
        directory = contained_path(root, relative_dir, must_exist=False)
    except ValueError:
        return []
    if not directory.is_dir() or directory.is_symlink():
        return []
    items: list[str] = []
    for child in sorted(directory.iterdir(), key=lambda p: p.name):
        if child.is_file() and not child.is_symlink() and child.suffix.lower() in suffixes:
            items.append(child.relative_to(root).as_posix())
    return items[:200]


def _scene_rows(root: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    locks = _read_json_file(root / ".reelsyntax/scene-locks.json")
    locked_ids = set(locks.keys()) if isinstance(locks, dict) else set()
    rows: list[dict[str, Any]] = []
    start = 0
    for scene in plan.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        params = scene.get("params") if isinstance(scene.get("params"), dict) else {}
        frames = int(scene.get("duration_frames", 0) or 0)
        rows.append({
            "id": str(scene.get("id", "")),
            "engine": scene.get("engine"),
            "recipe": scene.get("recipe"),
            "duration_frames": frames,
            "frame_range": [start, start + frames],
            "heading": _safe_text(params.get("heading", ""), 160),
            "subheading": _safe_text(params.get("subheading", ""), 200),
            "colors": [str(params[key]) for key in ("background", "foreground", "accent") if isinstance(params.get(key), str)],
            "locked": str(scene.get("id", "")) in locked_ids,
        })
        start += frames
    return rows


def _step_rows(runner_state: dict[str, Any]) -> list[dict[str, Any]]:
    raw_manifest = runner_state.get("manifest")
    manifest = raw_manifest if isinstance(raw_manifest, dict) else {}
    raw_steps = manifest.get("steps")
    steps = raw_steps if isinstance(raw_steps, list) else []
    raw_completed = runner_state.get("completed_steps")
    completed = raw_completed if isinstance(raw_completed, dict) else {}
    raw_approvals = runner_state.get("approvals")
    approvals = raw_approvals if isinstance(raw_approvals, dict) else {}
    current = runner_state.get("current_step_index")
    pending = runner_state.get("pending_gate")
    rows: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        sid = str(step.get("id", ""))
        output = completed.get(sid)
        detail: dict[str, Any] = {}
        if isinstance(output, dict):
            for key in ("profile", "scope", "artifact", "frames", "simulated", "technical_status"):
                if key in output:
                    detail[key] = output[key]
            previews = output.get("previews")
            if isinstance(previews, list):
                detail["previews"] = [str(p) for p in previews][:64]
        approval = approvals.get(sid)
        rows.append({
            "id": sid,
            "type": step.get("type"),
            "gate": step.get("gate"),
            "profile": step.get("profile"),
            "completed": sid in completed,
            "approved": bool(isinstance(approval, dict) and approval.get("approved")),
            "pending": sid == pending,
            "current": index == current,
            "output": detail,
        })
    return rows


def _qc_reports(root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for rel in _listing(root, "review", (".json",)):
        if not rel.endswith("-qc.json"):
            continue
        doc = _read_json_file(root / rel, max_bytes=4_194_304)
        if not isinstance(doc, dict):
            continue
        checks = []
        for check in doc.get("checks", []) if isinstance(doc.get("checks"), list) else []:
            if isinstance(check, dict):
                checks.append({
                    "id": _safe_text(check.get("id", ""), 80),
                    "status": _safe_text(check.get("status", ""), 32),
                    "observed": _safe_text(check.get("observed", "")),
                    "expected": _safe_text(check.get("expected", "")),
                })
        reports.append({
            "path": rel,
            "profile": doc.get("profile") or rel.rsplit("/", 1)[-1][: -len("-qc.json")],
            "technical_status": doc.get("technical_status"),
            "release_status": doc.get("release_status"),
            "checks": checks[:200],
        })
    return reports


def project_detail(state: StudioState, relative: Any) -> dict[str, Any]:
    root = resolve_project(state, relative)
    plan = _read_json_file(root / "reel.json")
    runner_state = _read_json_file(root / ".formats/state.json")
    prompt_doc = _read_json_file(root / "prompt.json")
    detail: dict[str, Any] = project_summary(state, root)
    detail["timeline"] = None
    if isinstance(plan, dict):
        raw_output = plan.get("output")
        output = raw_output if isinstance(raw_output, dict) else {}
        scenes = _scene_rows(root, plan)
        detail["timeline"] = {
            "id": plan.get("id"),
            "width": output.get("width"),
            "height": output.get("height"),
            "fps": output.get("fps"),
            "frames": sum(s["duration_frames"] for s in scenes),
            "scenes": scenes,
        }
    detail["workflow"] = None
    if isinstance(runner_state, dict):
        raw_intent = runner_state.get("intent")
        intent = raw_intent if isinstance(raw_intent, dict) else {}
        detail["workflow"] = {
            "format_id": runner_state.get("format_id"),
            "format_version": runner_state.get("format_version"),
            "provider": runner_state.get("provider"),
            "status": runner_state.get("status"),
            "current_step_index": runner_state.get("current_step_index"),
            "pending_gate": runner_state.get("pending_gate"),
            "aspect": intent.get("aspect"),
            "duration_sec": intent.get("duration_sec"),
            "video_lang": intent.get("video_lang"),
            "steps": _step_rows(runner_state),
        }
    detail["prompt"] = None
    if isinstance(prompt_doc, dict):
        raw_revisions = prompt_doc.get("revisions")
        revisions = raw_revisions if isinstance(raw_revisions, list) else []
        raw_langs = prompt_doc.get("languages")
        detail["prompt"] = {
            "text": _safe_text(prompt_doc.get("prompt", ""), 2000),
            "languages": raw_langs if isinstance(raw_langs, dict) else {},
            "revisions": len(revisions),
        }
    detail["snapshots"] = _listing(root, ".formats/snapshots", (".png", ".jpg", ".jpeg", ".webp"))
    videos = _listing(root, "output", (".mp4", ".webm")) + _listing(root, ".formats/pilot/output", (".mp4", ".webm"))
    detail["videos"] = [{"path": rel, "bytes": (root / rel).stat().st_size} for rel in videos]
    detail["qc"] = _qc_reports(root)
    return detail


def resolve_media(state: StudioState, project: Any, relative: Any) -> Path:
    root = resolve_project(state, project)
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise StudioHttpError(400, "Expected a media path relative to the project")
    try:
        target = contained_path(root, relative, must_exist=False)
    except ValueError as error:
        raise StudioHttpError(400, str(error)) from error
    allowed_location = relative in MEDIA_ROOT_FILES or relative.startswith(MEDIA_PREFIXES)
    if not allowed_location or target.suffix.lower() not in MEDIA_TYPES:
        raise StudioHttpError(403, "This file type or location is not served by the studio")
    if not target.is_file():
        raise StudioHttpError(404, "Media file not found")
    return target


def format_rows(state: StudioState) -> list[dict[str, Any]]:
    from ..formats.registry import discover_formats
    from ..make import BUILTIN_PROMPT_DIRECT_MANIFEST

    rows = discover_formats(extra_roots=state.extra_format_roots)
    if not any(row["id"] == "prompt-direct" for row in rows):
        rows = rows + [{**BUILTIN_PROMPT_DIRECT_MANIFEST, "builtin": True}]
    keys = ("id", "version", "title", "category", "aspect", "duration_sec", "languages", "engines", "needs", "optional", "qc_rules")
    out: list[dict[str, Any]] = []
    for row in rows:
        item = {key: row.get(key) for key in keys}
        item["builtin"] = bool(row.get("builtin"))
        item["steps"] = [
            {"id": s.get("id"), "type": s.get("type"), "gate": s.get("gate"), "profile": s.get("profile")}
            for s in row.get("steps", [])
            if isinstance(s, dict)
        ]
        out.append(item)
    return out


def available_locales() -> list[dict[str, str]]:
    from ..lang.catalog import load_locale_status, locales_directory

    status = load_locale_status()
    loc_dir = locales_directory()
    out = []
    for code, meta in sorted(status["locales"].items()):
        if (loc_dir / f"{code}.json").is_file():
            out.append({"code": code, "name": str(meta.get("native_name") or meta.get("name") or code)})
    return out


def normalize_locale(candidate: Any, fallback: str = "en") -> str:
    codes = {entry["code"] for entry in available_locales()}
    if isinstance(candidate, str) and candidate in codes:
        return candidate
    if isinstance(candidate, str) and candidate.split("-", 1)[0] in codes:
        return candidate.split("-", 1)[0]
    return fallback if fallback in codes else "en"


def ui_strings(locale: str) -> dict[str, str]:
    from ..lang.catalog import fallback_chain, load_catalog

    merged: dict[str, str] = {}
    for code in reversed(fallback_chain(locale)):
        try:
            catalog = load_catalog(code)
        except ValueError:
            continue
        for key, value in catalog.items():
            if isinstance(value, str) and key.startswith(UI_KEY_PREFIXES):
                merged[key] = value
    return merged


def session_payload(state: StudioState, requested_locale: Any = None) -> dict[str, Any]:
    locale = normalize_locale(requested_locale, state.locale)
    return {
        "version": __version__,
        "csrf_token": state.csrf_token,
        "csrf_header": CSRF_HEADER,
        "locale": locale,
        "locales": available_locales(),
        "strings": ui_strings(locale),
        "workspace": state.workspace.name or str(state.workspace),
        "offline": True,
        "aspects": list(ASPECTS),
        "profiles": list(PROFILES),
    }


def _optional_text(body: dict[str, Any], key: str, limit: int) -> str | None:
    value = body.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _required_text(body, key, limit)


def _required_text(body: dict[str, Any], key: str, limit: int) -> str:
    value = body.get(key)
    if value is None:
        raise StudioHttpError(400, f"Missing field: {key}")
    if not isinstance(value, str) or not value.strip():
        raise StudioHttpError(400, f"Field {key!r} must be a nonempty string")
    if len(value) > limit:
        raise StudioHttpError(400, f"Field {key!r} exceeds {limit} characters")
    return value.strip()


def _body_int(body: dict[str, Any], key: str, low: int, high: int) -> int | None:
    value = body.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise StudioHttpError(400, f"Field {key!r} must be an integer between {low} and {high}")
    return int(value)


def action_step(state: StudioState, body: dict[str, Any]) -> dict[str, Any]:
    from ..make import step_project

    root = resolve_project(state, body.get("project"))
    step_id = _required_text(body, "step_id", 64)
    if not STEP_ID_RE.fullmatch(step_id):
        raise StudioHttpError(400, "Invalid step identifier")
    action = body.get("action")
    if action not in STEP_ACTIONS:
        raise StudioHttpError(400, f"Field 'action' must be one of {sorted(STEP_ACTIONS)}")
    instruction = _required_text(body, "instruction", 600) if action == "edit" else None
    result = step_project(
        root,
        step_id,
        approve=action == "approve",
        edit=instruction,
        back=action == "back",
        allow_network=False,
        extra_format_roots=state.extra_format_roots,
        dry_run_render=state.dry_run_render,
    )
    result["project"] = project_label(state, root)
    result.pop("next_actions", None)
    return result


def action_revise(state: StudioState, body: dict[str, Any]) -> dict[str, Any]:
    from ..make import revise_project

    root = resolve_project(state, body.get("project"))
    instruction = _required_text(body, "instruction", 600)
    scene = _optional_text(body, "scene", 96)
    if scene is not None and not SCENE_ID_RE.fullmatch(scene):
        raise StudioHttpError(400, "Invalid scene identifier")
    render_after = body.get("render", False)
    if not isinstance(render_after, bool):
        raise StudioHttpError(400, "Field 'render' must be a boolean")
    result = revise_project(
        root,
        instruction,
        scene_id=scene,
        allow_network=False,
        render_after=render_after,
        profile="draft" if render_after else None,
    )
    result["project"] = project_label(state, root)
    return result


def _unique_project_dir(state: StudioState, name: str, explicit: bool) -> Path:
    for suffix in range(1, 1000):
        candidate = name if suffix == 1 else f"{name[:58]}-{suffix}"
        try:
            target = contained_path(state.workspace, f"out/{candidate}", must_exist=False)
        except ValueError as error:
            raise StudioHttpError(400, str(error)) from error
        if not target.exists() or (target.is_dir() and not any(target.iterdir())):
            return target
        if explicit:
            raise StudioHttpError(409, f"Project folder out/{name} already exists and is not empty")
    raise StudioHttpError(409, "Could not allocate a free project folder")


def action_make(state: StudioState, body: dict[str, Any]) -> dict[str, Any]:
    from ..formats.schema import FORMAT_ID_RE
    from ..lang.catalog import LOCALE_TAG_RE
    from ..make import make_video
    from ..prompt.compiler import sanitize_project_id

    prompt = _required_text(body, "prompt", 2000)
    format_id = _optional_text(body, "format_id", 64)
    if format_id is not None and not FORMAT_ID_RE.fullmatch(format_id):
        raise StudioHttpError(400, "Invalid format identifier")
    aspect = _optional_text(body, "aspect", 8)
    if aspect is not None and aspect not in ASPECTS:
        raise StudioHttpError(400, f"Field 'aspect' must be one of {list(ASPECTS)}")
    lang = _optional_text(body, "lang", 16)
    if lang is not None and not LOCALE_TAG_RE.fullmatch(lang):
        raise StudioHttpError(400, "Invalid video language tag")
    duration = _body_int(body, "duration", 1, 600)
    seed = _body_int(body, "seed", 0, 0xFFFFFFFF)
    dry_run = body.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise StudioHttpError(400, "Field 'dry_run' must be a boolean")
    name = _optional_text(body, "name", 64)
    if name is not None and not FOLDER_NAME_RE.fullmatch(name):
        raise StudioHttpError(400, "Folder name may use lowercase letters, digits, '-' and '_' only")
    target: Path | None = None
    if not dry_run:
        target = _unique_project_dir(state, name or sanitize_project_id(prompt[:40]), explicit=name is not None)
    result = make_video(
        prompt,
        format_id=format_id,
        out_dir=target,
        video_lang=lang,
        ui_lang=state.locale,
        aspect=aspect,
        duration_sec=duration,
        seed=42 if seed is None else seed,
        yes=False,
        dry_run=dry_run,
        allow_network=False,
        extra_format_roots=state.extra_format_roots,
        dry_run_render=state.dry_run_render,
    )
    if target is not None:
        result["project"] = project_label(state, target)
        result.pop("next_actions", None)
    return result


POST_ACTIONS = {
    "/api/step": action_step,
    "/api/revise": action_revise,
    "/api/make": action_make,
}


def _parse_range(header: str, size: int) -> tuple[int, int]:
    match = RANGE_RE.fullmatch(header.strip())
    if not match or size <= 0:
        raise StudioHttpError(416, "Unsatisfiable range")
    first, last = match.group(1), match.group(2)
    if not first and not last:
        raise StudioHttpError(416, "Unsatisfiable range")
    if not first:
        length = int(last)
        if length <= 0:
            raise StudioHttpError(416, "Unsatisfiable range")
        return max(0, size - length), size - 1
    start = int(first)
    end = int(last) if last else size - 1
    if start >= size or end < start:
        raise StudioHttpError(416, "Unsatisfiable range")
    return start, min(end, size - 1)


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "ReelSyntaxStudio/" + __version__
    sys_version = ""

    @property
    def studio(self) -> StudioState:
        return cast(StudioServer, self.server).studio

    def log_message(self, format: str, *args: Any) -> None:
        if not self.studio.quiet:
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def _handle(self, method: str) -> None:
        try:
            self._check_host()
            url = urlsplit(self.path)
            query = {key: values[-1] for key, values in parse_qs(url.query, max_num_fields=16).items()}
            if method == "GET":
                self._route_get(url.path, query)
            elif method == "POST":
                self._route_post(url.path)
            else:
                raise StudioHttpError(405, "Method not allowed")
        except StudioHttpError as error:
            self._send_json(error.status, {"ok": False, "error": error.message})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (ValueError, KeyError, TypeError) as error:
            self._send_json(400, {"ok": False, "error": str(error)})
        except FileNotFoundError as error:
            self._send_json(404, {"ok": False, "error": str(error)})
        except (OSError, RuntimeError) as error:
            self._send_json(500, {"ok": False, "error": str(error)})

    def _check_host(self) -> None:
        host = (self.headers.get("Host") or "").strip().lower()
        if host in self.studio.allowed_host_headers():
            return
        if self.studio.allow_non_loopback and host:
            parts = urlsplit("//" + host)
            try:
                port = parts.port
            except ValueError:
                port = None
            if parts.hostname and _is_ip_literal(parts.hostname) and port == self.studio.port:
                return
        raise StudioHttpError(400, "Host header is not allowed for this local studio")

    def _check_origin(self) -> None:
        site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if site and site not in {"same-origin", "none"}:
            raise StudioHttpError(403, "Cross-site request rejected")
        origin = self.headers.get("Origin")
        if origin is None:
            return
        parts = urlsplit(origin.strip())
        if parts.scheme != "http" or parts.netloc.lower() != (self.headers.get("Host") or "").strip().lower():
            raise StudioHttpError(403, "Cross-origin request rejected")

    def _route_get(self, route: str, query: dict[str, str]) -> None:
        if route in {"/", "/index.html"}:
            self._send_index()
        elif route in STATIC_ROUTES:
            name, ctype = STATIC_ROUTES[route]
            self._send_bytes(200, (UI_ASSET_DIR / name).read_bytes(), ctype)
        elif route == "/favicon.ico":
            self._send_bytes(204, b"", "text/plain; charset=utf-8")
        elif route == "/api/session":
            self._send_json(200, {"ok": True, "result": session_payload(self.studio, query.get("lang"))})
        elif route == "/api/formats":
            rows = format_rows(self.studio)
            self._send_json(200, {"ok": True, "result": {"total": len(rows), "formats": rows}})
        elif route == "/api/projects":
            rows = discover_projects(self.studio)
            self._send_json(200, {"ok": True, "result": {"total": len(rows), "projects": rows}})
        elif route == "/api/project":
            self._send_json(200, {"ok": True, "result": project_detail(self.studio, query.get("project"))})
        elif route == "/api/media":
            self._send_media(resolve_media(self.studio, query.get("project"), query.get("path")))
        else:
            raise StudioHttpError(404, "Not found")

    def _route_post(self, route: str) -> None:
        action = POST_ACTIONS.get(route)
        if action is None:
            raise StudioHttpError(404, "Not found")
        self._check_origin()
        token = self.headers.get(CSRF_HEADER) or ""
        if not token or not hmac.compare_digest(token.encode("utf-8"), self.studio.csrf_token.encode("utf-8")):
            raise StudioHttpError(403, "Missing or invalid CSRF token")
        body = self._read_json_body()
        if not self.studio.operation_lock.acquire(blocking=False):
            raise StudioHttpError(409, "Another studio operation is still running")
        try:
            from ..config import config_context

            project_hint = self.studio.workspace
            if isinstance(body.get("project"), str):
                project_hint = resolve_project(self.studio, body["project"])
            with config_context(self.studio.config_file, project_hint):
                result = action(self.studio, body)
        finally:
            self.studio.operation_lock.release()
        self._send_json(200, {"ok": True, "result": result})

    def _read_json_body(self) -> dict[str, Any]:
        ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            raise StudioHttpError(415, "Expected Content-Type: application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise StudioHttpError(411, "Content-Length required")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise StudioHttpError(400, "Invalid Content-Length") from error
        if length < 0:
            raise StudioHttpError(400, "Invalid Content-Length")
        if length > MAX_BODY_BYTES:
            raise StudioHttpError(413, "Request body too large")
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StudioHttpError(400, "Request body must be UTF-8 JSON") from error
        if not isinstance(body, dict):
            raise StudioHttpError(400, "Request body must be a JSON object")
        return body

    def _send_index(self) -> None:
        template = (UI_ASSET_DIR / "index.html").read_text(encoding="utf-8")
        page = template.replace(CSRF_META_PLACEHOLDER, html.escape(self.studio.csrf_token, quote=True))
        page = page.replace(LANG_PLACEHOLDER, html.escape(self.studio.locale, quote=True))
        self._send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def _send_media(self, path: Path) -> None:
        ctype = MEDIA_TYPES[path.suffix.lower()]
        size = path.stat().st_size
        range_header = self.headers.get("Range")
        start, end, status = 0, size - 1, 200
        extra = {"Accept-Ranges": "bytes"}
        if range_header:
            try:
                parsed = _parse_range(range_header, size)
            except StudioHttpError:
                self._send_bytes(416, b"", "text/plain; charset=utf-8", {"Content-Range": f"bytes */{size}"})
                return
            start, end = parsed
            status = 206
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        length = max(0, end - start + 1)
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        for key, value in extra.items():
            self.send_header(key, value)
        self.end_headers()
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(STREAM_CHUNK, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _security_headers(self) -> None:
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)

    def _send_bytes(self, status: int, payload: bytes, ctype: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    studio: StudioState


class StudioServerV6(StudioServer):
    address_family = socket.AF_INET6


def create_server(
    project: Path | str | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_non_loopback: bool = False,
    locale: str | None = None,
    config_file: Path | str | None = None,
    extra_format_roots: tuple[Path, ...] = (),
    dry_run_render: bool = False,
    quiet: bool = True,
) -> StudioServer:
    bind_host = validate_bind_host(host, allow_non_loopback)
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer between 0 and 65535")
    workspace = Path(project if project is not None else Path.cwd()).expanduser().resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError(f"Studio project path is not a directory: {workspace}")
    bare_host = bind_host.strip("[]")
    server_cls = StudioServerV6 if ":" in bare_host else StudioServer
    server = server_cls((bare_host, port), StudioHandler)
    from ..lang.catalog import resolve_ui_locale

    server.studio = StudioState(
        workspace=workspace,
        csrf_token=secrets.token_urlsafe(32),
        locale=normalize_locale(resolve_ui_locale(explicit=locale)),
        bind_host=bind_host,
        port=int(server.server_address[1]),
        allow_non_loopback=allow_non_loopback,
        config_file=Path(config_file).expanduser() if config_file is not None else None,
        extra_format_roots=tuple(Path(p) for p in extra_format_roots),
        dry_run_render=dry_run_render,
        quiet=quiet,
    )
    return server


def studio_url(server: StudioServer) -> str:
    host = server.studio.bind_host.strip("[]")
    shown = f"[{host}]" if ":" in host else host
    return f"http://{shown}:{server.studio.port}/"


def serve(
    project: Path | str | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    allow_non_loopback: bool = False,
    locale: str | None = None,
    config_file: Path | str | None = None,
) -> int:
    server = create_server(
        project,
        host=host,
        port=port,
        allow_non_loopback=allow_non_loopback,
        locale=locale,
        config_file=config_file,
        quiet=False,
    )
    url = studio_url(server)
    loopback = is_loopback_host(server.studio.bind_host)
    print(json.dumps({
        "ok": True,
        "command": "ui",
        "result": {
            "url": url,
            "host": server.studio.bind_host,
            "port": server.studio.port,
            "workspace": str(server.studio.workspace),
            "loopback": loopback,
            "locale": server.studio.locale,
        },
    }, ensure_ascii=False), flush=True)
    if not loopback:
        print(
            json.dumps({"warning": "Studio is reachable from other machines on this network; anyone who can load the page can start renders."}),
            file=sys.stderr,
            flush=True,
        )
    if open_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
