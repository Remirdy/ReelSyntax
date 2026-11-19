from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path, read_json

from ..ingest import scene_sources
from ..project import load
from ..skills import file_digest

APPROVED_SPDX_LICENSES = frozenset({
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "CC0-1.0",
    "CC-BY-4.0",
    "OFL-1.1",
    "User-Provided",
})

ATTRIBUTION_REQUIRED_SPDX = frozenset({
    "CC-BY-4.0",
})


def ledger_path(project_dir: Path) -> Path:
    return contained_path(Path(project_dir), ".reelsyntax/asset-licenses.json", must_exist=False)


def validate_license_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("Asset license entry must be an object")
    rel_path = entry.get("path")
    if not isinstance(rel_path, str) or not rel_path.strip() or rel_path.startswith("/") or ".." in Path(rel_path).parts:
        raise ValueError(f"Invalid project-relative asset path: {rel_path!r}")
    spdx = entry.get("spdx")
    if not isinstance(spdx, str) or spdx not in APPROVED_SPDX_LICENSES:
        raise ValueError(
            f"Disallowed or unknown asset SPDX license {spdx!r}; allowed: {sorted(APPROVED_SPDX_LICENSES)}"
        )
    attribution = str(entry.get("attribution", "")).strip()
    author = str(entry.get("author", "")).strip()
    if spdx in ATTRIBUTION_REQUIRED_SPDX and not (attribution or author):
        raise ValueError(f"License {spdx} requires non-empty 'author' or 'attribution'")
    sha = entry.get("sha256")
    if not isinstance(sha, str) or len(sha) != 64:
        raise ValueError(f"Invalid asset SHA-256 digest for {rel_path!r}")
    source_kind = str(entry.get("source_kind", "user_local"))
    synthetic_origin = entry.get("synthetic_origin")
    if source_kind == "generative":
        if not attribution:
            raise ValueError(f"Synthetic media asset {rel_path!r} requires non-empty disclosure attribution")
        if (
            not isinstance(synthetic_origin, dict)
            or synthetic_origin.get("synthetic") is not True
            or synthetic_origin.get("disclosed") is not True
        ):
            raise ValueError(f"Synthetic media asset {rel_path!r} requires valid synthetic_origin provenance")
    out = {
        "path": Path(rel_path).as_posix(),
        "spdx": spdx,
        "source_kind": source_kind,
        "author": author or "Unspecified",
        "attribution": attribution,
        "source_url": str(entry.get("source_url", "")),
        "sha256": sha,
        "recorded_at": str(entry.get("recorded_at") or datetime.now(timezone.utc).isoformat()),
    }
    if isinstance(synthetic_origin, dict):
        out["synthetic_origin"] = dict(synthetic_origin)
    return out


def load_license_ledger(project_dir: Path | str) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    lpath = ledger_path(root)
    if not lpath.is_file():
        return {"schema_version": 1, "assets": {}}
    raw = read_json(lpath, max_bytes=524_288)
    if not isinstance(raw, dict) or not isinstance(raw.get("assets"), dict):
        raise ValueError("Corrupted .reelsyntax/asset-licenses.json")
    return raw


