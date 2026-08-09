---
type: Query
title: orders_raw
description: Discovered SQL from bronze/sales/orders_raw.sql
dialect: sql
tags: [query, sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-orders-raw
truth_state: current
links:
- target: /tables/orders-api.md
  rel: queries
- target: /sql/orders-raw.md
  rel: implements
---

# orders_raw

Discovered SQL from bronze/sales/orders_raw.sql

## SQL

```sql
CREATE OR REPLACE TABLE bronze.orders_raw AS
SELECT * FROM landing.orders_api;
```
