---
name: showreel-direction
description: "Curate and cut a 25-to-45-second multi-format capability showreel that front-loads peak craft in frame 0, alternates visual mediums, matches motion vectors, and resolves into the signature card."
metadata:
  category: direction
  stage: edit
  status: validated
  version: "2.0.0"
  aliases: "showreel direction,demo reel editing arc,tanıtım seçkisi yönetimi,portfolyo şov릴 kurgusu,Showreel-Regie,Demoreel-Dramaturgie schneiden,dirección de bobina de demostración,direction de bande démo"
  requires: ""
---

# Showreel Direction

## Activation
Activate when assembling a flagship `25s–45s` capability reel (`showcase/showreel.mp4`), studio sizzle, or README/landing-page hero montage from real rendered project outputs. Search aliases: `showreel direction`, `tanıtım seçkisi yönetimi`, `Showreel-Regie`.

## Decision rules
- **Zero-throat-clearing frame-0 rule**: **never** open a showreel with a `3`-second logo fade-in! Open on frame `0` with the single most arresting `3D` / kinetic / cutscene shot already in motion, flash a crisp `1.2s` title overlay (`<= 36f`), and place the full creator signature sting at the *closing* bar!
- **Real pipeline provenance rule**: every clip included in a ReelSyntax showreel must be a genuine `reelsyntax make` / `render` output with reproducible `reel.json` provenance (`manifest.json`), never hand-retouched external footage pretending to be tool output.
- **Medium & language contrast alternation**: never place two flat typography cards or two slow dark 3D shots back-to-back; alternate visual texture and script across cuts (`3D Cycles -> crisp EN kinetic card -> low-poly character cutscene -> TR data chart -> DE paper-cutout -> shader loop`) so breadth registers effortlessly in `30` seconds.
- **Motion-vector & bar-grid continuity**: cut on `1`-bar or `half-bar` musical accents (`bar-grid-music-alignment`) and match directional momentum across hard cuts (a `push_in` shot cuts into a continuing forward camera glide, or a `wipe_left` carries left-ward motion into a pan-left cutscene).

## Parameters and defaults
- `ideal_duration_sec`: `32.0` s (`24s–45s` ceiling; cut the weakest `20%` of clips rather than padding to `60s`!).
- `avg_clip_frames_30fps`: `48–75` frames (`1.6s–2.5s` per showcase excerpt; `90f` max for dialogue/cutscene beat).
- `climax_window_pct`: `0.72–0.86` of runtime (fastest half-bar cut cluster + richest 3D/shader visual), followed by `brand-sting-remirdy` (`48–66f`).
- `aspect_master`: `16:9` (`1920x1080`) for README/desktop hero, framing `9:16` excerpts inside clean `3`-up triptych panels or dynamic editorial cards rather than ugly black pillarboxes!

## Procedure
1. Audit candidate `hero` renders, keeping only clips that passed `qc` (`technical_status == "pass"`) and passed human visual review; rank each `1..5` on instant `0.5s` silhouette impact.
2. Place rank-`#1` clip on frame `0`, rank-`#2` clip at the `78%` climax peak, and rank-`#3` clip right before the closing sting.
3. Sequence middle clips alternating `3D <-> 2D/Type <-> Character/Paper <-> Data` and showcasing `EN`, `TR`, and `DE` typography naturally without repeating the same palette twice in a row.
4. Present `9:16` vertical outputs inside a cohesive `16:9` triptych/editorial mat (`3` synchronized vertical reels side-by-side with `16 px` gutters over `#1E2430` slate) instead of lone black sidebars.
5. Normalize integrated loudness (`-14 LUFS`, `-1.5 dBTP`), conclude with `brand-sting-remirdy`, and generate both `MP4` (`H.264`) + `WebM` (`VP9`) + `poster.webp` for zero-layout-shift web embedding.

## Failure modes and fixes
- **3.5-second dark logo intro loses `60%` of README visitors before shot 1**: move brand sting to the final `2.0s` and start frame `0` on peak motion.
- **`9:16` vertical clip dropped raw into `1920x1080` leaves `66%` empty black pillarboxes**: stage `3` complementary `9:16` formats (`social-hook-reel` + `kinetic-typography` + `photo-slideshow`) as a synchronized `3`-column showcase grid!
- **Jarring luma/saturation jump between clips**: run `cross-shot-grade-consistency` black-floor (`Y >= 24`) and highlight-shoulder normalization across excerpt masters.

## Checklist
- [ ] Frame `0` opens directly on peak rendered motion (logo sting placed at the end).
- [ ] Every clip traces to a reproducible `reel.json` + passing `qc` report.
- [ ] Adjacent cuts alternate visual medium (`3D`, `2D type`, `cutscene`, `data`, `paper`) and showcase `EN`/`TR`/`DE`.
- [ ] `9:16` vertical clips sit in intentional multi-panel editorial frames rather than raw black pillarboxes.

## Worked examples
- **Example 1 (`32s` / `960f` `16:9` `120 BPM` `16`-bar showreel plan)**:
  - Bar `1` (`0–60f`): `cinematic-3d` monolith ignition (frame `0` hook!).
  - Bars `2–3` (`60–180f`): `3`-up vertical triptych (`EN` `social-hook-reel` + `TR` `kinetic-typography` + `DE` `photo-slideshow`).
  - Bars `4–6` (`180–360f`): `retro-lowpoly-cutscene` two-shot turn -> `data-story` animated bar proof.
  - Bars `7–10` (`360–600f`): `stepped-clay-look` -> `paper-cutout` parallax -> `news-ticker` -> `music-visualizer`.
  - Bars `11–14` (`600–840f`): half-bar climax acceleration (`shader-loop-art` -> `cinematic-3d` hero pull-back).
  - Bars `15–16` (`840–960f`): resolved tonic chord into `brand-sting-remirdy` (`120f` with hold).

## Resources (load only if needed)
- [16-bar showreel sequencing grid and 9:16-in-16:9 triptych layout](references/showreel-sequencing-grid.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
