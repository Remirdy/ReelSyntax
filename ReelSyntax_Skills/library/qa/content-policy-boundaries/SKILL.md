---
name: content-policy-boundaries
description: "Enforce strict ethical and legal content boundaries—no real-person likeness or voice impersonation, no third-party brand spoofing, and no unlicensed copyrighted IP."
metadata:
  category: qa
  stage: plan
  status: validated
  version: "2.0.0"
  aliases: "content policy boundaries,impersonation and trademark guard,içerik politikası sınırları,kişi taklidi ve marka koruması,Inhaltsrichtlinien-Grenzen,Imitations- und Markenschutz,límites de política de contenido,limites de politique de contenu"
  requires: ""
---

# Content Policy Boundaries

## Activation
Activate at the `idea` / `plan` and `ingest` gates before compiling scripts, synthesizing voices, or resolving character/logo assets to prevent non-consensual impersonation, deceptive news mimicry, or third-party IP infringement. Search aliases: `content policy boundaries`, `içerik politikası sınırları`, `Inhaltsrichtlinien-Grenzen`.

## Decision rules
- **Zero real-person voice or likeness impersonation**: reject requests to clone, mimic, or attribute fabricated quotes to living or real named individuals without documented first-party authorization in project provenance; substitute clearly fictional archetypes (`"The Architect"`, `"Field Engineer"`) and generic local synthesis voices.
- **Zero third-party brand, logo, or UI spoofing**: never generate or bundle third-party corporate logos, trademarked product trade dress, or real broadcast network chyrons; use generic geometric placeholders or the user's own registered `brand-kit` assets.
- **Zero copyrighted characters, lyrics, or musical scores**: reject prompts requesting famous film/game characters or copyrighted song lyrics; redirect `lyric-video` and `retro-lowpoly-cutscene` to user-provided licensed lyrics/stems or original procedural compositions and original character rigs.
- **Deceptive emergency / breaking-news guard**: `news-ticker` layouts must present real sourced project/domain updates or clearly labeled fictional/template demonstrations, never fabricated public-safety alerts or fake Breaking News impersonating public institutions.

## Parameters and defaults
- `allow_real_person_impersonation`: `false` (hard immutable rule).
- `allow_third_party_trademarks`: `false` unless user explicitly registers owned/authorized assets in `.reelsyntax/asset-licenses.json`.
- `synthetic_disclosure_metadata`: stamp `comment` / provenance manifest indicating procedural/local synthesis origin (`content-credentials-labeling`).

## Procedure
1. Screen brief intent, character names, speaker labels, and lyric inputs at the `idea` gate against real-person impersonation, copyrighted character/lyric requests, and deceptive public-alert framing.
2. If a brief uses a third-party brand/character as a loose style shorthand (for example `"retro console adventure vibe"`), strip all trademarked nouns/logos and translate purely into original geometric/color/cadence attributes (`low-poly faceted rig`, `warm lantern palette`, `stepped poses`).
3. If the brief explicitly demands impersonating a real person or reproducing copyrighted lyrics/logos, halt compilation cleanly with a clear boundary error and suggest an original brand-free alternative.
4. Verify all bundled starter assets and user-supplied files carry clean entries in `.reelsyntax/asset-licenses.json`.
5. Record provenance metadata in `prompt.json` and container tags.

## Failure modes and fixes
- **User writes `"Make famous actor X endorse my app"`**: refuse real-person endorsement fabrication; offer an original animated spokesperson character or kinetic-typography testimonial template using verified customer quotes.
- **`lyric-video` prompt pastes commercial chart-hit lyrics**: halt unlicensed lyric use and prompt the user to supply their own original lyrics or `CC0` / public-domain verse.
- **Mock UI tutorial copies a real social app's trademarked header**: render clean neutral wireframe UI chrome (`rounded pill`, `generic play icon`, `neutral handle @creator`).

## Checklist
- [ ] Zero real-person likenesses, voice clones, or unverified personal quotes appear.
- [ ] Zero third-party trademarks, corporate logos, or real network chyrons are rendered.
- [ ] Characters, music stems, and lyrics are original, public-domain, `CC0`/`CC-BY`, or user-owned.
- [ ] `news-ticker` outputs avoid deceptive public-emergency or institutional spoofing.

## Worked examples
- **Example 1 (Style-reference sanitization, EN)**: Brief `"Make a 90s adventure cutscene with a green-tunic elf hero"` -> Reject trademarked lookalike costume; stage original geometric explorer `"Kira"` in an ochre flight jacket inside an observatory set (`100%` original silhouette and palette).
- **Example 2 (Impersonation refusal, TR)**: Brief `"Ünlü bir haber spikerinin sesiyle sahte son dakika bülteni üret"` -> Reddedilir; kullanıcıya kendi metni ve açık kaynaklı genel sunucu sesiyle doğrulanmış veri özeti (`news-ticker`) şablonu önerilir.

## Resources (load only if needed)
- [Content boundary decision and safe-redirection table](references/boundary-decision-table.md)
- [Production quality contract](../../../QUALITY_STANDARD.md)
