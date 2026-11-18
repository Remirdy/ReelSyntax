from pathlib import Path
from typing import Any

from ReelSyntax_Skills.tools.registry import contained_path

from .sources.open_catalog import verify_open_catalog_candidate
from .sources.procedural import list_starter_assets, materialize_starter_asset
from .sources.user_local import register_local_asset


def resolve_project_asset(
    project_dir: Path | str,
    reference: str,
    *,
    duration_sec: float = 8.0,
    seed: int = 42,
    allow_network: bool = False,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    cleaned = reference.strip()
    if not cleaned:
        raise ValueError("Asset reference must not be empty")

    if cleaned.startswith("https://") or cleaned.startswith("http://"):
        return verify_open_catalog_candidate({"url": cleaned, "spdx": "CC0-1.0"}, allow_network=allow_network)

    starter_id = cleaned.split(":", 1)[1] if cleaned.startswith("starter:") else cleaned
    starter_ids = {item["id"] for item in list_starter_assets()}

    if not cleaned.startswith("starter:"):
        try:
            inside = contained_path(root, cleaned)
            if inside.is_file():
                rel = inside.relative_to(root).as_posix()
                return {"resolved": True, "source_kind": "project_local", "path": rel}
        except (OSError, ValueError):
            pass

        ext_file = Path(cleaned).expanduser()
        if ext_file.is_file() and not ext_file.is_symlink():
            reg = register_local_asset(root, ext_file)
            return {"resolved": True, "source_kind": "user_local", "path": reg["path"], "license": reg}

    if starter_id in starter_ids:
        mat = materialize_starter_asset(root, starter_id, duration_sec=duration_sec, seed=seed)
        return {"resolved": True, "source_kind": "starter_procedural", **mat}

    raise ValueError(f"Could not resolve asset {reference!r} from local files or starter pack")
