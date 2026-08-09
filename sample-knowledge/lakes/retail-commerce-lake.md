---
type: DataLake
title: Retail Commerce Lake
description: Primary commerce lakehouse
platform: fabric-onelake
uri: "abfss://lake@onelake/retail"
tags: [data-lake, dekc, fabric-onelake]
timestamp: "2026-08-09T12:22:13Z"
status: active
verified: true
generated: true
wiki_key: lake-retail-commerce-lake
truth_state: current
links:
- target: /layers/bronze.md
  rel: contains
- target: /layers/silver.md
  rel: contains
- target: /layers/gold.md
  rel: contains
- target: /diagrams/architecture-commerce-lake-architecture.md
  rel: documented_by
---

# Retail Commerce Lake

Primary commerce lakehouse

**Platform:** fabric-onelake

**URI:** `abfss://lake@onelake/retail`

## Layers

- [bronze](/layers/bronze.md)
- [silver](/layers/silver.md)
- [gold](/layers/gold.md)

## Architecture

```mermaid
flowchart LR
  S[Sources] --> B[Bronze] --> V[Silver] --> G[Gold]
```
