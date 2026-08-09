---
type: DesignPattern
title: Land stream to bronze
description: Standard pattern for landing continuous stream data into a bronze table with job/lineage capture.
intent: land-data
applies_to: [SourceSystem, Table, Workflow, LineagePath]
tags: [pattern, land-data, stream, dekc]
timestamp: "2026-08-09T12:00:00Z"
status: active
verified: true
wiki_key: pattern-land-stream-to-bronze
truth_state: current
---

# Land stream → bronze

1. Capture `SourceSystem` with `source_kind: stream` (Event Hub / Kinesis / Pub/Sub / Kafka).  
2. Capture bronze `Table` (landing) with schema/columns when known.  
3. Capture `Workflow` for the processor (optional if pure landing).  
4. Edges: stream `--feeds-->` bronze; job `--writes_to-->` bronze.  
5. Optional `DataContract` for freshness.  
6. Query second brain first: `dekc_brain.py "…" --intent land-data` to reuse conventions.
