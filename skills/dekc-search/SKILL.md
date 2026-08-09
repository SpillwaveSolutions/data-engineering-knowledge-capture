---
name: dekc-search
description: Search the indexed DEKC second brain.
---

# Search

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_index.py" --repo . --bundle knowledge build
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" "revenue" --repo . --bundle knowledge
```
