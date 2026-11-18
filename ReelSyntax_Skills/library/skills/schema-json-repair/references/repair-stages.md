# Deterministic JSON Repair Pipeline Stages

1. **Stage 0 — Byte & fence guard**: Reject inputs `> 256 KiB`; strip leading/trailing markdown code fences (` ```json ` .. ` ``` `).
2. **Stage 1 — String-safe balanced slice**: Scan from first `{` tracking `in_string` and `escape` flags until depth returns to `0`.
3. **Stage 2 — Outside-string trailing comma strip**: Remove commas followed only by whitespace and `}` or `]` outside string tokens.
4. **Stage 3 — Strict JSON decode**: `json.loads` with `unique_object` hook; reject `NaN`/`Infinity` (`parse_constant` raising `ValueError`).
5. **Stage 4 — Schema & invariant normalization**: Backfill optional defaults, clamp frame budgets, reconcile total frame count, or emit path-specific diagnostic for retry `1..3`.
