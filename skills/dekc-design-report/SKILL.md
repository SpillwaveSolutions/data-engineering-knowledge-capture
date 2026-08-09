---
name: dekc-design-report
description: Use the DEKC second brain to design a new report/dashboard from existing metrics, gold tables, business objects, and glossary.
---

# Design a report (second brain)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "<report topic>" \
  --intent design-report --repo . --bundle knowledge --write
```

Then:

1. Prefer **gold** tables + existing **Metric** / **SemanticModel** concepts  
2. Align language with **GlossaryTerm** / **BusinessObject**  
3. Capture Report/Dashboard:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge dashboard \
  --name "<dashboard>" --description "..." 
# link metrics/tables via dekc_link or capture helpers
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_index.py" --repo . --bundle knowledge build
```

Never invent tables or measures not in the brain; capture new ones explicitly first.
