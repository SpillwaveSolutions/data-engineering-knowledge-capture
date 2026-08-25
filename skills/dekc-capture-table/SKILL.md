---
name: dekc-capture-table
description: Capture a table with columns, layer, schema into DEKC/OKF.
---

# Capture Table

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge table \
  --name <name> --layer bronze|silver|gold --schema <schema> \
  --description "…" --columns-json '[{"name":"c","type":"string"}]'
```

Rules:

- Existence-only names default `verified: false`. Pass `--verified` or supply `--sql` / `--columns-json`.
- `--source` is a hint. `sourced_from` is a **lineage edge** — it is only written when `--sql` or `--evidence` is present. Otherwise the link is `related_to`.
- `--kind auto` (default) treats warehouse gold `vw*` / `x_vw*` / `CREATE VIEW` as **View**, not Table. Force with `--kind table`.
- `--schema` **merges** `contains` onto the Schema node (last table no longer wins).
- `--slug` / `--fabric-id` disambiguate Power BI names that slugify together (`Operations | …` vs two spaces).
- Fabric `Report` is not a DEKC `Dashboard`. Default SQL-endpoint models are not curated gold.
