# CLAUDE.md

Guidance for Claude Code (and Grok Build) when working in this repository.

## What this is

**DEKC** is a *plugin*, not only an app. It ships skills, slash commands, agents, hooks, and Python scripts that capture data-platform knowledge into an OKF graph. A TanStack explorer demo visualizes `sample-knowledge/`.

Depends on **PKC** + **OKF**. Dual/quad host: Claude, Grok, Codex, OpenCode — see PORTS.md.

## Commands

```bash
python3 tests/test_dekc.py
python3 tests/test_retrieval_ladder.py
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 scripts/dekc_doctor.py --bundle sample-knowledge
npm run test
npm run dev          # explorer on :8080
npm run typecheck
npm run build
```

Add new `scripts/dekc_*.py` is covered the moment it lands: `npm run py:compile` and CI both `py_compile scripts/dekc_*.py`.

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
- Retrieval: Git + Markdown is truth. `knowledge/.dekc/index.sqlite` is a disposable SQLite/FTS5 accelerator (gitignored, mtime+size self-heal). Ripgrep is optional (`DEKC_RG_PATH`). Search and pack must keep working when rg or FTS5 is absent. Never install packages from a hook. See `docs/designs/retrieval-ladder.md`. Do not resurrect JSON `.index/`.

## Docs

- User guide: `docs/user_guide/user-guide.md`
- Design (AGER loops + Fabric/AWS/GCP + streams/jobs): `docs/designs/current_design_doc.md`
- AGER: https://github.com/SpillwaveSolutions/okf-agent-graph

<!-- worklog:policy:start -->
## WikiTicket SDD (worklog)

This plugin tracks implementation with [WikiTicket SDD](https://github.com/SpillwaveSolutions/wiki_ticket_sdd).

- Install the `worklog` plugin from `SpillwaveSolutions/wiki_ticket_sdd` (Claude Code, Grok Build, Codex, Cursor).
- Config lives in `.work/config.yml`. Event log is `.work/todo.jsonl`.
- Every plan MUST end by running `worklog plan-capture`.
- Work discovered mid-flight: `worklog add --unplanned --discovered-during <item>` BEFORE doing the work.
- Never hand-edit `.work/*.jsonl` (use `worklog`) or `docs/roadmap.md` (generated).
- After changing work items, run `worklog roadmap-render` and commit the log and roadmap together.
- CLI: `worklog` on PATH, or `python3 <wiki_ticket_sdd>/bin/worklog`.
<!-- worklog:policy:end -->

