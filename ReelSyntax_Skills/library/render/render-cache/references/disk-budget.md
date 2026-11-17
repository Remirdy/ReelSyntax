# Delivery-protected scene cache budget

Use this reference when long image sequences or revisions are consuming local disk. The cache is regenerable scene output, while source media, current deliveries, review files and history have different retention rules. Inventory first; do not delete folders by a broad filename pattern.

```sh
reelsyntax cache ./film --max-mib 1024
reelsyntax cache ./film --max-mib 1024 --apply
reelsyntax render ./film --profile draft --cache-budget-mib 1024
```

The first command is a dry-run. Review `before_bytes`, `projected_bytes`, `selected`, `protected_entries`, `ignored` and `within_budget`. Recognized unreferenced scene caches are selected oldest-use first. Current Draft/Production/Hero delivery manifests and render-state cache keys are protected, including current ROI cache sources. If protected entries alone exceed the budget, `within_budget` remains false; the command does not discard them to claim success.

Apply acquires the same project mutex as rendering and refuses an active lock. Inventory rejects symbolic links and malformed reference records. Unknown entries are retained and reported. Cleanup does not cover quarantine, history, inputs, masters or review files. Source media belongs in an asset directory or `.reelsyntax/inputs`, never managed cache/output paths.

Cache hits require the expected contiguous PNG sequence, encoded scene and matching artifact hashes. Canonical scene parameters, output profile, seed, resolved engine, relevant source assets and environment/source versions form the key. A changed frame-producing module or GL driver can invalidate caches even when the project JSON is unchanged; record that environment change instead of weakening verification.

Save the preview/application report, protected-entry count, actual reclaimed bytes and any unmet budget. Confirm current outputs and required source files remain available. `tests/test_cache.py` checks LRU order, dry-run behavior, protected/unknown-data preservation, busy lock refusal and symlink rejection; actual renderer tests exercise post-delivery pruning. A small local test is not a long 4K disk/memory benchmark.
