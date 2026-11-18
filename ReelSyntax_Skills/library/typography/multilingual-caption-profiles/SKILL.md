---
name: multilingual-caption-profiles
description: "Configure per-language characters-per-second ceilings, line-length limits, minimum hold floors, and shot-cut lead/lag snapping across six languages."
metadata:
  category: typography
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "multilingual caption profiles,per language subtitle timing,çok dilli altyazı profilleri,dile göre okuma hızı sınırı,mehrsprachige Untertitelprofile,Lesegeschwindigkeit je Sprache,perfiles de subtítulos multilingües,profils de sous-titres multilingues"
  requires: ""
---

# Multilingual Caption Profiles

## Activation
Activate when generating `.srt`/`.vtt` sidecars, timing translated subtitles, or auditing caption pacing across `en`, `tr`, `de`, `es`, `fr`, and `pt` deliverables. Search aliases: `multilingual caption profiles`, `çok dilli altyazı profilleri`, `mehrsprachige Untertitelprofile`. Do not activate when `constraints.no_text` is true.

## Decision rules
- **Language-adapted CPS & CPL budgets** (adjustable defaults — verify against client/broadcaster style guide when applicable):
  - `en`: target `<= 17` CPS (`20` hard ceiling), `<= 42` CPL (`16:9`) / `<= 30` CPL (`9:16`).
  - `tr`: target `<= 15` CPS (`18` hard ceiling), `<= 38` CPL (`16:9`) / `<= 28` CPL (`9:16`) — agglutinative words pack multiple grammatical morphemes per word, increasing morphological decoding load per character.
  - `de`: target `<= 15` CPS (`18` hard ceiling), `<= 40` CPL (`16:9`) / `<= 28` CPL (`9:16`) — long compound nouns require extra fixation time.
  - `es` / `fr` / `pt`: target `<= 16` CPS (`19` hard ceiling), `<= 42` CPL (`16:9`) / `<= 30` CPL (`9:16`), accounting for `15%–25%` Romance expansion over English.
- **Event duration bounds**: keep every subtitle event inside `[0.85s, 6.00s]` (`[26f, 180f]` at `30/1` fps) with a `>= 2`-frame (`~67 ms`) blank gap between consecutive events so the eye registers the text refresh.
- **Shot-cut snapping**: never end or start a subtitle `1–4` frames away from a hard visual cut (which causes a double-flash); snap any event boundary within `<= 5` frames of a scene cut directly onto `cut_frame - 2` (out) or `cut_frame` (in).

## Parameters and defaults
- `min_event_frames_30fps`: `26` frames (`0.87s`).
- `max_event_frames_30fps`: `180` frames (`6.00s`).
- `inter_event_gap_frames`: `2` frames (`0.067s` at `30/1` fps).
- `cut_snap_tolerance_frames`: `5` frames.
- `max_lines_per_event`: `2`.

## Procedure
1. Load the active `lang-profiles/<lang>.json` timing parameters (`target_cps`, `hard_max_cps`, `max_cpl_16x9`, `max_cpl_9x16`).
2. Segment transcript clauses into `<= 2` lines obeying `max_cpl` and phrase boundaries (`orphan-widow-line-balance`).
3. Compute `min_needed_frames = max(min_event_frames, ceil(visible_chars / target_cps * fps))`; extend trailing silence tail up to the next speech onset (minus `inter_event_gap_frames`) when spoken delivery is rapid.
4. Snap event `start_frame` / `end_frame` within `cut_snap_tolerance_frames` of scene cut boundaries so captions never straddle a cut by `2` frames.
5. If a translated line still exceeds `hard_max_cps` after claiming available gap frames, condense paraphrase (`transcreation-tone`) rather than flashing unreadable `24` CPS captions.

## Failure modes and fixes
- **Direct German/French translation of fast English speech hits `23` CPS**: condense subordinate clauses into concise verb/noun phrasing (`15%–20%` character trim) instead of shrinking inter-event gaps to zero.
- **Caption disappears `3` frames *after* a scene cut**: trim `end_frame` back `5` frames to `cut_frame - 2` so the outgoing caption clears cleanly with the outgoing shot.
- **Zero-frame back-to-back events look stuck when consecutive lines have similar widths**: insert `2`-frame gap (`inter_event_gap_frames = 2`) on non-karaoke subtitle tracks.

## Checklist
- [ ] Every subtitle event obeys its language's `target_cps` and aspect-specific `max_cpl`.
- [ ] Event durations stay within `[0.85s, 6.0s]` with `>= 2`-frame gaps between distinct events.
- [ ] Boundaries within `<= 5` frames of a scene cut snap cleanly to the cut.
- [ ] Over-budget translations are condensed semantically rather than exceeding `hard_max_cps`.

## Worked examples
- **Example 1 (`tr` vertical `9:16` event timing at `30/1` fps)**: `"Sahneler önbellekten anında
yeniden birleştirilir."` (`49` visible chars). At `15` CPS target, `ceil(49 / 15 * 30) = 98` frames (`3.27s`); snapped end to scene cut `f = 178` (`2` frames before `180f` cut).
- **Example 2 (`fr` expansion compression)**: Literal translation of `"Skip unused passes"` (`18` chars in `1.1s`) -> `"Ignorer les passes inutilisées"` (`30` chars = `27.3` CPS fail) -> Condensed `"Omettre les passes inutiles"` + `0.5s` trailing breath extension (`27` chars / `1.6s` = `16.8` CPS pass).

## Resources (load only if needed)
- [Six-language subtitle timing and line-length matrix](references/six-language-timing-matrix.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
