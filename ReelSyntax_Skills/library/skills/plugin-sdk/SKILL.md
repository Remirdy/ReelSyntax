---
name: plugin-sdk
description: "Use for plugin sdk. Define capability manifest, lifecycle, version compatibility and isolated adapter interfaces."
metadata:
  category: skills
  stage: operate
  status: production-guidance
  version: "2.0.0"
  aliases: "eklenti sdk,plugin geliştirme"
  requires: ""
---

# Plugin Sdk

## Activation
Use for plugin sdk when it is a concrete work item. Search aliases: eklenti sdk,plugin geliştirme. Do not activate for generic video language alone. Read the project brief and relevant hard locks before changing any asset.

## Inputs and output
- Inputs: Agent request, registry, repository state and applicable permissions.
- Output: Skill package, routing result, test or integration artifact.
- Required capability: No specific adapter is mandated; inspect the chosen implementation path.
- Evidence bundle: skill metadata, source/license log, route/evaluation results.

## Production recipe
1. Locate shot/task IDs, approved assets, frame rate, duration and relevant constraints. Verify required capability; record assumptions and do not silently substitute missing resources.
2. Define capability manifest, lifecycle, version compatibility and isolated adapter interfaces.
3. Design versioned plugin interface and capability declarations; isolate untrusted plugins, avoid automatic arbitrary installs and test compatibility.
4. Record actual parameters in the editable source or project manifest; produce a representative preview or dry run before full execution. Apply only parameters relevant to the brief, not every technique in this skill.
5. Test positive, negative and mixed intents plus actual implementation claims; verify budget and security.

## Acceptance criteria
- Fixture plugin registers, runs and can be disabled safely.
- Record the concrete evidence path and frame/time range or measurement, plus target/tolerance and result (`pass`, `fail`, `review`, `blocked`, `not-applicable`). Never award a pass for an unperformed check.
- Check this stage against active project locks and the production profile. Aesthetic judgment requires actual visual/audio review; technical gate success is necessary but not sufficient for release.

## Failure and repair
Refine scope/aliases/instructions or split skill; reindex and run regression suite before release. If the required implementation is absent, return the exact blocker and an executable plan; do not present guidance as a rendered result. Recheck the original acceptance condition after repair.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric; load once per production, not for every skill.
- [agent-skills](https://agentskills.io/specification)
- [codex](https://developers.openai.com/codex/skills)
- [claude](https://code.claude.com/docs/en/skills)

Original production guidance. External references are starting points, not copied instructions. Verify current APIs and licenses; do not execute unreviewed third-party code.
