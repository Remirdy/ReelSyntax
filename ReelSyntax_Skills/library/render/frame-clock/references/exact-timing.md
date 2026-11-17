# Exact timing and evidence

Use a rational frame rate and integer frames. Scene intervals are half-open: frame `end` belongs to the next scene. At 30000/1001 fps, 300 frames last exactly 1001/100 seconds. Convert to floating point only at an engine boundary; never repeatedly accumulate rounded milliseconds.

The runtime uses `fractions.Fraction`; `reelsyntax.project.validate` derives duration from the sum of scene frames. `reelsyntax.sound.synthesize` produces `ceil(total_frames × 48000 / fps)` samples so the last fractional sample interval is covered. AAC priming and container rounding must be evaluated separately from source sample count.

Run `python3 -m unittest discover -s tests -v` from the checkout for rational timing and deterministic sound checks. After a real render, `python3 -m reelsyntax qc <project> --profile production` checks actual decoded frame count, nominal rate, timestamps and cadence. `cue_sync` remains review until actual encoded sound/picture alignment is independently assessed.

A frame clock is a technical prerequisite, not evidence of smooth or intentional motion. Review acceleration, hold duration, cuts and extrema in actual playback. Keep intentional still/dark/silent exceptions in the project as bounded frame ranges.
