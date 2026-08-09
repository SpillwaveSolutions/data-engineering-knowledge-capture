---
type: SqlArtifact
title: orders (SQL)
description: Discovered SQL from silver/sales/orders.sql
dialect: sql
tags: [sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: sql-orders
truth_state: current
links:
- target: /queries/orders.md
  rel: implements
---

# orders (SQL)

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
