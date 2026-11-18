from typing import Any

from ..license import APPROVED_SPDX_LICENSES, ATTRIBUTION_REQUIRED_SPDX


def verify_open_catalog_candidate(
    metadata: dict[str, Any],
    *,
    allow_network: bool = False,
) -> dict[str, Any]:
    if not allow_network:
        raise ValueError(
            "Open-catalog network asset retrieval is disabled by default; pass --allow-network or use local/starter assets"
        )
    url = str(metadata.get("url", "")).strip()
    if not url.startswith("https://"):
        raise ValueError(f"Open-catalog asset URL must use HTTPS: {url!r}")
    spdx = str(metadata.get("spdx", "")).strip()
    if spdx not in APPROVED_SPDX_LICENSES or spdx == "User-Provided":
        raise ValueError(f"Open-catalog asset has unapproved SPDX license: {spdx!r}")
    author = str(metadata.get("author", "")).strip()
    attribution = str(metadata.get("attribution", "")).strip()
    if spdx in ATTRIBUTION_REQUIRED_SPDX and not (author or attribution):
        raise ValueError(f"Open-catalog asset under {spdx} requires author or attribution metadata")
    return {
        "verified": True,
        "url": url,
        "spdx": spdx,
        "author": author or "Unspecified",
        "attribution": attribution,
    }
