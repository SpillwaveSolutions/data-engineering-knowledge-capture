# Data Engineering Knowledge Capture (DEKC)

**Git-native second brain for data platforms** — schemas, tables, views, queries, SQL/DAX, lineage, medallion layers (bronze → silver → gold), semantic models, dashboards, reports, business objects, and glossary terms.

DEKC **extends [Project Knowledge Capture (PKC)](https://github.com/SpillwaveSolutions/project-knowledge-capture)** and **depends on [OKF](https://github.com/SpillwaveSolutions/okf-plugin)**. Everything is OKF Markdown (YAML frontmatter + absolute links + typed edges).

| | |
|---|---|
| **Plugin name** | `data-engineering-knowledge-capture` |
| **Repo** | [SpillwaveSolutions/data-engineering-knowledge-capture](https://github.com/SpillwaveSolutions/data-engineering-knowledge-capture) |
| **Version** | 0.1.0 |
| **License** | MIT |
| **Hosts** | Claude Code · Grok Build · Codex · OpenCode |

## Why DEKC

Data teams lose institutional memory in tribal knowledge: “what does this gold table mean?”, “which bronze feed lands into silver.orders?”, “which DAX measure powers the exec dashboard?”

DEKC turns lake/warehouse reality into a **reviewable OKF knowledge graph** that agents can walk, pack, and search — while promoting technical assets into **business objects with glossary definitions**.

| System | Role | Repository |
|--------|------|------------|
| **OKF Plugin** | Graph format + impact / query / validate | [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin) |
| **PKC** | Meetings, experiments, decisions, features | [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture) |
| **DEKC (this)** | Data assets, lineage, semantic layer, glossary | this repo |

## Install

### Claude Code

```bash
# Companions (required conceptually; install both)
claude plugin marketplace add SpillwaveSolutions/okf-plugin
claude plugin install okf-graph-eng@okf-plugin-marketplace
claude plugin marketplace add SpillwaveSolutions/project-knowledge-capture
claude plugin install project-knowledge-capture@pkc-plugin-marketplace

# DEKC
claude plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
claude plugin install data-engineering-knowledge-capture@dekc-plugin-marketplace
```

### Grok Build

Grok Build loads Claude-compatible plugins with **zero extra config**. Optional identity pin: `.grok-plugin/marketplace.json`.

### Codex

```bash
codex plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
# then /plugins → install data-engineering-knowledge-capture
```

Native manifest: `.codex-plugin/plugin.json` (skills + hooks).

### OpenCode

Core works via skills + `AGENTS.md` policy. Project registration: `.opencode/opencode.json` + `.opencode/plugin/dekc.json`.

See [PORTS.md](./PORTS.md) for the full harness matrix.

## Quick start

```bash
# Scaffold knowledge/
python3 scripts/dekc_common.py init-bundle --repo . --bundle knowledge

# Walk a lake / SQL root
python3 scripts/dekc_walk.py path/to/lake --repo . --bundle knowledge

# Materialize lineage + promote gold → business objects
python3 scripts/dekc_lineage.py --repo . --bundle knowledge materialize
python3 scripts/dekc_business.py --repo . --bundle knowledge promote-layer --layer gold

# Index second brain + health
python3 scripts/dekc_index.py --repo . --bundle knowledge build
python3 scripts/dekc_doctor.py --repo . --bundle knowledge
python3 scripts/dekc_search.py "revenue" --repo . --bundle knowledge
```

Slash / skill entry points: `/dekc-init` · `/dekc-walk` · `/dekc-lineage` · `/dekc-business-object` · `/dekc-glossary` · `/dekc-semantic` · `/dekc-context` · `/dekc-search` · `/dekc-index` · `/dekc-doctor`

## Agents

| Agent | Role |
|-------|------|
| **data-lake-walker** | Orchestrator — walk, lineage, promote, index |
| **schema-scout** | Schemas, tables, columns, contracts |
| **lineage-tracer** | SQL/DAX/pipeline lineage, medallion promotions |
| **semantic-mapper** | Business objects, glossary, metrics, semantic models |
| **report-cataloger** | Dashboards, reports, BI bindings |
| **layer-auditor** | Bronze/silver/gold health, orphans, index freshness |

## Concept catalogs

`sources` · `layers` · `schemas` · `tables` · `views` · `queries` · `columns` · `sql` · `dax` · `transformations` · `workflows` · `lineage` · `contracts` · `semantic` · `metrics` · `reports` · `dashboards` · `business-objects` · `glossary` · `packs` · `agents`

### Typed edges (DEKC)

`lands_as` · `feeds` · `transforms_to` · `promotes_to` · `derived_from` · `reads_from` · `writes_to` · `defines` · `contains` · `queries` · `models` · `measures` · `visualizes` · `glosses` · `businessizes` · `sourced_from` · `layered_as` · …

## Sample knowledge

[`sample-knowledge/`](./sample-knowledge/) — retail commerce medallion chain:

**bronze.orders_raw → silver.orders → gold.order_daily** + LTV view, DAX measure, semantic model, executive dashboard, business objects, glossary (GMV).

```bash
python3 tests/test_dekc.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_doctor.py --bundle sample-knowledge
```

## Second-brain index

`dekc_index.py build` writes:

```
knowledge/.index/
  inventory.json
  search.json
  graph.json
  embeddings.jsonl   # local bag-of-tokens vectors (no API key)
  manifest.json
```

## Config

See [`.dekc/config.example.yml`](./.dekc/config.example.yml).

## License

MIT — see [LICENSE](./LICENSE).
