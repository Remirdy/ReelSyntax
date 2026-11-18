import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
import urllib.error
import urllib.request

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json

from ...config import ResolvedConfig, _check_endpoint, _check_text, load_config
from ...prompt.intent import sanitize_user_prompt
from ...prompt.providers.base import is_loopback_endpoint
from ..license import (
    APPROVED_SPDX_LICENSES,
    collect_synthetic_origin,
    record_asset_license,
    write_licenses_markdown,
)

MAX_GENERATED_BYTES = 32 * 1024 * 1024
MAX_JSON_ENVELOPE_BYTES = 48 * 1024 * 1024
ALLOWED_KINDS = frozenset({"image", "audio", "video"})
ALLOWED_ASPECTS = frozenset({"9:16", "1:1", "16:9", "4:5"})
ALLOWED_GENERATED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp4"})
KIND_DEFAULT_EXT = {"image": ".png", "audio": ".wav", "video": ".mp4"}
MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "video/mp4": ".mp4",
}
RESERVED_ROOT_PARTS = frozenset({".reelsyntax", "output", "review"})
RESERVED_FILENAMES = frozenset({"reel.json", "prompt.json", "manifest.json", "LICENSES.md", "reelsyntax.toml"})
DEFAULT_SYNTHETIC_DISCLOSURE = "Synthetic media produced by an opt-in external generative adapter"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:32] or "generated"


def validate_media_signature(data: bytes, ext: str) -> None:
    if not data:
        raise ValueError("Generative adapter returned an empty media payload")
    if len(data) > MAX_GENERATED_BYTES:
        raise ValueError("Generative media payload exceeds 32 MiB size budget")
    lower = ext.lower()
    if lower == ".png":
        valid = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif lower in {".jpg", ".jpeg"}:
        valid = data.startswith(b"\xff\xd8\xff")
    elif lower == ".webp":
        valid = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif lower == ".wav":
        valid = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    elif lower == ".mp4":
        valid = len(data) >= 12 and data[4:8] == b"ftyp"
    else:
        valid = False
    if not valid:
        raise ValueError(f"Generative media payload bytes do not match declared extension {lower!r}")


