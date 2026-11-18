# BT.709 Shot-Matching Tolerances and Contact-Strip Audit

| Metric | Same-Scene Cut Tolerance | Same-Reel Chapter Tolerance | Intentional Mood Shift |
| --- | --- | --- | --- |
| Black floor `P05` (8-bit `Y`) | `<= 6` | `<= 12` | Documented in color script (`Y >= 20` unless `black` exception) |
| Midtone `P50` (8-bit `Y`) | `<= 14` | `<= 28` | Motivated by spotlight/silhouette cue |
| Highlight `P95` (8-bit `Y`) | `<= 12` (`<= 235` legal) | `<= 20` | Soft shoulder roll-off required |
| Neutral `OKLab |Δa|, |Δb|` | `<= 0.015` | `<= 0.025` | Explicit warm/cool contrast chapter |
| Peak chroma `OKLCH |ΔC|` | `<= 0.04` | `<= 0.07` | Accent reveal beat only |

*Note:* Encoding flags and broadcast legal-range expectations (`16..235` luma, `16..240` chroma for 8-bit `tv` range) are adjustable defaults; verify against current delivery specification when mastering for external broadcast pipelines.
