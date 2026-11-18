---
name: safe-community-format-package
description: "Validate third-party community format packages as pure declarative data—blocking executable scripts, custom code recipes, symlinks, path traversal, and network fetches."
metadata:
  category: skills
  stage: ingest
  status: validated
  version: "2.0.0"
  aliases: "safe community format package,data only format install,güvenli topluluk biçim paketi,yalnızca veri biçim kurulumu,sicheres Community-Formatpaket,reines Datenformat installieren,paquete de formato seguro de solo datos,paquet de format communautaire sans code"
  requires: ""
---

# Safe Community Format Package

## Activation
Activate whenever installing, validating, or sharing community format packages via `reelsyntax formats install <source>` (local directory, `.zip` archive, or opt-in `--allow-network` git repository). Search aliases: `safe community format package`, `güvenli topluluk biçim paketi`, `sicheres Community-Formatpaket`.

## Decision rules
- **100% declarative data-only contract (zero executable code)**: a community format package may contain **only**:
  - `format.json` (validating against `format.v1.schema.json`)
  - `FORMAT.md` (UTF-8 Markdown documentation)
  - `example.reel.json` (validating against `reel.v1.schema.json` using **built-in declarative recipes only** — `custom-python`, `custom-shader` external script hooks, `blender-script`, or shell hooks are **rejected** in community packages!)
  - Optional `assets/` static media (`.png`, `.jpg`, `.webp`, `.svg` without `<script>`/`onload`, `.wav`, `.ttf`, `.otf`) accompanied by `licenses.json` using approved SPDX identifiers!
- **Reject every code/binary extension unconditionally**: fail installation before copying a single byte to the user config directory if any entry ends in `.py`, `.pyc`, `.js`, `.mjs`, `.ts`, `.sh`, `.bat`, `.ps1`, `.exe`, `.dll`, `.so`, `.dylib`, `.wasm`, `.blend` (which can embed auto-run Python!), or hidden dotfiles (`.git/hooks`, `.env`).
- **Archive & clone boundary hygiene**:
  - Reject symlinks, hardlinks, FIFO/device nodes, absolute paths, `..` traversal (`zip-slip`), files exceeding `16 MiB`, or archives exceeding `32 MiB` / `128` files (`zip-bomb` ratio guard).
  - For git URLs: require `--allow-network`, clone with `--depth 1 --no-checkout --config core.symlinks=false --config protocol.file.allow=never` into an isolated temp directory, inspect tree entries before extraction, and strip `.git/` completely!

## Parameters and defaults
- `allowed_root_files`: `{"format.json", "FORMAT.md", "example.reel.json", "licenses.json"}`.
- `allowed_asset_extensions`: `{".png", ".jpg", ".jpeg", ".webp", ".wav", ".ttf", ".otf"}` (if `.svg` is ever permitted, reject `<script>`, `foreignObject`, `on*=` attributes, and external `xlink:href`).
- `forbidden_example_recipes`: `{"blender-script", "custom-shader", "three-scene"}` or any scene field referencing executable code.
- `max_package_bytes`: `33554432` (`32 MiB`), `max_file_count`: `128`.
- `network_default`: `disabled` (remote `https://` git clone requires explicit `--allow-network`).

## Procedure
1. Stage incoming folder, `.zip` stream, or shallow no-hooks git tree inside a temporary sandbox directory.
2. Walk every member entry *before* extraction/copy: reject symlinks, `..` / `\` / drive-letter paths, hidden dotfiles, oversized payloads, and any filename extension outside `allowed_root_files` + `allowed_asset_extensions`.
3. Parse `format.json` and `example.reel.json` with `unique_object` JSON parser (`NaN` forbidden), validate against `format.v1.schema.json` and `reel.v1.schema.json`, and verify every scene `recipe` is in the safe declarative built-in allowlist and every path stays inside package root (`contained_path`).
4. Verify `id` does not shadow a built-in core format ID (`kinetic-typography`, `photo-slideshow`, `social-hook-reel`, etc.) so untrusted packages cannot hijack standard format names!
5. Atomically install verified data files into `<user_config_dir>/installed_formats/<id>/` and record package SHA-256 manifest.

## Failure modes and fixes
- **Archive contains `helpers/setup.py` or `.blend` file**: rejected immediately at extension allowlist check with `ValueError("Executable or disallowed file in format package")`.
- **Zip-slip entry `../../.bashrc`**: rejected before extraction by inspecting raw `ZipInfo.filename` path parts.
- **`example.reel.json` references `"font": "/System/Library/..."` or `http://` URL**: rejected by `contained_path` and URI disallow check.

## Checklist
- [ ] Package contains only `format.json`, `FORMAT.md`, `example.reel.json`, `licenses.json`, and static allowlisted `assets/`.
- [ ] Zero `.py`, `.js`, `.sh`, `.wasm`, `.blend`, symlinks, dotfiles, or `..` paths are accepted.
- [ ] `example.reel.json` uses strictly declarative built-in recipes with zero code hooks.
- [ ] Remote git sources require explicit `--allow-network` and disable git hooks/symlinks.

## Worked examples
- **Example 1 (Valid community package `minimal-quote-banner`)**: Contains `format.json` (`id: "minimal-quote-banner"`, `engines: ["pillow", "ffmpeg"]`), `FORMAT.md`, and `example.reel.json` (`2` `kinetic-type` scenes) -> Passes all 5 gates and installs cleanly to `installed_formats/minimal-quote-banner/`.
- **Example 2 (Blocked code-bearing package)**: Zip archive includes `format.json` + `postinstall.sh` -> Blocked in `< 2 ms` during pre-extraction zip header scan; target directory remains untouched.

## Resources (load only if needed)
- [Community format package allowlist and archive security rules](references/package-allowlist-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
