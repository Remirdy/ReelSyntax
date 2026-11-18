from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
from zipfile import ZipFile

from ReelSyntax_Skills.tools.registry import atomic_json, canonical, contained_path, read_json

from .registry import user_formats_directory
from .schema import FORMAT_ID_RE, validate_format_directory

REMOTE_GIT_RE = re.compile(r"^(?:https?://|git://|git@|ssh://)", re.IGNORECASE)
MAX_ARCHIVE_TOTAL_BYTES = 33_554_432
DISALLOWED_TEMPLATE_RECIPES = frozenset({"custom-shader", "three-scene"})


def is_remote_git_source(source: str) -> bool:
    return bool(REMOTE_GIT_RE.match(source.strip()))


def _safe_extract_zip(archive_path: Path, destination: Path) -> Path:
    total_unpacked = 0
    with ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            rel = info.filename
            if not rel or rel.startswith("/") or "\\" in rel or ":" in rel:
                raise ValueError(f"Archive contains unsafe path: {rel!r}")
            parts = Path(rel).parts
            if any(part in {"..", "."} for part in parts):
                raise ValueError(f"Archive contains path traversal: {rel!r}")
            unix_mode = info.external_attr >> 16
            if unix_mode and (unix_mode & 0o170000) == 0o120000:
                raise ValueError(f"Archive contains symbolic link: {rel!r}")
            if info.is_dir():
                continue
            total_unpacked += info.file_size
            if total_unpacked > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError("Archive exceeds 32 MiB unpacked limit")
            out_path = contained_path(destination, rel, must_exist=False)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src_stream:
                data = src_stream.read(MAX_ARCHIVE_TOTAL_BYTES + 1)
            if len(data) > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError("Archive member exceeds size limit")
            out_path.write_bytes(data)

    children = [p for p in destination.iterdir() if not p.name.startswith(".")]
    if len(children) == 1 and children[0].is_dir() and (children[0] / "format.json").is_file():
        return children[0]
    return destination


