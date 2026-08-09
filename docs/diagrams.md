---
doc_type: guide
title: Diagrams and wireframes in DEKC
slug: diagrams
wiki_key: guide/diagrams
truth_state: current
---

# Diagrams & wireframes

DEKC stores design visuals as **OKF concepts** whose Markdown bodies contain fenced **Mermaid** or **PlantUML** listings. Renderers (GitHub, IDE plugins, wiki) display them; the second brain indexes titles, subjects, and kinds for retrieval.

## Concept types

| Type | Catalog | Use |
|------|---------|-----|
| **Wireframe** | `wireframes/` | Report/dashboard layout (PlantUML salt preferred) |
| **Diagram** | `diagrams/` | Architecture, component, activity, state, class, ERD, sequence, deployment, C4 |

Frontmatter:

```yaml
type: Diagram   # or Wireframe
diagram_kind: architecture
language: mermaid   # or plantuml
subjects:
  - /lakes/retail-commerce-lake.md
links:
  - target: /lakes/retail-commerce-lake.md
    rel: documents
```

## Supported kinds

| Kind | Typical language | Subject examples |
|------|------------------|------------------|
| `wireframe` | plantuml (salt) | Dashboard, Report |
| `architecture` | mermaid / plantuml | DataLake, platform |
| `component` | mermaid / plantuml | Workflow, system |
| `activity` | mermaid / plantuml | Job / pipeline flow |
| `state` | mermaid / plantuml | Job lifecycle |
| `class` | mermaid / plantuml | Job object model |
| `erd` | mermaid / plantuml | Tables / BO model |
| `sequence` | mermaid / plantuml | Landing interactions |
| `deployment` | mermaid | Cloud layout |
| `flowchart` / `c4` | mermaid | Generic |

## CLI

```bash
python3 scripts/dekc_diagram.py templates
python3 scripts/dekc_diagram.py wireframe --name "..." --subject /dashboards/x.md
python3 scripts/dekc_diagram.py capture --name "..." --kind erd --language mermaid --subject /tables/y.md
python3 scripts/dekc_diagram.py job-pack --workflow /workflows/z.md --language mermaid
python3 scripts/dekc_diagram.py report-pack --subject /dashboards/x.md
```

Custom source: `--code-file path.puml` or `--code "..."`.

## Platform concepts (related)

Capture with `scripts/dekc_platform.py`:

| Type | Catalog |
|------|---------|
| DataLake | `lakes/` |
| DataMart | `marts/` |
| DataCatalog | `catalogs/` |
| DataDomain | `domains/` |
| DataProduct | `products/` |
| Stream | `streams/` |
| StorageLocation | `storage/` |
| DQRule | `quality/` |

Attach architecture/ERD/activity diagrams to these subjects for a complete design record.

## Rules

1. Prefer linking `subjects` to existing concepts.  
2. Diagrams document intent; **lineage edges still require evidence**.  
3. Keep secrets out of diagram labels.  
4. One primary diagram kind per concept file (compose multiple files for a job pack).
