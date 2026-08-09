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

## Mission

Turn data-platform reality into a durable OKF knowledge graph: walk lakes, capture technical assets, reconstruct lineage across medallion layers, and materialize **business objects + glossary** for LLM second brains.

**Depends on:** [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture) (PKC) and [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin) (OKF).

## Component map

- **Skills** — `skills/*/SKILL.md`
- **Commands** — `commands/*.md`
- **Agents** — `agents/*.md` (orchestrator + 5 subagents)
- **Hooks** — `hooks/hooks.json` / `hooks/codex-hooks.json` → `scripts/dekc-curate.sh`
- **Scripts** — `scripts/dekc_*.py`
- **Sample** — `sample-knowledge/`
- **Config** — `.dekc/config.example.yml`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (also set for Codex plugin hooks).

## Operating principles

1. OKF format only (frontmatter + body + absolute links + `links[].rel`).
2. Prefer deterministic scripts; agents extract structure from free text / SQL.
3. Idempotent writes; never invent lineage edges.
4. Direction matters: bronze `--feeds/transforms_to-->` silver `--feeds-->` gold; business objects `--derived_from-->` tables.
5. After walks: `dekc_index.py build` then `dekc_doctor.py`.
6. Progressive disclosure: 2-hop packs (~20 nodes).
7. Scrub secrets/PII on capture.

## Common commands

```bash
python3 scripts/dekc_common.py init-bundle --repo . --bundle knowledge
python3 scripts/dekc_walk.py <lake> --repo . --bundle knowledge
python3 scripts/dekc_lineage.py --repo . --bundle knowledge materialize
python3 scripts/dekc_business.py --repo . --bundle knowledge promote-layer --layer gold
python3 scripts/dekc_index.py --repo . --bundle knowledge build
python3 scripts/dekc_pack.py tables/<slug>.md --repo . --bundle knowledge --hops 2
python3 scripts/dekc_validate.py --bundle sample-knowledge
python3 tests/test_dekc.py
```

## Specialist routing

| User language | Agent / skill |
|---------------|---------------|
| walk the lake / inventory warehouse | data-lake-walker / dekc-walk |
| schema / columns / tables | schema-scout / dekc-capture-table |
| lineage / blast radius of a table | lineage-tracer / dekc-lineage |
| business meaning / glossary | semantic-mapper / dekc-business-object |
| dashboards / DAX / Power BI | report-cataloger / dekc-semantic |
| medallion health | layer-auditor / dekc-doctor |
| search the second brain | dekc-search / dekc-index |
