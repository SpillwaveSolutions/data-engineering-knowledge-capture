---
type: Table
title: order_daily
description: Inferred table from gold/marts/order_daily.sql
layer: gold
schema: ""
fqn: order_daily
tags: [table, dekc, gold]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: table-gold-order-daily
truth_state: current
links:
- target: /layers/gold.md
  rel: layered_as
- target: /sources/retail-lake-walk.md
  rel: sourced_from
- target: /quality/gold-order-daily-freshness.md
  rel: validated_by
- target: /diagrams/erd-orders-erd.md
  rel: documented_by
sql_fingerprint: 281615144300
---

# order_daily

**Layer:** gold  

Inferred table from gold/marts/order_daily.sql

## SQL

```sql
CREATE OR REPLACE TABLE gold.order_daily AS
SELECT
  CAST(order_ts AS DATE) AS order_date,
  currency,
  COUNT(*) AS order_count,
  SUM(gross_amount) AS gross_revenue
FROM silver.orders
GROUP BY 1, 2;
```
