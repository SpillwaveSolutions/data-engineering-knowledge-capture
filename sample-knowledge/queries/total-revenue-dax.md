---
type: Query
title: total-revenue-dax
description: Power BI total revenue measure
dialect: dax
tags: [query, dax, dekc]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: query-total-revenue-dax
truth_state: current
links:
- target: /tables/gold-order-daily.md
  rel: queries
- target: /dax/total-revenue-dax.md
  rel: implements
---

# total-revenue-dax

Power BI total revenue measure

## DAX

```dax
Total Revenue = SUMX('order_daily','order_daily'[gross_revenue])
```
