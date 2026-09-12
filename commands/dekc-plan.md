---
name: dekc-plan
description: Breadth-first RE plan. Map scan roots, rank areas, emit checklists. Pause before specialist fan-out.
---

Run the **dekc-plan** skill.

User request: `$ARGUMENTS`

Follow `${CLAUDE_PLUGIN_ROOT}/skills/dekc-plan/SKILL.md` completely. Prefer `scripts/dekc_plan.py` / `dekc_orchestrate.py --plan-only`. Do not spawn specialists the plan did not list. Do not run query-time retrieve.
