---
name: dekc-land-data
description: Use the DEKC second brain to plan landing new stream or batch data into bronze (and beyond) with sources, jobs, contracts, and lineage.
---

# Land new data (second brain)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_brain.py" "<source or domain>" \
  --intent land-data --repo . --bundle knowledge --write
```

Checklist (also in brain output):

1. **SourceSystem** — stream vs batch, URI/platform  
2. **Bronze table** — schema/columns when known  
3. **IngestionJob** — orchestrator that lands data (AGER owns `Workflow`)  
4. **Edges** — feeds / lands_as / writes_to (evidence only)  
5. **DataContract** — freshness/SLA if known  
6. Plan silver **Transformation** without inventing hops  

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge source \
  --name "..." --kind stream --uri "..." --description "..."
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_capture.py" --repo . --bundle knowledge table \
  --name "..." --layer bronze --description "Landing table"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" --repo . --bundle knowledge ingestion \
  --name "..." --orchestrator fabric-pipeline --lands-as bronze-... --target-layer bronze
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_index.py" --repo . --bundle knowledge build
```

Semantic model refresh is **not** bronze ingest:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_platform.py" ingestion \
  --name data_central_wh_semantic_model_refresh \
  --orchestrator fabric-pipeline --refreshes "GWII - Exec Dashboard"
```

Silver→gold promotions are `dekc_capture.py transformation`, not IngestionJob.

Reuse prior landings from the pack as patterns (same bronze conventions).
