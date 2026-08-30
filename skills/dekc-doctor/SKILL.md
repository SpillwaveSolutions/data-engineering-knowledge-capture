---
name: dekc-doctor
description: Health check: validation, business coverage, orphans, toolchain (rg / FTS5 / sqlite index).
---

# Doctor

One-screen health: validation, business-object coverage, orphan tables, plus
toolchain (Python, ripgrep, SQLite FTS5) and whether
`knowledge/.dekc/index.sqlite` is present. Warms the index status on each run.
If rg is missing, offer installing ripgrep yourself — never from a hook.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_doctor.py" --repo . --bundle knowledge
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_validate.py" --repo . --bundle knowledge
```
