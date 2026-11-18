---
name: asset-license-ledger
description: "Track SHA-256 digests, approved SPDX license identifiers, source URLs, and attribution notices for every bundled or imported font, audio, image, and 3D asset."
metadata:
  category: ingest
  stage: ingest
  status: validated
  version: "2.0.0"
  aliases: "asset license ledger,spdx attribution manifest,varlık lisans defteri,telif ve atıf kaydı,Asset-Lizenzverzeichnis,SPDX-Quellen- und Lizenzbuch,registro de licencias de recursos,registre de licences des médias"
  requires: ""
---

# Asset License Ledger

## Activation
Activate whenever bundling starter assets, resolving open-catalog media, importing user local files (`photos`, `.ttf`/`.otf` fonts, `.wav` stems, `.glb` meshes), or running pre-release `qc` so zero unlicensed or hash-mismatched files enter a deliverable. Search aliases: `asset license ledger`, `varlık lisans defteri`, `Asset-Lizenzverzeichnis`.

## Decision rules
- **Strict SPDX allowlist for bundled / open-catalog assets**: accept only `CC0-1.0`, `CC-BY-4.0`, `OFL-1.1` (fonts), `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, or `Public-Domain` for repository/catalog assets, plus explicit `User-Provided` for local files owned/supplied by the project author.
- **Reject non-commercial, share-alike copyleft, or unknown licenses (`CC-BY-NC`, `CC-BY-ND`, `GPL`, `Unknown`, `"free from web"`)** on media/fonts bundled into commercial-ready video outputs unless explicitly overridden in private non-redistributed workspaces.
- **Content-addressed SHA-256 binding**: bind every ledger entry to the exact `sha256` digest of the file on disk; if an asset file is swapped on disk without updating its license record, `check_asset_licenses` in `qc` **must** fail (`hash_mismatches != []`).
- **Automatic `LICENSES.md` generation**: whenever `CC-BY-4.0`, `OFL-1.1`, `MIT`, or `Apache-2.0` assets are used in a project, generate `<project>/LICENSES.md` containing full title, creator attribution, SPDX code, source URI, and copyright notice alongside the rendered video!

## Parameters and defaults
- `ledger_path`: `<project>/.reelsyntax/asset-licenses.json`.
- `human_credits_path`: `<project>/LICENSES.md`.
- `approved_spdx_set`: `{"CC0-1.0", "CC-BY-4.0", "OFL-1.1", "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "Public-Domain", "User-Provided"}`.
- `require_attribution_field_for`: `{"CC-BY-4.0", "OFL-1.1", "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}`.

## Procedure
1. Before referencing any external or starter file in `reel.json` (`delivery.font`, `audio.music`, `layer-stack` image paths, `.glb` models), compute its `sha256` digest and verify containment inside `<project>/`.
2. Validate `spdx_license` against `approved_spdx_set` and require non-empty `author` + `attribution` fields whenever the license mandates credit (`CC-BY-4.0`, `OFL-1.1`, `Apache-2.0`).
3. Upsert the verified record into `.reelsyntax/asset-licenses.json` using atomic file replacement (`atomic_json`).
4. Regenerate deterministic `<project>/LICENSES.md` sorted by relative path so users can paste exact `CC-BY` credits into video descriptions or ship `LICENSES.md` with client deliverables.
5. Run `qc` (`asset_licenses == pass`) confirming zero unregistered files and zero SHA-256 drift.

## Failure modes and fixes
- **Font downloaded from web has `"free for personal use"` readme**: reject immediately (`not in approved_spdx_set`); substitute an `OFL-1.1` font with verified `OFL.txt`.
- **User replaces `assets/photo1.png` with a new file of the same filename**: `sha256` mismatch trips `asset_licenses: fail` in `qc`, prompting clean re-registration of the replacement file's license.
- **`CC-BY-4.0` music stem used without credit string**: require `author`, `title`, `source_url`, and `license_url` at registration time and emit ready-to-copy attribution text in `LICENSES.md`.

## Checklist
- [ ] Every file asset referenced by `reel.json` has a matching entry in `.reelsyntax/asset-licenses.json`.
- [ ] Every entry uses an approved SPDX identifier and matches on-disk `sha256`.
- [ ] Attribution-requiring licenses (`CC-BY-4.0`, `OFL-1.1`) include non-empty creator & source strings.
- [ ] `<project>/LICENSES.md` is generated deterministically and `qc` `asset_licenses` returns `pass`.

## Worked examples
- **Example 1 (Starter plate + custom OFL font ledger)**:
  - `assets/plates/photo-plate-warm.png` -> `CC0-1.0`, `sha256: e3b0...`, `author: "ReelSyntax Starter Pack"`.
  - `assets/fonts/Inter-Bold.ttf` -> `OFL-1.1`, `sha256: 9a4f...`, `author: "The Inter Project Authors"`.
  - `LICENSES.md` lists both cleanly -> `qc` `asset_licenses: pass`.
- **Example 2 (Blocked `CC-BY-NC-4.0` sound effect)**: `reelsyntax assets register proj sfx.wav --license CC-BY-NC-4.0` -> Raises `ValueError: Unsupported or restricted license 'CC-BY-NC-4.0'` before entering project state.

## Resources (load only if needed)
- [Approved SPDX allowlist and `.reelsyntax/asset-licenses.json` schema](references/spdx-allowlist-and-ledger-format.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
