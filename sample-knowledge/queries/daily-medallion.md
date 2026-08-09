---
type: Query
title: daily_medallion
description: Discovered SQL from workflows/daily_medallion.sql
dialect: sql
tags: [query, sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-daily-medallion
truth_state: current
links:
- target: /sql/daily-medallion.md
  rel: implements
---

# daily_medallion

Discovered SQL from workflows/daily_medallion.sql

## SQL

```sql
-- orchestrated steps (documented)
-- 1. land API → bronze.orders_raw
-- 2. clean → silver.orders
-- 3. aggregate → gold.order_daily
SELECT 1;
```
