# Data Engineering Knowledge Capture (DEKC)

**Git-native second brain for data platforms** — schemas, tables, views, queries, SQL/DAX, lineage, medallion layers (bronze → silver → gold), semantic models, dashboards, reports, streams, jobs, business objects, and glossary terms.

DEKC **extends [Project Knowledge Capture (PKC)](https://github.com/SpillwaveSolutions/project-knowledge-capture)** and **depends on [OKF](https://github.com/SpillwaveSolutions/okf-plugin)**. Multi-agent **walk loops** are designed with **[OKF Agent Graph (AGER)](https://github.com/SpillwaveSolutions/okf-agent-graph)** so orchestrators, scouts, judges, and synthesizers reverse-engineer real platforms (Azure Fabric, AWS, GCP) into the same portable graph.

| | |
|---|---|
| **Plugin name** | `data-engineering-knowledge-capture` |
| **Repo** | [SpillwaveSolutions/data-engineering-knowledge-capture](https://github.com/SpillwaveSolutions/data-engineering-knowledge-capture) |
| **Version** | 0.4.0 |
| **License** | MIT |
| **Hosts** | Claude Code · Grok Build · Codex · OpenCode · Agent Plugins 1.0 · Grok Bot · LangChain Deep Agents |

## Docs

| Doc | Audience |
|-----|----------|
| **[Noun-ownership migration](./docs/user_guide/noun-ownership-migration.md)** | Existing brains: `Workflow` → `IngestionJob`; mixed AGER/SAC types |
| **[User guide](./docs/user_guide/user-guide.md)** | Install, walk a lake, promote business objects, multi-cloud recipes |
| **[Design doc](./docs/designs/current_design_doc.md)** | Agent graph loops (AGER), Azure Fabric / AWS / GCP reverse engineering, streams & jobs |
| **[Typed edges](./docs/typed-edges.md)** | Relation vocabulary for lineage and business meaning |
| **[PORTS](./PORTS.md)** | Claude / Grok / Codex / OpenCode packaging |
| **[Onboarding](./docs/ONBOARDING.md)** | Grok Bot / any host start |
| **[Grok Bot](./docs/GROK_BOT.md)** | Cloud Grok Bot binding |
| **[Deep Agents](./docs/LANG_CHAIN_DEEP_AGENTS.md)** | LangChain Deep Agents |
| **[Isolation](./docs/ISOLATION.md)** | Worktree + PR write isolation |


## Multi-host

| Host | How it loads |
|------|----------------|
| Claude Code | Marketplace / local plugin (`.claude-plugin`) |
| Grok Build | Claude-compatible, zero-config (`.grok-plugin` pins identity) |
| Codex | `.codex-plugin` + `hooks/codex-hooks.json` |
| OpenCode | Skills + `AGENTS.md` |
| Agent Plugins 1.0 | Root `plugin.json` |
| Grok Bot | Skills + [docs/GROK_BOT.md](docs/GROK_BOT.md) (not a Claude-style install) |
| LangChain Deep Agents | `skills=` / SkillsMiddleware — [docs/LANG_CHAIN_DEEP_AGENTS.md](docs/LANG_CHAIN_DEEP_AGENTS.md) |

Write isolation (worktree + PR) is in [docs/ISOLATION.md](docs/ISOLATION.md). Public examples use fictional **lumenfield-detector** and **northstar-console** only. Point `SECOND_BRAIN_ROOT` at a path the human already has. Never hard-code a private remote.

## Why DEKC

Data teams lose institutional memory in tribal knowledge: “what does this gold table mean?”, “which Event Hub lands into bronze?”, “which Glue job promotes silver → gold?”, “which DAX measure powers the exec dashboard?”

DEKC turns lakehouse / warehouse / stream reality into a **reviewable OKF knowledge graph** that agents can walk, pack, and search — while promoting technical assets into **business objects with glossary definitions**.

## Nouns (this plugin)

DEKC owns the **data plane**. Catalog / ContextPack live in okf-plugin. `AgentNode` / `Workflow` live in AGER. `Diagram` / `Wireframe` live in SAC.

BusinessObject, Column, DQRule, Dashboard, DataCatalog, DataContract, DataDomain, DataLake, DataMart, DataProduct, Dataset, DaxArtifact, DesignPattern, GlossaryTerm, IngestionJob, Layer, LineagePath, Metric, Query, Report, Schema, SemanticModel, SourceSystem, SqlArtifact, StorageLocation, Stream, Table, Transformation, View.

| Group | Nouns |
|-------|-------|
| Assets | Dataset, Table, View, Column, Schema, Query, SqlArtifact, DaxArtifact |
| Platform | SourceSystem, DataLake, DataMart, DataCatalog, DataDomain, DataProduct, StorageLocation, Stream, Layer |
| Movement | IngestionJob, Transformation, LineagePath, DataContract, DQRule |
| Semantic | SemanticModel, Metric, Report, Dashboard, BusinessObject, GlossaryTerm |
| Other | DesignPattern |

`Dashboard`, `DataLake`, and `GlossaryTerm` also exist in SAC with architecture/runtime meaning. Orchestration graphs (`Workflow`) and walk-loop agents (`AgentNode`) belong to AGER — DEKC records jobs as `IngestionJob` / `Transformation`.

Standard concept schemas: [`schemas/okf-concepts/`](./schemas/okf-concepts/). Registry: [`schemas/README.md`](./schemas/README.md).

## Second brain (core goal)

DEKC is a **schema-typed OKF second brain** for data engineering work. Capture platform truth once; reuse it when you:

| Intent | Command |
|--------|---------|
| **Design a report** | `python3 scripts/dekc_brain.py "executive revenue" --intent design-report` |
| **Land new data** | `python3 scripts/dekc_brain.py "orders stream" --intent land-data` |
| **Design a metric** | `python3 scripts/dekc_brain.py "GMV" --intent design-metric` |
| **Impact analysis** | `python3 scripts/dekc_brain.py "gold order_daily" --intent impact` |

Standard concept schemas: [`schemas/okf-concepts/`](./schemas/okf-concepts/) (Table, SourceSystem, Metric, Dashboard, BusinessObject, …). Registry: [`schemas/README.md`](./schemas/README.md).

```bash
python3 scripts/dekc_schemas.py list
python3 scripts/dekc_schemas.py validate --bundle sample-knowledge
python3 scripts/dekc_index.py --bundle sample-knowledge build   # refresh search index
```


## Diagrams, wireframes & platform concepts

Capture **Mermaid** and **PlantUML** listings inside OKF Markdown for:

- Report/dashboard **wireframes** (PlantUML salt)
- **Architecture**, **component**, **activity**, **state**, **class**, **ERD**, **sequence** diagrams (jobs, lakes, models)

```bash
python3 scripts/dekc_diagram.py wireframe --name "Exec UI" --subject /dashboards/executive-revenue.md
python3 scripts/dekc_diagram.py job-pack --workflow /workflows/daily-medallion-orders.md
python3 scripts/dekc_diagram.py capture --name "Orders ERD" --kind erd --language mermaid --subject /tables/gold-order-daily.md
```

First-class platform types: **DataLake**, **DataMart**, **DataCatalog**, **DataDomain**, **DataProduct**, **Stream**, **StorageLocation**, **DQRule**, **IngestionJob**.

```bash
python3 scripts/dekc_platform.py lake --name "Retail Lake" --platform fabric-onelake
python3 scripts/dekc_platform.py catalog --name "Workspace Catalog" --engine unity
python3 scripts/dekc_platform.py dq-rule --name freshness --target gold-order-daily --rule-type freshness
python3 scripts/dekc_platform.py ingestion --name orders-stream-landing --mode streaming \
  --streams orders-events --lands-as bronze-orders-raw
python3 scripts/dekc_diagram.py ingestion-pack --job /ingestion/orders-stream-landing.md
```


See [docs/diagrams.md](./docs/diagrams.md).


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

## Agent loop (AGER-shaped): producers + adversarial judges

**Orchestrators:** `data-lake-walker` (default) · `reverse-engineering-orchestrator` (Fabric/AWS/GCP).

Producer workers fan out, then **adversarial skeptics grade reverse engineering with rubrics** before index/pack. Lead judge: **re-adversary-judge** (threshold **0.75**). Fail → re-plan or **retract** unproven claims — never invent edges to pass.

```text
Trigger → Orchestrator (LoopPolicy: goal · max_turns · no_progress)
              │ FanOut producers
              ├─ schema-scout · lineage-tracer · stream-job-scout
              ├─ report-cataloger · semantic-mapper
              │ FanOut adversaries (rubrics)
              ├─ lineage-skeptic · business-skeptic
              ├─ stream-job-skeptic · coverage-skeptic · layer-auditor
              ▼
         re-adversary-judge  → reverse-engineering-rubric.md
              │ pass? ──no──► revise / retract
              ▼ yes
         index + pack (Synthesizer) + judgment receipt
```

| Rubric | Path | Threshold |
|--------|------|-----------|
| Reverse engineering (aggregate) | [evaluation/reverse-engineering-rubric.md](./evaluation/reverse-engineering-rubric.md) | 0.75 |
| Lineage integrity | [evaluation/lineage-integrity-rubric.md](./evaluation/lineage-integrity-rubric.md) | 0.80 |
| Business fidelity | [evaluation/business-fidelity-rubric.md](./evaluation/business-fidelity-rubric.md) | 0.72 |
| Stream & job landing | [evaluation/stream-job-landing-rubric.md](./evaluation/stream-job-landing-rubric.md) | 0.70 |

Automated baseline: `python3 scripts/dekc_grade.py --bundle knowledge` (skill `/dekc-grade`). Full cloud RE playbooks: [design doc](./docs/designs/current_design_doc.md).

## Sample knowledge

[`sample-knowledge/`](./sample-knowledge/) — retail commerce medallion:

**bronze.orders_raw → silver.orders → gold.order_daily** + LTV view, DAX measure, semantic model, executive dashboard, business objects, glossary (GMV).

```bash
python3 tests/test_dekc.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_doctor.py --bundle sample-knowledge
```

## Second-brain index

> **Do not commit the index.** It is fully derived and rebuilds in seconds;
> `search.json` alone runs to megabytes and would churn every diff. Add this to
> your `.gitignore` (a copy ships at `templates/gitignore-fragment`):
>
> ```gitignore
> **/.index/
> ```
>
> `**/.index/` rather than `*/.index/`, so it holds at any nesting depth and for
> every bundle rather than one hardcoded name. A repo with two bundles is where
> the narrower pattern shows: ignoring `knowledge/.index/` leaves the second
> bundle's index sitting in `git status`.


`dekc_index.py build` writes:

```text
<bundle>/.index/
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
