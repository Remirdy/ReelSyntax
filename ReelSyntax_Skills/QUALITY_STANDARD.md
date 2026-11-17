# Production quality contract — v2

AAA is an aspirational production quality target, not a certification or a guarantee. A cinematic image, a brand film, a data explainer and an intentionally static tribute require different choices. Respect the brief above all defaults. This contract is loaded once for a production; specialist skills and references are opened only for active work items.

## Gate sequence

| Gate | Required evidence | Release-blocking examples |
|---|---|---|
| G0 Brief and rights | requirement matrix, source/license ledger, approved brand/identity/camera/text locks | ambiguous hard requirements, unauthorized assets, unsupported claims |
| G1 Concept | visual thesis, shot map, style bible, 2–3 candidate hero frames | no readable focal action, infeasible visual direction |
| G2 Animatic | integer-frame timeline, temporary audio, approved duration, shot IDs | timing mismatch, unreadable key action, wrong narrative |
| G3 Look development | representative hero + supporting frames, neutral look reference, material/typography tests | wrong color transform, unstable identity, poor silhouettes |
| G4 Motion and picture lock | motion previews, full edit, continuity ledger, locked regions | visible unintended clipping, jumps, unwanted text, changed approved material |
| G5 Sound | source/stem/cue manifest, loudness and peak measurement, playback review | clipped/absent required mix, wrong sync, missing rights |
| G6 Technical master | declared output profile, decode/probe report, frame counts, QA exceptions | corrupt file, wrong dimensions, rate, duration or locked properties |
| G7 Creative acceptance | actual rendered playback, timecoded review and issue closure | unresolved material visual defects, unreviewed high-risk output |

Do not proceed to final delivery with a failed hard gate. If a gate cannot be tested, mark blocked or review, not pass. Drafts may proceed only with clearly marked unresolved assumptions. Approvals are conditional on operation mode; autonomous mode does not waive hard constraints.

## Quality profiles and defaults

`draft`: representative keyframes and risky 1–3-second motion segments; low-cost resolution/samples; temporary assets explicitly marked. `production`: complete full-rate render, source manifests, visual/audio review, technical tests. `hero`: production requirements plus neutral/hero comparison, motion extrema review, high-quality source/intermediate when needed, A/B refinement and final target-device review. Do not upscale, force 60 fps, add HDR, or maximize samples merely because the hero profile is selected.

Suggested defaults, override by brief or delivery specification: 24 or 25 fps for film-style cadence; 30 fps for many web/product demos; 60 only for meaningful smooth motion or source fidelity. Work at target aspect ratio. Use 1080p as common output baseline where requested and assets support it, 4K only when justified; review target crop separately. Use rational rates (e.g. 30000/1001) without cumulative rounding. Intermediate PNG/EXR or suitable mezzanine if necessary; use 48 kHz production audio when feasible. Explicit color primaries/transfer/matrix and full/limited range, consistent linear-light compositing as appropriate, one output transform only. ACES/AgX are options, not interchangeable defaults. For typical web delivery use a declared SDR profile and compatible codec; never label SDR pixels as HDR.

### Suggested objective thresholds (project presets, not universal industry rules)

- Exact dimensions, requested rational frame rate, expected frame count, decodable required streams. Nominal runtime tolerance ≤1 output frame when container rounding applies; account explicitly for AAC priming/encoder padding. No unexplained PTS discontinuities or repeated frames.
- Require intentional-black, stillness and silence exceptions with half-open time ranges, not global disabling. Initial screening: blackdetect interval ≥0.25 s; freeze ≥0.6 s; silence below −50 dB for ≥0.5 s. Tune thresholds to content and review findings. Intentional locked camera does not imply frozen image. Automated detection can miss near-black, small-area motion or content errors.
- Locked camera: compare all transform/projection samples when available; unchanged within declared numerical tolerance (e.g. 1e-6 for normalized transform values); protected pixel regions compare at lossless pre-encode stage with appropriate tolerance. Compression differences make bit-exact decoded comparison inappropriate unless lossless.
- Voice/visual event alignment: suggested ≤2 output frames for visual emphasis anchors, tighter for lip sync when possible; verify actual sound/picture. For web, example −14 LUFS target ±1 LU and true peak ≤−1 dBTP if delivery profile requests; for EBU R128 broadcast use −23 LUFS and applicable tolerance/true-peak spec. Never normalize intentional silence. Check after encode.
- Text: use measured glyph bounds at keyframes and motion extrema, safe area from platform/brief, no unsupported glyphs, no unintended overlays. Contrast 4.5:1 for normal and 3:1 for large text as a readability heuristic adapted from WCAG; not a general film compliance certificate. Review animated backgrounds and localized strings. 5% title inset can be a starting layout margin, not a platform overlay guarantee.
- Motion: purposeful acceleration, readable holds, no unexplained pops or foot sliding. Shadow/contact, material scale, light direction, spatial hierarchy and character/prop continuity must be visually reviewed. No generic slideshow look unless requested. Flash screening is not a photosensitivity safety certification.

## Creative review rubric

Score each applicable dimension 0–4 after viewing actual frames and full playback. 0 absent/broken, 1 major defects, 2 acceptable draft, 3 production-ready, 4 exceptional in context. Use N/A with explanation; do not assign artificial precision. For a hero candidate require every applicable dimension ≥3 and no unresolved blocking defect; a human or capable visual/audio reviewer must separately approve release. Never infer a score from a successful encode.

| Dimension | What to assess |
|---|---|
| Intent and storytelling | every beat changes information, action, or feeling; strong opening/payoff |
| Art direction | intentional palette, form, typography and negative space; no generic filler |
| Composition | focal hierarchy, eye trace, readable silhouettes, appropriate camera |
| Motion | spacing, acceleration, weight, contact, continuity, rhythm |
| Lighting/material | believable surfaces or coherent stylization, exposure, reflections, contact |
| Editing | purposeful cuts, spatial logic, timing, transitions, no padding |
| Sound | intelligibility, cue motivation, controlled dynamics, no unwanted masking |
| Brand/identity | exact locked assets, style and character continuity |
| Delivery | target crop, accessible text when required, clean actual encode |

Avoid gratuitous gradients, neon, particle clutter, fake letterboxing, generic UI card piles, uncontrolled camera movement, overexposure, gratuitous blur, and repetitive template transitions. These are failure modes, not absolute bans. A restrained design is often better than more effects. A film-quality human performance needs suitable rig/asset/animation and review; code-only methods do not automatically create photoreal actors or studio CGI.

## Evidence and repair

Record `check_id`, `stage`, `skill_id`, `artifact`, `frame_range`, `expected`, `observed`, `status`, `severity`, `reviewer`, and `repair` in a per-project ledger. No fabricated metrics. Classify blocker/major/minor; fix root cause at source. Preserve originals and locks; use scene-level invalidation; default maximum 2 automatic repair attempts for same issue, then report blocker or request direction. Re-run affected tests and adjacent transitions. Keep before/after contact sheets, source and final file. A final artifact is valid only if actual file exists and was decoded. No unverified host or adapter claim.

## Technical sources

- FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
- EBU R128: https://tech.ebu.ch/publications/r128
- ACES output transforms: https://docs.acescentral.com/system-components/output-transforms/
- Three.js color management: https://threejs.org/manual/pages/color-management.html
- WCAG readable contrast basis: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- Agent Skills specification: https://agentskills.io/specification
- Animation foundational principles overview: https://www.lafilm.edu/blog/history-and-use-12-principles-of-animation/

These inform the independent project defaults and methods. Follow delivery-specific requirements and current versions; the pack does not implement every cited standard or certify compliance.
