# Low-Poly Cutscene 5-Shot Blocking and Mouth-Envelope Spec

| Shot # | Role | Focal `mm` (`36mm` eq.) | Duration (`30/1` fps) | Camera Motion |
| --- | --- | ---: | ---: | --- |
| `01` | Establishing Wide | `28mm` | `75–96f` | Slow `dolly_in` (`4%`) or `locked` |
| `02` | Speaker A OTS / Medium | `50mm` | `120–165f` | `locked` (`x_subj = 0.36w`) |
| `03` | Speaker B Reverse Medium | `50mm` | `120–165f` | `locked` (`x_subj = 0.64w`) |
| `04` | Prop / Clue Insert Close-up | `65mm` | `90–120f` | Crisp state change + SFX |
| `05` | Two-Shot Payoff | `35mm` | `120–180f` | Gentle pull-back + tonic resolve |

## Mouth-envelope extraction (`30/1` fps)
Compute RMS amplitude over each frame's `1600` audio samples (`48000 / 30`), normalize by the clip's `95th` percentile RMS, and quantize into `{0.0, 0.35, 0.75, 1.0}` with a `-42 dBFS` noise gate so silent frames lock cleanly at `0.0`.
