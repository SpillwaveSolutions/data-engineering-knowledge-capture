---
type: Rubric
title: Reverse engineering quality rubric
description: Grades DEKC reverse-engineering output of a platform (lake, Fabric, AWS, GCP) for structural fidelity, lineage honesty, landing completeness, and business materialization.
scale: 0_1
aggregation: weighted_mean
threshold: 0.75
ager_version: "0.3.0"
tags: [dekc, evaluation, reverse-engineering, adversarial]
criteria:
  - id: structural_coverage
    weight: 0.20
    description: >
      Schemas, tables, views, and layers reflect what the source mirror/export
      actually contains. No phantom tables. Medallion layer assignment matches
      path/schema evidence (bronze/silver/gold or cloud equivalent).
  - id: lineage_integrity
    weight: 0.25
    description: >
      Every feeds/transforms_to/promotes_to/derived_from edge is justified by
      SQL, job config, dbt ref, pipeline activity, or explicit human input.
      No invented hops. Bidirectional pack edges present where required.
  - id: stream_job_landing
    weight: 0.15
    description: >
      Streams (Event Hub/Kinesis/Pub/Sub/etc.) and jobs (pipelines/Glue/Dataflow)
      that land or transform data are captured as SourceSystem/Workflow plus
      landing tables and edges. Batch-only systems are not forced into fake streams.
  - id: business_fidelity
    weight: 0.15
    description: >
      Gold/mart assets have BusinessObject + GlossaryTerm with non-vacuous
      definitions. Metrics/dashboards bind to real technical assets.
  - id: evidence_traceability
    weight: 0.15
    description: >
      Concepts cite sources (file paths, job names, FQNs). Walk receipts and
      ScratchPad/agent logs allow an auditor to re-derive claims.
  - id: adversarial_resistance
    weight: 0.10
    description: >
      Survives skeptic challenges: removed edges that lack proof, demoted
      overconfident layer labels, fixed orphan gold, no secret leakage.
status: active
timestamp: 2026-08-09T00:00:00Z
---

# Reverse engineering quality rubric

Used by **re-adversary-judge** and automated `dekc_grade.py` (partial scores).

## Pass bar

Weighted mean **≥ 0.75** and no hard fails:

| Hard fail | Meaning |
|-----------|---------|
| Invented lineage | Edge without evidence |
| Secret in body | Credential/PII pattern persisted |
| Empty gold promotion | Gold tables exist but zero business objects when promote was claimed |

## Scoring guidance (0.0–1.0 per criterion)

| Score | Meaning |
|-------|---------|
| 0.0–0.3 | Missing or largely wrong |
| 0.4–0.6 | Partial; major gaps |
| 0.7–0.84 | Solid with minor issues |
| 0.85–1.0 | Adversary cannot break claims with available evidence |

## Adversarial protocol

1. **Producer** (workers + orchestrator) completes a walk turn.
2. **Skeptics** attack lineage, coverage, streams/jobs, business meaning (parallel).
3. **re-adversary-judge** aggregates skeptic findings against this rubric.
4. On fail (`score < threshold` or hard fail): orchestrator re-plans; do **not** raise score by inventing data — only by capturing evidence or retracting claims.
