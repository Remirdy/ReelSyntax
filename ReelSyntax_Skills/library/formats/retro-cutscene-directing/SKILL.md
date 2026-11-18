---
name: retro-cutscene-directing
description: "Direct original 22-to-30-second low-poly 3D character cutscenes with crisp faceted lighting, 180-degree dialogue staging, mouth-envelope lip sync, and HUD dialogue boxes."
metadata:
  category: formats
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "retro cutscene directing,lowpoly cutscene staging,retro ara sahne yönetimi,düşük poligonlu diyalog sahnesi,Retro-Zwischensequenz-Regie,Low-Poly-Dialogszene inszenieren,dirección de cinemática retro,mise en scène de cinématique rétro"
  requires: ""
---

# Retro Cutscene Directing

## Activation
Activate when planning and staging `retro-lowpoly-cutscene` stories (`20s–35s`) featuring original low-poly characters, atmospheric geometry sets, dialogue boxes, and stylized speech/blip audio. Search aliases: `retro cutscene directing`, `retro ara sahne yönetimi`, `Retro-Zwischensequenz-Regie`.

## Decision rules
- **100% original IP & brand-free visual design**: use original geometric character silhouettes, custom emblem shapes, and original color schemes — **never** imitate copyrighted console boot logos, trademarked franchise HUDs, or named game characters.
- **Classic 5-shot cutscene grammar (`22s–30s` / `660–900f` at `30/1` fps)**:
  1. `establishing_wide` (`75–96f`): reveals architectural prop + both characters' spatial relationship (`locked` or slow `dolly_in`).
  2. `speaker_a_ots` (`120–165f`): over-the-shoulder medium on Character A (`x = 0.36w`, looking right) stating the inciting problem.
  3. `speaker_b_reverse` (`120–165f`): reverse medium on Character B (`x = 0.64w`, looking left, preserving `180°` axis!) delivering the counter-clue or Dry reaction.
  4. `insert_detail_or_turn` (`90–120f`): close-up on the prop/terminal/artifact changing state (glowing core, dial flip, map marker).
  5. `two_shot_resolve` (`120–165f`): wide/medium two-shot payoff + clean hold.
- **Faceted low-poly shading discipline**: use deliberate flat/hard-creased normals (`300–1200` triangles per character), vertex-style warm/cool key-rim contrast, nearest/crisp low-res procedural textures (`64x64` or `128x128` pixel-art UVs with `interpolation = 'Closest'` so texels stay razor-sharp, never muddy bilinear soup!), and `mouth_envelope` quantized to `3–4` discrete jaw/uv states synced within `<= 2` frames of speech energy (`mouth_sync == pass`).
- **HUD dialogue box safe framing**: reserve the bottom `22%` (`16:9`) or `20%–32%` (`9:16` above platform chrome) for a beveled semi-opaque dialogue box with character portrait/name tag (`>= 7.0:1` text contrast), framing character chins strictly above the box top edge (`y <= 0.72h`).

## Parameters and defaults
- `target_duration_sec`: `24.0` s (`22.0–30.0` s range, `5–7` shots).
- `character_tri_budget`: `350–1200` triangles per character (`flat` / sharp-edge shading).
- `texture_filtering`: `"Closest"` (nearest-neighbor crisp texels) or pure vertex/face-material palettes.
- `mouth_states`: `4` discrete openness steps (`0.0` closed, `0.35` half, `0.75` open, `1.0` wide accent) sampled per frame from vocal RMS envelope.
- `dialogue_box_top_y`: `0.74 * height` (`16:9`) or `0.68 * height` (`9:16`, clearing bottom `0.82h` UI zone).

## Procedure
1. Cast `1` or `2` original low-poly character rigs from the local character kit with contrasting silhouettes and distinct color accents (for example amber vs teal).
2. Block character positions on a top-down stage floorplan (`2.2 m` apart) and place cameras all on one side of the `180°` line between them (`eyeline-headroom-grammar`).
3. Synthesize per-line character dialogue (`local-text-to-speech` + `voice-fx-flat-synth` or `retro_blip_chatter`) and compute per-frame `mouth_envelope` (`len == scene.duration_frames`) + idle blink (`4`-frame blink every `90–135` frames, staggered between characters!).
4. Composite the original beveled dialogue box (`speaker_name` + typewriter or phrase-revealed localized line) below `y = 0.74h` (`16:9`) so zero faces or props of interest are covered.
5. Run `pilot` (`first_5s`) and full `qc` (`mouth_sync == pass`, `contrast == pass`, `reading_speed == pass`).

## Failure modes and fixes
- **Bilinear texture filtering blurs `64x64` low-poly UVs intoVaseline smudge**: switch image texture node interpolation from `'Linear'` to `'Closest'`.
- **Dialogue box covers speaking character's mouth**: raise camera target `y` slightly so character shoulders sit above `dialogue_box_top_y` (`eye_y ≈ 0.32h`).
- **Both characters blink on the exact same frame (`f = 90`) looking robotic**: offset character B's blink seed by `+47` frames.

## Checklist
- [ ] Characters, props, and dialogue HUD are `100%` original and free of third-party game IP/trademarks.
- [ ] Shot sequence preserves the `180°` axis and keeps faces above `dialogue_box_top_y`.
- [ ] Low-poly materials use crisp flat/creased normals and `'Closest'` texel filtering.
- [ ] `mouth_envelope` length matches `duration_frames` (`mouth_sync == pass`) with staggered natural blinks.

## Worked examples
- **Example 1 (`24s` / `720f` `16:9` observatory cutscene, EN)**: Shot 1 (`90f` wide relay tower), Shot 2 (`150f` Engineer Kira `"Signal dropped on sector four."`), Shot 3 (`150f` Bot Orin `"Not dropped — redirected from inside."`), Shot 4 (`120f` close-up amber switch flipping to cyan), Shot 5 (`210f` two-shot looking up as beacon ignites).
- **Example 2 (`22s` / `660f` `9:16` vertical cutscene adaptation, TR)**: Diyalog kutusu `y = 0.68h..0.81h` güvenli bandına alınır, karakter kadrajları yakın-orta ölçeğe (`eye_y = 0.34h`) çekilerek dikey ekranda yüz ifadeleri net korunur.

## Resources (load only if needed)
- [Low-poly cutscene 5-shot blocking and mouth-envelope spec](references/cutscene-shot-grammar.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
