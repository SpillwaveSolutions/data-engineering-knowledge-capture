---
type: Rubric
title: Lineage integrity rubric
description: Adversarial rubric for lineage-skeptic — every edge must be evidence-backed.
scale: 0_1
aggregation: weighted_mean
threshold: 0.80
ager_version: "0.3.0"
tags: [dekc, evaluation, lineage, adversarial]
criteria:
  - id: edge_evidence
    weight: 0.40
    description: Each lineage edge cites SQL, job, config, or human attestation.
  - id: hop_honesty
    weight: 0.25
    description: Multi-hop paths do not skip unproven intermediate tables.
  - id: directionality
    weight: 0.15
    description: Edge direction matches data flow (upstream → downstream).
  - id: no_phantom_nodes
    weight: 0.20
    description: Endpoints of edges exist as real concepts with stable paths.
status: active
timestamp: 2026-08-09T00:00:00Z
---

# Lineage integrity rubric

**lineage-skeptic** scores only this rubric, then reports failed edges for retraction or evidence attach.
