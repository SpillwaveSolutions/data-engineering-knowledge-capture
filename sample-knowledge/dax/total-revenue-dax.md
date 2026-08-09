---
type: DaxArtifact
title: total-revenue-dax (DAX)
description: Power BI total revenue measure
tags: [dax, dekc]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: false
generated: true
wiki_key: dax-total-revenue-dax
truth_state: current
links:
- target: /queries/total-revenue-dax.md
  rel: implements
---

# total-revenue-dax (DAX)

```dax
Total Revenue = SUMX('order_daily','order_daily'[gross_revenue])
```
