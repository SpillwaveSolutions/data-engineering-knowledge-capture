---
type: Diagram
title: daily-medallion-orders-class
description: class diagram for workflow /workflows/daily-medallion-orders.md
diagram_kind: class
language: mermaid
tags: [diagram, class, mermaid, dekc]
timestamp: "2026-08-09T12:22:18Z"
status: active
verified: true
generated: true
wiki_key: diagram-class-daily-medallion-orders-class
truth_state: current
subjects: [/workflows/daily-medallion-orders.md]
links:
- target: /workflows/daily-medallion-orders.md
  rel: documents
---

# daily-medallion-orders-class

**Kind:** `class` · **Language:** `mermaid`

class diagram for workflow /workflows/daily-medallion-orders.md

## Subjects

- [daily-medallion-orders](/workflows/daily-medallion-orders.md)

## Diagram

```mermaid
classDiagram
  class Workflow {
    +name
    +orchestrator
    +schedule
    +mode
  }
  class Task {
    +name
    +retries
  }
  class Table {
    +fqn
    +layer
  }
  class DQRule {
    +rule_type
    +severity
  }
  Workflow "1" --> "*" Task : contains
  Task --> Table : reads_writes
  DQRule --> Table : validates
```

## Notes

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
