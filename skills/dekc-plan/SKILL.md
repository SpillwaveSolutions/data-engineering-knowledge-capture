---
name: dekc-plan
description: Breadth-first reverse-engineering plan — map scan roots and optional exports, rank focus areas, emit deep-dive checklists. Pause here before spawning specialists. Not query-time retrieve.
---

# DEKC Plan

Cheap, deterministic map of what is *present* in each `--scan-root` (plus optional Fabric / PBI / inventory `--export`). Presence and counts only — not a full walk and not `data-retriever`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_plan.py" \
  --repo . --system "$SYSTEM_NAME" --scan-root "$MIRROR" \
  --export workspace-items.json --write --json

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_orchestrate.py" \
  --repo . --system "$SYSTEM_NAME" --scan-root "$MIRROR" --plan-only --json

# Same flags on walk
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_walk.py" "$MIRROR" \
  --repo . --bundle knowledge --plan-only --system "$SYSTEM_NAME"
```

Writes `knowledge/.dekc/re-plan.md` + `.json` (+ progress) with ranked areas, **signal-gated** orchestration/ELT specialists, unchecked checklists, suggested sub-agents. Do **not** spawn a specialist the plan did not list (no Airflow scout without DAG markers).

Mark progress after an area walker finishes an item:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_plan.py" mark \
  --plan knowledge/.dekc/re-plan.json --area lake --item capture --status done
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_plan.py" mark \
  --plan knowledge/.dekc/re-plan.json --area orch-airflow --item inventory --status done
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dekc_plan.py" mark \
  --plan knowledge/.dekc/re-plan.json --area dq --item capture --status blocked \
  --note "GE suite present; runtime not executed"
```

Then fan out with `reverse-engineering-orchestrator` / `--from-plan --area <id>`. After producers: existing adversarial skeptics → `re-adversary-judge`.

DEKC owns data orchestration + ELT/ETL. SAC owns CI/CD. If Actions only trigger Glue/dbt, cross-link — do not steal Pipeline nouns.
