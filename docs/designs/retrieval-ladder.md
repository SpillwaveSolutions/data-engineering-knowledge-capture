---
wiki_key: design/retrieval-ladder
doc_type: design
truth_state: current
---

# Retrieval ladder

Git + Markdown is the source of truth on every rung. Everything above Git is
a disposable accelerator you can delete and rebuild. Same philosophy as PKC
(`docs/designs/retrieval-ladder.md` there) and research-graph (`rg_project.py`:
"the index can be destroyed and rebuilt").

Each rung attacks a different cost, buys roughly an order of magnitude of
scale, and keeps the rung below it as a runtime fallback:

```
index present  →  use it
else rg on PATH  →  prefilter
else             →  pure Python scan
```

Three tiers, one behavior. `--no-rg` / `--no-index` force a lower rung.

0.4.x wrote JSON `knowledge/.index/` (inventory + inverted tokens) and
rebuilt the whole thing. That was a full scan plus a JSON parse, and it
got committed by accident. 0.5.0 replaced it with PKC's ladder: SQLite FTS5
at `knowledge/.dekc/index.sqlite`, gitignored, incremental, self-healing.

## Rung 1 — ripgrep prefilter (now)

**Cost it attacks:** reading and lowercasing files that cannot possibly match.

**Mechanics:** `find_rg()` / `rg_list_files()` in `dekc_common.py`. Search
AND-intersects `rg -l` per term, then runs the existing Python scorer
(`title×10 / description×5 / tags×4 / min(body,8)`) over only those
candidates. Pack inbound discovery is `rg -lF` of the concept path, then
the current file is always parsed for outbound typed-flow + SQL lineage
(the file almost never contains its own path). Override with `DEKC_RG_PATH`
/ `PKC_RG_PATH` / `OKF_RG_PATH`. Missing rg is not an error.

**Why scores stay identical:** rg only decides which files get read.
Over-selection is harmless (Python re-checks). It cannot under-select for
plain substring terms.

**Why it is first:** no state on disk, so no cache-staleness class of bugs.
Zero new dependencies. Claude Code / Grok hosts usually ship `rg`.

**Ceiling:** still an O(corpus) scan per query — compiled, parallel,
memory-mapped. It only accelerates "which files contain X." Parsed-graph
commands (validate, doctor orphans, mermaid via `build_graph`) still walk
the tree. The curate hook does not install rg and does not build the index.

| Hot path | Rung 1 helps? | Why |
|---|---|---|
| `dekc_search.py` | yes | candidate prefilter |
| `dekc_pack.py` inbound | yes | reverse index via literal path + self SQL |
| `dekc_validate.py` / `dekc-curate.sh` | **no** | must parse frontmatter + resolve links |
| orphans / doctor listings | **no** | need the parsed graph |
| mermaid (`build_graph`) | **no** | leftover full scan; accepted |

## Rung 2 — stdlib SQLite + FTS5 incremental index (now)

**Cost it attacks:** re-parsing files that have not changed since the last
invocation.

**Why SQLite:** `sqlite3` is in the stdlib. FTS5 is compiled into CPython
(doctor reports it). Honors the hard "no pip dependencies" rule. One file,
atomic transactions, concurrent readers, trivially deletable.

**Shape:**

| Table | Role |
|---|---|
| `meta(schema_version)` | drop-rebuild on mismatch |
| `nodes(path, type, title, description, status, tags, layer, mtime, size, fm_json, body, hay)` | concept cards |
| `edges(src, dst, rel, label, origin)` | typed flow + SQL lineage; `origin` is the file that authored the edge so incremental delete does not leak |
| `fts` (FTS5 over title / description / tags / body) | lexical retrieval (`--engine fts`) |

Path: `knowledge/.dekc/index.sqlite`. Gitignore `**/.dekc/index.sqlite*`.
Do not ignore the whole `.dekc/` directory — repo-level
`.dekc/config.example.yml` lives there. Never a hook install, never a pip
dep. `scripts/dekc_index.py` + `/dekc-index`.

**Incremental refresh is the whole trick.** On each invocation the reader
stats the tree, compares `mtime+size` against stored rows, re-parses only
what changed, deletes vanished files. Every reader does this sweep itself
rather than trusting `dekc-curate.sh` — that makes it self-healing against
hand edits, `git checkout`, branch switches, and a disabled hook. Cold
rebuild costs one full scan. Steady-state queries are 1–10 ms.

**Scoring identity.** FTS5 `bm25()` with column weights is *not* the same
function as `title.count×10`. Same pattern as rg:

- Default (`engine=index`): SQL LIKE on the stored haystack decides
  candidates. Existing Python scorer ranks, so `--no-index` stays
  score-identical.
- `--engine fts` exposes FTS5 MATCH with prefix tokens as an opt-in.

**Pack identity.** Lineage is undirected for every visited node (typed
`FORWARD_FLOW` / `REVERSE_FLOW` + SQL `sql_from`). Extra non-lineage
`links[]` are added on the focus only. Scores/graphs match a scan unless
`--engine fts`.

**Trigger.** Implemented. `DEKC_NO_INDEX=1` / `--no-index` disables it.
`DEKC_INDEX_PATH` overrides the sqlite location (tests).

## Rung 3 — okfcli (if ever)

The fast-native slot is already assigned by okf-plugin working rule #1:
prefer `okf` / `okfcli` when installed, else `python3`. A single static
binary (Rust/Go) with the Python scripts as the portable fallback. Do not
invent a second runtime (Ruby closed-won't-do, PKC #60).

## Runtime degradation (load this, do not skip it)

```
def retrieve(bundle, query):
    if index_ok(bundle):          # rung 2
        return from_index(bundle, query)
    if find_rg():                 # rung 1
        return from_rg(bundle, query)
    return from_scan(bundle, query)  # rung 0
```

Git remains the only durable store. Deleting `knowledge/.dekc/index.sqlite`
is always valid recovery.