def _clone_git_source(source: str, destination: Path, *, ref: str | None = None) -> tuple[Path, str | None]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "SSH_AUTH_SOCK"}
    }
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    clone_target = destination / "repo"
    cmd = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "protocol.file.allow=always",
        "clone",
        "--depth",
        "1",
        "--no-recurse-submodules",
    ]
    if ref:
        if ref.startswith("-"):
            raise ValueError(f"Invalid git ref: {ref!r}")
        cmd.extend(["--branch", ref])
    cmd.extend([source, str(clone_target)])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.strip()[-600:] or "clone failed"
        raise ValueError(f"Failed to clone format repository: {detail}")

    commit_sha: str | None = None
    rev = subprocess.run(
        ["git", "-C", str(clone_target), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )
    if rev.returncode == 0:
        commit_sha = rev.stdout.strip()
    shutil.rmtree(clone_target / ".git", ignore_errors=True)
    return clone_target, commit_sha


def _audit_project_json_safety(plan_path: Path) -> None:
    doc = read_json(plan_path, max_bytes=524_288)
    if not isinstance(doc, dict):
        raise ValueError(f"{plan_path.name}: expected JSON object")
    for scene in doc.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        if scene.get("recipe") in DISALLOWED_TEMPLATE_RECIPES:
            raise ValueError(f"{plan_path.name}: community format cannot use executable recipe {scene.get('recipe')!r}")
        params = scene.get("params", {})
        if isinstance(params, dict):
            for bad_key in ("fragment_file", "module_file"):
                if bad_key in params:
                    raise ValueError(f"{plan_path.name}: community format cannot declare {bad_key}")
            src = params.get("source")
            if isinstance(src, str) and ("://" in src or src.startswith("/") or ".." in Path(src).parts):
                raise ValueError(f"{plan_path.name}: unsafe external or non-contained source {src!r}")
    audio = doc.get("audio", {})
    if isinstance(audio, dict):
        for track in audio.get("tracks", []):
            if isinstance(track, dict):
                tsrc = track.get("source")
                if isinstance(tsrc, str) and ("://" in tsrc or tsrc.startswith("/") or ".." in Path(tsrc).parts):
                    raise ValueError(f"{plan_path.name}: unsafe audio track source {tsrc!r}")


def _compute_package_digest(format_dir: Path) -> str:
    entries: list[list[str]] = []
    for file_path in sorted(format_dir.rglob("*")):
        if file_path.is_file() and file_path.name != ".install-receipt.json":
            rel = file_path.relative_to(format_dir).as_posix()
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            entries.append([rel, file_hash])
    return hashlib.sha256(canonical(entries)).hexdigest()


def install_format(
    source: str,
    *,
    subdir: str | None = None,
    ref: str | None = None,
    allow_network: bool = False,
    force: bool = False,
    install_root: Path | None = None,
) -> dict[str, Any]:
    cleaned_source = source.strip()
    if not cleaned_source:
        raise ValueError("Format source must not be empty")

    if is_remote_git_source(cleaned_source) and not allow_network:
        raise ValueError(
            "Installing a format from a remote git URL requires --allow-network (or general.allow_network = true in reelsyntax.toml)"
        )

    dest_root = Path(install_root) if install_root is not None else user_formats_directory()
    dest_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        commit_sha: str | None = None
        local_path = Path(cleaned_source).expanduser()
        if not is_remote_git_source(cleaned_source) and local_path.is_symlink():
            raise ValueError("Refusing to install format from a symbolic link source")

        if not is_remote_git_source(cleaned_source) and local_path.is_file() and local_path.suffix.lower() == ".zip":
            candidate_root = _safe_extract_zip(local_path, staging / "unpacked")
        elif not is_remote_git_source(cleaned_source) and local_path.is_dir() and not (local_path / ".git").exists():
            copied = staging / local_path.name
            shutil.copytree(local_path, copied, symlinks=True)
            candidate_root = copied
        else:
            git_src = str(local_path.resolve()) if local_path.exists() else cleaned_source
            candidate_root, commit_sha = _clone_git_source(git_src, staging, ref=ref)

        if subdir:
            sub_target = contained_path(candidate_root, subdir, must_exist=False)
            if not sub_target.is_dir():
                raise ValueError(f"Requested --subdir {subdir!r} does not exist in format source")
            candidate_root = sub_target

        manifest_file = contained_path(candidate_root, "format.json")
        manifest_raw = read_json(manifest_file, max_bytes=131_072)
        fid = manifest_raw.get("id", "")
        if not isinstance(fid, str) or not FORMAT_ID_RE.fullmatch(fid):
            raise ValueError(f"Invalid format id in format.json: {fid!r}")

        normalized_stage = staging / "normalized" / fid
        normalized_stage.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate_root, normalized_stage, symlinks=True)
        (normalized_stage / ".install-receipt.json").unlink(missing_ok=True)

        validated = validate_format_directory(normalized_stage)
        _audit_project_json_safety(normalized_stage / "template/reel.skel.json")
        for example_plan in sorted((normalized_stage / "examples").rglob("reel.json")) if (normalized_stage / "examples").is_dir() else []:
            _audit_project_json_safety(example_plan)

        pkg_sha256 = _compute_package_digest(normalized_stage)
        receipt = {
            "schema_version": 1,
            "id": fid,
            "version": validated["version"],
            "source": cleaned_source,
            "subdir": subdir,
            "commit_sha": commit_sha,
            "package_sha256": pkg_sha256,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(normalized_stage / ".install-receipt.json", receipt)

        final_dest = dest_root / fid
        if final_dest.exists():
            if not force:
                raise ValueError(f"Format {fid!r} is already installed at {final_dest} (pass --force to replace)")
            shutil.rmtree(final_dest)
        shutil.copytree(normalized_stage, final_dest)

    return {
        "installed": True,
        "id": fid,
        "version": validated["version"],
        "path": str(final_dest),
        "commit_sha": commit_sha,
        "package_sha256": pkg_sha256,
    }


def list_installed_formats(install_root: Path | None = None) -> list[dict[str, Any]]:
    dest_root = Path(install_root) if install_root is not None else user_formats_directory()
    if not dest_root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(dest_root.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.is_symlink() or not (child / "format.json").is_file():
            continue
        receipt_path = child / ".install-receipt.json"
        receipt = read_json(receipt_path) if receipt_path.is_file() else {}
        manifest = read_json(child / "format.json")
        items.append({
            "id": manifest.get("id", child.name),
            "version": manifest.get("version", "0.0.0"),
            "category": manifest.get("category", ""),
            "path": str(child),
            "source": receipt.get("source"),
            "commit_sha": receipt.get("commit_sha"),
            "package_sha256": receipt.get("package_sha256"),
        })
    return items


def uninstall_format(format_id: str, *, install_root: Path | None = None) -> dict[str, Any]:
    if not FORMAT_ID_RE.fullmatch(format_id):
        raise ValueError(f"Invalid format identifier: {format_id!r}")
    dest_root = Path(install_root) if install_root is not None else user_formats_directory()
    target = dest_root / format_id
    if target.is_symlink():
        raise ValueError("Refusing to remove symbolic link")
    if not target.is_dir():
        raise ValueError(f"Installed format not found: {format_id}")
    shutil.rmtree(target)
    return {"uninstalled": True, "id": format_id, "path": str(target)}
