# Social Hook Reel (`social-hook-reel`)

Fast-opening vertical short-form reels engineered around a `<= 2.0 s` opening hook, crisp visual progression, and an unambiguous closing payoff.

## Structural contract

1. **Hook beat (`<= 60` frames at `30 fps`)** — Opens immediately on frame `0` with a localized attention kicker (`HOOK` / `DİKKAT` / `STOPP`), bold display headline, subtle 3D `dolly_in` depth (`prism-monolith`), and a `68 Hz` `sub_impact` transient cue. No fade-from-black intros.
2. **Proof beats (`02 .. N-1`)** — Enters via a brisk `6`-frame `wipe_left` or `slide_left`, delivering one concrete point per beat.
3. **Payoff beat (`PAYOFF` / `SONUÇ` / `FAZIT`)** — Resolves the open loop opened in beat `1` and holds steady inside the `9:16` safe zone.

## Vertical safe-zone defaults (adjustable baseline)

Platform UI chrome dimensions change over time; treat these margins as adjustable defaults and verify against current platform specifications when delivering commercial campaigns:

- **Top clearance:** `>= 12%` of frame height (`>= 230 px` on `1080x1920`).
- **Bottom clearance:** `>= 18%` of frame height (`>= 345 px` on `1080x1920`).
- **Right-rail icon clearance:** Keep primary headline blocks inside the left editorial zone (`x in [0.07w, 0.50w]`).

## Wired skills

- `opening-hook` — Immediate visual and sonic contrast within the first two seconds.
- `idea-angle-framing` — Focused tension framing for sub-45s vertical narratives.
- `open-loop-retention` — Concrete opening gap, progressive middle clues, and timely payoff closure.
- `procedural-broll-planner` — Motivated procedural plates for abstract proof beats.
- `vertical-safe-zones` — Clearance from top, bottom, and right-edge UI overlays.
- `kinetic-typography` — Scannable headline hierarchy and damped entrances.
- `end-card` — Clear closing takeaway without cluttered overlays.
- `contrast-audit` — Verified WCAG foreground/background ratios.
- `frame-clock` — Exact integer frame conservation when capping hook length.
