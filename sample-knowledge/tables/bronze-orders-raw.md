---
type: Table
title: orders_raw
description: Inferred table from bronze/sales/orders_raw.sql
layer: bronze
schema: ""
fqn: orders_raw
tags: [table, dekc, bronze]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: table-bronze-orders-raw
truth_state: current
links:
- target: /layers/bronze.md
  rel: layered_as
- target: /sources/retail-lake-walk.md
  rel: sourced_from
- target: /streams/orders-events.md
  rel: sourced_from
sql_fingerprint: 247273013766
---

# orders_raw

**Layer:** bronze  

Inferred table from bronze/sales/orders_raw.sql

## SQL

```sql
CREATE OR REPLACE TABLE bronze.orders_raw AS
SELECT * FROM landing.orders_api;
```
