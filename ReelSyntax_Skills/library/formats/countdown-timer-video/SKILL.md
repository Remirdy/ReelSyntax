---
name: countdown-timer-video
description: "Drive a countdown from integer frame indices."
metadata:
  category: formats
  stage: plan
  status: guidance
  version: "1.0.0"
  aliases: "countdown, geri sayım videosu"
  requires: ""
---

# Countdown timer video

Drive a countdown from integer frame indices.

1. Derive the display value from the rational frame rate.
2. Anchor the final beep to the first zero frame.
3. Inspect the frames immediately before and after each displayed second changes.
