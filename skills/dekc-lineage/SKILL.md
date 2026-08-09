---
name: dekc-lineage
description: Extract and materialize data lineage paths and mermaid diagrams.
---

# Lineage

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_lineage.py" --repo . --bundle knowledge graph
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_lineage.py" --repo . --bundle knowledge materialize
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_lineage.py" --repo . --bundle knowledge mermaid --focus tables/<slug>.md
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge lineage \
  --name <name> --nodes <up> <mid> <down>
```
