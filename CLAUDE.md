# CLAUDE.md

Guidance for Claude Code (and Grok Build) when working in this repository.

## What this is

**DEKC** is a *plugin*, not only an app. It ships skills, slash commands, agents, hooks, and Python scripts that capture data-platform knowledge into an OKF graph. A TanStack explorer demo visualizes `sample-knowledge/`.

Depends on **PKC** + **OKF**. Dual/quad host: Claude, Grok, Codex, OpenCode — see PORTS.md.

## Commands

```bash
python3 tests/test_dekc.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_doctor.py --bundle sample-knowledge
npm run dev          # explorer on :8080
npm run typecheck
npm run build
```

Add new `scripts/dekc_*.py` to `package.json` typecheck/test lists and CI.

## Layout

- `skills/`, `commands/`, `agents/`, `hooks/`, `scripts/`
- `.claude-plugin/`, `.grok-plugin/`, `.codex-plugin/`, `.opencode/`
- `sample-knowledge/` — retail medallion demo
- `src/` — explorer UI (optional surface for demos)

## Conventions

- OKF frontmatter required: `type`, `title`, `description`, `timestamp`
- Absolute in-bundle links; typed `links[].rel` for lineage/business edges
- Never invent edges; prefer scripts over freehand Markdown when possible
- Reverse engineering: orchestrators + adversarial skeptics/rubrics (`dekc_grade.py`, re-adversary-judge); no success without pass

## Docs

- User guide: `docs/user_guide/user-guide.md`
- Design (AGER loops + Fabric/AWS/GCP + streams/jobs): `docs/designs/current_design_doc.md`
- AGER: https://github.com/SpillwaveSolutions/okf-agent-graph

