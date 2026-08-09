---
type: SqlArtifact
title: daily_medallion (SQL)
description: Discovered SQL from workflows/daily_medallion.sql
dialect: sql
tags: [sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: sql-daily-medallion
truth_state: current
links:
- target: /queries/daily-medallion.md
  rel: implements
---

# daily_medallion (SQL)

```sql
-- orchestrated steps (documented)
-- 1. land API → bronze.orders_raw
-- 2. clean → silver.orders
-- 3. aggregate → gold.order_daily
SELECT 1;
```
