---
type: Diagram
title: Orders ERD
description: Logical ERD for commerce orders
diagram_kind: erd
language: mermaid
tags: [diagram, erd, mermaid, dekc]
timestamp: "2026-08-09T12:22:13Z"
status: active
verified: true
generated: true
wiki_key: diagram-erd-orders-erd
truth_state: current
subjects: [/tables/gold-order-daily.md]
links:
- target: /tables/gold-order-daily.md
  rel: documents
---

# Orders ERD

**Kind:** `erd` · **Language:** `mermaid`

Logical ERD for commerce orders

## Subjects

- [gold-order-daily](/tables/gold-order-daily.md)

## Diagram

```mermaid
erDiagram
  CUSTOMER ||--o{ ORDER : places
  ORDER ||--|{ ORDER_LINE : contains
  PRODUCT ||--o{ ORDER_LINE : "sold as"
  ORDER {
    string order_id PK
    string customer_id FK
    date order_ts
    number gross_amount
  }
  CUSTOMER {
    string customer_id PK
    string segment
  }
  PRODUCT {
    string product_id PK
    string name
  }
  ORDER_LINE {
    string order_id FK
    string product_id FK
    number qty
  }
```

## Notes

_Edit the fenced listing above; keep language tag as mermaid or plantuml._
