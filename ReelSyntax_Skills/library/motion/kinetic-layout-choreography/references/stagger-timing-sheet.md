# Multi-Element Stagger Timing Sheet (`30/1` fps)

| Hierarchy Slot | Start Frame | End Frame | Curve | Spatial Motion (Normalized) |
| --- | ---: | ---: | --- | --- |
| `01` Background plate / grid | `0` | `8` | `quad_out` | Opacity `0.85 -> 1.0` |
| `02` Kicker badge | `0` | `10` | `cubic_out` | `dy: +0.008h -> 0` |
| `03` Accent rule / divider | `2` | `14` | `cubic_out` | `scale_x: 0.0 -> 1.0` from left rail |
| `04` Primary heading | `4` | `16` | `cubic_out` | `dy: +0.014h -> 0` (clip-masked) |
| `05` Subheading / metric | `8` | `20` | `cubic_out` | `dy: +0.010h -> 0`, opacity `0 -> 1` |
| `06` Settled reading hold | `20` | `N - 6` | static | `0.0` (locked) |
