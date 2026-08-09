# AGENTS.md — data-engineering-knowledge-capture

Agent-facing instructions for **Claude Code**, **Grok Build**, **Codex**, and **OpenCode**.

## Host compatibility

| Host | How this plugin loads |
|------|------------------------|
| **Claude Code** | Native plugin (`.claude-plugin/plugin.json`, skills, agents, hooks, commands) |
| **Grok Build** | Zero-config Claude plugin compatibility |
| **Codex** | `.codex-plugin/plugin.json` + skills + `hooks/codex-hooks.json` |
| **OpenCode** | Skills + policy via this file; `.opencode/plugin/dekc.json` registration |

One plugin tree, four hosts. Do not diverge packaging without updating [PORTS.md](./PORTS.md).

## Docs

- [User guide](./docs/user_guide/user-guide.md) — install, walks, streams/jobs, multi-cloud recipes
- [Design doc](./docs/designs/current_design_doc.md) — AGER agent loops, adversarial rubrics, Azure Fabric / AWS / GCP
- [Typed edges](./docs/typed-edges.md)
- [PORTS](./PORTS.md)
- [Evaluation rubrics](./evaluation/index.md)

Agent loops follow [okf-agent-graph (AGER)](https://github.com/SpillwaveSolutions/okf-agent-graph): **orchestrators**, producer workers, **adversarial skeptics with rubrics**, and a lead **re-adversary-judge**. Parallel workers **append** ScratchPad lists.

## Second brain

Goal: maintain a **standard OKF schema set** for data engineering concepts and an indexed second brain used when **designing reports**, **landing data**, **defining metrics**, and **impact analysis**.

```bash
python3 scripts/dekc_brain.py "<topic>" --intent design-report|land-data|design-metric|impact
python3 scripts/dekc_schemas.py validate --bundle knowledge
```

Schemas: `schemas/okf-concepts/`. Skills: `dekc-second-brain`, `dekc-design-report`, `dekc-land-data`.

## Mission

Turn data-platform reality into a durable OKF knowledge graph: walk lakes, capture technical assets, reconstruct lineage across medallion layers, materialize **business objects + glossary**, and **grade reverse engineering** before claiming done.

**Depends on:** [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture), [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin), preferably [okf-agent-graph](https://github.com/SpillwaveSolutions/okf-agent-graph).

## Component map

- **Skills** — `skills/*/SKILL.md` (includes `dekc-grade`)
- **Commands** — `commands/*.md`
- **Agents** — `agents/*.md` (orchestrators + producers + adversarial judges)
- **Evaluation** — `evaluation/*-rubric.md`
- **Hooks** — `hooks/hooks.json` / `hooks/codex-hooks.json` → `scripts/dekc-curate.sh`
- **Scripts** — `scripts/dekc_*.py` (includes `dekc_grade.py`)
- **Sample** — `sample-knowledge/`
- **Config** — `.dekc/config.example.yml`

Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## Operating principles

1. OKF format only (frontmatter + body + absolute links + `links[].rel`).
2. Prefer deterministic scripts; agents extract structure from free text / SQL.
3. Idempotent writes; never invent lineage edges.
4. Direction matters: bronze → silver → gold; business objects `derived_from` tables.
5. After walks: grade (`dekc_grade.py` + adversarial judges) then `dekc_index.py build` + `dekc_doctor.py`.
6. Progressive disclosure: 2-hop packs (~20 nodes).
7. Scrub secrets/PII on capture.
8. **No RE success without re-adversary-judge pass** (threshold 0.75) unless user waives.
9. On fail: capture missing evidence or **retract** unproven claims — never invent to raise scores.

## Orchestrators

| Agent | Role |
|-------|------|
| **data-lake-walker** | Default orchestrator: walk → produce → adversarial grade → index |
| **reverse-engineering-orchestrator** | Multi-cloud RE (Fabric/AWS/GCP), strict LoopPolicy + fan-out |

## Producer workers

| Agent | Role |
|-------|------|
| **schema-scout** | Schemas, tables, columns, contracts |
| **lineage-tracer** | SQL/job lineage edges |
| **stream-job-scout** | Streams + jobs landing data |
| **semantic-mapper** | Business objects, glossary, metrics |
| **report-cataloger** | Dashboards, reports, DAX |

## Adversarial subagents (rubric graders)

| Agent | Rubric | Threshold |
|-------|--------|-----------|
| **lineage-skeptic** | lineage-integrity | 0.80 |
| **business-skeptic** | business-fidelity | 0.72 |
| **stream-job-skeptic** | stream-job-landing | 0.70 |
| **coverage-skeptic** | structural / evidence slices | — |
| **layer-auditor** | doctor/validate health baseline | — |
| **re-adversary-judge** | reverse-engineering (aggregate) | **0.75** |

Hard fails: invented lineage, secrets in bodies, gold without BO when promotion claimed.

## Common commands

```bash
python3 scripts/dekc_common.py init-bundle --repo . --bundle knowledge
python3 scripts/dekc_walk.py <lake> --repo . --bundle knowledge
python3 scripts/dekc_lineage.py --repo . --bundle knowledge materialize
python3 scripts/dekc_business.py --repo . --bundle knowledge promote-layer --layer gold
python3 scripts/dekc_grade.py --repo . --bundle knowledge
python3 scripts/dekc_index.py --repo . --bundle knowledge build
python3 scripts/dekc_pack.py tables/<slug>.md --repo . --bundle knowledge --hops 2
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 tests/test_dekc.py
```

## Specialist routing

| User language | Agent / skill |
|---------------|---------------|
| walk the lake / inventory warehouse | data-lake-walker / dekc-walk |
| reverse engineer Fabric/AWS/GCP | reverse-engineering-orchestrator |
| schema / columns / tables | schema-scout / dekc-capture-table |
| lineage / blast radius | lineage-tracer / dekc-lineage |
| streams / jobs / landing | stream-job-scout |
| business meaning / glossary | semantic-mapper / dekc-business-object |
| dashboards / DAX | report-cataloger / dekc-semantic |
| grade / audit RE quality | re-adversary-judge / dekc-grade + skeptics |
| medallion health | layer-auditor / dekc-doctor |
| search the second brain | dekc-search / dekc-index |
| multi-agent loop authoring | okf-agent-graph `/ager-*` + DEKC KnowledgeBind |
