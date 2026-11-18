# Channel Intro (`channel-intro`)

Crisp `4–15 s` opener cards for creator channels: a damped reveal, a name card, and a short end card, for widescreen (`16:9`), vertical (`9:16`), square (`1:1`), and portrait (`4:5`) delivery.

## Structural contract

1. **Reveal (`CHANNEL` / `KANAL` / `KANAL`)** — `prism-monolith` assembly with a slow `dolly_in` camera; heading only, no body text, so the name lands instantly.
2. **Name card (`NOW` / `ŞİMDİ` / `JETZT`)** — `kinetic-type` card with a critically damped entrance (no overshoot) and a one-line tagline subheading.
3. **End card (`SUBSCRIBE` / `ABONE OL` / `ABONNIEREN`)** — heading-only closing call to action that holds steady (`end-card`).

Default section weights are `4 : 5 : 3`; transitions are `8`-frame `cross_dissolve` blends.

## Sound

- Frame `0`: soft `392 Hz` `harmonic_pluck` accent under the reveal.
- Name card: `523 Hz` `harmonic_pluck` lift.
- End card: `262 Hz` `warm_pad` resolution.

All cues are short transients with clean tails and no sub-bass impact, so the intro stays subtle under a channel's own music (`sfx-layering-transient-tail`).

## Timing and readability defaults

- Duration is clamped to `4–15 s`. Because the reveal and end card carry no body text, even a `4 s` intro stays under the locale reading-speed ceiling (`reading-speed` QC rule active).
- Keep the channel name to one short word or two; very long names spill into the subheading on the name card.

## Wired skills

- `end-card` — Clear closing call to action without clutter.
- `kinetic-layout-choreography` — Shared left editorial rail across all three cards.
- `sfx-layering-transient-tail` — Subtle harmonic accents with clean tails.
- `easing-design` — Critically damped entrances without overshoot.
- `frame-clock` — Integer frame budgeting inside the `4–15 s` window.
- `contrast-audit` — Kicker, heading, and tagline contrast.
- `format-runner-protocol` — Approval gates before draft, full, and hero renders.
- `locale-aware-casing` — Turkish and German display casing.
