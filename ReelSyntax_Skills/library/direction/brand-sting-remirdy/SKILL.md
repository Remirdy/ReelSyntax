---
name: brand-sting-remirdy
description: "Render the restrained 1.6-to-2.4-second Remirdy closing signature sting or corner mark for first-party showcase deliverables while keeping --attribution off completely unbranded."
metadata:
  category: direction
  stage: export
  status: validated
  version: "2.0.0"
  aliases: "brand sting remirdy,creator signature sting,remirdy kapanış imzası,üretici imza kartı kuralları,Remirdy-Signatur-Abspann,dezentes Urheber-Signet,cierre de firma remirdy,signature finale remirdy"
  requires: ""
---

# Brand Sting Remirdy

## Activation
Activate when rendering official ReelSyntax showcase videos, showreels, social demos, or projects where `general.attribution = "on"` / `--attribution on` is active, or when verifying that `--attribution off` omits all first-party marks cleanly. Search aliases: `brand sting remirdy`, `remirdy kapanış imzası`, `Remirdy-Signatur-Abspann`.

## Decision rules
- **User sovereignty rule (`--attribution off` = zero trace)**: user-created videos belong `100%` to the user; when `--attribution off` (or `attribution = "off"` in `reelsyntax.toml`) is set, append **zero** sting frames, **zero** corner watermarks, and **zero** container credit overrides!
- **Restrained editorial craftsmanship when `on` (never a loud intrusive watermark)**:
  - **Closing sting mode (`default` for `showcase/` & `showreel`)**: `48–66` frames (`1.6s–2.2s` at `30/1` fps) appended cleanly after the payoff card: geometric aperture/frame mark draws in over `16` frames (`cubic_out`), wordmark `"Remirdy"` + subtle subtitle `"Built with ReelSyntax"` (`"ReelSyntax ile üretildi"` / `"Erstellt mit ReelSyntax"`) settles for `32–44` frames on `#1F2430` charcoal slate (`contrast >= 11.0:1`), paired with a quiet warm harmonic fifth chime (`-18 LUFS` momentary, `tp <= -2.0 dBTP`, silent when `constraints.no_audio` is true).
  - **Subtle end-corner mode (for seamlessly looping `loop-art`)**: because appending an end card would break an infinite loop, `loop-art` omits the appended card even when attribution is `on` (recording credit in `manifest.json` metadata instead, or placing a `18%`-opacity micro-caption only when explicitly requested).
- **Safe-zone & aspect adaptability**: center optical wordmark inside `[0.25w..0.75w, 0.42h..0.58h]` across `16:9`, `9:16`, `4:5`, and `1:1` so platform UI overlays never clip the signature.

## Parameters and defaults
- `attribution_mode`: `"off"` | `"on"` (controlled via CLI `--attribution` or `reelsyntax.toml` `general.attribution`).
- `sting_duration_frames_30fps`: `54` frames (`1.80s` at `30/1` fps: `14f` geometric mark reveal + `34f` settled hold + `6f` tail breath).
- `sting_ground_hex`: `#1F2430` (`Y = 36`, safely above `blackdetect` `0.10` floor so the sting itself never triggers a false `black` warning!).
- `sting_ink_hex` / `accent_hex`: `#F8FAFC` (`13.8:1` contrast) / `#38BDF8` (`2.5 px` aperture mark stroke, `2x` SSAA).
- `audio_chime_gain_dbfs`: `-18.0` dBFS (`0` when `no_audio` or `no_music` lock is active).

## Procedure
1. Read resolved `attribution` setting (`CLI --attribution` > `reelsyntax.toml` > default). If `"off"`, return the project scene list untouched (`zero` added frames or marks).
2. Check format loop constraint: if `loop == True` (`loop-art`), keep timeline seamless and write attribution strictly to provenance `manifest.json` rather than breaking the visual loop.
3. Otherwise append the deterministic `brand_sting` scene (`54` frames scaled to rational `fps`) using localized credit line (`EN`: `"Built with ReelSyntax"`, `TR`: `"ReelSyntax ile üretildi"`, `DE`: `"Erstellt mit ReelSyntax"`).
4. Synthesize or attach the gentle `440 + 660 Hz` damped harmonic chime (`380 ms` cosine decay, `-18 dBFS`) unless `no_audio` is active; under `--reduced-motion`, replace geometric stroke draw-in with a calm `8`-frame opacity fade.
5. Verify the appended sting passes `contrast`, `vertical_safe_zones`, `black`, `freeze`, and `true_peak` checks in `qc`.

## Failure modes and fixes
- **`--attribution off` still leaves a metadata banner or extra `54` frames**: test both `--attribution on` and `--attribution off` in automated unit tests to guarantee exact `0`-frame / `0`-pixel overhead when `"off"`.
- **Pure `#000000` sting background trips `qc` `blackdetect`**: use `#1F2430` architectural slate (`Y = 36/255`) so the sting looks sleek and passes `black == pass` without needing special exceptions.
- **Appended sting breaks `loop-art` seamless wrap**: bypass appended end-cards whenever `format_id == "loop-art"` or `--loop` is active.

## Checklist
- [ ] `--attribution off` produces zero extra frames, watermarks, or visual marks.
- [ ] Closing sting lasts `1.6s–2.2s` (`54f` default) on `#1F2430` ground (`>= 11:1` contrast, `black == pass`).
- [ ] Subtitle line localizes cleanly to `video_lang` (`EN` / `TR` / `DE`).
- [ ] Seamless `loop-art` deliverables remain unbroken loops without appended end cards.

## Worked examples
- **Example 1 (`showcase/social-hook-en.mp4`, `--attribution on`, `30/1` fps)**: `450f` main reel + `54f` `brand_sting` (`504f` = `16.8s` total): `14f` `2x`-SSAA aperture hexagon draw, `"Remirdy"` (`56 px` SemiBold `#F8FAFC`) + `"Built with ReelSyntax"` (`28 px` `#94A3B8`, `6.2:1` contrast), soft `-18 dBFS` harmonic chime -> `qc` `technical_status: pass`.
- **Example 2 (User client project with `--attribution off`)**: `450f` main reel -> `450f` output (`0` sting scenes, `0` marks).

## Resources (load only if needed)
- [`--attribution` flag contract and Remirdy sting geometry](references/attribution-flag-and-sting-spec.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
