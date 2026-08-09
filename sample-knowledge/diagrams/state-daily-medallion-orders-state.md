---
type: Diagram
title: daily-medallion-orders-state
description: state diagram for workflow /workflows/daily-medallion-orders.md
diagram_kind: state
language: mermaid
tags: [diagram, state, mermaid, dekc]
timestamp: "2026-08-09T12:22:18Z"
status: active
verified: true
generated: true
wiki_key: diagram-state-daily-medallion-orders-state
truth_state: current
subjects: [/workflows/daily-medallion-orders.md]
links:
- target: /workflows/daily-medallion-orders.md
  rel: documents
---

# daily-medallion-orders-state

**Kind:** `state` · **Language:** `mermaid`

state diagram for workflow /workflows/daily-medallion-orders.md

## Subjects

- [daily-medallion-orders](/workflows/daily-medallion-orders.md)

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

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
