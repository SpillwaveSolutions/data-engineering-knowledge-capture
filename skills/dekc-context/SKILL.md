---
name: dekc-context
description: Build progressive-disclosure context packs for a data concept.
---

# Context Pack

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_pack.py" tables/<slug>.md --repo . --bundle knowledge --hops 2
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_pack.py" tables/<slug>.md --repo . --bundle knowledge --tiny
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_pack.py" tables/<slug>.md --repo . --bundle knowledge --write
```

When okf-plugin is installed, `okf pack` / impact also work on DEKC concepts.
