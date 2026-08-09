---
type: Wireframe
title: Executive Revenue Wireframe
description: PlantUML salt wireframe for exec revenue dashboard
diagram_kind: wireframe
language: plantuml
tags: [diagram, wireframe, plantuml, dekc, wireframe]
timestamp: "2026-08-09T12:22:18Z"
status: active
verified: true
generated: true
wiki_key: wireframe-wireframe-executive-revenue-wireframe
truth_state: current
subjects: [/dashboards/executive-revenue.md]
links:
- target: /dashboards/executive-revenue.md
  rel: wireframes
---

# Executive Revenue Wireframe

**Kind:** `wireframe` · **Language:** `plantuml`

PlantUML salt wireframe for exec revenue dashboard

## Subjects

- [executive-revenue](/dashboards/executive-revenue.md)

## Diagram

```plantuml
@startuml
!include <salt/all>
salt
{{+
  {T
    Executive Revenue Dashboard | [Refresh] | [Export]
  }
  {
    Period: ^Last 30 days^ | Currency: ^All^
  }
  {
    {^GMV^
    $1.2M
    }
    |
    {^Orders^
    8,420
    }
    |
    {^AOV^
    $142
    }
  }
  {
    Revenue by day
    ^chart area^
  }
  {
    Top products
    ^table^
  }
}}
@enduml
```

## Notes

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
