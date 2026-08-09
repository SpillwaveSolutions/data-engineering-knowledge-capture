---
type: Transformation
title: cleanse-orders
description: Type coercion, null status drop, commerce order cleanse
from_layer: bronze
to_layer: silver
tags: [transformation, dekc, bronze, silver]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: xform-cleanse-orders
truth_state: current
links:
- target: /layers/bronze.md
  rel: reads_from
- target: /layers/silver.md
  rel: writes_to
- target: /layers/bronze.md
  rel: transforms_to
- target: /tables/bronze-orders-raw.md
  rel: reads_from
- target: /tables/silver-orders.md
  rel: writes_to
---

# cleanse-orders

**bronze → silver**

Type coercion, null status drop, commerce order cleanse

## SQL

```sql
SELECT * FROM bronze.orders_raw WHERE status IS NOT NULL
```
