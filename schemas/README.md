# DEKC standard OKF schemas

This directory defines the **standard concept schemas** for the Data Engineering Knowledge Capture **second brain**.

Everything captured in a DEKC knowledge bundle (tables, lineage, streams, metrics, reports, glossary, …) is OKF Markdown whose YAML frontmatter should conform to one of these schemas.

| Path | Purpose |
|------|---------|
| [`okf-concepts/`](./okf-concepts/) | Per-type JSON Schema for concept frontmatter |
| [`okf-concepts/registry.json`](./okf-concepts/registry.json) | Catalog of 29 DEKC types + design **intents** |

The OKF envelope (`BaseConcept`) and `Catalog` / `ContextPack` live in [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin). Do not fork them here.

## Nouns (this plugin)

BusinessObject, Column, DQRule, Dashboard, DataCatalog, DataContract, DataDomain, DataLake, DataMart, DataProduct, Dataset, DaxArtifact, DesignPattern, GlossaryTerm, IngestionJob, Layer, LineagePath, Metric, Query, Report, Schema, SemanticModel, SourceSystem, SqlArtifact, StorageLocation, Stream, Table, Transformation, View.

`AgentNode` / `Workflow` → AGER. `Diagram` / `Wireframe` → SAC.

## Why this exists

When you:

- **design a new report** → load metrics, gold tables, business objects, existing dashboards  
- **land new data** → load sources, bronze patterns, jobs/streams, contracts, similar landings  
- **define a metric** → load glossary, related BOs, DAX/SQL measures  

…agents and humans query the second brain with a typed schema vocabulary (not freeform notes).

## Validate

```bash
# List registry
python3 scripts/dekc_schemas.py list

# Validate all concepts in a bundle against type schemas
python3 scripts/dekc_schemas.py validate --bundle sample-knowledge

# Second-brain intent pack
python3 scripts/dekc_brain.py "executive revenue" --intent design-report --bundle sample-knowledge
python3 scripts/dekc_brain.py "orders stream landing" --intent land-data --bundle sample-knowledge
```

## Intents → types

From `registry.json`:

| Intent | Prefer concept types |
|--------|----------------------|
| `design-report` | Dashboard, Report, Metric, SemanticModel, BusinessObject, GlossaryTerm, Table, View |
| `land-data` | SourceSystem, IngestionJob, Transformation, Table, Layer, DataContract, LineagePath |
| `design-metric` | Metric, BusinessObject, GlossaryTerm, Table, DaxArtifact, SemanticModel |
| `impact` | Table, View, Query, Transformation, IngestionJob, Dashboard, Report, BusinessObject |

## Authoring rule

1. Pick a type from the registry.  
2. Fill required BaseConcept fields: `type`, `title`. `description` and `timestamp` are recommended.  
3. Add type-specific fields (`layer`, `fqn`, `orchestrator`, …).  
4. Add typed `links[].rel` (see [docs/typed-edges.md](../docs/typed-edges.md)).  
5. Prefer capture scripts over freehand so frontmatter stays schema-aligned.

## Platform types

| Type | Catalog |
|------|---------|
| DataLake | lakes |
| DataMart | marts |
| DataCatalog | catalogs |
| DataDomain | domains |
| DataProduct | products |
| Stream | streams |
| StorageLocation | storage |
| DQRule | quality |
| IngestionJob | ingestion |

Diagrams/wireframes are SAC nouns. DEKC sample knowledge may still *link* to them; it does not own the types.
