---
type: DesignPattern
title: Design report from gold metrics
description: Standard pattern for designing a BI report from gold tables, metrics, and glossary in the second brain.
intent: design-report
applies_to: [Dashboard, Report, Metric, BusinessObject, GlossaryTerm, Table]
tags: [pattern, design-report, gold, dekc]
timestamp: "2026-08-09T12:00:00Z"
status: active
verified: true
wiki_key: pattern-design-report-from-gold
truth_state: current
---

# Design report from gold

1. `dekc_brain.py "<topic>" --intent design-report`  
2. Bind report language to **GlossaryTerm** / **BusinessObject**.  
3. Prefer **gold** tables and existing **Metric** concepts.  
4. Capture `Dashboard`/`Report` with `visualizes` → metrics/tables.  
5. If a measure is missing, use `--intent design-metric` before inventing DAX/SQL.  
6. Re-index; optional impact pack if changing shared metrics.