def record_asset_license(
    project_dir: Path | str,
    rel_path: str,
    *,
    spdx: str,
    source_kind: str = "user_local",
    author: str = "",
    attribution: str = "",
    source_url: str = "",
    synthetic_origin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    target = contained_path(root, rel_path)
    normalized_rel = target.relative_to(root).as_posix()
    raw_entry: dict[str, Any] = {
        "path": normalized_rel,
        "spdx": spdx,
        "source_kind": source_kind,
        "author": author,
        "attribution": attribution,
        "source_url": source_url,
        "sha256": file_digest(target),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    if synthetic_origin is not None:
        raw_entry["synthetic_origin"] = dict(synthetic_origin)
    entry = validate_license_entry(raw_entry)
    ledger = load_license_ledger(root)
    ledger["assets"][normalized_rel] = entry
    atomic_json(ledger_path(root), ledger)
    return entry


def collect_synthetic_origin(project_dir: Path | str, *, paths: set[str] | None = None) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    ledger = load_license_ledger(root)
    assets: list[dict[str, Any]] = []
    for rel, raw in sorted(ledger.get("assets", {}).items()):
        if paths is not None and rel not in paths:
            continue
        if not isinstance(raw, dict) or raw.get("source_kind") != "generative":
            continue
        entry = validate_license_entry(raw)
        origin = entry.get("synthetic_origin") or {}
        record: dict[str, Any] = {
            "path": entry["path"],
            "spdx": entry["spdx"],
            "sha256": entry["sha256"],
            "attribution": entry["attribution"],
            "disclosed": True,
        }
        for key in ("kind", "adapter", "endpoint", "generator", "seed"):
            if key in origin and origin[key] is not None:
                record[key] = origin[key]
        assets.append(record)
    return {"present": bool(assets), "assets": assets}


def audit_project_licenses(project_dir: Path | str) -> dict[str, Any]:
    root, plan, _ = load(project_dir)
    ledger = load_license_ledger(root)
    recorded = ledger.get("assets", {})

    referenced: set[str] = {
        Path(src).as_posix()
        for scene in plan["scenes"]
        for src in scene_sources(scene)
    }
    delivery = plan.get("delivery", {})
    for key in ("logo", "font"):
        if key in delivery:
            referenced.add(Path(delivery[key]).as_posix())
    for track in plan.get("audio", {}).get("tracks", []):
        referenced.add(Path(track["source"]).as_posix())

    missing_entries: list[str] = []
    hash_mismatches: list[str] = []
    invalid_entries: list[str] = []
    verified: list[dict[str, Any]] = []

    for rel in sorted(referenced):
        abs_file = contained_path(root, rel)
        current_sha = file_digest(abs_file)
        rec = recorded.get(rel)
        if rec is None:
            missing_entries.append(rel)
            continue
        try:
            validated = validate_license_entry(rec)
        except ValueError:
            invalid_entries.append(rel)
            continue
        if validated["sha256"] != current_sha:
            hash_mismatches.append(rel)
            continue
        verified.append(validated)

    synthetic_assets = [item["path"] for item in verified if item.get("source_kind") == "generative"]
    ok = not missing_entries and not hash_mismatches and not invalid_entries
    return {
        "ok": ok,
        "technical_status": "pass" if ok else "fail",
        "referenced_count": len(referenced),
        "verified": verified,
        "synthetic_assets": synthetic_assets,
        "missing_licenses": missing_entries,
        "hash_mismatches": hash_mismatches,
        "invalid_entries": invalid_entries,
    }


def render_licenses_markdown(project_dir: Path | str) -> str:
    root = Path(project_dir).resolve(strict=True)
    ledger = load_license_ledger(root)
    items = [validate_license_entry(v) for _, v in sorted(ledger.get("assets", {}).items())]

    lines = [
        "# Asset Licenses",
        "",
        "This file is generated from `.reelsyntax/asset-licenses.json` and records the provenance, SPDX license identifier, and content digest for bundled or user-registered project assets.",
        "",
    ]
    if not items:
        lines.append("No external or starter file assets are registered in this project (all media is synthesized inline at render time under `CC0-1.0` / `MIT`).")
        lines.append("")
        return "\n".join(lines)

    lines.extend([
        "| Asset path | SPDX license | Source | Author / Attribution | SHA-256 (prefix) |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in items:
        attrib = (item["attribution"] or item["author"]).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        source_col = f"`{item['source_kind']}` (synthetic)" if item["source_kind"] == "generative" else f"`{item['source_kind']}`"
        short_sha = f"`{item['sha256'][:16]}`"
        lines.append(
            f"| `{item['path']}` | `{item['spdx']}` | {source_col} | {attrib} | {short_sha} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_licenses_markdown(project_dir: Path | str) -> Path:
    root = Path(project_dir).resolve(strict=True)
    out_path = contained_path(root, "LICENSES.md", must_exist=False)
    out_path.write_text(render_licenses_markdown(root), encoding="utf-8")
    return out_path
