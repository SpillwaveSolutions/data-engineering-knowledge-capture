---
type: Workflow
title: daily-medallion-orders
description: Nightly bronze→silver→gold orders pipeline
orchestrator: airflow
tags: [workflow, airflow, dekc]
timestamp: "2026-08-09T10:28:09Z"
status: active
verified: true
generated: true
wiki_key: workflow-daily-medallion-orders
truth_state: current
links:
- target: /diagrams/activity-daily-medallion-orders-activity.md
  rel: documented_by
- target: /diagrams/state-daily-medallion-orders-state.md
  rel: documented_by
- target: /diagrams/class-daily-medallion-orders-class.md
  rel: documented_by
- target: /diagrams/component-daily-medallion-orders-component.md
  rel: documented_by
---

# daily-medallion-orders

Orchestrator: **airflow**

Nightly bronze→silver→gold orders pipeline

## Steps

1. Land commerce API to bronze.orders_raw
2. Cleanse to silver.orders
3. Aggregate gold.order_daily
4. Refresh Power BI semantic model
