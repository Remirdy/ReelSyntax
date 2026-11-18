# `yuv420p` Luma-Separation Math and FFmpeg `swscale` Flags

## BT.709 8-bit Luma Estimate (from sRGB `0..255`)
`Y_approx = 0.2126 * R + 0.7152 * G + 0.0722 * B`

Notice blue contributes only `7.2%` and red only `21.3%` to full-resolution `Y`!
- Pure `#0000FF` blue has `Y = 18` — nearly indistinguishable in luma from black!
- Pure `#FF0000` red has `Y = 54` — low luma separation on `#1F2937` (`Y = 39`, `|ΔY| = 15` -> severe `4:2:0` smear).
- Safe rule: require `|Y_fg - Y_bg| >= 85` (`>= 120` recommended) so full-resolution `Y` carries crisp letterform edges on every `4:2:0` decoder.

*Note:* Hardware decoder profile support (`High` `4:2:0` vs `High 4:4:4 Predictive`) varies across browsers and mobile chipsets; verify target playback devices before delivering non-`4:2:0` streams.
