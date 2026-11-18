---
name: cross-shot-grade-consistency
description: "Match black floor, neutral white balance, highlight shoulder, and perceptual chroma across consecutive shots so cuts never pop."
metadata:
  category: lighting
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "shot grade consistency,grade consistency,çekim renk tutarlılığı,sahneler arası renk uyumu,Schnitt-Farbkonsistenz,Farbabgleich zwischen Szenen,consistencia de etalonaje,cohérence colorimétrique"
  requires: ""
---

# Cross-Shot Grade Consistency

## Activation
Activate when assembling multi-scene photo slideshows, mixed procedural + 3D sequences, or multi-angle cuts where adjacent shots risk unintentional black-level jumps, white-balance casts, or saturation spikes. Search aliases: `shot grade consistency`, `çekim renk tutarlılığı`, `Schnitt-Farbkonsistenz`. Do not flatten intentional dramatic palette shifts declared in a color script.

## Decision rules
- **Black-floor anchor**: keep shadow floor (`5th` percentile luma `Y` in 8-bit BT.709) within `+-6` code values across same-location or same-chapter shots, and above `Y >= 20` (`>= 44` sRGB on solid graphic plates) so `blackdetect` is never tripped unintentionally.
- **Neutral axis alignment**: across consecutive shots sharing a scene environment, constrain neutral gray/highlight chromaticity drift to `|Δa|, |Δb| <= 0.015` in OKLab unless an explicit warm/cool story turn is marked.
- **Chroma ceiling harmony**: keep `95th` percentile perceptual chroma (`OKLCH C`) within `<= 0.04` delta between adjacent A/B cuts so one oversaturated plate does not make the following shot look washed out.
- **Metadata lock**: verify final stream tags match `bt709` (`color_space`, `color_transfer`, `color_primaries`) and `tv` legal range consistently across every concatenated segment.

## Parameters and defaults
- `shadow_p05_delta_max`: `6` (8-bit luma units `0..255` across matched shots; adjustable default).
- `midtone_p50_delta_max`: `14` (8-bit luma units unless motivated lighting change).
- `oklch_chroma_delta_max`: `0.04` across matched cuts.
- `highlight_ceiling_y`: `235` (`tv` range ceiling) or `248` (`full` pre-encode working space before legal-range scale).

## Procedure
1. Designate one hero shot in each sequence chapter as the reference anchor and measure its `P05` (black floor), `P50` (midtone luma), `P95` (highlight shoulder), and mean neutral `OKLab (a, b)`.
2. Normalize incoming photo or 3D render plates into linear/working space before applying exposure lift, white-balance offset, and soft highlight roll-off.
3. Match black floors first (`lift`), white balance second (`gain/temp-tint`), midtone contrast third (`gamma`), and accent saturation last.
4. Inspect consecutive cut pairs (`last frame of scene i` next to `first frame of scene i+1`) in a side-by-side contact strip to catch subtle magenta/green shifts.
5. Verify encoded output carries uniform `bt709` / `tv` stream tags in `qc` (`color_metadata == pass`).

## Failure modes and fixes
- **Crushed dark plate next to milky lifted photo**: lift crushed plate black floor to match reference `P05` (`Y ~ 24–44`) or pull milky photo blacks down with a toe curve.
- **Mixed sRGB JPEG + untagged 3D render concatenation shifts gamma on cut**: convert every plate explicitly to working sRGB before compositing and tag BT.709 once at final FFmpeg encode.
- **Neon accent clipping in 4:2:0 chroma**: pull peak `OKLCH C` back `10%–15%` on thin saturated graphics so `bt709` encode preserves clean edges.

## Checklist
- [ ] Reference anchor shot metrics (`P05`, `P50`, `P95`, neutral `a/b`) recorded per chapter.
- [ ] Adjacent matched cuts stay within `+-6` black-floor luma and `<= 0.04` OKLCH chroma delta.
- [ ] Side-by-side cut boundary contact strip reviewed for green/magenta cast jumps.
- [ ] Final stream `color_metadata` passes `bt709` + `tv` verification.

## Worked examples
- **Example 1 (`6`-photo slideshow normalization, EN)**: Photo 3 has milky blacks (`P05 = 58`, cool cast `b = -0.028`) while Hero Photo 1 has `P05 = 28, b = +0.006`. Apply black-point minus `-30` toe curve and warm `+0.032` `b`-axis balance before Ken Burns pan; cut boundary luma jump drops from `30` to `3`.
- **Example 2 (Procedural intro into 3D scene, TR)**: Sahne 1 arka planı `#1E293B` (`Y ≈ 45`), Sahne 2 3B render gölgesi `#05070A` (`Y ≈ 7`, `blackdetect` uyarısı). Sahne 2 ortam dolgu ışığı artırılarak gölge tabanı `Y = 41` seviyesine çekilir; kesme sıçraması kaybolur.

## Resources (load only if needed)
- [BT.709 shot-matching tolerances and contact-strip audit](references/bt709-matching-tolerances.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
