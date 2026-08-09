# DEKC standard OKF schemas

This directory defines the **standard concept schemas** for the Data Engineering Knowledge Capture **second brain**.

Everything captured in a DEKC knowledge bundle (tables, lineage, streams, metrics, reports, glossary, …) is OKF Markdown whose YAML frontmatter should conform to one of these schemas.

| Path | Purpose |
|------|---------|
| [`okf-concepts/`](./okf-concepts/) | Per-type JSON Schema for concept frontmatter |
| [`okf-concepts/BaseConcept.schema.json`](./okf-concepts/BaseConcept.schema.json) | Shared required fields |
| [`okf-concepts/registry.json`](./okf-concepts/registry.json) | Catalog of types + design **intents** |

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
| `land-data` | SourceSystem, Workflow, Transformation, Table, Layer, DataContract, LineagePath |
| `design-metric` | Metric, BusinessObject, GlossaryTerm, Table, DaxArtifact, SemanticModel |
| `impact` | Table, View, Query, Transformation, Workflow, Dashboard, Report, BusinessObject |

## Authoring rule

1. Pick a type from the registry.  
2. Fill required BaseConcept fields: `type`, `title`, `description`, `timestamp`.  
3. Add type-specific fields (`layer`, `fqn`, `orchestrator`, …).  
4. Add typed `links[].rel` (see [docs/typed-edges.md](../docs/typed-edges.md)).  
5. Prefer capture scripts over freehand so frontmatter stays schema-aligned.


## Platform & diagram types (v0.2)

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
| Diagram | diagrams |
| Wireframe | wireframes |

Diagram bodies use fenced `mermaid` or `plantuml` code. See [docs/diagrams.md](../docs/diagrams.md).
