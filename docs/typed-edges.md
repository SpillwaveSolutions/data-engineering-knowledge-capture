# DEKC Typed Edges

Markdown body links remain universal. Frontmatter `links[].rel` enriches them for packs and lineage.

## Data-flow

| rel | Direction | Meaning |
|-----|-----------|---------|
| `sourced_from` | Table → SourceSystem | Physical origin |
| `layered_as` | Table/View → Layer | Medallion zone |
| `lands_as` | Source → Table | Landing mapping |
| `feeds` | Upstream → Downstream | Data flows forward |
| `transforms_to` | Input → Output | Transformation result |
| `promotes_to` | Lower layer asset → Higher | Medallion promotion |
| `reads_from` | Query/View/Xform → Table | Read dependency |
| `writes_to` | Xform/Workflow → Table | Write target |
| `queries` | Query → Table | Query references |
| `defines` | Schema → Table / Column → Table | Structural |
| `contains` | Parent → Child | Ownership of members |

## Business / semantic

| rel | Direction | Meaning |
|-----|-----------|---------|
| `derived_from` | BusinessObject → Table/View | Technical source |
| `businessizes` | Table → BusinessObject | Inverse for packs |
| `glosses` | GlossaryTerm ↔ BusinessObject | Definition link |
| `models` | SemanticModel → Table | Semantic binding |
| `measures` | Metric → BusinessObject | Metric measures entity |
| `visualizes` | Dashboard/Report → Metric/Table | BI consumption |
| `implements` | Sql/Dax artifact → Query | Code implements query |
| `implements_contract` | Table → DataContract | Contract conformance |

## Rules

1. Never invent edges.
2. Prefer absolute targets (`/tables/…`).
3. Keep a human Markdown link for the same target.
4. Direction is not symmetric — packs walk outbound edges.

## Diagrams & platform

| rel | Direction | Meaning |
|-----|-----------|---------|
| `documents` | Diagram → subject | Diagram documents asset/job |
| `documented_by` | Subject → Diagram | Inverse for packs |
| `wireframes` | Wireframe → Report/Dashboard | Layout design |
| `has_wireframe` | Report/Dashboard → Wireframe | Inverse |
| `part_of_lake` | Mart/Table → DataLake | Membership |
| `part_of_mart` | Table → DataMart | Membership |
| `cataloged_in` | Schema/Table → DataCatalog | Catalog registration |
| `belongs_to_domain` | Product/Mart → DataDomain | Domain ownership |
| `publishes` | DataProduct → Table/View | Product outputs |
| `stored_in` | Table → StorageLocation | Physical placement |
| `consumes_stream` | Job/Table → Stream | Stream input |
| `validates` / `quality_of` | DQRule → Table | Quality binding |
| `validated_by` | Table → DQRule | Inverse |
