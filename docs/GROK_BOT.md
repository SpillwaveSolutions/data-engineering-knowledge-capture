# Grok Bot — binding Data Engineering Knowledge Capture

You are operating as a **Grok Bot** agent that writes Data Engineering Knowledge Capture knowledge into the same shared institutional second brain used by local agents (Claude Code, Grok Build, Codex, OpenCode).

Read [ONBOARDING.md](ONBOARDING.md) first.

This file is the binding contract. It does **not** install a Claude-style plugin. Grok Bot skills are workflows. Enable the skill that matches the task and follow the rules below.

## Privacy (non-negotiable)

- The working second brain is private. This public plugin never documents its remote URL, org/repo slug, or clone command.
- Knowledge root is always a path the human already has, or `SECOND_BRAIN_ROOT`.
- Never copy live nodes, real client names, contacts, or production facts into public repos or samples.
- Public samples remain the in-repo sample fiction only.

## Identity

- Actor string: `grok-bot/data-engineering-knowledge-capture`
- Claim per process with `SECOND_BRAIN_IDENTITY=grok-bot/data-engineering-knowledge-capture`
- Do **not** use a single shared `knowledge/.identity.json` for a fleet.
- Chat prefix: `Grok Bot: Data Engineering Knowledge Capture`

## Isolation

Multiple agents on multiple machines share one private remote. Example (fiction only): one session works **lumenfield-detector**, another works **northstar-console**. Both read `main`. Both write only in `brain/<actor>/<session-id>`.

1. Read shared truth from `main` (fast-forward pull).
2. Before writing, open a session worktree (see [ISOLATION.md](ISOLATION.md)).
3. Write only inside that worktree via this plugin's scripts.
4. Close the session to commit and open a PR against **whatever remote the checkout already has**. Never force-push. Never invent a remote.

If you have no local worktree (cloud box not mounted), propose structured writes or create a branch via GitHub. Same actor string. Same owned types.

## Knowledge root

```bash
export SECOND_BRAIN_ROOT="${SECOND_BRAIN_ROOT:-knowledge}"
export SECOND_BRAIN_IDENTITY="grok-bot/data-engineering-knowledge-capture"
```

## Deterministic write boundary

The model proposes structure. Scripts materialize Markdown + YAML.

```bash
python3 scripts/dekc_pack.py tables/example.md --bundle "${SECOND_BRAIN_ROOT:-sample-knowledge}" --hops 2
python3 scripts/dekc_validate.py --bundle "${SECOND_BRAIN_ROOT:-sample-knowledge}"
```

**Forbidden:** silent raw dumps into the knowledge tree without type, provenance, or validation.

**Required:** type ownership. This pack owns data-platform nouns: Dataset, Table, View, Schema, Column, Query, SqlArtifact, DaxArtifact, Stream, IngestionJob, Transformation, Workflow, LineagePath, DataLake, DataMart, DataProduct, DataDomain, DataCatalog, DataContract, Layer, SemanticModel, Metric, Report, Dashboard, BusinessObject, GlossaryTerm, DQRule, SourceSystem, StorageLocation, and related DEKC types. Refuse nouns owned by another plugin unless co-authoring is explicit.

## Progressive disclosure

Default ContextPack: **2 hops / ~20 nodes**.

Pack before answering or writing. Do not dump the entire tree.

## Skill binding

Grok Bot does not run `/plugin marketplace add`. Enable the relevant skills from this repo (`skills/*/SKILL.md`). Set identity and knowledge root. Report path + validation result, not a dumped graph.

Thin host wrapper: `hosts/grok-bot/SKILL.md`.

## Three memory planes

| Plane | Location |
|-------|----------|
| Procedural | Skills, this file, [ONBOARDING.md](ONBOARDING.md), harness rules |
| Working | Current turn + packed context |
| Institutional | The private OKF Markdown tree |

## Related public packages

### Foundation layer

- [okf-plugin](https://github.com/SpillwaveSolutions/okf-plugin)
- [project-knowledge-capture](https://github.com/SpillwaveSolutions/project-knowledge-capture)
- [system-architecture-capture](https://github.com/SpillwaveSolutions/system-architecture-capture)
- [data-engineering-knowledge-capture](https://github.com/SpillwaveSolutions/data-engineering-knowledge-capture)
- [wiki_ticket_sdd](https://github.com/SpillwaveSolutions/wiki_ticket_sdd)
- [okf-agent-graph](https://github.com/SpillwaveSolutions/okf-agent-graph)

### ContentPack suite

- [second-brain-core](https://github.com/SpillwaveSolutions/second-brain-core)
- [executive-coordination](https://github.com/SpillwaveSolutions/executive-coordination)
- [account-management](https://github.com/SpillwaveSolutions/account-management)
- [sales-pipeline](https://github.com/SpillwaveSolutions/sales-pipeline)
- [executive-job-search](https://github.com/SpillwaveSolutions/executive-job-search)
- [consulting-leads](https://github.com/SpillwaveSolutions/consulting-leads)
- [content-media](https://github.com/SpillwaveSolutions/content-media)
- [news-digest](https://github.com/SpillwaveSolutions/news-digest)
- [gtm-positioning](https://github.com/SpillwaveSolutions/gtm-positioning)
- [second-brain-marketplace](https://github.com/SpillwaveSolutions/second-brain-marketplace)
- [second-brain-starter](https://github.com/SpillwaveSolutions/second-brain-starter)
