# Acoustic Pause Duration and De-Click Envelope Specification

| Pause Class | Frames (`30/1` fps) | Seconds | Acoustic Floor | `quality.exceptions.silence` Required? |
| --- | ---: | ---: | --- | --- |
| Clause breath | `6–10f` | `0.20–0.33s` | `-inf` or `-44 dBFS` | No (`< 0.50s` `silencedetect` window) |
| Pre-reveal beat | `15–24f` | `0.50–0.80s` | `-inf` (hard stop) | **Yes** (`[[start_f, end_f]]`) |
| Contemplative hold | `24–36f` | `0.80–1.20s` | `-44 dBFS` warm air pad | Recommended (`[[start_f, end_f]]`) |

## Raised-cosine de-click formula (`48 kHz`)
For `N = 240` samples (`5 ms`), multiply outgoing tail samples `i = 0..N-1` by `0.5 * (1 + cos(pi * i / N))` and incoming onset samples by `0.5 * (1 - cos(pi * i / N))`.
