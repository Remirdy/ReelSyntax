---
name: mermaid-to-video
description: "Turn diagram edges into a timed reading sequence."
metadata:
  category: data
  stage: build
  status: guidance
  version: "1.0.0"
  aliases: "mermaid animation, mermaid videosu"
  requires: ""
---

# Mermaid to video

Turn diagram edges into a timed reading sequence.

1. List the node IDs and directed edges from the source.
2. Allocate a hold for each new label and reveal edges in traversal order.
3. Compare the final visible graph with the source.
