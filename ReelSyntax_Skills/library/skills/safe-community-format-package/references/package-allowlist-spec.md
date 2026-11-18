# Community Format Package Allowlist and Archive Security Rules

| Check | Rule | Rejection Reason Code |
| --- | --- | --- |
| Network gate | Remote URL requires `--allow-network` (`https://` only) | `network_disabled` |
| Archive bounds | `<= 128` entries, `<= 32 MiB` uncompressed, ratio `<= 25:1` | `archive_bounds_exceeded` |
| Path safety | Relative POSIX path, no `..`, no leading `/`, no symlinks | `unsafe_archive_path` |
| File allowlist | `format.json`, `FORMAT.md`, `example.reel.json`, `licenses.json`, `assets/*.{png,jpg,webp,wav,ttf,otf}` | `disallowed_file_type` |
| Recipe allowlist | Built-in declarative recipes only (`kinetic-type`, `prism-monolith`, `layer-stack`, `signal-grid`) | `executable_recipe_forbidden` |
| Namespace collision | `id` must not collide with built-in formats | `builtin_id_reserved` |
