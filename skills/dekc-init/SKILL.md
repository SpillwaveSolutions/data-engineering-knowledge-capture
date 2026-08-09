---
name: dekc-init
description: Scaffold a DEKC knowledge bundle with medallion catalogs.
---

# DEKC Init

Create a data-engineering OKF knowledge root.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_common.py" init-bundle \
  --repo . --bundle knowledge --title "Data Platform Knowledge"
```

Optionally write `.dekc/config.yml` from `.dekc/config.example.yml`.

Depends on: **OKF** for graph ops, **PKC** for project reasoning (install companions).

Done when: `index.md` has `okf_version`, catalogs exist, bronze/silver/gold layers seeded.
