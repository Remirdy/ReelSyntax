---
name: multilingual-glyph-audit
description: "Test a selected font against localized strings."
metadata:
  category: typography
  stage: build
  status: guidance
  version: "1.0.0"
  aliases: "glyph audit, karakter seti denetimi"
  requires: ""
---

# Multilingual glyph audit

Test a selected font against localized strings.

1. Collect distinct characters from the actual copy and compare their masks with the missing-glyph signature.
2. Include marks and punctuation.
3. Inspect joined scripts as whole words in a rendered frame.
