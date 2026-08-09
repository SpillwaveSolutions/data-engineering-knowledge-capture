---
name: dekc-design-report
description: Design a report from the DEKC second brain
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "$ARGUMENTS" \
  --intent design-report --repo . --bundle knowledge --write
```

Follow the checklist in the pack; capture Dashboard/Report/Metric with schema-aligned frontmatter.
