---
type: Stream
title: orders-events
description: Order placement events
platform: eventhubs
uri: "endpoints://eventhubs/orders"
format: json
tags: [stream, dekc, eventhubs]
timestamp: "2026-08-09T12:22:13Z"
status: active
verified: true
generated: true
wiki_key: stream-orders-events
truth_state: current
links:
- target: /tables/bronze-orders-raw.md
  rel: lands_as
- target: /tables/bronze-orders-raw.md
  rel: feeds
- target: /ingestion/orders-stream-landing.md
  rel: ingested_by
---

# orders-events

Order placement events

**Platform:** eventhubs  
**URI:** `endpoints://eventhubs/orders`  
**Format:** json

**Lands as:** /tables/bronze-orders-raw.md

```mermaid
flowchart LR
  P[Producers] --> S[Stream] --> B[Bronze landing]
```
