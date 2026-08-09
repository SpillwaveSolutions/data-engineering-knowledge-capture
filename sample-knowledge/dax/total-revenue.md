---
type: DaxArtifact
title: total_revenue (DAX)
description: Discovered DAX from dax/total_revenue.dax
tags: [dax, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: dax-total-revenue
truth_state: current
links:
- target: /queries/total-revenue.md
  rel: implements
---

# total_revenue (DAX)

```dax
Total Revenue =
SUMX(
  'order_daily',
  'order_daily'[gross_revenue]
)
```
