# Adjustable Loudness Preset Table and Two-Pass FFmpeg Parameters

| Preset ID | Integrated Target (`I`) | Pre-Codec True Peak (`TP`) | Max `LRA` | Typical Use Case |
| --- | ---: | ---: | ---: | --- |
| `social_shortform` | `-14.0 LUFS` | `-1.5 dBTP` | `7.0 LU` | General web & vertical short-form video |
| `mobile_speech` | `-16.0 LUFS` | `-1.5 dBTP` | `6.0 LU` | Voice-led mobile tutorials & podcasts |
| `cinema_trailer_web` | `-16.0 LUFS` | `-1.5 dBTP` | `11.0 LU` | Dynamic 3D cutscenes & showreels |
| `broadcast_r128` | `-23.0 LUFS` | `-1.5 dBTP` | `11.0 LU` | Broadcast master delivery |

*Note:* Streaming normalization targets and codec ceiling rules change periodically; treat this table as an adjustable default and verify against current official delivery documentation before mastering commercial campaigns.
