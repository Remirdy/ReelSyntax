# Three-Band Procedural SFX Synthesis Recipes (`48 kHz`)

| Cue Archetype | Pre-Lead (`Band / Window`) | Transient (`Band / Window`) | Body & Tail (`Band / Window`) | Solo Peak / Under-VO Peak |
| --- | --- | --- | --- | --- |
| `hero_impact` | Optional `120 ms` riser | `2.6 kHz` burst (`12 ms`) | `90->50 Hz` + `180->100 Hz` (`180 ms`) | `-8 dBFS` / `-14 dBFS` |
| `card_whoosh` | `350->1800 Hz` noise (`-150..0 ms`) | `2.1 kHz` soft click (`8 ms`) | `3.5 kHz` air fade (`+90 ms`) | `-14 dBFS` / `-20 dBFS` |
| `micro_tick` | None | `1.4–2.8 kHz` damped sine (`16 ms`) | None | `-18 dBFS` / `-23 dBFS` |
| `resolve_chime` | None | `880 Hz` bell attack (`5 ms`) | Fifth interval `880+1320 Hz` (`420 ms`) | `-12 dBFS` / `-18 dBFS` |
