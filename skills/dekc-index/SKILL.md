---
name: dekc-index
description: Rebuild the local second-brain index (inventory, inverted search, graph, embeddings).
---

# Index

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_index.py" --repo . --bundle knowledge build
```

Writes `knowledge/.index/{inventory,search,graph,embeddings,manifest}.*` for LLM retrieval.
