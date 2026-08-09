---
type: Diagram
title: orders-stream-landing-state
description: state diagram for ingestion job /ingestion/orders-stream-landing.md
diagram_kind: state
language: mermaid
tags: [diagram, state, mermaid, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: diagram-state-orders-stream-landing-state
truth_state: current
subjects: [/ingestion/orders-stream-landing.md]
links:
- target: /ingestion/orders-stream-landing.md
  rel: documents
---

# orders-stream-landing-state

**Kind:** `state` · **Language:** `mermaid`

state diagram for ingestion job /ingestion/orders-stream-landing.md

## Subjects

- [orders-stream-landing](/ingestion/orders-stream-landing.md)

## Diagram

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Running: trigger
  Running --> Succeeded: complete
  Running --> Failed: error
  Failed --> Running: retry
  Failed --> DeadLetter: max retries
  Succeeded --> [*]
  DeadLetter --> [*]
```

## Notes

_Edit the fenced listing above; keep language tag as `mermaid` or `plantuml`._
