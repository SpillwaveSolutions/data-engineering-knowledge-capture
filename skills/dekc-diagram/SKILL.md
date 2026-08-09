---
name: dekc-diagram
description: Capture Mermaid or PlantUML diagrams (architecture, component, activity, state, class, ERD, sequence) and PlantUML wireframes for reports/dashboards into the DEKC second brain.
---

# DEKC diagrams & wireframes

All diagrams are OKF Markdown concepts with fenced code:

- ` ```mermaid ` … ` ``` `
- ` ```plantuml ` … ` ``` `

## Wireframe a report/dashboard (PlantUML salt)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" wireframe \
  --name "Exec Revenue Wireframe" \
  --subject /dashboards/executive-revenue.md \
  --language plantuml \
  --repo . --bundle knowledge
```

Or Mermaid layout sketch: `--language mermaid`.

## Architecture / ERD / job diagrams

```bash
# Architecture for a lake
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" capture \
  --name "Commerce lake arch" --kind architecture --language mermaid \
  --subject /lakes/retail-commerce-lake.md --repo . --bundle knowledge

# ERD
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" capture \
  --name "Orders ERD" --kind erd --language mermaid \
  --subject /tables/gold-order-daily.md --repo . --bundle knowledge

# Job pack: activity + state + class + component
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" job-pack \
  --workflow /workflows/daily-medallion-orders.md --language mermaid \
  --repo . --bundle knowledge
```

## Kinds

`wireframe` · `architecture` · `component` · `activity` · `state` · `class` · `erd` · `sequence` · `deployment` · `flowchart` · `c4`

## Custom code

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" capture \
  --name "Custom" --kind sequence --language plantuml \
  --code-file ./seq.puml --subject /workflows/foo.md --no-template
```

List templates: `dekc_diagram.py templates` / `templates --show erd mermaid`.

Prefer linking `--subject` to real concept paths. Never invent lineage in diagrams that the graph does not support—diagrams **document** design intent.
