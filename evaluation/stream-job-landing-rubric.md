---
type: Rubric
title: Stream and job landing rubric
description: Grades capture of continuous streams and batch/micro-batch jobs that land or transform data.
scale: 0_1
aggregation: weighted_mean
threshold: 0.70
ager_version: "0.3.0"
tags: [dekc, evaluation, streams, jobs, adversarial]
criteria:
  - id: producer_capture
    weight: 0.30
    description: Known streams/jobs in the mirror are SourceSystem or Workflow concepts.
  - id: landing_table
    weight: 0.30
    description: Landing bronze (or raw) tables exist and are linked from producers.
  - id: schedule_or_mode
    weight: 0.15
    description: Continuous vs micro-batch vs nightly is stated when known.
  - id: no_fake_streams
    weight: 0.25
    description: Pure batch systems are not polluted with invented stream sources.
status: active
timestamp: 2026-08-09T00:00:00Z
---

# Stream and job landing rubric

**stream-job-skeptic** applies this after cloud reverse-engineering walks.
