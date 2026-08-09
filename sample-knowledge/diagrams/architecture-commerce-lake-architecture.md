---
type: Diagram
title: Commerce lake architecture
description: "architecture diagram (mermaid): Commerce lake architecture"
diagram_kind: architecture
language: mermaid
tags: [diagram, architecture, mermaid, dekc]
timestamp: "2026-08-09T12:22:13Z"
status: active
verified: true
generated: true
wiki_key: diagram-architecture-commerce-lake-architecture
truth_state: current
subjects: [/lakes/retail-commerce-lake.md]
links:
- target: /lakes/retail-commerce-lake.md
  rel: documents
---

# Commerce lake architecture

**Kind:** `architecture` · **Language:** `mermaid`

## Subjects

- [retail-commerce-lake](/lakes/retail-commerce-lake.md)

## Diagram

```mermaid
flowchart LR
  SRC[Sources / Streams] --> BRZ[Bronze Landing]
  BRZ --> SLV[Silver Cleansed]
  SLV --> GLD[Gold Marts]
  GLD --> SEM[Semantic Model]
  SEM --> RPT[Reports / Dashboards]
  JOB[Jobs / Pipelines] -.-> BRZ
  JOB -.-> SLV
  JOB -.-> GLD
```

## Notes

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
