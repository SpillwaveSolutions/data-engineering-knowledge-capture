---
name: dekc-retrieve
description: Query-time DEKC retrieval. Spawn data-retriever; parent gets a summary card only. Use for Table, Metric, LineagePath, IngestionJob, Transformation, Dashboard, DataProduct, GlossaryTerm, BusinessObject questions.
---

# Retrieve (query-time)

The parent **must spawn `data-retriever`**. Do **not** run `dekc_search.py` or `dekc_pack.py` in the parent for retrieval. Search, score, pack, and deepen stay in the sub-agent so hit lists and pack markdown never contaminate the parent.

This is **not** reverse engineering. Do not spawn `data-lake-walker`, `lineage-tracer`, or other RE/capture agents for a question about existing knowledge.

## Spawn

Ask the host to run the `data-retriever` sub-agent with the user's question (and a seed path if the user already named one). The only thing you keep is the retrieval card:

```markdown
## Retrieval card
- Query: …
- Seed: `/path` (`Type`) — why chosen
- Fit: high|medium|low — one sentence
- Engine: index|rg|scan
- Pack: hops=N nodes=N tokens=N/budget
- Lead nodes: (5–8 bullets)
- Lineage note: (upstream/downstream one-liner) or none
- Open gaps: or none
- Next: stay|deepen-2hop|lineage|try-alt-seed `/other`
```

If `Next` is `deepen-2hop`, `lineage`, or `try-alt-seed /other`, spawn `data-retriever` again with that instruction. Do not unpack the graph yourself.

## Orthogonal fan-out

When the question also needs project decisions or system topology, spawn in parallel:

| Plane | Sub-agent |
|-------|-----------|
| Data platform (this pack) | **data-retriever** |
| Project / product knowledge | PKC **knowledge-retriever** |
| System architecture | SAC **architecture-retriever** |

Do not merge their packs into the parent. Each returns its own card.

## Not this skill

| Need | Use |
|------|-----|
| Walk / capture / reverse-engineer | `data-lake-walker` / `/dekc-walk` |
| Raw keyword search (developer) | `/dekc-search` — still not for parent Q&A |
| Full pack for a known seed (retriever internals) | `/dekc-context` |
| Intent checklists (`dekc_brain.py`) | `/dekc-second-brain` — do **not** dump those packs inline for Q&A |

See `agents/data-retriever.md`.
