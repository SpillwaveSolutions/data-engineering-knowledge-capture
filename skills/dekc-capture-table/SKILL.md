---
name: dekc-capture-table
description: Capture a table with columns, layer, schema into DEKC/OKF.
---

# Capture Table

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge table \
  --name <name> --layer bronze|silver|gold --schema <schema> \
  --description "…" --columns-json '[{"name":"c","type":"string"}]'
```
