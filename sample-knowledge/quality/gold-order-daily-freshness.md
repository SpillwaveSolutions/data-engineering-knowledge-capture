---
type: DQRule
title: gold-order-daily-freshness
description: Gold mart must be fresh within 1 day
rule_type: freshness
severity: error
expression: "max(order_date) >= current_date - 1"
tags: [dq, quality, freshness, dekc]
timestamp: "2026-08-09T12:22:13Z"
status: active
verified: true
generated: true
wiki_key: dq-gold-order-daily-freshness
truth_state: current
links:
- target: /tables/gold-order-daily.md
  rel: validates
- target: /tables/gold-order-daily.md
  rel: quality_of
---

# gold-order-daily-freshness

Gold mart must be fresh within 1 day

**Type:** `freshness` · **Severity:** `error`

## Expression

```
max(order_date) >= current_date - 1
```

**Target:** /tables/gold-order-daily.md
