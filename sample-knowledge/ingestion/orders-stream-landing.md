---
type: IngestionJob
title: orders-stream-landing
description: Lands order events from Event Hubs into bronze Delta
ingestion_mode: streaming
pattern: stream-to-bronze
orchestrator: fabric-pipeline
schedule: ""
connector: eventhubs
source_format: json
target_format: delta
target_layer: bronze
idempotent: true
watermark_column: ""
checkpoint: checkpoints/orders-stream
tags: [ingestion, job, streaming, bronze, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: ingest-orders-stream-landing
truth_state: current
sla_minutes: 15.0
links:
- target: /layers/bronze.md
  rel: writes_to
- target: /layers/bronze.md
  rel: layered_as
- target: /streams/orders-events.md
  rel: ingests_from
- target: /streams/orders-events.md
  rel: consumes_stream
- target: /tables/bronze-orders-raw.md
  rel: lands_as
- target: /tables/bronze-orders-raw.md
  rel: writes_to
- target: /tables/bronze-orders-raw.md
  rel: lands_into
- target: /storage/bronze-orders-prefix.md
  rel: writes_to
- target: /storage/bronze-orders-prefix.md
  rel: stored_in
- target: /diagrams/sequence-orders-stream-landing-sequence.md
  rel: documented_by
- target: /diagrams/activity-orders-stream-landing-activity.md
  rel: documented_by
- target: /diagrams/state-orders-stream-landing-state.md
  rel: documented_by
- target: /diagrams/component-orders-stream-landing-component.md
  rel: documented_by
---

# orders-stream-landing

Lands order events from Event Hubs into bronze Delta

**Mode:** `streaming` · **Pattern:** `stream-to-bronze` · **Target layer:** `bronze`

**Orchestrator:** fabric-pipeline
**Connector:** eventhubs
**Formats:** json → delta
**Checkpoint:** `checkpoints/orders-stream`
**Idempotent:** True
**SLA:** 15.0 minutes

## Sources

- Stream: /streams/orders-events.md

## Lands as (tables)

- /tables/bronze-orders-raw.md

## Storage

- /storage/bronze-orders-prefix.md

## Steps

1. Read Event Hub
2. Write bronze Delta
3. Update watermark

## Ingestion flow

```mermaid
flowchart LR
  SRC[Source / Stream] --> JOB[Ingestion Job]
  JOB --> LAND[bronze landing]
  JOB --> DQ[Optional DQ]
```
