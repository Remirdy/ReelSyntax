---
name: emoji-rendering
description: "Render emoji with consistent scale and fallback."
metadata:
  category: typography
  stage: build
  status: guidance
  version: "1.0.0"
  aliases: "emoji rendering, emoji çizimi"
  requires: ""
---

# Emoji rendering

Render emoji with consistent scale and fallback.

1. Keep variation selectors and joined sequences intact.
2. Verify the selected renderer supports the font color tables.
3. Inspect multi-codepoint glyphs on both light and dark backgrounds.
