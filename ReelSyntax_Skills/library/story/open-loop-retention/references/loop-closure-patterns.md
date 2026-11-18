# Loop Closure Ledger and Midpoint Patterns

## Loop ledger schema
Track every narrative loop during planning so none are orphaned:
```json
{
  "loop_id": "primary_size_anomaly",
  "planted_at_frame": 0,
  "question": "Why is file B 6x smaller at equal visual fidelity?",
  "clues": [
    {"frame": 90, "evidence": "Bit-depth and dimensions match"},
    {"frame": 240, "evidence": "Naive bitrate clamp causes block artifacts"}
  ],
  "closed_at_frame": 410,
  "payoff_statement": "Keyframe interval + CRF 20 + AAC 192k"
}
```

## Proven non-clickbait opening loop templates
1. **Twin-output anomaly**: Show two outputs with one dramatic metric gap; hold back the single differing parameter until beat 4.
2. **Naive-fix trap**: State a common problem, test the popular one-line fix in beat 2 (showing its side effect), then reveal the clean fix at `80%`.
3. **Countdown elimination**: Present three plausible culprits on screen, cross out culprit 1 and 2 with visual tests, confirm culprit 3.
