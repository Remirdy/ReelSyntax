# Core master-based OTIO interchange

The installed core implements the OTIO-format capability with a native JSON writer; a separate OpenTimelineIO SDK is not required for this path. The export describes a flattened rendered master segmented at scene boundaries. It does not reconstruct editable source effects or a general multitrack source edit.

```sh
reelsyntax export ./film --profile hero --format otio
```

Render and QC the current plan first when delivering real media. Export before any render is supported as a planned timeline, but its media paths may not exist and must not be presented as a verified delivery. Existing stale plan manifests or changed source hashes are rejected. Resolve those mismatches by rendering current sources rather than editing the manifest hashes.

Inspect the resulting JSON for `Timeline.1`, exact frame counts, source in-points, original rational FPS metadata, driver-independent file references and scene markers. RationalTime rates use double precision. Media URIs are absolute and percent-encoded; a receiving workstation must retain or relink those paths.

The picture track references the baked MP4. Baked transitions are metadata, not new OTIO transitions, so the receiving editor does not apply them again. The audio track references the separate mix WAV when present and otherwise the master audio. Markers use the clip's source time frame. These are deliberate flattening losses; audio source tracks, shader parameters, camera controls, typography and masks are not native editable OTIO effects.

For the available native editorial adapter:

```sh
reelsyntax export ./film --profile hero --format blender --frame 48
```

This requires the rendered master and a separately installed Blender. The adapter creates a Video Sequencer `.blend`, reopens the saved file headlessly, renders the chosen frame to an adjacent PNG and reports clip offsets/durations. Compare that preview with the same H.264-decoded frame, recording MAE and any color difference. Local tests verify Blender 5.1.2 and fractional-rate timing. This is a ReelSyntax adapter, not a general OTIO importer.

Native Final Cut, Premiere and Resolve imports remain separate gates. Save an unsupported-feature/loss list, source hashes, exact duration and the actual target import outcome. JSON structure alone does not prove another editor's import behavior. Primary model reference: [OTIO time ranges](https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/main/docs/tutorials/time-ranges.md).
