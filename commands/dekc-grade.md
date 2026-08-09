---
name: dekc-grade
description: Grade DEKC reverse-engineering with rubrics and adversarial skeptics
---

Run automated grade then adversarial judges.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_grade.py" --repo . --bundle knowledge
```

Spawn lineage-skeptic, business-skeptic, stream-job-skeptic, coverage-skeptic, then re-adversary-judge. Do not declare reverse engineering complete unless pass (score ≥ 0.75, no hard fails) or the user explicitly waives grading.
