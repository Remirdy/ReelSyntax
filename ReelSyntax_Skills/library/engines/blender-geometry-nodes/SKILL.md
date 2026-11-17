---
name: blender-geometry-nodes
description: "Use for blender geometry nodes. Construct version-compatible node graph with typed sockets and deterministic inputs."
metadata:
  category: engines
  stage: build
  status: guidance
  version: "2.0.0"
  aliases: "geometry nodes,geometri düğümleri"
  requires: "blender"
---

# Blender Geometry Nodes

## Activation
Use for blender geometry nodes when it is a concrete work item. Search aliases: geometry nodes,geometri düğümleri. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Installed engine/version, scene contract and capabilities.
- Output: Engine-specific source, fixture render or explicit unavailable report.
- Required capability: blender
- Evidence bundle: versioned adapter command, fixture source, logs and artifact.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Construct version-compatible node graph with typed sockets and deterministic inputs.
3. Expose named geometry-node inputs, stable seed and unit scale; apply/bake only as needed; test evaluated geometry and memory.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Probe actual installed capabilities and decode representative output; verify deterministic frame/stage behavior.

## Acceptance criteria
- Graph evaluates at test frames without broken links.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Isolate adapter failure, correct version/API mismatch or use approved fallback; report unavailable engines. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [ffmpeg](https://ffmpeg.org/ffmpeg-filters.html)
- [threejs](https://threejs.org/docs/)
- [blender](https://docs.blender.org/api/current/)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
