---
name: dekc-land-data
description: Plan landing new data using the DEKC second brain
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "$ARGUMENTS" \
  --intent land-data --repo . --bundle knowledge --write
```

Capture SourceSystem, bronze Table, Workflow, and evidence-backed lineage edges only.
