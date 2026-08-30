---
name: dekc-search
description: Full-text search over the DEKC knowledge bundle (AND terms, type filters). Use when finding tables, lineage, or metrics by keyword.
---

# Search

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" "revenue" --repo .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" revenue --type Table,Metric --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" revenue --engine index
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" revenue --no-index --rg
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" revenue --engine scan
```

AND semantics across terms. Scores title > description > tags > body
(`title×10 / description×5 / tags×4 / min(body,8)`).

Ladder: SQLite index → ripgrep → full scan. Ranking stays in Python, so
`--engine scan` and the index path return the same scores. `--engine fts`
uses FTS5 MATCH (prefix tokens; not score-identical). Missing index or rg
is not an error. See `/dekc-index`.

After hits on a table, offer `/dekc-context` (2-hop pack).
