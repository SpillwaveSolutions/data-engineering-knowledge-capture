---
type: LineagePath
title: orders-to-revenue
description: Core commerce revenue lineage from landing to gold mart
hop_count: 2
nodes: [/tables/bronze-orders-raw.md, /tables/silver-orders.md, /tables/gold-order-daily.md]
tags: [lineage, dekc]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: lineage-orders-to-revenue
truth_state: current
links:
- target: /tables/bronze-orders-raw.md
  rel: contains
- target: /tables/silver-orders.md
  rel: contains
- target: /tables/gold-order-daily.md
  rel: contains
- target: /tables/silver-orders.md
  rel: feeds
- target: /tables/gold-order-daily.md
  rel: feeds
---

# orders-to-revenue

Core commerce revenue lineage from landing to gold mart

## Path

[bronze-orders-raw](/tables/bronze-orders-raw.md) → [silver-orders](/tables/silver-orders.md) → [gold-order-daily](/tables/gold-order-daily.md)

```mermaid
flowchart LR
  n0["bronze-orders-raw"]
  n1["silver-orders"]
  n2["gold-order-daily"]
  n0 --> n1
  n1 --> n2
```
