---
name: dekc-walk
description: Walk a data lake/warehouse filesystem or ingest Fabric/Power BI inventory JSON into DEKC.
---

# DEKC Walk

`dekc_walk.py` is a **filesystem mirror walker** plus optional **control-plane JSON ingest**.
It does not call Fabric REST itself.

```bash
# Git SQL / parquet mirror
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" <path-to-lake> \
  --repo . --bundle knowledge --source-name <name>

# Fabric workspace items + Power BI bindings (export JSON first)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" \
  --fabric-items workspace-items.json \
  --pbi-bindings pbi-reports.json \
  --inventory information-schema.json \
  --workspace data_central_ws \
  --repo . --bundle knowledge
```

Then lineage + business promote + index (see data-lake-walker agent).

- `CREATE TABLE` with no `FROM` is reported as **DDL-only**, not “no lineage”.
- Fabric `Report` captures as DEKC **Report**, not Dashboard.
- Default SQL-endpoint SemanticModels are tagged in the description as not curated gold.
- Grade a walk inside a mixed brain with `dekc_grade.py --prefix semantic,tables/gold-` (or `--tag`) rather than scoring 15k SAC nodes.
