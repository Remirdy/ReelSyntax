# Bidirectional WCAG Media Parity Check Matrix (Adjustable Reference)

| Check Dimension | Reference Principle (Verify Official WCAG 2.2 Docs) | Automated Check | Human / Script Check |
| --- | --- | --- | --- |
| Synchronized Captions (Prerecorded) | `1.2.2` (Level A) | `.vtt`/`.srt` presence, `+-100ms` onset, CPS | Non-speech `[sfx]` & speaker `- ` accuracy |
| Audio Description / Media Alternative | `1.2.3` / `1.2.5` (Level A / AA) | Detect silent-only numbers vs transcript | Zero unspoken `"look here"` deictic gaps |
| Contrast (Minimum / Enhanced) | `1.4.3` (`4.5:1`) / `1.4.6` (`7.0:1`) | `quality.py` `contrast` gate | Verify over brightest video frame |
| Three Flashes or Below Threshold | `2.3.1` (Level A) | Luminance delta `> 3/s` scan | Inspect glitch/strobe transitions |
| Motion Actuation / Reduced Motion | `2.3.3` (Level AAA) | `render --reduced-motion` | Confirm calm cuts & locked cameras |

*Note:* Accessibility conformance levels and jurisdictional regulations vary; verify against current official W3C WCAG documentation for formal compliance sign-off.
