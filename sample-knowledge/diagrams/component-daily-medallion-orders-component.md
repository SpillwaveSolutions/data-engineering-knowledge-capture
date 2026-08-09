---
type: Diagram
title: daily-medallion-orders-component
description: component diagram for workflow /workflows/daily-medallion-orders.md
diagram_kind: component
language: mermaid
tags: [diagram, component, mermaid, dekc]
timestamp: "2026-08-09T12:22:18Z"
status: active
verified: true
generated: true
wiki_key: diagram-component-daily-medallion-orders-component
truth_state: current
subjects: [/workflows/daily-medallion-orders.md]
links:
- target: /workflows/daily-medallion-orders.md
  rel: documents
---

# daily-medallion-orders-component

**Kind:** `component` · **Language:** `mermaid`

component diagram for workflow /workflows/daily-medallion-orders.md

## Subjects

- [daily-medallion-orders](/workflows/daily-medallion-orders.md)

## Diagram

```mermaid
flowchart TB
  subgraph Orchestrator
    WF[Workflow / Pipeline]
  end
  subgraph Compute
    T1[Extract Task]
    T2[Transform Task]
    T3[Load Task]
  end
  subgraph Storage
    S1[(Landing path)]
    S2[(Curated tables)]
  end
  WF --> T1 --> S1
  WF --> T2 --> S2
  WF --> T3 --> S2
```

## Notes

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
