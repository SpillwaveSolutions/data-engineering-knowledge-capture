---
name: dekc-second-brain
description: Query DEKC second brain with design intent (report, land-data, metric, impact)
---

Run intent-aware second-brain retrieval using standard OKF concept schemas.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "<query>" \
  --intent design-report|land-data|design-metric|impact|general \
  --repo . --bundle knowledge
```

Schemas: `schemas/okf-concepts/`. Validate: `dekc_schemas.py validate`.
