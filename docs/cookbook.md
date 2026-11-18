# Prompt Cookbook

`reelsyntax make` compiles a natural-language brief into a validated `reel.json` plan, routes production skills, and steps through approval gates (`idea -> script -> look -> frames -> pilot -> full -> hero -> qc`). Clear constraints in the prompt prevent crowded headlines, missed opening hooks, unverified claims, and wasted renders.

See [CLI](cli.md) for command flags, [Quality](quality.md) for objective checks, and [Glossary](i18n/glossary.md) for localized terminology across English (`en`), Turkish (`tr`), and German (`de`).

## Prompt anatomy and workflow

Include five signals in every production prompt:

1. **Format and aspect** — explicit `--format <id>` or clear format keywords plus `9:16`, `1:1`, `16:9`, or `4:5`.
2. **Duration and cadence** — seconds (`12s`, `15 sn`, `24 Sek.`) and optional frame rate (`24fps`, `30fps`, `60fps`).
3. **Topic and scene count** — concrete beats instead of vague adjectives, leaving room for short display headings.
4. **Language separation** — keep prompt language, target video language (`--lang`), and interface language (`--ui-lang`) explicit when mixing locales.
5. **Tone and palette** — keywords such as `calm`, `editorial`, `warm`, or `high contrast` paired with dark/light slate discipline (`Y >= 44/255` on dark cards).

Preview plans and render budgets with zero disk writes before creating a project:

```sh
reelsyntax make "<prompt>" --format kinetic-typography --dry-run --json
reelsyntax make "<prompt>" --format kinetic-typography --out ./out/my-reel
reelsyntax step ./out/my-reel idea --approve
reelsyntax step ./out/my-reel script --edit "Shorten beat 2 heading to three words"
reelsyntax revise ./out/my-reel "scene 2 heading: Clear Metrics" --render --profile draft
```

## Format index

