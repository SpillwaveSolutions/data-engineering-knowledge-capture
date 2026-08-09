---
type: Table
title: orders
description: Inferred table from silver/sales/orders.sql
layer: silver
schema: ""
fqn: orders
tags: [table, dekc, silver]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: table-silver-orders
truth_state: current
links:
- target: /layers/silver.md
  rel: layered_as
- target: /sources/retail-lake-walk.md
  rel: sourced_from
sql_fingerprint: 602783558248
---

# orders

**Layer:** silver  

Inferred table from silver/sales/orders.sql

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
