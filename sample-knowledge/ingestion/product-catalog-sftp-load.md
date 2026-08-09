---
type: IngestionJob
title: product-catalog-sftp-load
description: Nightly full extract of product catalog from SFTP to bronze
ingestion_mode: file_drop
pattern: sftp-to-bronze
orchestrator: adf
schedule: "0 2 * * *"
connector: sftp-products
source_format: csv
target_format: delta
target_layer: bronze
idempotent: true
watermark_column: ""
checkpoint: ""
tags: [ingestion, job, file_drop, bronze, dekc]
timestamp: "2026-08-09T12:26:46Z"
status: active
verified: true
generated: true
wiki_key: ingest-product-catalog-sftp-load
truth_state: current
links:
- target: /layers/bronze.md
  rel: writes_to
- target: /layers/bronze.md
  rel: layered_as
- target: /sources/product-catalog-sftp.md
  rel: ingests_from
- target: /sources/product-catalog-sftp.md
  rel: reads_from
---

# product-catalog-sftp-load

Nightly full extract of product catalog from SFTP to bronze

**Mode:** `file_drop` · **Pattern:** `sftp-to-bronze` · **Target layer:** `bronze`

**Orchestrator:** adf
**Schedule:** `0 2 * * *`
**Connector:** sftp-products
**Formats:** csv → delta
**Idempotent:** True

## Sources

- Source: /sources/product-catalog-sftp.md

## Steps

1. List SFTP files
2. Copy to landing
3. Register bronze table

## Ingestion flow

```mermaid
flowchart LR
  SRC[Source / Stream] --> JOB[Ingestion Job]
  JOB --> LAND[bronze landing]
  JOB --> DQ[Optional DQ]
```
