---
name: dekc-diagram
description: Capture Mermaid/PlantUML diagrams and report wireframes
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" wireframe \
  --name "$ARGUMENTS" --subject <dashboard-or-report> --language plantuml

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" capture \
  --name "..." --kind architecture|component|activity|state|class|erd|sequence \
  --language mermaid|plantuml --subject <concept>
```
