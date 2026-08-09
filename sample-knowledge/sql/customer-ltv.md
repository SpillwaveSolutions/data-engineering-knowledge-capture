---
type: SqlArtifact
title: customer_ltv (SQL)
description: Discovered SQL from gold/marts/customer_ltv.sql
dialect: sql
tags: [sql, dekc]
timestamp: "2026-08-09T10:28:10Z"
status: active
verified: false
generated: true
wiki_key: sql-customer-ltv
truth_state: current
links:
- target: /queries/customer-ltv.md
  rel: implements
---

# customer_ltv (SQL)

```sql
CREATE OR REPLACE VIEW gold.customer_ltv AS
SELECT
  customer_id,
  SUM(gross_amount) AS lifetime_value,
  COUNT(*) AS order_count
FROM silver.orders
GROUP BY customer_id;
```