| Format | Category | Primary engine | Default checks to plan for |
| --- | --- | --- | --- |
| [`kinetic-typography`](#kinetic-typography) | `social` | `pillow`, `ffmpeg` | Reading speed, contrast, left-rail width |
| [`photo-slideshow`](#photo-slideshow) | `personal` | `pillow`, `ffmpeg` | Registered photo assets, EXIF orientation, dissolve holds |
| [`social-hook-reel`](#social-hook-reel) | `social` | `pillow`, `ffmpeg` | Opening hook (`<= 2.0s`), vertical safe zones |
| [`explainer-slides`](#explainer-slides) | `education` | `pillow`, `ffmpeg` | Chapter cadence, source notes, caption CPS |
| [`lyric-video`](#lyric-video) | `music` | `pillow`, `ffmpeg` | Beat-grid sync, two-line caption fit, vocal timing |
| [`music-visualizer`](#music-visualizer) | `music` | `pillow`, `ffmpeg` | Flash safety (`< 3 Hz`), beat quantization, contrast |
| [`channel-intro`](#channel-intro) | `creator` | `pillow`, `ffmpeg` | `4s–15s` runtime window, reveal pacing, end card |
| [`data-story`](#data-story) | `education` / `business` | `pillow`, `ffmpeg` | Sourced quantitative claims, tabular units, bar contrast |
| [`news-ticker`](#news-ticker) | `business` | `pillow`, `ffmpeg` | Bottom `18%` safe zone, `--reduced-motion` pagination |
| [`product-promo`](#product-promo) | `business` | `pillow`, `ffmpeg` | `<= 2.0s` hook, sourced proof, asset licenses |
| [`loop-art`](#loop-art) | `art` | `pillow`, `ffmpeg` | Periodic seam (`qc --loop`), flash threshold |
| [`retro-lowpoly-cutscene`](#retro-lowpoly-cutscene) | `comedy` | `blender`, `pillow`, `ffmpeg` | `18s–45s` arc, dialogue safe zone, mouth sync |
| [`cinematic-3d`](#cinematic-3d) | `art` | `blender`, `pillow`, `ffmpeg` | Lookdev lighting, depth of field, tonal progression |
| [`stepped-clay-look`](#stepped-clay-look) | `art` | `blender`, `pillow`, `ffmpeg` | Stepped `10–12` poses/sec timing, tactile rim light |
| [`paper-cutout`](#paper-cutout) | `art` | `pillow`, `ffmpeg` | Layer shadow separation, `--reduced-motion` static fold |

---

## `kinetic-typography`

High-contrast typographic statement cards across `9:16`, `1:1`, `16:9`, and `4:5` (`6s–60s`).

### EN — `kinetic-typography`

- **Weak prompt:** `Make a cool video with some coding advice`
- **Strong prompt:** `12s 9:16 kinetic typography reel: 4 concise tips on deterministic local builds, calm charcoal slate palette, max 3 words per heading.`

### TR — `kinetic-typography`

- **Weak prompt:** `Yazılım hakkında güzel bir yazı videosu yap`
- **Strong prompt:** `12 sn 9:16 kinetik tipografi videosu: Yerel derlemede hız kazandıran 4 kısa ipucu, sakin koyu arduvaz palet, başlıklar en fazla 3 sözcük.`

### DE — `kinetic-typography`

- **Weak prompt:** `Mach ein Video über sauberen Code`
- **Strong prompt:** `12 Sek. 9:16 Kinetische Typografie: 4 knappe Tipps für deterministische Builds, ruhige Schieferpalette, maximal 3 Wörter pro Überschrift.`

- **Diagnosis:** Weak prompts omit duration, aspect, card count, and heading length, causing multi-line display overflow (`DejaVuSans-Bold` clipping inside the left `0.07w..0.50w` column) or hurried cuts above `15`/`14`/`13` CPS (`en`/`tr`/`de`). Pure `#000000` backgrounds can also trigger broadcast black-frame alarms.
- **Repair tips:** Run `reelsyntax make ... --format kinetic-typography --dry-run` first to verify frame count (`360` frames at `30 fps`). If a heading clips at `frames`, run `reelsyntax step <dir> script --edit "Move detail from scene 2 heading into subheading"` or lift dark backgrounds via `reelsyntax revise <dir> "scene 1 background #242933"`.

---

## `photo-slideshow`

Beat-paced memory and portfolio slideshows (`8s–90s`) using `layer-stack` photo plates, Ken Burns motion, and continuous audio bridges.

### EN — `photo-slideshow`

- **Weak prompt:** `Slideshow of my trip`
- **Strong prompt:** `18s 4:5 warm photo slideshow of an autumn harbor walk, 4 paced chapters with short 5-word captions and gentle dissolves.`

### TR — `photo-slideshow`

- **Weak prompt:** `Fotoğraflarımdan bir slayt yap`
- **Strong prompt:** `18 sn 4:5 sıcak tonlu sonbahar liman yürüyüşü fotoğraf slaytı, 4 bölüm, 5 sözcüklük kısa altyazılar ve yumuşak geçişler.`

### DE — `photo-slideshow`

- **Weak prompt:** `Diashow aus meinen Bildern`
- **Strong prompt:** `18 Sek. 4:5 warme Foto-Diashow eines Herbstspaziergangs am Hafen, 4 Kapitel mit kurzen Untertiteln und weichen Überblendungen.`

- **Diagnosis:** Unspecified photo slideshows rush transitions before viewers parse each frame and miss asset licensing metadata if external photos are unregistered.
- **Repair tips:** Place photos inside `<dir>/assets/` or run `reelsyntax assets register <dir> <photo>` before `make` so `LICENSES.md` and EXIF orientation stay verified. Re-run `reelsyntax render <dir> --reduced-motion` if pan-and-zoom motion needs static easing for accessible delivery.

---

## `social-hook-reel`

Fast-opening vertical reels (`9:16`, `4:5`, `1:1`; `8s–45s`) governed by a `<= 2.0s` opening hook and right-rail clearance.

### EN — `social-hook-reel`

- **Weak prompt:** `Short reel explaining why caching matters`
- **Strong prompt:** `15s 9:16 social hook reel: open in under 2s with "Builds Slow?", 3 proof beats on content-addressed frame caches, punchy payoff.`

### TR — `social-hook-reel`

- **Weak prompt:** `Önbellek hakkında kısa dikey video`
- **Strong prompt:** `15 sn 9:16 dikey kısa kanca videosu: ilk 2 saniyede "Derleme Yavaş mı?" açılışı, 3 kanıt sahnesi ve net sonuç kartı.`

### DE — `social-hook-reel`

- **Weak prompt:** `Kurzes Hochformatvideo über Caching`
- **Strong prompt:** `15 Sek. 9:16 vertikales Hook-Reel: Einstieg unter 2 Sek. mit "Builds träge?", 3 Beleg-Beats zum Frame-Cache und klares Fazit.`

- **Diagnosis:** Weak briefs bury the premise in a slow fade-in or place wide titles across the bottom `18%` / right-edge UI rail, failing `opening_hook` and `vertical_safe_zones` QC checks.
- **Repair tips:** Specify a two-to-three-word opening question so beat `1` stays at `<= 60` frames (`30 fps`) with a localized kicker (`HOOK` / `DİKKAT` / `STOPP`). Use `reelsyntax revise <dir> "scene 1 heading: Builds Slow?"` if the hook drifts past the `2.0s` window.

---

## `explainer-slides`

Structured educational lessons (`15s–120s`, `16:9`, `9:16`, `1:1`) with chapter framing, timed narration or captions, and a closing recap.

### EN — `explainer-slides`

- **Weak prompt:** `Explain how rational frame rates work`
- **Strong prompt:** `30s 16:9 explainer slides on rational frame clocks: 3 chapters (integer ticks, drift risk, FFprobe check) plus 1-sentence recap, editorial light palette.`

### TR — `explainer-slides`

- **Weak prompt:** `Kare hızını anlatan eğitim videosu`
- **Strong prompt:** `30 sn 16:9 konu anlatımı slaytları: rasyonel kare saati, 3 bölüm (tam kare, kayma riski, FFprobe denetimi) ve kısa özet, açık editoryal palet.`

### DE — `explainer-slides`

- **Weak prompt:** `Erklärvideo zu Bildraten erstellen`
- **Strong prompt:** `30 Sek. 16:9 Erklärvideo-Folien zu rationalen Bildraten: 3 Kapitel (ganzzahlige Frames, Drift-Risiko, FFprobe-Prüfung) plus kurzes Fazit, heller Editorial-Stil.`

- **Diagnosis:** Open-ended topics cram paragraphs onto a single slide, violating reading-speed CPS ceilings and leaving chapters unbalanced.
- **Repair tips:** Name the exact chapters (`3`–`5` beats) and hold technical jargon inside concise `subheading` lines. If `qc` reports `reading_speed` warnings, extend that scene's hold at the `script` gate with `reelsyntax step <dir> script --edit "Split slide 2 into two beats"`.

---

## `lyric-video`

Beat-quantized kinetic lyric cards (`10s–120s`) using original or properly licensed text and balanced two-line phrasing.

### EN — `lyric-video`

- **Weak prompt:** `Make a lyric video for my song`
- **Strong prompt:** `20s 16:9 calm lyric video at 24fps: 4 short original lines ("Harbor lights drift past the pier / Quiet water holds the night"), warm slate background.`

### TR — `lyric-video`

- **Weak prompt:** `Şarkım için söz videosu yap`
- **Strong prompt:** `20 sn 16:9 24fps sakin şarkı sözü videosu: 4 kısa özgün dize ("Liman ışıkları geçer iskeleden / Durgun su saklar geceyi"), sıcak koyu palet.`

### DE — `lyric-video`

- **Weak prompt:** `Erstelle ein Lyric-Video`
- **Strong prompt:** `20 Sek. 16:9 24fps ruhiges Liedtext-Video: 4 kurze eigene Zeilen ("Hafenlichter ziehen am Kai vorbei / Stilles Wasser trägt die Nacht"), warme dunkle Palette.`

- **Diagnosis:** Pasting full verses without line breaks overruns caption line limits (`42`/`40`/`38` characters per line for `en`/`tr`/`de`) and misaligns beats when duration does not match bar count.
- **Repair tips:** Provide explicit `/` line breaks for each two-line beat and keep lyrics original or licensed in `<dir>/assets/`. Adjust stanza timing via `reelsyntax step <dir> script --edit "Hold chorus card 2 for 150 frames"`.

---

## `music-visualizer`

Audio-reactive spectrum and concentric ring animations (`10s–90s`) locked to a quantized beat grid and `< 3 Hz` flash safety.

### EN — `music-visualizer`

- **Weak prompt:** `Flashing audio visualizer with neon strobes`
- **Strong prompt:** `16s 1:1 calm music visualizer: concentric spectrum rings synced to 120 BPM, smooth pulse below 3 Hz, deep midnight blue and teal accent.`

### TR — `music-visualizer`

- **Weak prompt:** `Hızlı yanıp sönen müzik görselleştirici`
- **Strong prompt:** `16 sn 1:1 sakin müzik görselleştirici: 120 BPM ritmine kilitli eş merkezli spektrum halkaları, 3 Hz altı yumuşak nabız, gece mavisi palet.`

### DE — `music-visualizer`

- **Weak prompt:** `Blitzender Musik-Visualizer`
- **Strong prompt:** `16 Sek. 1:1 ruhiger Musik-Visualizer: konzentrische Spektrumringe im 120-BPM-Raster, weiche Pulsation unter 3 Hz, tiefes Nachtblau mit Türkis-Akzent.`

- **Diagnosis:** Asking for "strobes" or rapid full-frame flashes causes visual discomfort and fails luminance-modulation safety checks; missing BPM/duration produces arbitrary bar timing.
- **Repair tips:** Replace strobe terms with smooth harmonic cues (`rings`, `steady glow`) and verify the rendered preview with `reelsyntax render <dir> --reduced-motion` when exporting accessible variants.

---

## `channel-intro`

Crisp creator opener and end-card stings (`4s–15s`, `16:9`, `9:16`, `1:1`) with immediate mark reveal, tagline, and clean audio tail.

### EN — `channel-intro`

- **Weak prompt:** `Make a 30 second intro for my channel`
- **Strong prompt:** `6s 16:9 channel intro: immediate geometric emblem reveal on frame 0, 3-word tagline "Frame Accurate Video", clean resolve to end card, editorial palette.`

### TR — `channel-intro`

- **Weak prompt:** `Kanalım için uzun bir giriş videosu yap`
- **Strong prompt:** `6 sn 16:9 kanal açılış jeneriği: 0. karede sade geometrik amblem açılışı, "Tam Kare Kurgu" sloganı ve temiz bitiş kartı.`

### DE — `channel-intro`

- **Weak prompt:** `Langes Kanal-Intro erstellen`
- **Strong prompt:** `6 Sek. 16:9 Kanal-Intro: geometrisches Emblem ab Frame 0, dreiteiliger Claim "Präziser Frameschnitt" und ruhige End-Card.`

- **Diagnosis:** Requesting `20s–30s` intros exceeds the `channel-intro` `4s–15s` ceiling (`FormatRunner` clamps duration, or audiences drop off before content starts).
- **Repair tips:** Keep `duration_sec` between `5` and `8` seconds and avoid multi-paragraph taglines. Revise the tagline cleanly without re-rendering the emblem via `reelsyntax revise <dir> "scene 2 subheading: Frame Accurate Video"`.

---

## `data-story`

Comparison bars and metric stories (`10s–60s`) governed by `claims-must-be-sourced`, tabular numeral formatting, and legible chart contrast.

### EN — `data-story`

- **Weak prompt:** `Show that our tool is 10x faster than everything else`
- **Strong prompt:** `16s 16:9 data story comparing draft vs. cached render time (18.4 s vs. 2.1 s, source: local benchmark ledger), editorial light palette, 3 beats.`

### TR — `data-story`

- **Weak prompt:** `Aracımızın herkesten 10 kat hızlı olduğunu gösteren grafik yap`
- **Strong prompt:** `16 sn 16:9 veri hikâyesi: önbelleksiz ve önbellekli derleme süresi (18,4 sn vs. 2,1 sn, kaynak: yerel ölçüm kaydı), açık editoryal palet, 3 sahne.`

### DE — `data-story`

- **Weak prompt:** `Zeig dass alles zehnmal schneller läuft`
- **Strong prompt:** `16 Sek. 16:9 Datenstory zum Vergleich von Kalt- und Cache-Render (18,4 s vs. 2,1 s, Quelle: lokales Messprotokoll), heller Editorial-Stil.`

- **Diagnosis:** Unqualified quantitative claims (`10x faster`, `#1`, `%` figures without attribution) trip `claims_sourced` QC in `data-story` and `product-promo`, and mixed decimal conventions break locale readability (`18.4` vs. `18,4`).
- **Repair tips:** Include a concrete source label right in the prompt or attach a project `sources` note before running `reelsyntax qc <dir> --rule claims-must-be-sourced`.

---

## `news-ticker`

Headline banners and stepped/crawl bulletin boards (`8s–45s`, `16:9`, `9:16`, `1:1`) with safe-zone hierarchy and accessible pagination.

### EN — `news-ticker`

- **Weak prompt:** `Breaking news crawl with tiny bottom text`
- **Strong prompt:** `14s 9:16 release bulletin news ticker: bold 3-word headline above bottom 18% safe zone, 3 short dateline items, high-contrast slate.`

### TR — `news-ticker`

- **Weak prompt:** `En alta küçük kayan yazı ekle`
- **Strong prompt:** `14 sn 9:16 sürüm duyurusu haber bandı: alt %18 güvenli alan üzerinde 3 sözcüklük ana başlık ve 3 kısa bülten maddesi, yüksek kontrast.`

### DE — `news-ticker`

- **Weak prompt:** `Kleiner Lauftext ganz unten im Bild`
- **Strong prompt:** `14 Sek. 9:16 Release-Bulletin im News-Ticker-Stil: knappe Schlagzeile oberhalb der unteren 18-%-Zone, 3 kurze Meldungen, hoher Kontrast.`

- **Diagnosis:** Placing the crawl near the bottom edge collides with mobile player chrome (`vertical_safe_zones`), and continuous sub-pixel scrolls fail accessibility without stepped pagination.
- **Repair tips:** Keep bulletin headlines brief and test static pagination with `reelsyntax render <dir> --reduced-motion` followed by `reelsyntax qc <dir> --profile draft`.

---

## `product-promo`

Problem -> proof -> CTA launch reels (`8s–45s`) enforcing `<= 2.0s` opening hook, sourced proof claims, and verified `LICENSES.md` entries.

### EN — `product-promo`

- **Weak prompt:** `Hype commercial claiming #1 market share`
- **Strong prompt:** `15s 9:16 product promo: 1.5s problem hook ("Manual Renders Drift"), proof beat (deterministic SHA-256 scene cache, source: spec), clear CLI CTA.`

### TR — `product-promo`

- **Weak prompt:** `Dünyanın bir numarası olduğumuzu söyleyen reklam yap`
- **Strong prompt:** `15 sn 9:16 ürün tanıtımı: 1,5 sn sorun kancası ("Manuel Kurgu Kayar"), kanıt sahnesi (SHA-256 sahne önbelleği, kaynak: teknik şartname), net çağrı.`

### DE — `product-promo`

- **Weak prompt:** `Werbespot dass wir ungeschlagen die Nummer 1 sind`
- **Strong prompt:** `15 Sek. 9:16 Produkt-Promo: 1,5-Sek.-Hook ("Manuelle Schnitte verschieben sich"), Beleg-Beat mit SHA-256-Szenencache (Quelle: Spezifikation) und klarer CTA.`

- **Diagnosis:** Superlative claims (`#1`, `best`) without a source fail `claims_sourced`, and unregistered screenshots or audio stems fail `asset_licenses`.
- **Repair tips:** State factual, verifiable product mechanics, register every external media asset via `reelsyntax assets register <dir> <file>`, and confirm `LICENSES.md` before `hero` render.

---

## `loop-art`

Seamless periodic geometric and procedural loops (`4s–30s`, `1:1`, `9:16`, `16:9`) validated with `reelsyntax qc --loop`.

### EN — `loop-art`

- **Weak prompt:** `Random changing shapes that cut at the end`
- **Strong prompt:** `8s 1:1 seamless loop art at 30fps: concentric phase-locked orbital arcs completing 2 full cycles, calm slate and warm amber palette.`

### TR — `loop-art`

- **Weak prompt:** `Sonunda kesilen rastgele şekiller`
- **Strong prompt:** `8 sn 1:1 30fps kesintisiz döngü sanatı: tam 2 turda başa dönen eş merkezli yörünge yayları, sakin arduvaz ve sıcak kehribar palet.`

### DE — `loop-art`

- **Weak prompt:** `Zufällige Formen mit hartem Schnitt am Ende`
- **Strong prompt:** `8 Sek. 1:1 30fps nahtlose Loop-Kunst: phasenstarre konzentrische Kreisbögen mit 2 vollen Zyklen, ruhiges Schiefergrau mit warmem Bernstein.`

- **Diagnosis:** Arbitrary durations or unaligned phase counts create a visible jump between the last frame and frame `0`, failing `reelsyntax qc --loop`.
- **Repair tips:** Pick an even duration (`6s`, `8s`, `12s`) and verify seam continuity locally with `reelsyntax qc <dir> --profile draft --loop`.

---

## `retro-lowpoly-cutscene`

Original, brand-free comedic character dialogue sketches (`18s–45s`) pairing low-poly rigs, stepped camera beats, dialogue boxes above bottom `18%`, and `voice_fx` mouth-sync envelopes.

### EN — `retro-lowpoly-cutscene`

- **Weak prompt:** `Retro console parody featuring a trademarked video hero`
- **Strong prompt:** `24s 16:9 original retro lowpoly cutscene between Scout and Archivist debating frame drift, quiet beat shock, deadpan punchline, dialogue safe zone.`

### TR — `retro-lowpoly-cutscene`

- **Weak prompt:** `Ünlü bir oyun karakteriyle retro konsol parodisi`
- **Strong prompt:** `24 sn 16:9 özgün ve markasız retro low-poly ara sahne: Kâşif ile Arşivci kare kaymasını tartışır, kısa sessiz şaşkınlık anı ve kuru esprili kapanış.`

### DE — `retro-lowpoly-cutscene`

- **Weak prompt:** `Lustige Szene mit bekannter Spielefigur`
- **Strong prompt:** `24 Sek. 16:9 eigene markenfreie Retro-Low-Poly-Zwischensequenz: Scout und Archivar streiten über Frame-Drift, kurzer Stille-Moment und trockene Pointe.`

- **Diagnosis:** Referencing trademarked console brands or external characters breaks content boundaries, while long dialogue lines break `mouth_sync` (`<= 2` frames) and `reading_speed`.
- **Repair tips:** Use original character archetypes (`Scout`, `Archivist`) and one sentence per beat. Check both `mouth_sync` and `reading_speed` after `pilot` with `reelsyntax qc <dir> --profile draft`.

---

## `cinematic-3d`

Monolithic studio 3D showcase scenes (`8s–45s`, `16:9`, `9:16`, `1:1`) supporting Blender lookdev with automatic deterministic Pillow fallback when Blender is absent.

### EN — `cinematic-3d`

- **Weak prompt:** `Cool 3D thing spinning fast`
- **Strong prompt:** `12s 16:9 cinematic 3d monolith showcase with slow 3-point key and rim lighting sweep, shallow depth-of-field focus pull, warm amber glow and cool slate.`

### TR — `cinematic-3d`

- **Weak prompt:** `Hızlı dönen havalı 3B cisim`
- **Strong prompt:** `12 sn 16:9 sinematik 3B monolit vitrini: yavaş üç noktalı anahtar ve kenar ışığı geçişi, yumuşak alan derinliği, sıcak ve soğuk kontrast.`

### DE — `cinematic-3d`

- **Weak prompt:** `Schnell rotierendes 3D-Objekt`
- **Strong prompt:** `12 Sek. 16:9 kinematisches 3D-Monolith-Showcase: langsame Dreipunkt-Lichtfahrt mit Kantenlicht, geringe Schärfentiefe, warmer gegen kühler Kontrast.`

- **Diagnosis:** Fast spins blur geometry and break lighting continuity, and prompts lacking key/rim light or focal intent fall back to flat ambient framing.
- **Repair tips:** Run `reelsyntax doctor --blender` to check whether local Blender (`>= 5.1` for Aperture scenes) is active; headless containers and Blender-free hosts still pass `draft` render and `qc` via procedural fallback.

---

## `stepped-clay-look`

Tactile stop-motion inspired sculptural showcases (`8s–30s`) holding `10–12` distinct poses per second with warm rim separation.

### EN — `stepped-clay-look`

- **Weak prompt:** `Smooth 60fps clay animation`
- **Strong prompt:** `10s 1:1 stepped clay look showcase at 12 poses/sec: sculpted arch rotating in tactile increments, soft top-left studio key and warm rim light.`

### TR — `stepped-clay-look`

- **Weak prompt:** `Akıcı 60fps kil animasyonu`
- **Strong prompt:** `10 sn 1:1 adım adım kil görünümü vitrini, saniyede 12 poz: dokulu kemer formunun küçük adımlı dönüşü, yumuşak tepe ve kenar ışığı.`

### DE — `stepped-clay-look`

- **Weak prompt:** `Flüssige 60fps Knetanimation`
- **Strong prompt:** `10 Sek. 1:1 gestufter Ton-Look mit 12 Posen/Sek.: skulpturaler Bogen in taktilen Schritten, weiches Oberlicht und warmes Streiflicht.`

- **Diagnosis:** Requesting `60fps` smooth motion fights the stepped pose rhythm (`10–12` poses/sec), erasing the handmade tactile cadence.
- **Repair tips:** Explicitly specify `10`–`12` poses per second and high-relief lighting contrast; lock character/prop poses via `reelsyntax lock <dir> --scene <scene_id>` before revising title copy.

---

## `paper-cutout`

Layered `2.5D` paper silhouettes (`8s–30s`) built around unified directional drop shadows, subtle parallax planes, and static unfold support under `--reduced-motion`.

### EN — `paper-cutout`

- **Weak prompt:** `Flat paper icons moving everywhere`
- **Strong prompt:** `12s 4:5 layered paper cutout mountain diorama: 4 Z-offset silhouettes with unified top-left shadow, gentle horizontal drift, warm cream and sage.`

### TR — `paper-cutout`

- **Weak prompt:** `Her yere hareket eden düz kâğıt ikonlar`
- **Strong prompt:** `12 sn 4:5 katmanlı kâğıt kesme dağ dioraması: ortak sol-üst gölgeli 4 derinlik katmanı, hafif yatay kayma, krem ve adaçayı paleti.`

### DE — `paper-cutout`

- **Weak prompt:** `Flache Papier-Icons die wild herumfliegen`
- **Strong prompt:** `12 Sek. 4:5 geschichtetes Papier-Cutout-Diorama: 4 Tiefenebenen mit einheitlichem Schattenwurf von links oben, sanftes Parallax, Creme und Salbeigrün.`

- **Diagnosis:** Conflicting shadow directions or erratic layer motion break depth illusion; missing palette cues wash out thin cutout edges against bright backgrounds.
- **Repair tips:** Specify a single shadow direction (`top-left`), `3`–`5` depth layers, and distinct foreground/background lightness contrast. Verify static accessibility with `reelsyntax render <dir> --reduced-motion`.
