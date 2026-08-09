---
type: Diagram
title: orders-stream-landing-activity
description: activity diagram for ingestion job /ingestion/orders-stream-landing.md
diagram_kind: activity
language: mermaid
tags: [diagram, activity, mermaid, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: diagram-activity-orders-stream-landing-activity
truth_state: current
subjects: [/ingestion/orders-stream-landing.md]
links:
- target: /ingestion/orders-stream-landing.md
  rel: documents
---

# orders-stream-landing-activity

**Kind:** `activity` · **Language:** `mermaid`

activity diagram for ingestion job /ingestion/orders-stream-landing.md

## Subjects

- [orders-stream-landing](/ingestion/orders-stream-landing.md)

## Diagram

```mermaid
flowchart TD
  A([Start]) --> B[Validate source]
  B --> C{Data OK?}
  C -->|yes| D[Land bronze]
  C -->|no| E[Dead-letter / alert]
  D --> F[Transform silver]
  F --> G[Publish gold]
  G --> H[Run DQ rules]
  H --> I{DQ pass?}
  I -->|yes| J([Success])
  I -->|no| K[Quarantine + notify]
  E --> L([Fail])
  K --> L
```

## Notes

_Edit the fenced listing above; keep language tag as `mermaid` or `plantuml`._
