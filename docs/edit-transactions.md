# Scene edit transactions

The `edit` command previews and applies a bounded group of scene edits. It operates on the current sequential `reel.json` model; it is not a general multitrack timeline or an automatic visual cut detector. It never removes source media files.

An operations file contains a JSON array. Indices address the scene list after the preceding operation in that same transaction:

```json
[
  {"type": "move", "scene_id": "assembly", "to_index": 0},
  {"type": "duplicate", "scene_id": "hero", "new_id": "hero-alt"},
  {"type": "update", "scene_id": "hero-alt", "changes": {"params": {"shot": "hero", "samples": 32}}}
]
```

```sh
reelsyntax edit ./my-film --operations edits.json --audio-mode follow-scenes
reelsyntax edit ./my-film --operations edits.json --audio-mode follow-scenes --expected-plan <before_sha256> --apply
reelsyntax undo-edit ./my-film --revision <revision>
reelsyntax undo-edit ./my-film --revision <revision> --apply
```

The first invocation writes nothing. Its result includes exact before/after plan hashes, frame counts, changed scene ranges, resulting audio anchors and invalidated quality exceptions. `--expected-plan` makes application conditional on the preview's original plan hash. An applied change saves the exact original JSON bytes plus an integrity-checked snapshot journal in `.reelsyntax/edits/`. Undo previews by default, rejects later intervening changes and creates its own reversible journal when applied. The original formatting remains available in the source backup; semantic undo rewrites validated JSON.

Supported operations:

| Operation | Fields | Behavior |
| --- | --- | --- |
| `move` | `scene_id`, `to_index` | Move a scene to a final zero-based index |
| `insert` | `scene`, `at_index` | Insert a complete scene with a new unique ID |
| `duplicate` | `scene_id`, `new_id`, optional `at_index` | Deep-copy a scene; default placement is directly after the source |
| `remove` | `scene_id` | Remove the scene declaration; retain its source files and prior render history |
| `update` | `scene_id`, `changes` | Replace declared scene fields; `params` is a complete replacement, not a deep merge |

`update.changes` accepts `duration_frames`, `recipe`, `engine`, `params`, `camera`, `transition` and `locked_regions`. A footage trim is an explicit update of its decoded-source `params.in_frame` and project `duration_frames`. Changing a procedural scene's duration reparameterizes its motion; it does not preserve an arbitrary source-frame subrange. Automatic split/slip/retiming operations are deferred until the source-range model supports them faithfully.

Audio timing is explicit. `absolute` leaves cue/track anchors and lengths unchanged. `follow-scenes` maps each existing anchor by the scene containing its original start frame and preserves its local offset and duration. Removing/shortening that anchor scene or extending audio past the resulting timeline fails. Duplicating a picture scene does not duplicate audio. J/L tracks are independent; this mode does not infer their intended linked picture or support negative named-scene offsets.

Any effective edit invalidates existing QC exception ranges, which must be reviewed and redeclared for the new timeline. Undo restores the complete prior plan, including those ranges. Whole-scene approval locks are checked before application or undo. Editing shares the render/cache mutex, validates the complete resulting transaction, and keeps the previous plan on validation or lock failure. Assets and prior deliveries remain in place; rerender and run QC before treating an edited plan as delivered.

Preview does not decode source media or verify that a proposed source trim has enough frames. The renderer performs those source checks and preserves the previous delivered master on failure. The lock coordinates ReelSyntax operations; optimistic hash checks do not turn the local filesystem into a sandbox against unrelated external writers.
