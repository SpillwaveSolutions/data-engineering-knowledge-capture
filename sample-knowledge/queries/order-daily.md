---
type: Query
title: order_daily
description: Discovered SQL from gold/marts/order_daily.sql
dialect: sql
tags: [query, sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-order-daily
truth_state: current
links:
- target: /tables/silver-orders.md
  rel: queries
- target: /sql/order-daily.md
  rel: implements
---

# order_daily

Discovered SQL from gold/marts/order_daily.sql

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
