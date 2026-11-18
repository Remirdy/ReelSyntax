# Stylized Vocal DSP Chains and Parameter Bounds (`48 kHz`)

| Archetype | Pre-HPF | Nonlinear Stage | Post-LPF | Spatial / Accent | Caption Requirement |
| --- | ---: | --- | ---: | --- | --- |
| `field_intercom` | `280 Hz` (`Q=0.7`) | `tanh(1.5x)` normalized | `3600 Hz` (`Q=0.7`) | `12 ms` squelch burst (`-22 dBFS`) | Recommended |
| `flat_droid_monotone` | `160 Hz` (`Q=0.7`) | `12`-bit quantizer after `-46 dBFS` gate | `5200 Hz` (`Q=0.7`) | `14 ms` delay (`10%` mix) | Recommended |
| `retro_blip_chatter` | `120 Hz` | Band-limited triangle/pulse grains (`45–65 ms`) | `2800 Hz` | `4 ms` attack / `18 ms` decay | **Mandatory** |
