---
name: reelsyntax-router
description: Discover and load relevant ReelSyntax filmmaking, editing, animation, sound, rendering, quality, and skill-development procedures without exposing the entire specialist library. Use for video production and ReelSyntax development tasks.
---
# ReelSyntax router

Locate the ReelSyntax skill-pack root (contains `registry/index.json` and `tools/route.py`). Treat the rest of the library as on-demand reference material, not always-on instructions.

1. Extract the current brief, hard constraints, input media and work phase. For multi-step production, split into concrete work items, not a single all-purpose search.
2. Run `python tools/route.py "<work item in user language or normalized English>" --json --limit 6` from the pack root. Optionally pass `--stage`, repeated `--category`, explicit `--include` or `--exclude`, and `--available` with verified adapter capabilities. On Windows use `py -3` if appropriate. This command reads only metadata. Never paste `registry/index.json` or `CATALOG.md` into model context.
3. Inspect candidate names, descriptions, scores, availability and locked requirements. Drop unrelated candidates; refine ambiguous work items using precise terms. Use `--include` for a known necessary skill. An unfulfilled mandatory skill is a blocker, not permission to ignore the brief. No candidate is not permission to load all 500.
4. Open only the selected useful `SKILL.md` paths; usually 2–6 per work item. Read a linked reference only when necessary. Alternatively use `--load` deliberately to return the selected bodies. Do not recursively read the library and do not install all 500 into native host discovery folders.
5. Apply guidance using actual available tools. Re-route when the stage changes or a new work item arises; retain approvals, hard constraints and a compact handoff rather than repeatedly loading the same instruction bodies. Never claim an underlying adapter exists just because a skill describes it.
6. Verify the resulting artifacts against acceptance criteria. Record the selected IDs and versions, actual checks and blockers. Do not execute untrusted third-party scripts or send private inputs to external services implicitly.

The router is lexical and local, not a semantic model. The host agent must interpret negation, multilingual nuance, and project state, enforce hard constraints and disambiguate candidates. See `SKILL_SYSTEM.md` for the production integration specification only when developing the skill system itself.

## Production-grade operating protocol (v2)
For actual production, read `QUALITY_STANDARD.md` once at the start. Establish the draft/production/hero profile and a compact lock ledger. Split the job into concept, animatic, lookdev, motion, sound, render and QA work items. Route each separately; preserve selected skill IDs, findings and evidence, not complete prior bodies. Default budget is 2,400 words per route and at most six skills; use a smaller budget for simple jobs. When a necessary skill cannot fit, route that requirement as its own work item. Do not load `registry/technical-recipes.json` into context; it is a maintenance artifact.

The metadata router is deterministic lexical retrieval, not a semantic oracle or host lifecycle hook. Interpret the brief, locks, negation and available capabilities before routing; explicitly include missing relevant IDs. A request for AAA-quality is a signal to use the `hero` target, not to inject every skill, invent visual scores or override project constraints. Run `python tools/quality_audit.py <video> --profile <profile.json>` for supported media-level checks, then complete visual/audio review. Validate actual outputs; no automatic technical pass certifies aesthetic quality.
