---
name: dekc-walk
description: Walk a data lake/warehouse filesystem and capture tables, SQL, DAX, parquet datasets.
---

# DEKC Walk

Orchestrated discovery — prefer the **data-lake-walker** agent for multi-step runs.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" <path-to-lake> \
  --repo . --bundle knowledge --source-name <name>
```

Then lineage + business promote + index (see data-lake-walker agent).
