---
name: dekc-business-object
description: Promote tables/views to business objects with glossary definitions.
---

# Business Objects

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_business.py" --repo . --bundle knowledge promote tables/<file>.md \
  --name "Business Name" --definition "…" --owner "…"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_business.py" --repo . --bundle knowledge promote-layer --layer gold
```
