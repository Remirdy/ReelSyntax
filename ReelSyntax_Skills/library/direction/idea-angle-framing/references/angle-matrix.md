# Angle Selection Matrix and Scoring Rubric

| Tension Type | Best Runtime Window | Opening Beat Shape | Proof Requirement | Disqualifying Flaw |
| --- | --- | --- | --- | --- |
| `mistake-correction` | `15s–35s` | Show the broken result on frame 0 | Side-by-side corrected state | Scolding tone without actionable fix |
| `counter-intuitive-metric` | `18s–45s` | Lead with the surprising number | Sourced chart or benchmark delta | Unsourced number or cherry-picked baseline |
| `before-after-delta` | `12s–30s` | Split or rapid A/B toggle in first `1.8s` | Identical framing across both states | Changed lighting/scale hiding real delta |
| `constraint-challenge` | `25s–60s` | State the hard constraint and clock | Stepwise build under visible budget | Constraint quietly dropped mid-video |

## Scoring formula
Score each candidate angle before storyboarding:
1. `specificity` (`0–3`): `0` = generic noun, `1` = named domain, `2` = specific mechanism, `3` = specific mechanism + bounded condition.
2. `visualizability` (`0–3`): `0` = talking-head or wall-of-text only, `1` = static icon, `2` = state transition, `3` = unmistakable frame-0 visual contrast.
3. `stake_clarity` (`0–3`): `0` = trivia, `1` = mild curiosity, `2` = saves time/avoids error, `3` = immediate repeatable viewer win.

Select the highest score `>= 6`; if tied, prefer higher `visualizability`.
