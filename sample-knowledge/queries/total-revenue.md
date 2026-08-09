---
type: Query
title: total_revenue
description: Discovered DAX from dax/total_revenue.dax
dialect: dax
tags: [query, dax, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-total-revenue
truth_state: current
links:
- target: /dax/total-revenue.md
  rel: implements
---

# total_revenue

Discovered DAX from dax/total_revenue.dax

## DAX

```dax
Total Revenue =
SUMX(
  'order_daily',
  'order_daily'[gross_revenue]
)
```
