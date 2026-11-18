---
name: bilingual-dual-subtitles
description: "Stack primary and secondary language subtitle tracks with distinct size/luminance hierarchy, locked shared event timestamps, and <= 3 total lines."
metadata:
  category: typography
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "bilingual subtitles,dual language captions,çift dilli altyazı,iki dilli altyazı yerleşimi,zweisprachige Untertitel,Doppel-Untertitel anordnen,subtítulos bilingües,sous-titres bilingues"
  requires: ""
---

# Bilingual Dual Subtitles

## Activation
Activate when producing language-learning reels, international conference clips, festival previews, or cross-border social deliverables that intentionally display two languages simultaneously on screen. Search aliases: `bilingual subtitles`, `çift dilli altyazı`, `zweisprachige Untertitel`. Do not activate for single-language variants (`reelsyntax variants`) or when `constraints.no_text` is true.

## Decision rules
- **Strict 3-line ceiling (`1 + 1` preferred, `2 + 1` max)**: never stack `2` lines of Language A on top of `2` lines of Language B (`4` lines cover `> 28%` of vertical frame height!); segment shorter clauses so `L1` + `L2` each fit on `1` single line (`1 + 1 = 2` lines total) on `>= 85%` of events, and never exceed `3` combined lines.
- **Unambiguous visual hierarchy (`1.00x` vs `0.78x`)**: render the primary track (`L1`) at `1.00x` nominal size in crisp neutral white (`#F8FAFC`, semi-bold) and the secondary translation (`L2`) directly beneath at `0.76x–0.82x` size in warm soft tint (`#E2E8F0` or `#FDE68A`, regular/medium), separated by `0.35 * L1_px` vertical gap inside one unified dark backing pill (`>= 7.0:1` contrast for *both* lines!).
- **Locked shared cue timestamps**: bind `L1` and `L2` to the **exact same** `[start_frame, end_frame]` interval per phrase — asynchronous independent entrances/exits between `L1` and `L2` create severe flicker and split attention.
- **Duration governed by the slower track**: set `event_frames >= max(needed_frames(L1), needed_frames(L2)) * 1.10` (`+10%` dual-track scanning allowance).

## Parameters and defaults
- `l1_font_px_16x9` / `l2_font_px_16x9`: `44 px` (`#F8FAFC` SemiBold) / `35 px` (`#FDE68A` Medium).
- `l1_font_px_9x16` / `l2_font_px_9x16`: `46 px` (`#F8FAFC` Bold) / `36 px` (`#E2E8F0` Medium).
- `inter_track_gap_px`: `14` px (`~0.32 * l1_font_px`).
- `max_combined_lines`: `3` (`1 + 1` target).
- `shared_pill_rgba`: `(12, 17, 26, 218)` (`>= 7.0:1` contrast for both `#F8FAFC` and `#E2E8F0` / `#FDE68A`).

## Procedure
1. Segment spoken transcript into compact `3–7` word clauses so both `L1` and translated `L2` stay `<= 1` line each (`<= 34` chars `L1`, `<= 42` chars `L2` on `16:9`; `<= 24` / `<= 30` on `9:16`).
2. Translate meaning idiomatically (`transcreation-tone`) to match the compact clause boundary so `L2` never lags one clause behind `L1`.
3. Compute shared `[start_frame, end_frame]` satisfying both language CPS budgets plus a `10%` dual-track buffer, snapped to scene cuts.
4. Draw a single unified rounded backing pill enclosing both `L1` and `L2` with `inter_track_gap_px` separation so two separate pills never collide or step at different widths.
5. Verify combined bounding box stays inside `vertical_safe_zones` (`bottom <= 0.82h` on `9:16`) and both tracks clear `>= 7.0:1` WCAG contrast.

## Failure modes and fixes
- **Two equal-size white lines confuse eye over which language is which**: differentiate via `1.00x` SemiBold `#F8FAFC` (`L1`) vs `0.78x` Medium `#FDE68A` (`L2`).
- **`L1` changes at `f = 60` while `L2` changes at `f = 69`**: lock `L1` and `L2` onto one shared cue object `{start_frame, end_frame, l1, l2}`.
- **4-line wall blocks character's face**: split the sentence into two consecutive `1 + 1` cue events.

## Checklist
- [ ] `L1` and `L2` share identical `[start_frame, end_frame]` cue boundaries.
- [ ] Combined line count is `2` (`1 + 1`) on standard cues and never exceeds `3`.
- [ ] `L1` (`1.0x`) and `L2` (`~0.78x` tinted) sit inside one unified `>= 7.0:1` backing pill.
- [ ] Event hold duration satisfies the slower of the two language CPS profiles (`+10%`).

## Worked examples
- **Example 1 (`16:9` `1920x1080` `DE + EN` tech keynote clip)**: `f = 30..114` (`2.8s`), unified pill at `y = 875..995 px`:
  - `L1` (`44px` `#F8FAFC`): `"Jede Szene wird deterministisch zwischengespeichert."` (`52`? -> segmented into `2` cues: Cue A `"Jede Szene hat einen eigenen Hash."` / `"Every scene has its own hash."` (`1+1` lines!), Cue B `"Nur geänderte Teile rendern neu."` / `"Only edited parts re-render."`).
- **Example 2 (`9:16` `TR + EN` vocabulary micro-lesson)**: `L1` (`46px` `#F8FAFC`): `"Kare hızı sabit kaldı."` / `L2` (`36px` `#FDE68A`): `"The frame rate stayed constant."` (`f = 0..78`, bottom at `1520 px < 1574 px` safe ceiling).

## Resources (load only if needed)
- [Dual-track subtitle stacking coordinates and color pairs](references/dual-track-stacking.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
