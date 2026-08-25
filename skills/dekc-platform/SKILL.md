---
name: dekc-platform
description: Capture data lakes, data marts, data catalogs, domains, products, streams, storage locations, and data quality rules into the DEKC second brain.
---

# DEKC platform concepts

```bash
# Data lake — mermaid only includes layers you pass
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" lake \
  --name "Retail Commerce Lake" --platform fabric-onelake \
  --uri "abfss://..." --layers bronze silver gold --repo . --bundle knowledge

# Bronze-only lakehouse (no invented silver/gold promotion)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" lake \
  --name data_central_canal_lh --platform fabric-onelake --layers bronze
```

# Catalog (Glue / Unity / Purview / DataHub)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" catalog \
  --name "Workspace Catalog" --engine unity --repo . --bundle knowledge

# Domain + mart + product
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" domain --name Commerce --owner "AE"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" mart \
  --name "Revenue Mart" --domain Commerce --tables gold-order-daily
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" product \
  --name "Daily Revenue Product" --domain Commerce --outputs gold-order-daily

# Stream + storage + DQ
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" stream \
  --name orders-events --platform eventhubs --lands-as bronze-orders-raw
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" storage \
  --name bronze-orders --kind path --uri "s3://lake/bronze/orders" --layer bronze
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" dq-rule \
  --name freshness-gold --rule-type freshness --target gold-order-daily \
  --expression "max(order_date) >= current_date - 1"

Then attach diagrams with `dekc-diagram` / `dekc_diagram.py`.

## Ingestion jobs

Layer `writes_to` is emitted **only** when `--lands-as` is set. A semantic refresh is not a gold-layer writer.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" ingestion \
  --name "orders-stream-landing" \
  --mode streaming --pattern stream-to-bronze \
  --streams orders-events --lands-as bronze-orders-raw \
  --storage bronze-orders-prefix --target-layer bronze

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" ingestion \
  --name data_central_wh_semantic_model_refresh \
  --mode batch --orchestrator fabric-pipeline \
  --refreshes enterprise-data-model-prod

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" ingestion-pack \
  --job /ingestion/orders-stream-landing.md
```

Modes: batch | microbatch | streaming | cdc | full_load | incremental | file_drop | api_pull

Silver→gold is `dekc_capture.py transformation`, not this command. `workflow` was removed in 0.4.0.
