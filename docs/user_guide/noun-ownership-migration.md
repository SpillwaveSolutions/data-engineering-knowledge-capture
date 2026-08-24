---
doc_type: guide
slug: noun-ownership-migration
title: Noun-ownership migration (DEKC)
truth_state: current
---

# Noun-ownership migration (DEKC 0.4.0)

Family runbook: [okf-plugin noun-ownership migration](https://github.com/SpillwaveSolutions/okf-plugin/blob/main/docs/user_guide/noun-ownership-migration.md).

DEKC keeps the **data plane**. These types left this pack’s registry:

| Left DEKC | Lives in |
|-----------|----------|
| `AgentNode` | AGER |
| `Workflow` | AGER (multi-agent graph — **not** a Glue/ADF job) |
| `ContextPack`, `BaseConcept` | okf-plugin |
| `Diagram`, `Wireframe` | SAC |

`concepts` in `schemas/okf-concepts/registry.json` is 29 data-plane nouns. Intents no longer name `Workflow`, `Diagram`, or `Wireframe`.

This plugin’s `sample-knowledge/` still mixes AGER walk receipts and SAC diagrams **on purpose**: a mixed bundle when siblings are installed. Isolated `dekc_schemas.py validate` does not register those types.

## Upgrade

1. Install **okf-graph-eng v0.8.0**, **PKC v0.8.0** if you capture decisions/tickets, **AGER v0.7.0** if you keep walk receipts as `AgentNode`, **SAC v0.5.0** if you keep diagrams, then **DEKC v0.4.0**.
2. Inventory:

```bash
rg -n '^type:[[:space:]]*(Workflow|AgentNode|Diagram|Wireframe|ContextPack)' knowledge
```

3. Retype **data jobs** only (section below).
4. Validate:

```bash
python3 scripts/dekc_schemas.py validate --bundle knowledge
python3 path/to/okf-plugin/scripts/okf-graph.py validate knowledge --strict
```

## Retype: data `Workflow` → `IngestionJob`

Before 0.4.0, DEKC called orchestrated jobs `Workflow`. That string is now AGER’s multi-agent graph.

| Node meaning | New `type` |
|--------------|------------|
| Glue / ADF / Airflow / Fabric / Composer / Step Functions **job** | `IngestionJob` |
| Spark/SQL transform (already a transform) | keep `Transformation` |
| Multi-agent harness graph | keep `Workflow`, install AGER |

Procedure:

1. `rg -n '^type:[[:space:]]*Workflow' knowledge` — read each hit.
2. For a job, change only the frontmatter line `type: Workflow` → `type: IngestionJob`. Do not rewrite the body or break absolute links.
3. If a catalog `workflows/index.md` listed the file, either keep the path (mixed catalog) or move the file under `ingestion/` and fix links. Prefer **keep the path** for this cut; catalogs are indexes, not owners of the type.
4. Validate one file’s neighborhood with `dekc_brain.py` / `okf-graph.py pack` before batching.

Do **not** `sed` every Workflow in a monorepo that also contains AGER graphs.

## Mixed types you may keep

| `type` | Keep if | Requires |
|--------|---------|----------|
| `AgentNode` walk receipt (`agents/walk-*.md`) | You still want a harness node for the walk | AGER |
| `Diagram` / `Wireframe` | Visual artifacts for reports/lakes | SAC |
| `Dashboard` / `DataLake` / `GlossaryTerm` | Data-plane meaning | this plugin (SAC uses the same strings for topology — do not mix meanings) |

`DataCatalog` (this pack) is not okf-plugin `Catalog`. Folder `catalogs/` for `DataCatalog` is fine.

## Intents

`dekc_brain.py --intent` no longer loads `Workflow` / `Diagram` / `Wireframe`. Saved prompts that asked the agent to “author a Workflow for the nightly job” should say `IngestionJob` or `Transformation`.

## What not to do

- Do not copy `BaseConcept.schema.json` back into this repo.
- Do not author `ContextPack` as a DEKC type; generate packs with `dekc_pack.py` / okf-plugin `pack`.
- Do not treat isolated schema-validate failure on `type: Diagram` as a reason to delete the diagram. Install SAC or defer.

## Done when

- Data-pipeline `Workflow` nodes that are jobs are `IngestionJob`.
- `rg -n 'Workflow|Diagram|Wireframe' schemas/okf-concepts/registry.json` is empty (already true on v0.4.0).
- Mixed remaining types have their owning plugins installed, or are on an explicit defer list.
- `log.md` notes the 0.4.0 pin.
