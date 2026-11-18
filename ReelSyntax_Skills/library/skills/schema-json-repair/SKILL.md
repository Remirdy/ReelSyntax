---
name: schema-json-repair
description: "Recover valid, schema-conformant scene plans from malformed JSON outputs using deterministic syntax normalization, bounded retries, and rule-based fallback."
metadata:
  category: skills
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "schema json repair,json plan repair,şema json onarımı,bozuk json düzeltme,JSON-Schema-Reparatur,Strukturdaten-Reparatur,reparación de json,réparation de schéma json"
  requires: ""
---

# Schema JSON Repair

## Activation
Activate when parsing structured storyboard, intent, or `reel.json` payloads produced by compact local text-to-JSON engines or manual edits that may contain markdown fences, trailing commas, unquoted keys, or out-of-range numeric fields. Search aliases: `schema json repair`, `şema json onarımı`, `JSON-Schema-Reparatur`. Do not use to silently mask corrupted binary media manifests.

## Decision rules
- **Deterministic syntactic pass first**: attempt zero-cost syntactic extraction (strip fenced code blocks, isolate outermost balanced `{...}`, remove trailing commas before `}` / `]`) before spending a retry pass.
- **Hard retry ceiling**: cap diagnostic re-queries at `max_attempts = 3`, passing only the exact field path and validation error (`scenes[1].duration_frames: expected integer >= 15, got -4`).
- **Never invent factual user copy during repair**: clamp numeric bounds (`duration_frames`, `font_size`, RGB hex contrast) and backfill structural defaults (`transition: {"type": "cut", "duration_frames": 0}`), but never fabricate quantitative claims.
- **Guaranteed offline fallback**: if attempt `3` still fails schema validation, switch cleanly to the deterministic rule-based storyboard builder and record `repair_fallback: true` in `prompt.json`.

## Parameters and defaults
- `max_attempts`: `3` total validation passes.
- `max_payload_bytes`: `262144` bytes (`256 KiB` parser safety cap).
- `allow_duplicate_keys`: `false` (`object_pairs_hook=unique_object` after repair).
- `numeric_clamp_policy`: clamp `duration_frames` into `[15, 1800]` and `fps` to known rationals (`"24/1"`, `"25/1"`, `"30/1"`, `"60/1"`, `"30000/1001"`).

## Procedure
1. Enforce `max_payload_bytes`, strip surrounding prose or triple-backtick fences, and locate the first balanced `{...}` object using a string-aware brace scanner.
2. Normalize safe syntax glitches outside string literals: remove trailing commas `,}` / `,]` and replace smart quotes `“` `”` wrapping JSON keys only when standard parse fails.
3. Parse with `json.loads(..., object_pairs_hook=unique_object)` and reject `NaN` / `Infinity`.
4. Validate against the target schema (`intent`, `storyboard`, or `reel.v1.schema.json`), collecting path-indexed errors (`path`, `expected`, `observed`).
5. Apply safe structural defaults (missing optional `kicker: ""`, missing `transition`, frame-sum normalization); if required semantic fields are missing, run bounded error-feedback retry (`<= 3`) or deterministic offline fallback, logging every repair action in provenance metadata.

## Failure modes and fixes
- **Greedy regex `{.*}` grabs braces inside trailing commentary**: use a character-by-character state scanner that tracks JSON string escapes `"` and nesting depth.
- **Infinite repair loop on stubborn syntax failure**: enforce `attempt <= 3` counter with deterministic offline compiler fallback on exhaustion.
- **Silent key overwrite from duplicate JSON keys**: enforce `unique_object` pair hook and surface duplicate-key paths explicitly in diagnostic feedback.

## Checklist
- [ ] String-aware balanced brace extractor isolates JSON without corrupting string literals.
- [ ] `NaN`, `Infinity`, and duplicate keys are rejected.
- [ ] Schema errors report exact field paths (`scenes[2].recipe`).
- [ ] Bounded `<= 3` retry ceiling falls back cleanly and logs provenance in `prompt.json`.

## Worked examples
- **Example 1 (Fenced JSON with trailing comma, EN)**: Raw payload ```` ```json
{"title": "Focus", "duration_sec": 15, "beats": [{"heading": "START NOW", "frames": 90,}],}
``` ```` -> Fences stripped, two trailing commas removed outside strings, parsed cleanly on pass 1 (`retries_used = 0`).
- **Example 2 (Invalid recipe enum on pass 1, DE)**: `beats[0].recipe = "neon_explosion"` -> Validator emits `"beats[0].recipe: must be one of ['kinetic-type','prism-monolith','layer-stack','signal-grid']"` -> Pass 2 maps to `"prism-monolith"`, schema passes (`retries_used = 1`).

## Resources (load only if needed)
- [Deterministic JSON repair pipeline stages](references/repair-stages.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
