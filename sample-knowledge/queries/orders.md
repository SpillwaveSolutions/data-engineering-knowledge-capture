---
type: Query
title: orders
description: Discovered SQL from silver/sales/orders.sql
dialect: sql
tags: [query, sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-orders
truth_state: current
links:
- target: /tables/bronze-orders-raw.md
  rel: queries
- target: /sql/orders.md
  rel: implements
---

# orders

Discovered SQL from silver/sales/orders.sql

## SQL

```sql
CREATE OR REPLACE TABLE silver.orders AS
SELECT
  order_id,
  customer_id,
  order_ts,
  status,
  gross_amount,
  currency
FROM bronze.orders_raw
WHERE status IS NOT NULL;
```
