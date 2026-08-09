---
name: dekc-platform
description: Capture data lakes, data marts, data catalogs, domains, products, streams, storage locations, and data quality rules into the DEKC second brain.
---

# DEKC platform concepts

```bash
# Data lake
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" lake \
  --name "Retail Commerce Lake" --platform fabric-onelake \
  --uri "abfss://..." --repo . --bundle knowledge

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
```

Then attach diagrams with `dekc-diagram` / `dekc_diagram.py`.

## Ingestion jobs

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" ingestion \
  --name "orders-stream-landing" \
  --mode streaming --pattern stream-to-bronze \
  --streams orders-events --lands-as bronze-orders-raw \
  --storage bronze-orders-prefix --target-layer bronze

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_diagram.py" ingestion-pack \
  --job /ingestion/orders-stream-landing.md
```

Modes: batch | microbatch | streaming | cdc | full_load | incremental | file_drop | api_pull
