---
type: Transformation
title: aggregate-order-daily
description: Daily grain aggregation for revenue reporting
from_layer: silver
to_layer: gold
tags: [transformation, dekc, silver, gold]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: xform-aggregate-order-daily
truth_state: current
links:
- target: /layers/silver.md
  rel: reads_from
- target: /layers/gold.md
  rel: writes_to
- target: /layers/silver.md
  rel: transforms_to
- target: /tables/silver-orders.md
  rel: reads_from
- target: /tables/gold-order-daily.md
  rel: writes_to
---

# aggregate-order-daily

**silver → gold**

Daily grain aggregation for revenue reporting
