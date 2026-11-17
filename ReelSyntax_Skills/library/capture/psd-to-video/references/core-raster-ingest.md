# Supported PSD raster ingest

Use the core extractor for an authorized 8-bit RGB PSD whose visible appearance can be represented as normal-alpha raster layers. Preserve the source and inspect unsupported features before committing to this path. This is a supported subset of PSD production, not a substitute for a fully editable Photoshop/After Effects composition.

## Preflight

- Confirm the source is local and immutable. Record its SHA-256 and canvas dimensions.
- Reuse an existing optional AfterEffectsMCP Node runtime with `ag-psd` and `sharp`. Extraction does not launch After Effects or install dependencies. If the runtime is absent, report that dependency instead of claiming extraction worked.
- Limits: 64 MiB input, 16 megapixel 8-bit RGB canvas, 128 visible raster layers and 32 megapixels of decoded buffers. PSB, CMYK and 16-bit documents require explicit conversion first.
- Masks, clipping, layer effects, adjustments, non-normal blends and group opacity require reviewed rasterization. The extractor refuses unsupported compositing instead of omitting it. Text uses its stored raster pixels; it does not become editable core typography.

## Extract and compose

```sh
reelsyntax ingest-psd ./film --source assets/design.psd --destination assets/design-layers
```

The destination must be new. Read `assets/design-layers/layers.json`: it records bottom-to-top layer order, pixel positions, opacity, dimensions and a `params` object. Copy that `params` into a scene with `recipe: "layer-stack"`, `engine: "pillow"` and an explicit duration. Coordinates remain in project pixels and are scaled for Draft. Set project dimensions to the intended canvas; do not assume an imported document silently changes output geometry.

Validate, render Draft and run QC. Compare the actual frame against a trusted source composite at full opacity, checking overlap, positions, layer visibility, alpha fringes and text pixels. Save the source hash, extraction report, frame paths and mismatch notes. Verify that the original PSD hash is unchanged. Source-embedded text is not automatically covered by the core glyph audit or `no_text` classification.

`layer-stack` is a static raster composition. It does not implement editable PSD masks, live text, layer-style animation or arbitrary blend modes. If those are required, use a separately verified native adapter or obtain an approved rasterized appearance. Never present a generic placeholder animation as the source document.

`tests/test_ingest.py` verifies a real layered PSD round trip, normal-alpha pixel composition, source preservation, existing-destination protection and unsupported-blend refusal. That fixture is evidence for this subset only; compare every production document's actual appearance.
