---
name: dekc-capture-query
description: Capture SQL or DAX query artifacts.
---

# Capture Query

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge query \
  --name <name> --dialect sql|dax --sql "…" --reads-from <tables>
```
