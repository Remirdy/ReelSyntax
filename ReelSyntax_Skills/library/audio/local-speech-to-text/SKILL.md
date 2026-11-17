---
name: local-speech-to-text
description: "Align a transcript from a user-provided local recognizer."
metadata:
  category: audio
  stage: ingest
  status: guidance
  version: "1.0.0"
  aliases: "local transcription, yerel yazıya dökme"
  requires: ""
---

# Local speech to text

Align a transcript from a user-provided local recognizer.

1. Record the installed recognizer and model version.
2. Run it on a copy of the source audio and map word timestamps to project frames.
3. Spot-check names and boundaries against playback.
