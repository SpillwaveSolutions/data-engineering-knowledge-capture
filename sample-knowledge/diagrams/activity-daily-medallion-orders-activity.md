---
type: Diagram
title: daily-medallion-orders-activity
description: activity diagram for workflow /workflows/daily-medallion-orders.md
diagram_kind: activity
language: mermaid
tags: [diagram, activity, mermaid, dekc]
timestamp: "2026-08-09T12:22:18Z"
status: active
verified: true
generated: true
wiki_key: diagram-activity-daily-medallion-orders-activity
truth_state: current
subjects: [/workflows/daily-medallion-orders.md]
links:
- target: /workflows/daily-medallion-orders.md
  rel: documents
---

# daily-medallion-orders-activity

**Kind:** `activity` · **Language:** `mermaid`

activity diagram for workflow /workflows/daily-medallion-orders.md

## Subjects

- [daily-medallion-orders](/workflows/daily-medallion-orders.md)

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

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
