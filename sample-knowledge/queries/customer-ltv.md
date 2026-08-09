---
type: Query
title: customer_ltv
description: Discovered SQL from gold/marts/customer_ltv.sql
dialect: sql
tags: [query, sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: true
generated: true
wiki_key: query-customer-ltv
truth_state: current
links:
- target: /tables/silver-orders.md
  rel: queries
- target: /sql/customer-ltv.md
  rel: implements
---

# customer_ltv

Discovered SQL from gold/marts/customer_ltv.sql

## SQL

```sql
CREATE OR REPLACE VIEW gold.customer_ltv AS
SELECT
  customer_id,
  SUM(gross_amount) AS lifetime_value,
  COUNT(*) AS order_count
FROM silver.orders
GROUP BY customer_id;
```
