---
type: Rubric
title: Business fidelity rubric
description: Grades promotion of technical assets to business objects and glossary quality.
scale: 0_1
aggregation: weighted_mean
threshold: 0.72
ager_version: "0.3.0"
tags: [dekc, evaluation, business, glossary, adversarial]
criteria:
  - id: gold_coverage
    weight: 0.30
    description: Gold/mart tables (or certified metrics) have BusinessObject links.
  - id: definition_quality
    weight: 0.30
    description: Definitions are specific, non-circular, usable by analysts/LLM.
  - id: glossary_alignment
    weight: 0.20
    description: Glossary terms gloss the right BO; synonyms/aliases when needed.
  - id: metric_binding
    weight: 0.20
    description: Metrics/dashboards point at real tables/measures, not orphans.
status: active
timestamp: 2026-08-09T00:00:00Z
---

# Business fidelity rubric

**business-skeptic** rejects vacuous definitions ("data about X") and unlinked gold.
