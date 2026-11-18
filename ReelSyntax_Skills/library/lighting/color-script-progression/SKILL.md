---
name: color-script-progression
description: "Design a timeline-wide perceptual OKLCH lightness, chroma, and hue arc so visual mood evolves coherently from opening tension to closing resolution."
metadata:
  category: lighting
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "color script,color script progression,renk senaryosu akışı,duygusal renk yayılımı,Farbdramaturgie,Farbskript-Verlauf,guion de color,script colorimétrique"
  requires: ""
---

# Color Script Progression

## Activation
Activate during visual look development (`look` step) when planning a multi-scene video so background lightness, primary accent hue, and chroma intensity follow narrative tension rather than picking disconnected colors per scene. Search aliases: `color script`, `renk senaryosu akışı`, `Farbdramaturgie`.

## Decision rules
- **60-30-10 area proportion**: on every scene frame, allocate `~60%` canvas area to dominant ground (`background`), `~30%` to structural surface/midground (`card`/`grid`), and `<= 10%` to high-chroma focal accent (`accent` badge/bar/pointer).
- **Perceptual OKLCH interpolation**: define chapter palettes in `(L, C, H)` rather than raw RGB hex lerps so hue steps preserve perceived brightness and never dip through muddy gray midpoints.
- **Three proven short-form color arcs**:
  - *Problem -> Clarity*: muted cool low-chroma slate (`L=0.24, C=0.03, H=255°`) -> crisp high-chroma cyan/amber proof (`C=0.15`) -> open lifted resolution (`L=0.30, C=0.11, H=195°`).
  - *Escalation -> Peak*: steady dark neutral ground (`L=0.23`) while accent chroma climbs step-by-step (`C: 0.06 -> 0.11 -> 0.17`) on the climax beat.
  - *Warm Retrospective*: cohesive warm earth/amber harmony (`H ∈ [45°, 75°]`) with gentle lightness breathing (`L: 0.25 <-> 0.32`).
- **Accessibility & `blackdetect` guard**: clamp dark ground `L >= 0.23` (`sRGB Y >= 44/255`) and enforce foreground text contrast `>= 4.5:1` (`>= 7.0:1` preferred for captions) at every stop of the color script.

## Parameters and defaults
- `ground_lightness_dark`: `0.24–0.32` OKLCH `L` (safe above `blackdetect` `0.10` threshold while feeling rich and dark).
- `ground_lightness_light`: `0.91–0.95` OKLCH `L` (avoids harsh `1.00` pure white glare).
- `ground_chroma_cap`: `0.04` (keep backgrounds low-chroma so `10%` accents pop effortlessly).
- `accent_chroma_range`: `0.11–0.18` (clamped to sRGB/BT.709 gamut).

## Procedure
1. Map each narrative act (`hook`, `conflict/context`, `proof`, `payoff`) to explicit `(L, C, H)` tokens for `ground`, `surface`, `ink`, and `accent`.
2. Keep `ground` hue drift smooth (`<= 25°` per act unless executing a deliberate polarity contrast cut) while reserving peak `accent` chroma (`C >= 0.15`) for the single primary proof or CTA element.
3. Convert OKLCH tokens to sRGB hex with gamut-clipping binary search on `C` (preserving `L` and `H` first so contrast never shifts).
4. Run automated WCAG contrast check (`ink` vs `ground` and `ink` vs `surface` `>= 4.5:1`) on every act's palette before rendering frames.
5. Render a horizontal color-script strip (`1` swatch column per scene proportional to `duration_frames`) to verify the macro arc at a glance.

## Failure modes and fixes
- **Every scene uses full-saturation rainbow backgrounds**: drop `ground` chroma to `<= 0.04` and restrict `C > 0.12` to `<= 10%` focal elements.
- **Dark act triggers FFmpeg `blackdetect`**: raise `ground` OKLCH `L` from `0.12` (`#080A0F`) to `0.25` (`#1F2430`) and create darkness through key-to-fill contrast rather than crushed `0` RGB values.
- **Accent label illegible on midtone surface**: use high-luminance `ink` (`#F8FAFC`) for text and apply `accent` to the pill border, bar, or underline instead of thin body glyphs.

## Checklist
- [ ] Every act specifies `60%` ground, `30%` surface, and `<= 10%` focal accent in OKLCH.
- [ ] Dark grounds stay at `OKLCH L >= 0.23` (`Y >= 44/255`) unless `black` exception is intended.
- [ ] Peak accent chroma is reserved for the climax proof or closing action element.
- [ ] Every scene's `ink` vs `ground`/`surface` clears `>= 4.5:1` WCAG contrast.

## Worked examples
- **Example 1 (`4`-act technical reel color script)**: Act 1 Hook (`ground #232834`, `accent #F97316` warning amber on bottleneck), Act 2 Diagnosis (`ground #212936`, muted `#64748B` inactive nodes), Act 3 Proof (`ground #1F2B37`, `#38BDF8` active throughput bar), Act 4 Payoff (`ground #222F36`, `#34D399` verified pass badge, `ink #F8FAFC` = `12.6:1` contrast).
- **Example 2 (Warm photo retrospective, TR)**: Tüm sahnelerde sıcak taş zemin (`#2C2825`, `L=0.27, C=0.015, H=65°`), krem metin (`#F5F0E6`, `11.8:1` kontrast) ve altın vurgu çizgisi (`#EAB308`, `%8` alan).

## Resources (load only if needed)
- [OKLCH three-act palette templates](references/oklch-story-arcs.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
