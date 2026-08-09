---
type: SqlArtifact
title: order_daily (SQL)
description: Discovered SQL from gold/marts/order_daily.sql
dialect: sql
tags: [sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: sql-order-daily
truth_state: current
links:
- target: /queries/order-daily.md
  rel: implements
---

# order_daily (SQL)

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
