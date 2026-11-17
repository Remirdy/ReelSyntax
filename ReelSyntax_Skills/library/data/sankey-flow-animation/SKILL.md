---
name: sankey-flow-animation
description: "Animate weighted flows between labeled nodes."
metadata:
  category: data
  stage: build
  status: guidance
  version: "1.0.0"
  aliases: "sankey, akış diyagramı"
  requires: ""
---

# Sankey flow animation

Animate weighted flows between labeled nodes.

1. Normalize edge widths against one unit scale.
2. Account for sinks and sources at each node.
3. Check that combined incoming and outgoing widths match the stated totals.
