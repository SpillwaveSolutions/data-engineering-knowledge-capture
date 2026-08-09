---
type: SqlArtifact
title: orders_raw (SQL)
description: Discovered SQL from bronze/sales/orders_raw.sql
dialect: sql
tags: [sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: sql-orders-raw
truth_state: current
links:
- target: /queries/orders-raw.md
  rel: implements
---

# orders_raw (SQL)

```sql
CREATE OR REPLACE TABLE bronze.orders_raw AS
SELECT * FROM landing.orders_api;
```
