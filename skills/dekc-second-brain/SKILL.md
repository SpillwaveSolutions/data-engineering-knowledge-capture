---
name: dekc-second-brain
description: Query the DEKC OKF second brain with design intents (reports, land data, metrics, impact). Uses standard concept schemas under schemas/okf-concepts/.
---

# DEKC second brain

The knowledge bundle is a **schema-typed second brain** for data platform design work.

## Schemas

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_schemas.py" list
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_schemas.py" intents
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_schemas.py" validate --repo . --bundle knowledge
```

## Intent query

```bash
# Design a report
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "executive revenue" \
  --intent design-report --repo . --bundle knowledge

# Land new data
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "orders event hub" \
  --intent land-data --repo . --bundle knowledge

# Metric design
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "GMV" \
  --intent design-metric --repo . --bundle knowledge

# Impact of changing a table
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "gold order_daily" \
  --intent impact --repo . --bundle knowledge --write
```

## Workflow

1. **Retrieve** with `dekc_brain.py` (intent + query) → checklist + ranked concepts + 2-hop pack  
2. **Design** using only evidence from the pack (do not invent lineage)  
3. **Capture** new assets with `dekc_capture.py` matching `schemas/okf-concepts/`  
4. **Index** is optional — search/pack refresh `knowledge/.dekc/index.sqlite` themselves. `dekc_index.py build` is `refresh --force`.  
5. Optional **grade** if reverse-engineering

See `schemas/README.md` and `docs/user_guide/user-guide.md`.
