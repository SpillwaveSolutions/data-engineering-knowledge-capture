---
type: Reference
title: DEKC evaluation catalog
description: Rubrics and adversarial grading for reverse-engineering quality (AGER Judge plane).
timestamp: 2026-08-09T00:00:00Z
status: active
tags: [dekc, evaluation]
links:
  - target: /evaluation/reverse-engineering-rubric.md
    rel: related_to
  - target: /evaluation/lineage-integrity-rubric.md
    rel: related_to
  - target: /evaluation/business-fidelity-rubric.md
    rel: related_to
  - target: /evaluation/stream-job-landing-rubric.md
    rel: related_to
---

# Evaluation

| Rubric | Primary judge / skeptic | Threshold |
|--------|-------------------------|-----------|
| [Reverse engineering quality](./reverse-engineering-rubric.md) | re-adversary-judge | 0.75 |
| [Lineage integrity](./lineage-integrity-rubric.md) | lineage-skeptic | 0.80 |
| [Business fidelity](./business-fidelity-rubric.md) | business-skeptic | 0.72 |
| [Stream & job landing](./stream-job-landing-rubric.md) | stream-job-skeptic | 0.70 |

Automated partial scores: `python3 scripts/dekc_grade.py --bundle knowledge`.
