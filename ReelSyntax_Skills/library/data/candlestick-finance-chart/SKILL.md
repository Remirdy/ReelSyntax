---
name: candlestick-finance-chart
description: "Plot time-ordered OHLC candles and volume."
metadata:
  category: data
  stage: build
  status: guidance
  version: "1.0.0"
  aliases: "candlestick, mum grafik"
  requires: ""
---

# Candlestick finance chart

Plot time-ordered OHLC candles and volume.

1. Validate low and high against the open and close of each candle.
2. Align volume columns and disclose timezone and adjustment method.
3. Verify a sampled candle against the source row.
