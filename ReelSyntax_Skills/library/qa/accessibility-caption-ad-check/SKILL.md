---
name: accessibility-caption-ad-check
description: "Verify caption completeness for non-speech audio cues, speaker changes, contrast, and visual-only information parity for blind and deaf/hard-of-hearing viewers."
metadata:
  category: qa
  stage: review
  status: validated
  version: "2.0.0"
  aliases: "accessibility caption check,caption and audio description qa,erişilebilir altyazı ve sesli betimleme denetimi,işitme görme erişilebilirlik kontrolü,Barrierefreiheit Untertitel-Prüfung,Hörbeschreibung und Untertitel prüfen,auditoría de subtítulos accesibles,contrôle accessibilité sous-titres"
  requires: ""
---

# Accessibility Caption AD Check

## Activation
Activate during `review` / `qc` on any deliverable with spoken narration, narrative sound effects, or visual-only metrics/warnings to verify bidirectional sensory parity (deaf/hard-of-hearing viewers receive all meaningful sound via captions; blind/low-vision listeners receive all critical visual claims via narration or an audio-description stem). Search aliases: `accessibility caption check`, `erişilebilir altyazı ve sesli betimleme denetimi`, `Barrierefreiheit Untertitel-Prüfung`.

## Decision rules
- **Audio-to-text parity (D/HoH)**:
  - Every spoken word must appear in synchronized captions (`+-3` frames onset accuracy).
  - Every **story-bearing** non-speech sound cue (for example, an alarm chime signaling failure, a door slam, or comedic music hard-stop) must be bracket-tagged in the active `video_lang` (`"[warning chime]"`, `"[uyarı sesi]"`, `"[Warnton]"`), while decorative background pads that carry zero narrative turn need only an initial `"[calm synth pulse]"` or can omit cluttering tags.
  - Multi-speaker scenes (`>= 2` voices) must mark speaker switches via `"- "` prefix or `[Speaker Name]` label whenever the speaker is off-screen or ambiguous.
- **Visual-to-audio parity (Blind / screenless listening)**:
  - Never rely on `"Look at this number right here"` with an unspoken on-screen `"94%"` — either weave the concrete number directly into primary narration (*integrated description*, best for short-form!) or provide a separate timed audio-description (`AD`) stem inside natural speech pauses.
- **Visual & vestibular safety**: enforce caption contrast `>= 4.5:1` (`>= 7.0:1` AAA preferred), flash rate `< 3` luminance transitions per second (`flash-safety`), and `--reduced-motion` availability.

## Parameters and defaults
- `sync_onset_tolerance_frames`: `3` frames (`100 ms` at `30/1` fps).
- `caption_contrast_min`: `4.5` (`7.0` recommended for open burned-in pills).
- `integrated_narration_preferred`: `true` (write self-describing primary narration so short-form reels need zero awkwardly squeezed secondary AD tracks).
- `non_speech_tag_brackets`: `"[...]"` localized to `video_lang`.

## Procedure
1. **Mute-watch pass (D/HoH test)**: inspect the rendered timeline with audio muted; flag any beat where a joke, warning, speaker switch, or sonic reveal becomes incomprehensible without sound, and add localized `[sound cue]` or speaker tags.
2. **Eyes-closed pass (Audio-only / AD test)**: read/listen to the narration + audio track without looking at frames; flag every deictic orphan (`"this"`, `"here"`, `"as shown"`, unspoken title card, silent end-card URL/handle) and either speak the concrete value in narration or author an AD cue in natural pause windows.
3. Verify caption `reading_speed`, `contrast`, and `vertical_safe_zones` gates all return `pass`.
4. Check `flash-safety` (`<= 3 Hz` luminance flashes) across transitions and visualizers.
5. Emit structured accessibility audit status (`caption_parity`, `visual_info_spoken`, `speaker_id`, `contrast`, `flash_safe`) in the review report.

## Failure modes and fixes
- **Deictic black hole (`"This flag cuts size to this much!"`)**: rewrite primary script to `"The crf-20 flag cuts file size to seven megabytes"` — clearer for *every* viewer and 100% accessible without an extra track!
- **Silent title card + silent end-card CTA with music only**: add concise spoken title/CTA or an optional `ad.vtt` / `ad.wav` cue naming the title and call to action.
- **Untranslated `[music]` tag in Turkish/German `.vtt` file**: localize non-speech tags (`[sakin elektronik müzik]`, `[ruhige Elektronikmusik]`).

## Checklist
- [ ] Mute-watch test confirms all speech, speaker changes, and plot-bearing SFX are captioned in `video_lang`.
- [ ] Audio-only test confirms zero unspoken numbers, warnings, or `"look at this"` deictic orphans.
- [ ] Caption contrast clears `>= 4.5:1` (`>= 7.0:1` target) and sync stays within `+-3` frames.
- [ ] Luminance flashes stay `< 3` per second and `--reduced-motion` renders cleanly.

## Worked examples
- **Example 1 (Fixing unspoken chart metric via integrated description, EN)**: Draft script `"As you can see here, option B wins easily"` (fails audio-only parity) -> Rewritten `"Option B finishes in four seconds compared to nineteen seconds for option A"` -> Passes both eyes-free listening and clear captioning with zero extra runtime.
- **Example 2 (Two-character cutscene `.vtt` cue, DE)**:
  ```text
  00:00:04.200 --> 00:00:06.800
  [Relais klickt, Lüfter verstummt]
  - Warte — der Takt steht still.
  ```

## Resources (load only if needed)
- [Bidirectional WCAG media parity check matrix](references/wcag-media-parity-matrix.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
