# Approved SPDX Allowlist and `.reelsyntax/asset-licenses.json` Schema

```json
{
  "schema_version": 1,
  "assets": {
    "assets/plates/photo-plate-warm.png": {
      "path": "assets/plates/photo-plate-warm.png",
      "sha256": "64-hex-char-digest",
      "license": "CC0-1.0",
      "author": "ReelSyntax Starter Pack",
      "source": "builtin://starter-assets/photo-plate-warm",
      "attribution": "Public domain dedication (CC0-1.0)"
    }
  }
}
```

| SPDX Identifier | Commercial Output OK? | Credit Required in `LICENSES.md`? | Share-Alike Viral? |
| --- | :---: | :---: | :---: |
| `CC0-1.0` / `Public-Domain` | Yes | Optional (good hygiene) | No |
| `OFL-1.1` (Fonts) | Yes | Yes (copyright + OFL notice) | Font derivatives only, never rendered video |
| `CC-BY-4.0` | Yes | **Yes** (Creator, Title, License URI, Changes) | No |
| `MIT` / `BSD-3-Clause` / `Apache-2.0` | Yes | **Yes** | No |
| `User-Provided` | Owner responsibility | Recorded as first-party | N/A |
