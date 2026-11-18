---
name: format-runner-protocol
description: "Execute step-gated format pipelines (idea, script, look, frames, pilot, full, hero, qc) with approval checkpoints, upstream-edit cache invalidation, and hero render protection."
metadata:
  category: workflow
  stage: operate
  status: validated
  version: "2.0.0"
  aliases: "format runner protocol,step gated video pipeline,biçim yürütücü protokolü,onay kapılı üretim hattı,Format-Ausführungsprotokoll,Stufengesteuerte Render-Pipeline,protocolo de ejecución de formatos,protocole d'exécution de format"
  requires: ""
---

# Format Runner Protocol

## Activation
Activate when orchestrating `reelsyntax make`, `step`, `revise`, `resume`, or local UI approval workflows across declarative formats (`formats/*/format.json`) so cheap validation stages always gate expensive renders. Search aliases: `format runner protocol`, `biçim yürütücü protokolü`, `Format-Ausführungsprotokoll`.

## Decision rules
- **Strict progressive cost ladder (`cheap -> expensive`)**:
  1. `idea` (angle & thesis JSON — milliseconds/seconds)
  2. `script` (beat copy & frame durations — seconds)
  3. `look` (palette, typography, camera & recipe assignment — seconds)
  4. `frames` (`snapshot` keyframe PNGs — `1–2` seconds)
  5. `pilot` (`first_5s` `draft` render + audio check — `3–6` seconds)
  6. `full` (`draft` complete timeline render — `5–15` seconds)
  7. `hero` (`hero`/`production` full-resolution high-sample render — **blocked** unless `full` is approved or `--yes` unattended mode is explicitly passed!)
  8. `qc` (automated technical & domain rule verification on delivered artifact).
- **Downstream invalidation on upstream revision**: editing `script` (`step 2`) invalidates `look`, `frames`, `pilot`, `full`, `hero`, and `qc` step approvals in `.formats/state.json`, while per-scene content-addressed caches (`.reelsyntax/cache/<key>`) still preserve unchanged scenes so only modified beats re-render!
- **Crash-safe resumability**: persist `.formats/state.json` atomically after every completed step (`step_id`, `status`, `input_sha256`, `artifact_path`) so `reelsyntax resume <project>` picks up at the exact first incomplete or invalidated step.
- **No silent completion without `qc`**: a format run is `complete` **only** when the terminal `qc` step finishes with `technical_status == "pass"` (or documented review items in interactive mode).

## Parameters and defaults
- `state_file`: `<project>/.formats/state.json`.
- `provenance_file`: `<project>/prompt.json`.
- `interactive_gate_default`: pause at `"gate": "approve"` steps unless `--yes` is passed.
- `pilot_scope_frames`: `min(total_frames, round(5.0 * fps))` (`150` frames at `30/1` fps).

## Procedure
1. Load and schema-validate `format.json` (`format.v1.schema.json`), resolving active `video_lang`, `aspect_ratio`, and `duration_sec` inside the format's allowed ranges.
2. Initialize or load `.formats/state.json`, checking upstream `input_sha256` hashes from step `0..K-1`; mark any step downstream of a hash change as `"stale"`.
3. Execute the next pending/stale step: pause for user inspection at `"gate": "approve"` checkpoints in interactive CLI/UI mode, or advance automatically when `--yes` is active.
4. Enforce the `hero` guard: raise a clear precondition error if `hero` is requested while `full` is neither `"approved"` nor `"completed"`.
5. Run terminal `qc` passing `format.json`'s `qc_rules` (`opening-hook`, `claims-must-be-sourced`, `contrast`, `safe-area`, `reading-speed`, `loudness`) and record final artifact digest.

## Failure modes and fixes
- **Expensive 4-minute Blender Cycles `hero` render runs on a broken typo in scene 2**: prevented by running `frames` (`snapshot`) -> `pilot` (`first_5s`) -> `full` (`draft`) before unlocking `hero`.
- **User edits `reel.json` manually between `full` and `hero`, then runs `qc` on stale `.mp4`**: `plan_sha256` mismatch in `state.json` / `manifest.json` invalidates `full`/`hero` and requires rendering current sources before `qc`.
- **Interrupted process corrupts `.formats/state.json`**: write all state updates via `atomic_json` (`NamedTemporaryFile` + `fsync` + `os.replace`).

## Checklist
- [ ] Step order progresses strictly from cheap text/snapshot gates to `pilot`, `full`, `hero`, and `qc`.
- [ ] `hero` render cannot execute before `full` draft passes/approves.
- [ ] Upstream edits invalidate downstream step statuses while keeping unchanged scene caches warm.
- [ ] `.formats/state.json` updates atomically for crash-safe `resume`.

## Worked examples
- **Example 1 (`revise` selective invalidation)**: `6`-scene `kinetic-typography` project completes `full`. User runs `reelsyntax revise proj --scene s03 --heading "NEW FACT"`. Steps `frames..qc` mark `"stale"` in `.formats/state.json`; re-running `full` hits `.reelsyntax/cache/` on `5` unchanged scenes and redraws only `s03` + `6`-frame transition handles in `1.8s`.
- **Example 2 (Hero protection test)**: Calling `runner.run_step("hero")` while `full` status is `"pending"` raises `ValueError("Cannot run 'hero' before 'full' is approved")`.

## Resources (load only if needed)
- [Format runner state machine and invalidation matrix](references/state-machine-and-invalidation.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
