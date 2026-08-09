---
doc_type: guide
title: DEKC User Guide
slug: user-guide
wiki_key: guide/user-guide
truth_state: current
---

# DEKC user guide

**Data Engineering Knowledge Capture** turns data platforms into a durable, Git-native [OKF](https://github.com/SpillwaveSolutions/okf-plugin) knowledge graph, with multi-agent walk loops designed using [AGER](https://github.com/SpillwaveSolutions/okf-agent-graph) (OKF Agent Graph Engineering Runtime).

Plugin release **0.1.0**. Storage format is OKF **0.2**. Agent loops follow AGER **0.3** roles (orchestrator / worker / judge / synthesizer) even when you run DEKC skills without a separate AGER bundle.

## Who this is for

- Analytics / platform engineers reverse-engineering a lakehouse
- Agents that must answer “what is this table?” with business meaning
- Teams that already use PKC for decisions and want the same graph for data

## Prerequisites

| Dependency | Why |
|------------|-----|
| [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin) (`okf-graph-eng`) | Validate links, impact, packs, visualization |
| [okf-agent-graph](https://github.com/SpillwaveSolutions/okf-agent-graph) (recommended) | Author explicit LoopPolicy / FanOut graphs for walks |
| [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture) (recommended) | Meetings, ADRs, features linked to data decisions |
| Python 3.10+ | Deterministic DEKC scripts (stdlib only) |

## Install

### Claude Code

```bash
claude plugin marketplace add SpillwaveSolutions/okf-plugin
claude plugin install okf-graph-eng@okf-plugin-marketplace

claude plugin marketplace add SpillwaveSolutions/okf-agent-graph
claude plugin install okf-agent-graph@okf-agent-graph-marketplace

claude plugin marketplace add SpillwaveSolutions/project-knowledge-capture
claude plugin install project-knowledge-capture@pkc-plugin-marketplace

claude plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
claude plugin install data-engineering-knowledge-capture@dekc-plugin-marketplace
```

Start a new session. DEKC exposes `/dekc-*` commands; AGER exposes `/ager-*`.

### Grok Build

Load the same Claude marketplaces — zero-config Claude plugin compatibility.

### Codex

```bash
codex plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
codex
# /plugins → install data-engineering-knowledge-capture
```

Skills are also invokable as `$dekc-init`, `$dekc-walk`, etc.

### OpenCode

Use skills under `skills/` plus `AGENTS.md`. Register permissions via `.opencode/opencode.json`.

## First 15 minutes

### 1. Scaffold a knowledge bundle

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_common.py" init-bundle \
  --repo . --bundle knowledge --title "Platform Knowledge"
```

Or invoke `/dekc-init`.

Creates catalogs (tables, layers, lineage, glossary, …), seeds bronze/silver/gold **Layer** concepts, and writes `index.md` + `log.md`.

Optional config:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/.dekc/config.example.yml" .dekc/config.yml
# edit knowledge_root, walk.max_files, promote.default_layer
```

### 2. Walk a filesystem export of your platform

Point the walker at SQL models, dbt, notebooks export, or a local mirror of lake paths:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" ./lake-mirror \
  --repo . --bundle knowledge --source-name retail-lake
```

Or `/dekc-walk` with path arguments. The walker:

1. Registers a **SourceSystem**
2. Discovers `*.sql`, `*.dax`, parquet directories, medallion folder names
3. Captures **Query** / **Table** / **View** concepts
4. Infers bronze→silver→gold **Transformation** promotions when basenames align
5. Writes an **AgentNode** walk receipt

### 3. Materialize lineage and business meaning

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_lineage.py" --repo . --bundle knowledge materialize
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_business.py" --repo . --bundle knowledge \
  promote-layer --layer gold
```

Promote a single asset:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_business.py" --repo . --bundle knowledge promote \
  tables/gold-order-daily.md \
  --name "Daily Order Summary" \
  --definition "Business-facing daily GMV and order volume by currency." \
  --owner "Analytics Engineering"
```

### 4. Index the second brain

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_index.py" --repo . --bundle knowledge build
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_search.py" "GMV" --repo . --bundle knowledge
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_doctor.py" --repo . --bundle knowledge
```

Index layout:

```text
knowledge/.index/
  inventory.json      # all concepts
  search.json         # inverted tokens
  graph.json          # lineage adjacency
  embeddings.jsonl    # local bag-of-tokens vectors
  manifest.json
```

### 5. Progressive disclosure packs

When an agent works on one table:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_pack.py" tables/gold-order-daily.md \
  --repo . --bundle knowledge --hops 2
# tiny pack for chat focus
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_pack.py" tables/gold-order-daily.md \
  --repo . --bundle knowledge --tiny
```

If `okf-graph-eng` is available, prefer its pack/impact for the same paths.

## Skills & commands

| Skill / command | Purpose |
|-----------------|---------|
| `dekc-init` | Scaffold knowledge catalogs + medallion layers |
| `dekc-walk` | Filesystem / SQL root discovery |
| `dekc-capture-table` | Manual table + columns |
| `dekc-capture-query` | SQL or DAX query |
| `dekc-lineage` | Graph, mermaid, materialize paths |
| `dekc-business-object` | Promote technical → business + glossary |
| `dekc-glossary` | Author glossary terms |
| `dekc-semantic` | Semantic models, metrics, dashboards |
| `dekc-context` | Context packs |
| `dekc-search` | Second-brain search |
| `dekc-index` | Rebuild index |
| `dekc-doctor` | Health: coverage, orphans, validation |

## Agents (how to invoke)

| Agent | Use when |
|-------|----------|
| **data-lake-walker** | Full reverse-engineer loop (orchestrator) |
| **schema-scout** | Only structure (schemas/tables/columns) |
| **lineage-tracer** | Only SQL/job lineage and promotions |
| **semantic-mapper** | Business objects, glossary, metrics |
| **report-cataloger** | Dashboards, reports, DAX |
| **layer-auditor** | Judge medallion health and orphans |

In Claude/Grok, ask for the agent by name or describe the walk (“walk this lake and promote gold tables”). In AGER terms, the walker is an **OrchestratorAgent**; scouts are **WorkerAgents**; the auditor is a **JudgeAgent**.

See the [design doc](../designs/current_design_doc.md) for the full loop graph, LoopPolicy, ScratchPad keys, and cloud playbooks.

## Capturing streams and jobs

Landing is not only batch SQL. Capture continuous and scheduled producers explicitly:

### Streams (landing)

```bash
# Conceptual capture today: source + transformation + table + lineage path
python3 scripts/dekc_capture.py --repo . --bundle knowledge source \
  --name "orders-eventhub" --kind stream \
  --uri "endpoints://eventhubs/.../orders" \
  --description "Commerce order events stream"

python3 scripts/dekc_capture.py --repo . --bundle knowledge table \
  --name orders_raw --layer bronze --schema bronze \
  --source orders-eventhub \
  --description "Landing table for order stream"

python3 scripts/dekc_capture.py --repo . --bundle knowledge lineage \
  --name stream-orders-landing \
  --nodes sources/orders-eventhub tables/bronze-orders-raw \
  --description "Stream lands as bronze table"
```

Typical stream sources by cloud:

| Cloud | Stream services | Lands as |
|-------|-----------------|----------|
| **Azure** | Event Hubs, IoT Hub, Fabric Eventstream | Bronze Lakehouse / Eventhouse tables |
| **AWS** | Kinesis Data Streams, MSK (Kafka), Firehose | S3 raw prefixes, Iceberg/Glue tables |
| **GCP** | Pub/Sub, Dataflow streaming | BigQuery landing, GCS raw, Bigtable |

### Jobs (batch & micro-batch)

```bash
python3 scripts/dekc_capture.py --repo . --bundle knowledge workflow \
  --name "nightly-silver-orders" --orchestrator airflow \
  --description "Promotes bronze.orders_raw → silver.orders" \
  --steps "Extract bronze" "Cleanse" "Write silver" "DQ checks"

python3 scripts/dekc_capture.py --repo . --bundle knowledge transformation \
  --name cleanse-orders --from-layer bronze --to-layer silver \
  --inputs bronze-orders-raw --outputs silver-orders \
  --description "Nightly cleanse job body"
```

| Cloud | Job / pipeline services |
|-------|-------------------------|
| **Azure** | Fabric Data Pipelines, Data Factory, Synapse pipelines, Fabric notebooks |
| **AWS** | Glue jobs, EMR, Step Functions, MWAA (Airflow), Lambda micro-batch |
| **GCP** | Dataflow batch, Cloud Composer, Dataproc, Cloud Scheduler + Functions |

Tag concepts with `tags: [stream]` or `tags: [job]` and link with `feeds` / `writes_to` / `triggered_by` (AGER Trigger when using an agent-graph bundle).

## Multi-cloud reverse engineering (practical recipes)

Full architecture and agent graph: [design doc § cloud reverse engineering](../designs/current_design_doc.md#4-reverse-engineering-cloud-platforms).

### Azure Fabric (typical)

1. Export or mirror: Lakehouse tables, Warehouse SQL, Pipelines JSON, Notebooks, Semantic models (`.bim` / Power BI), Eventstreams definitions.
2. `/dekc-walk` on the mirror root (prefer folders named `bronze`/`silver`/`gold` or `lh_*`).
3. Map **Eventstream / Event Hub** → SourceSystem `kind: stream` → bronze tables.
4. Map **Data Pipeline / Notebook jobs** → Workflow + Transformation.
5. Map **Semantic model + reports** → SemanticModel / Metric / Dashboard (DAX via `dekc-capture-query --dialect dax`).
6. Promote gold Lakehouse / Warehouse tables → business objects.

### AWS (typical)

1. Mirror: Glue Data Catalog export (or Athena DDL), S3 prefixes (`s3://bucket/bronze|silver|gold/`), Glue job scripts, MWAA DAGs, Kinesis/Firehose configs, QuickSight assets if available.
2. Walk SQL + job scripts; register S3/Glue as SourceSystem.
3. Firehose/Kinesis → bronze landing prefixes as stream lineage.
4. Glue/EMR/Step Functions → Workflow + Transformation edges.
5. Athena/Redshift views → View/Query; promote curated marts.

### GCP (typical)

1. Mirror: BigQuery dataset DDL, Dataform/dbt SQL, Dataflow templates, Pub/Sub topic configs, Composer DAGs, Looker/Looker Studio exports if present.
2. Walk SQL roots; register project.dataset as schemas.
3. Pub/Sub → Dataflow streaming → BQ landing as stream lineage.
4. Scheduled queries / Dataform assertions → Workflow + DQ-oriented Transformations.
5. Promote mart datasets (`*_mart`, gold) to business objects.

## Linking to PKC decisions

When a data design decision is made in a meeting:

1. Capture with PKC (`/pkc-capture-meeting` or `/pkc-capture-decision`).
2. Link the DecisionRecord to a DEKC table or business object:

```bash
python3 scripts/dekc_link.py decisions/use-delta-lake.md \
  /tables/silver-orders.md --rel decides --repo .
```

(If the decision lives in a PKC bundle, federate paths or colocate catalogs under one knowledge root.)

## Validation & doctor

```bash
python3 scripts/dekc_validate.py --bundle knowledge
python3 scripts/dekc_doctor.py --bundle knowledge --json
```

Doctor reports concept counts, lineage edge count, business coverage (tables→BO ratio), orphan technical assets, and whether the second-brain index exists.

When `okf-graph-eng` is installed:

```bash
python3 path/to/okf-plugin/scripts/okf-graph.py validate knowledge --strict
python3 path/to/okf-plugin/scripts/okf-graph.py impact knowledge tables/gold-order-daily.md
```

## Sample bundle

```bash
python3 tests/test_dekc.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_search.py revenue --repo . --bundle sample-knowledge
```

Explorer UI (this repo): `npm run dev` → open the live preview catalog tabs.

## CLI cheat sheet

| Script | Role |
|--------|------|
| `dekc_common.py init-bundle` | Scaffold |
| `dekc_walk.py <path>` | Discover |
| `dekc_capture.py <subcommand>` | source/table/view/query/lineage/… |
| `dekc_lineage.py` | graph / upstream / mermaid / materialize |
| `dekc_business.py` | promote / promote-layer |
| `dekc_index.py` | build / search |
| `dekc_pack.py` | context packs |
| `dekc_search.py` | full-text + index |
| `dekc_validate.py` / `dekc_doctor.py` | quality |
| `dekc_link.py` | typed edges |

Global flags (parent before subcommand): `--repo`, `--bundle`, often `--json`.

## Safety

- Capture scripts scrub common secrets and PII patterns.
- Never commit credentials; use AGER `SecretRef` patterns for runtime tools.
- Prefer readonly federation when linking remote knowledge roots.

## Next reading

- [Design doc — agent loops & multi-cloud](../designs/current_design_doc.md)
- [Typed edges](../typed-edges.md)
- [AGER user guide](https://github.com/SpillwaveSolutions/okf-agent-graph/blob/main/docs/user_guide/user-guide.md)
- [AGER specification](https://github.com/SpillwaveSolutions/okf-agent-graph/blob/main/docs/AGER_SPEC.md)
