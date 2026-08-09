---
type: Diagram
title: orders-stream-landing-sequence
description: sequence diagram for ingestion job /ingestion/orders-stream-landing.md
diagram_kind: sequence
language: mermaid
tags: [diagram, sequence, mermaid, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: diagram-sequence-orders-stream-landing-sequence
truth_state: current
subjects: [/ingestion/orders-stream-landing.md]
links:
- target: /ingestion/orders-stream-landing.md
  rel: documents
---

# orders-stream-landing-sequence

**Kind:** `sequence` · **Language:** `mermaid`

sequence diagram for ingestion job /ingestion/orders-stream-landing.md

## Subjects

- [orders-stream-landing](/ingestion/orders-stream-landing.md)

## Diagram

```mermaid
sequenceDiagram
  participant Src as Source/Stream
  participant Job as Landing Job
  participant Brz as Bronze
  participant DQ as DQ Rules
  participant Slv as Silver
  Src->>Job: event/batch
  Job->>Brz: write landing
  Job->>DQ: validate
  DQ-->>Job: pass/fail
  Job->>Slv: promote on pass
```

## Notes

_Edit the fenced listing above; keep language tag as `mermaid` or `plantuml`._
