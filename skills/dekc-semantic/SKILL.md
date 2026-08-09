---
name: dekc-semantic
description: Capture semantic models, metrics, dashboards, reports.
---

# Semantic / BI

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge semantic --name "…" --tables … --metrics …
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge metric --name "…" --definition "…" --expression "…"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge dashboard --name "…" --tool powerbi --metrics … --visualizes …
```