def resolve_generative_policy(
    *,
    config: ResolvedConfig | None = None,
    project_dir: Path | str | None = None,
    endpoint: str | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    cfg = config if config is not None else load_config(project=project_dir)
    if not cfg.generative.enabled:
        raise ValueError(
            "Generative media adapter is disabled by default; set [generative] enabled = true in reelsyntax.toml or REELSYNTAX_GENERATIVE_ENABLED=true"
        )
    raw_endpoint = endpoint if endpoint is not None else cfg.generative.endpoint
    _check_endpoint(raw_endpoint, "generative.endpoint")
    chosen_endpoint = raw_endpoint.rstrip("/")
    if not chosen_endpoint:
        raise ValueError("Generative media adapter requires an explicit [generative] endpoint URL (or --endpoint)")
    loopback = is_loopback_endpoint(chosen_endpoint)
    effective_network = bool(allow_network or cfg.general.allow_network)
    if not loopback and not effective_network:
        raise ValueError(
            f"Remote generative endpoint {chosen_endpoint!r} requires --allow-network or general.allow_network = true"
        )
    return {
        "enabled": True,
        "endpoint": chosen_endpoint,
        "loopback": loopback,
        "allow_network": effective_network,
        "timeout_sec": int(cfg.generative.timeout_sec),
        "spdx": cfg.generative.spdx,
        "attribution": cfg.generative.attribution,
    }


def _checked_destination(root: Path, dest_rel: str) -> Path:
    dest = contained_path(root, dest_rel, must_exist=False)
    rel = dest.relative_to(root)
    if not rel.parts or rel.parts[0] in RESERVED_ROOT_PARTS or rel.name in RESERVED_FILENAMES:
        raise ValueError(f"Generative media output cannot target reserved path {rel.as_posix()!r}")
    if dest.suffix.lower() not in ALLOWED_GENERATED_EXTENSIONS:
        raise ValueError(
            f"Unsupported generative media extension {dest.suffix!r}; allowed: {sorted(ALLOWED_GENERATED_EXTENSIONS)}"
        )
    return dest


class _RefuseRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise ValueError(f"Generative adapter refused HTTP redirect to {newurl!r}")


def _write_bytes_atomic(dest: Path, payload: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.chmod(temporary, 0o644)
        os.replace(temporary, dest)
    finally:
        temporary.unlink(missing_ok=True)


def stamp_synthetic_origin(project_dir: Path | str) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    provenance = collect_synthetic_origin(root)
    now = datetime.now(timezone.utc).isoformat()

    prompt_path = contained_path(root, "prompt.json", must_exist=False)
    if prompt_path.is_file():
        prompt_doc = read_json(prompt_path)
        if not isinstance(prompt_doc, dict):
            raise ValueError("prompt.json must be a JSON object")
    else:
        prompt_doc = {"schema_version": 1}
    prompt_doc["synthetic_origin"] = provenance
    prompt_doc["updated_at"] = now
    atomic_json(prompt_path, prompt_doc)

    manifest_path = contained_path(root, "manifest.json", must_exist=False)
    if manifest_path.is_file():
        manifest_doc = read_json(manifest_path)
        if not isinstance(manifest_doc, dict):
            raise ValueError("manifest.json must be a JSON object")
    else:
        manifest_doc = {"schema_version": 1}
    manifest_doc["synthetic_origin"] = provenance
    manifest_doc["updated_at"] = now
    atomic_json(manifest_path, manifest_doc)

    out_dir = contained_path(root, "output", must_exist=False)
    if out_dir.is_dir():
        for profile in ("draft", "production", "hero"):
            p_manifest = contained_path(root, f"output/{profile}-manifest.json", must_exist=False)
            if p_manifest.is_file():
                doc = read_json(p_manifest)
                if isinstance(doc, dict):
                    doc["synthetic_origin"] = provenance
                    atomic_json(p_manifest, doc)

    return provenance


def _decode_response(raw_body: bytes, content_type: str, default_ext: str) -> tuple[bytes, str, dict[str, Any]]:
    ctype = content_type.split(";", 1)[0].strip().lower()
    if ctype == "application/json" or raw_body.lstrip().startswith(b"{"):
        try:
            envelope = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Generative adapter returned invalid JSON: {error}") from error
        if not isinstance(envelope, dict):
            raise ValueError("Generative adapter JSON response must be an object")
        encoded = envelope.get("data_base64")
        if not isinstance(encoded, str) or not encoded.strip():
            raise ValueError("Generative adapter JSON response requires non-empty 'data_base64'")
        try:
            media_bytes = base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise ValueError(f"Generative adapter returned invalid base64 media: {error}") from error
        mime = str(envelope.get("mime_type", "")).split(";", 1)[0].strip().lower()
        ext = MIME_TO_EXT.get(mime, default_ext)
        meta = {
            key: envelope[key]
            for key in ("spdx", "attribution", "generator", "adapter", "model")
            if isinstance(envelope.get(key), str) and envelope[key].strip()
        }
        return media_bytes, ext, meta
    if ctype in MIME_TO_EXT:
        return raw_body, MIME_TO_EXT[ctype], {}
    if not ctype or ctype == "application/octet-stream":
        return raw_body, default_ext, {}
    raise ValueError(f"Unsupported generative adapter response content type: {ctype!r}")


def generate_media_asset(
    project_dir: Path | str,
    prompt: str,
    *,
    kind: str = "image",
    dest_rel: str | None = None,
    endpoint: str | None = None,
    aspect: str = "9:16",
    seed: int = 42,
    spdx: str | None = None,
    attribution: str | None = None,
    allow_network: bool = False,
    config: ResolvedConfig | None = None,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project path must be an existing directory")
    policy = resolve_generative_policy(
        config=config,
        project_dir=root,
        endpoint=endpoint,
        allow_network=allow_network,
    )
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"Unsupported generative asset kind {kind!r}; expected {sorted(ALLOWED_KINDS)}")
    if aspect not in ALLOWED_ASPECTS:
        raise ValueError(f"Unsupported aspect ratio {aspect!r}")
    clean_prompt = sanitize_user_prompt(prompt)
    if dest_rel is not None:
        _checked_destination(root, dest_rel)

    payload = {
        "kind": kind,
        "prompt": clean_prompt,
        "aspect": aspect,
        "seed": int(seed) & 0xFFFFFFFF,
    }
    req = urllib.request.Request(
        policy["endpoint"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json, image/*, audio/*, video/*"},
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(_RefuseRedirectHandler())
        with opener.open(req, timeout=policy["timeout_sec"]) as resp:
            raw_body = resp.read(MAX_JSON_ENVELOPE_BYTES + 1)
            if len(raw_body) > MAX_JSON_ENVELOPE_BYTES:
                raise ValueError("Generative adapter response exceeds maximum envelope budget")
            content_type = str(resp.headers.get("Content-Type", ""))
    except urllib.error.URLError as error:
        raise ValueError(f"Generative adapter request failed ({policy['endpoint']}): {error.reason}") from error
    except (http.client.HTTPException, OSError) as error:
        raise ValueError(f"Generative adapter request failed ({policy['endpoint']}): {error}") from error

    default_ext = Path(dest_rel).suffix.lower() if dest_rel else KIND_DEFAULT_EXT[kind]
    media_bytes, resolved_ext, remote_meta = _decode_response(raw_body, content_type, default_ext)

    chosen_rel = dest_rel
    if chosen_rel is None:
        short_hash = hashlib.sha256(f"{clean_prompt}:{seed}:{kind}".encode("utf-8")).hexdigest()[:10]
        chosen_rel = f"assets/generated/{_slugify(clean_prompt)}-{short_hash}{resolved_ext}"
    dest = _checked_destination(root, chosen_rel)
    validate_media_signature(media_bytes, dest.suffix)

    chosen_spdx = (spdx if spdx is not None else remote_meta.get("spdx") or policy["spdx"]).strip()
    if chosen_spdx not in APPROVED_SPDX_LICENSES:
        raise ValueError(f"Unsupported SPDX license {chosen_spdx!r}; allowed: {sorted(APPROVED_SPDX_LICENSES)}")
    if attribution is not None:
        _check_text(attribution, 256, "generative.attribution")
        chosen_attrib = attribution.strip()
        if not chosen_attrib:
            raise ValueError("Synthetic media attribution disclosure cannot be empty")
    else:
        raw_attrib = remote_meta.get("attribution") or policy["attribution"] or DEFAULT_SYNTHETIC_DISCLOSURE
        _check_text(raw_attrib, 256, "generative.attribution")
        chosen_attrib = raw_attrib.strip()
        if not chosen_attrib:
            raise ValueError("Synthetic media attribution disclosure cannot be empty")

    adapter_name = _check_text(remote_meta.get("adapter") or "external_http", 128, "generative.adapter").strip() or "external_http"
    _write_bytes_atomic(dest, media_bytes)
    normalized_rel = dest.relative_to(root).as_posix()
    origin_meta: dict[str, Any] = {
        "synthetic": True,
        "disclosed": True,
        "kind": kind,
        "adapter": adapter_name,
        "endpoint": policy["endpoint"],
        "seed": int(seed) & 0xFFFFFFFF,
    }
    if remote_meta.get("generator"):
        origin_meta["generator"] = _check_text(remote_meta["generator"], 128, "generative.generator").strip()

    entry = record_asset_license(
        root,
        normalized_rel,
        spdx=chosen_spdx,
        source_kind="generative",
        author="External Generative Adapter",
        attribution=chosen_attrib,
        source_url=policy["endpoint"],
        synthetic_origin=origin_meta,
    )
    write_licenses_markdown(root)
    provenance = stamp_synthetic_origin(root)
    return {
        "path": normalized_rel,
        "kind": kind,
        "spdx": entry["spdx"],
        "sha256": entry["sha256"],
        "bytes": len(media_bytes),
        "endpoint": policy["endpoint"],
        "attribution": entry["attribution"],
        "synthetic_origin": provenance,
        "license_entry": entry,
    }
