# Shot-Type Floor and Ceiling Reference Table (`30/1` fps)

| Shot / Scene Archetype | Net Floor (Frames) | Net Floor (Sec) | Single-State Ceiling (Frames) | Notes |
| --- | ---: | ---: | ---: | --- |
| Textless visual accent | `24f` | `0.80s` | `90f` | Avoid `< 18f` strobe cuts |
| 2–4 word hook card | `42f` | `1.40s` | `60f` | Keep `<= 60f` for social hook rules |
| Heading + subheading card | `60f` | `2.00s` | `135f` | Add `ceil(chars / cps * 30)` |
| Photo plate (`layer-stack`) | `60f` | `2.00s` | `120f` | Pair with subtle pan or matte reveal |
| Data chart / diagram | `75f` | `2.50s` | `150f` | Finish bar sweep in first `35%`, hold `65%` |
| Closing end card / sting | `60f` | `2.00s` | `105f` | Hold settled final state `>= 36f` |
