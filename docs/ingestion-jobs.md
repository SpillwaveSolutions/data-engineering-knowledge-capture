---
doc_type: guide
title: Data ingestion jobs in DEKC
slug: ingestion-jobs
wiki_key: guide/ingestion-jobs
truth_state: current
---

# Data ingestion jobs

**IngestionJob** is a first-class DEKC concept for **landing** data into the platform
(typically bronze). It is distinct from a multi-stage **Workflow** that transforms
across silver/gold.

## Catalog

`ingestion/` — type `IngestionJob`

## Fields

| Field | Meaning |
|-------|---------|
| `ingestion_mode` | batch, microbatch, streaming, cdc, full_load, incremental, file_drop, api_pull |
| `pattern` | e.g. stream-to-bronze, sftp-to-bronze, cdc-to-bronze |
| `orchestrator` | ADF, Fabric, Airflow, Glue, Dataflow, … |
| `connector` | Linked service / Airbyte / Fivetran connector name |
| `source_format` / `target_format` | json, csv, avro → delta, parquet |
| `target_layer` | Usually bronze |
| `watermark_column` / `checkpoint` | Incremental / streaming state |
| `sla_minutes` | Landing SLA |
| `idempotent` | Safe re-run |

## Capture

```bash
python3 scripts/dekc_platform.py ingestion \
  --name "orders-stream-landing" \
  --mode streaming --pattern stream-to-bronze \
  --orchestrator fabric-pipeline --connector eventhubs \
  --streams orders-events \
  --lands-as bronze-orders-raw \
  --storage bronze-orders-prefix \
  --target-layer bronze --sla-minutes 15

python3 scripts/dekc_platform.py ingestion \
  --name "product-catalog-sftp-load" \
  --mode file_drop --pattern sftp-to-bronze \
  --orchestrator adf --sources product-catalog-sftp \
  --schedule "0 2 * * *"
```

## Diagrams

```bash
python3 scripts/dekc_diagram.py ingestion-pack \
  --job /ingestion/orders-stream-landing.md --language mermaid
```

Produces sequence, activity, state, and component diagrams linked to the job.

## Related concepts

SourceSystem · Stream · StorageLocation · Table (bronze) · DQRule · Workflow (downstream transforms) · DataLake

## Second-brain intents

`land-data` and `design-job` retrieve IngestionJob concepts alongside streams and storage.
