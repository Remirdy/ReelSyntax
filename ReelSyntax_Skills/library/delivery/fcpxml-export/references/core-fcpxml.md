# Core FCPXML delivery checks

Use `reelsyntax export PROJECT --profile PROFILE --format fcpxml` for the implemented FCPXML 1.10 representation. It segments a flattened MP4 master, preserving rational scene timing and source-coordinate markers. It does not create a native Final Cut library or editable source effects.

Before delivery, render and QC the current plan. Inspect the exported format's dimensions against FFprobe on the selected profile: Draft can be half the project resolution. Check `frameDuration`, sequence duration, clip source in-points and contiguous record offsets. A marker at the start of a trimmed clip must use that clip's source start, not zero for every clip. Compare rational values without rounding them to decimal seconds.

The file uses absolute percent-encoded media URIs. Validate that the master exists and document a relinking strategy for another machine. A stale render manifest or changed source asset must be resolved by rerendering; do not repair the export by falsifying hashes or dimensions.

List flattening losses: procedural parameters, live typography, layer blends, camera animation and transitions remain baked. The core validates document construction and media contracts; native Final Cut/Premiere/Resolve imports have not been certified by those checks. If the target application is unavailable, record that import as blocked or not exercised.

For an available native editor check, use the separately verified Blender Video Sequencer export and save/reopen preview. That proves the Blender adapter only. Keep the source frame, target frame, exact duration, file hashes and observed differences in the evidence bundle. Reference: Apple's [FCPXML timing attributes](https://developer.apple.com/documentation/professional-video-applications/timing-attributes).
