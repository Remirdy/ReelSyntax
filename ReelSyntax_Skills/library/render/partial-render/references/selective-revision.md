# Verify a selective rerender

Use scene-level caching when a localized source or design change should preserve unrelated scenes. Keep scene IDs stable, preserve approval locks and checkpoint the plan before revision. The core renderer always assembles and verifies the full master; partial work refers to reusing valid scene caches, not claiming an unrendered timeline has been delivered.

1. Render the original profile and save `output/PROFILE-manifest.json`, scene cache keys, source asset hashes and QC report.
2. Change one unapproved scene or one asset that only that scene uses. Keep output dimensions/FPS, seed and render environment constant for the comparison.
3. Render the same profile again. Inspect each scene's `cache_hit`, `cache_key` and declared frame count. The changed scene should miss; unrelated scenes should hit if all their inputs and the environment remain identical.
4. Decode sample frames from the actual master and run QC. Confirm unchanged locked regions and review cut/audio boundaries. Cache success does not prove creative correctness.

Audio-only plan edits can reuse picture caches when picture source bytes and the render environment remain unchanged. Modifying audio inside a container also used as picture changes that container's content hash, so conservative picture invalidation is expected. Profile changes, source-module changes, engine changes and driver changes can invalidate multiple scenes.

Corrupt cache artifacts must fail digest verification and regenerate. An interrupted job should retain completed caches and the previous delivered master; use `resume` only when the previous process has stopped. Never break a live render lock to force a hit. Record original/revised hashes, hit/miss vector, elapsed time, unchanged-region checks and the final encoded artifact.

Runtime coverage includes `test_render_decode_cache_selective_revision_and_recovery` and source-layer selective invalidation in `tests/test_ingest.py`. Keep cache pruning separate from revision acceptance; pinned delivery caches may legitimately exceed a requested disk budget.
