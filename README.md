# Data Engineering Knowledge Capture (DEKC)

**Git-native second brain for data platforms** — schemas, tables, views, queries, SQL/DAX, lineage, medallion layers (bronze → silver → gold), semantic models, dashboards, reports, streams, jobs, business objects, and glossary terms.

DEKC **extends [Project Knowledge Capture (PKC)](https://github.com/SpillwaveSolutions/project-knowledge-capture)** and **depends on [OKF](https://github.com/SpillwaveSolutions/okf-plugin)**. Multi-agent **walk loops** are designed with **[OKF Agent Graph (AGER)](https://github.com/SpillwaveSolutions/okf-agent-graph)** so orchestrators, scouts, judges, and synthesizers reverse-engineer real platforms (Azure Fabric, AWS, GCP) into the same portable graph.

| | |
|---|---|
| **Plugin name** | `data-engineering-knowledge-capture` |
| **Repo** | [SpillwaveSolutions/data-engineering-knowledge-capture](https://github.com/SpillwaveSolutions/data-engineering-knowledge-capture) |
| **Version** | 0.1.0 |
| **License** | MIT |
| **Hosts** | Claude Code · Grok Build · Codex · OpenCode |

## Docs

| Doc | Audience |
|-----|----------|
| **[User guide](./docs/user_guide/user-guide.md)** | Install, walk a lake, promote business objects, multi-cloud recipes |
| **[Design doc](./docs/designs/current_design_doc.md)** | Agent graph loops (AGER), Azure Fabric / AWS / GCP reverse engineering, streams & jobs |
| **[Typed edges](./docs/typed-edges.md)** | Relation vocabulary for lineage and business meaning |
| **[PORTS](./PORTS.md)** | Claude / Grok / Codex / OpenCode packaging |

## Why DEKC

Data teams lose institutional memory in tribal knowledge: “what does this gold table mean?”, “which Event Hub lands into bronze?”, “which Glue job promotes silver → gold?”, “which DAX measure powers the exec dashboard?”

DEKC turns lakehouse / warehouse / stream reality into a **reviewable OKF knowledge graph** that agents can walk, pack, and search — while promoting technical assets into **business objects with glossary definitions**.

## Ecosystem

```text
okf-plugin (okf-graph-eng)          portable OKF graph ops (validate, pack, impact)
        ▲
        │ depends on
okf-agent-graph (AGER)              multi-agent loop schema (orchestrator/worker/judge,
        ▲                           LoopPolicy, ScratchPad, tools, triggers)
        │ agent loops modeled with
project-knowledge-capture (PKC)     meetings, decisions, features
        ▲
        │ extends
data-engineering-knowledge-capture  data assets, lineage, streams/jobs, glossary (this repo)
```

| System | Role | Repository |
|--------|------|------------|
| **OKF** | Graph format + impact / query / validate | [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin) |
| **AGER** | Multi-agent loop / harness graph as OKF | [okf-agent-graph](https://github.com/SpillwaveSolutions/okf-agent-graph) |
| **PKC** | Meetings, experiments, decisions, features | [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture) |
| **DEKC** | Data assets, lineage, streams/jobs, semantic layer | this repo |

## What gets captured

| Catalog | Examples |
|---------|----------|
| **Sources** | Fabric Lakehouse, S3 data lake, GCS bucket, API landing |
| **Layers** | Bronze / silver / gold (medallion) |
| **Schemas · tables · views · columns** | Physical + logical structure |
| **Queries · SQL · DAX** | Models, measures, notebooks |
| **Transformations · workflows · jobs** | dbt, Airflow, Glue, Data Factory, Dataform, Composer |
| **Streams** | Event Hub, Kinesis, Pub/Sub, Kafka → landing tables |
| **Lineage** | Multi-hop feeds / promotes_to paths |
| **Semantic · metrics · dashboards · reports** | BI consumption surface |
| **Business objects · glossary** | Human meaning of technical assets |
| **Agents** | Walk receipts (AGER runs materialized as knowledge) |

## Install

### Claude Code

```bash
# Graph + agent-loop substrate
claude plugin marketplace add SpillwaveSolutions/okf-plugin
claude plugin install okf-graph-eng@okf-plugin-marketplace
claude plugin marketplace add SpillwaveSolutions/okf-agent-graph
claude plugin install okf-agent-graph@okf-agent-graph-marketplace

# Project reasoning (optional but recommended)
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
# /plugins → install data-engineering-knowledge-capture
```

### OpenCode

Skills + `AGENTS.md` policy; registration in `.opencode/plugin/dekc.json`.

See [PORTS.md](./PORTS.md).

## Quick start

```bash
# Scaffold knowledge/
python3 scripts/dekc_common.py init-bundle --repo . --bundle knowledge

# Walk a lake / SQL / job root (filesystem reverse engineer)
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

## Agent loop (AGER-shaped)

DEKC’s **data-lake-walker** is the orchestrator. Subagents are AGER-style workers; a layer-auditor acts as judge; packs/index act as synthesizer output.

```text
Trigger (manual | cron | okf_change | ticket)
        │
        ▼
┌───────────────────┐
│ data-lake-walker  │  Orchestrator — plan hops, spawn, re-plan
│  LoopPolicy:      │  goal=coverage · max_turns · no_progress
└─────────┬─────────┘
          │ fan-out
    ┌─────┼──────────────┬────────────────┐
    ▼     ▼              ▼                ▼
 schema  lineage     report-cataloger  (stream/job scouts)
 scout   tracer
    │     │              │
    └─────┴──────┬───────┘
                 ▼
         semantic-mapper  → business objects + glossary
                 │
                 ▼
          layer-auditor   → score coverage / orphans (Judge)
                 │
                 ▼
            index + pack  → second-brain artifacts (Synthesizer)
```

Full reverse-engineering playbooks for **Azure Fabric**, **AWS**, and **GCP** (including **streams and jobs**) live in the [design doc](./docs/designs/current_design_doc.md).

## Sample knowledge

[`sample-knowledge/`](./sample-knowledge/) — retail commerce medallion:

**bronze.orders_raw → silver.orders → gold.order_daily** + LTV view, DAX measure, semantic model, executive dashboard, business objects, glossary (GMV).

```bash
python3 tests/test_dekc.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_doctor.py --bundle sample-knowledge
```

## Second-brain index

`dekc_index.py build` writes:

```text
knowledge/.index/
  inventory.json
  search.json
  graph.json
  embeddings.jsonl   # local bag-of-tokens (no API key)
  manifest.json
```

## Config

See [`.dekc/config.example.yml`](./.dekc/config.example.yml).

## License

MIT — see [LICENSE](./LICENSE).
