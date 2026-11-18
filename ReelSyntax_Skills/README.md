# ReelSyntax skills

The [catalog](CATALOG.md) lists every indexed skill, its effective status, search phrases and source. Its category table is rebuilt with `reelsyntax skills reindex`. The JSON index also records integrity hashes, optional resources and dependencies.

```sh
reelsyntax skills search "locked camera"
reelsyntax skills explain "sync voiceover with footage" --stage plan
reelsyntax skills load frame-clock
```

Install the router into a project to keep specialist instructions outside automatic host discovery. Warm searches read only metadata. Use the resource path returned by `skills load` to request a reference. Session loads charge the selected content against the context budget and reload changed references by hash.

Status and evidence conventions are described in [SKILL_SYSTEM.md](SKILL_SYSTEM.md). The [runtime matrix](../docs/runtime-coverage.md) identifies the implemented commands and their limits.

## Category distribution

```text
art          27  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
audio        23  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
camera       23  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
capture      20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
character    20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
data         29  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
delivery     28  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
direction    22  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
editing      20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
engines      24  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
formats      32  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
graphics     20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
ingest       20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
lighting     22  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
modeling     21  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
motion       21  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
music        20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
qa           21  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
render       20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
skills       29  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
story        24  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
transitions  20  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
typography   28  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
vfx          21  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
workflow     21  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇
```
