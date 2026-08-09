---
type: Diagram
title: orders-stream-landing-component
description: component diagram for ingestion job /ingestion/orders-stream-landing.md
diagram_kind: component
language: mermaid
tags: [diagram, component, mermaid, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: diagram-component-orders-stream-landing-component
truth_state: current
subjects: [/ingestion/orders-stream-landing.md]
links:
- target: /ingestion/orders-stream-landing.md
  rel: documents
---

# orders-stream-landing-component

**Kind:** `component` · **Language:** `mermaid`

component diagram for ingestion job /ingestion/orders-stream-landing.md

## Subjects

- [orders-stream-landing](/ingestion/orders-stream-landing.md)

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

_Edit the fenced listing above; keep language tag as `mermaid` or `plantuml`._
