---
name: render-artifact-validation
description: "Use for render artifact validation. Check expected file presence, size, checksum and frame/stream decode before reuse."
metadata:
  category: render
  stage: render
  status: production-guidance
  version: "2.0.0"
  aliases: "render dosya kontrolü,artifact validation"
  requires: ""
---

# Render Artifact Validation

## Activation
Use for render artifact validation when it is a concrete work item. Search aliases: render dosya kontrolü,artifact validation. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Validated scene plan, engine probe, hardware budget and output target.
- Output: Render artifact or job/diagnostic report.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: versioned job manifest, settings, logs and frame/artifact hashes.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Check expected file presence, size, checksum and frame/stream decode before reuse.
3. Validate expected codec, dimensions, frame count, duration, streams, decode success, color tags and checksums before approving.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Check contiguous frames, exact timing and decode; compare sampled output to approved preview.

## Acceptance criteria
- Corrupt or incomplete render artifacts cannot become cache hits.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Retry bounded scope with compatible settings; invalidate stale cache and report failed dependencies. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [playwright](https://playwright.dev/docs/screenshots)
- [threejs](https://threejs.org/docs/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
