---
type: View
title: customer_ltv
description: Per-customer lifetime value view
layer: gold
tags: [view, dekc, gold]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: view-gold-customer-ltv
truth_state: current
links:
- target: /business-objects/customer-lifetime-value.md
  rel: businessizes
rel: reads_from
---

# customer_ltv

Per-customer lifetime value view

## SQL

```sql
SELECT customer_id, SUM(gross_amount) lifetime_value, COUNT(*) order_count FROM silver.orders GROUP BY customer_id
```

## Reads from

- [silver-orders](/tables/silver-orders.md)
