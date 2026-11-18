from pathlib import Path
import shutil
from typing import Any

from ReelSyntax_Skills.tools.registry import contained_path

from ..license import APPROVED_SPDX_LICENSES, record_asset_license


def register_local_asset(
    project_dir: Path | str,
    source_path: Path | str,
    *,
    dest_rel: str | None = None,
    spdx: str = "User-Provided",
    author: str = "Project Owner",
    attribution: str = "",
) -> dict[str, Any]:
    if spdx not in APPROVED_SPDX_LICENSES:
        raise ValueError(f"Unsupported SPDX license {spdx!r}; choose from {sorted(APPROVED_SPDX_LICENSES)}")
    root = Path(project_dir).resolve(strict=True)
    src = Path(source_path).expanduser()
    if src.is_symlink() or not src.is_file():
        raise ValueError(f"Local asset must be a regular file: {source_path}")

    rel = dest_rel if dest_rel else f"assets/{src.name}"
    dest = contained_path(root, rel, must_exist=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)

    normalized_rel = dest.relative_to(root).as_posix()
    return record_asset_license(
        root,
        normalized_rel,
        spdx=spdx,
        source_kind="user_local",
        author=author,
        attribution=attribution,
    )
