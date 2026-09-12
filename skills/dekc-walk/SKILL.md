---
name: dekc-walk
description: Walk a data lake/warehouse filesystem or ingest Fabric/Power BI inventory JSON into DEKC.
---

# DEKC Walk

`dekc_walk.py` is a **filesystem mirror walker** plus optional **control-plane JSON ingest**.
It does not call Fabric REST itself.

Always **plan first** when reverse-engineering a new root (`/dekc-plan` or `--plan-only`). Then scoped capture:

```bash
# Git SQL / parquet mirror
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" <path-to-lake> \
  --repo . --bundle knowledge --source-name <name>

# Pause after plan
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" <path-to-lake> \
  --repo . --bundle knowledge --plan-only --system "Retail Lake"

# One plan area (not a full re-walk)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" <path-to-lake> \
  --repo . --bundle knowledge --from-plan knowledge/.dekc/re-plan.json --area lake

# Fabric workspace items + Power BI bindings (export JSON first)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" \
  --fabric-items workspace-items.json \
  --pbi-bindings pbi-reports.json \
  --inventory information-schema.json \
  --workspace data_central_ws \
  --repo . --bundle knowledge
```

Or `dekc_orchestrate.py --from-plan … --area <id>`.

Then lineage + business promote + **adversarial grade** (see data-lake-walker / reverse-engineering-orchestrator).

- `CREATE TABLE` with no `FROM` is reported as **DDL-only**, not “no lineage”.
- Fabric `Report` captures as DEKC **Report**, not Dashboard.
- Default SQL-endpoint SemanticModels are tagged in the description as not curated gold.
- Grade a walk inside a mixed brain with `dekc_grade.py --prefix semantic,tables/gold-` (or `--tag`) rather than scoring 15k SAC nodes.
- DuckDB / notebooks / DQ / orchestration markers get cheap script writes when those plan areas run. Agents enrich; they do not invent edges.
