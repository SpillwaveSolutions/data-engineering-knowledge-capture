---
name: dekc-doctor
description: Health check: validation, business coverage, orphans, index.
---

# Doctor

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_doctor.py" --repo . --bundle knowledge
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_validate.py" --repo . --bundle knowledge
```
