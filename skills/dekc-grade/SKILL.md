---
name: dekc-grade
description: Grade reverse-engineering quality with automated rubric scores and adversarial judge protocol. Use after walks, before claiming RE complete.
---

# DEKC grade (adversarial RE quality)

## Automated baseline

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_grade.py" --repo . --bundle knowledge
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_grade.py" --repo . --bundle knowledge --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_grade.py" --repo . --bundle knowledge --write
```

## Adversarial loop (required for acceptance)

1. Spawn **lineage-skeptic**, **business-skeptic**, **stream-job-skeptic**, **coverage-skeptic**
2. Aggregate with **re-adversary-judge** against `evaluation/reverse-engineering-rubric.md` (threshold 0.75)
3. On fail → orchestrator revises (capture evidence or **retract** claims) → re-grade
4. On pass → `dekc_index.py build`

Orchestrators: **data-lake-walker**, **reverse-engineering-orchestrator**.

## Rubrics

- `evaluation/reverse-engineering-rubric.md`
- `evaluation/lineage-integrity-rubric.md`
- `evaluation/business-fidelity-rubric.md`
- `evaluation/stream-job-landing-rubric.md`
