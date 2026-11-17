---
name: asset-portability
description: "Use for asset portability. Use relative logical IDs and package only permitted dependencies."
metadata:
  category: ingest
  stage: ingest
  status: guidance
  version: "2.0.0"
  aliases: "taşınabilir asset,dosya taşıma"
  requires: ""
---

# Asset Portability

## Activation
Use for asset portability when it is a concrete work item. Search aliases: taşınabilir asset,dosya taşıma. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Approved input roots, source permissions, project manifest.
- Output: Inventory, provenance report or normalized derivative.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: source manifest, hashes, rights and derived asset paths.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Use relative logical IDs and package only permitted dependencies.
3. Use relative paths and checksums, package allowed assets and fonts/links; test extraction in clean directory without original absolute paths.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Confirm usable dimensions, exact references, provenance and privacy; spot-check probe results.

## Acceptance criteria
- Project resolves assets after relocation without absolute path leaks.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Quarantine unresolved assets or choose approved fallback; never silently overwrite or delete sources. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [openmontage](https://github.com/OpenMontageInc/OpenMontage)
- [awesome-editing](https://github.com/devanasolver/awesome-video-editing)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
