# Changelog

## 0.3.5

- WikiTicket SDD (worklog) is the tracking system for this plugin.


## 0.3.4

- Three-host hooks: Codex + Cursor-native when Claude hooks exist.


## 0.3.3 — 2026-08-17

- **Cursor host.** `.cursor-plugin/plugin.json` (Cursor Plugins) plus `.cursor/rules/second-brain.mdc`. Docs: `docs/CURSOR.md`. `docs/GROK_BOT.md` now covers Grok Bot spawning Cursor cloud agents.

Notable changes to **data-engineering-knowledge-capture**. Newest first.

## 0.3.2 — 2026-08-16

### Added

- ContextPack token budget matches second-brain-core 0.3.3 / PKC 0.7.2: default 1/4 of `SECOND_BRAIN_WINDOW_TOKENS` (128000 → 32000). Override with `--max-tokens` or `SECOND_BRAIN_PACK_MAX_TOKENS`.
- Pack is **fail-closed** when the rendered subgraph exceeds the budget. `--write` is skipped.
- Bodies off unless that node is the pack root. Neighbors keep title, type, path, and frontmatter `description` only.
- Node clip (`--max-nodes` / `--tiny`) is not a token budget.
- Implements part of [okf-plugin#55](https://github.com/SpillwaveSolutions/okf-plugin/issues/55).

## 0.3.1 — 2026-08-16

### Added

- Required identity on every knowledge write: `--author` or `SECOND_BRAIN_IDENTITY`.
- `write_knowledge()` stamps `author` and emits a `WriteEvent`. `write_concept` stays pure.
- Wired through capture, walk, platform, diagram, business, brain `--write`, pack `--write`, grade `--write`, and link.
- Fail-closed tests. Scan / pack / grade / brain print-only paths do not require identity.

## 0.3.0 — 2026-08-15

### Added

- **Multi-host bindings + write isolation.** Root Agent Plugins 1.0 `plugin.json`, Grok Bot / Deep Agents / isolation / onboarding docs, host wrappers, vendored `scripts/brain_session.py`, and `dekc-session` skill/command.
- Concurrent writers read `main` and write `brain/<actor>/<session-id>`. Close via PR against the checkout's existing remote.
- Isolation tests use fictional **lumenfield-detector** / **northstar-console** actors only.

## 0.2.1 — 2026-08-13

### Changed

- **Aligned BaseConcept with the shared okf-plugin envelope.** Required frontmatter
  is now `type` + `title` only (`description` and `timestamp` stay recommended).
  `dekc_validate.py` and every type schema were updated so a mixed second brain
  with PKC/SAC nodes that omit those fields still validates.
- **`truth_state` union.** Accepts PKC/SAC values (`snapshot`, `superseded`,
  `archived`) in addition to DEKC's `current | historical | proposed`.

## 0.2.0 — 2026-08-10


Six fixes, all found by running this plugin alongside `project-knowledge-capture`
and `system-architecture-capture` against a single shared bundle.

### Fixed

- **Frontmatter round-trip doubled backslash escaping.** The dumper escaped
  backslashes and quotes; the reader stripped only the surrounding quotes. Every
  write-modify-write cycle re-escaped already-escaped text, doubling the
  backslash count each pass. Worse here than in the sibling plugins, because both
  `write_concept` and `refresh_catalog_index` do a read-modify-write and the
  latter is driven by the curate hook — so ordinary editing compounded it. It was
  also self-concealing: reading back with the same parser returned a value that
  looked correct. (#3)

- **A bracketed concept title dropped the catalog edge.** `Fact [Sales]` rendered
  as `[Fact [Sales]](/tables/a.md)`, which the graph reader's link regex cannot
  match. That produces a *missing* edge rather than a broken one, and `validate`
  reports only broken edges — so the concept lost its catalog backlink silently.
  Note this half needs the matching reader change to take effect: backslash
  escaping does not rescue a reader whose label class is `[^\]]+`. (#2)

- **The `· <layer>` annotation broke shared bundles.** It fired for any concept
  with a `layer` key in any of the 32 catalogs, including the 8 that
  `system-architecture-capture` also declares — whose renderer emits a bare
  `- [label](path)`. So a shared catalog flipped on every alternation between
  plugins. Now scoped to catalogs only this plugin owns; all three plugins render
  a shared catalog byte-identically. (#4)

- **`refresh_catalog_index` accepted any catalog name.** It now refuses catalogs
  this plugin does not declare, so an outside caller cannot drive this renderer
  over a sibling's catalog. On its own this does *not* stabilise a shared
  bundle — for a catalog two plugins both declare it passes in both — which is
  why the annotation scoping above is the load-bearing change. (#4)

- **`resolve_knowledge_root` fell through to `sample-knowledge/` in silence.**
  When the configured root is not an initialized bundle, resolution probes other
  candidates. That is reasonable; not saying so was not. There are 16 call sites
  and only `dekc_doctor` announced the bundle it used — and this repo ships a
  `sample-knowledge/`, so a capture run inside a clone wrote there. (#5)

- **The curate hook refreshed all 32 catalogs on every edit.** Each refresh is a
  whole-file read-modify-write, so rapid edits raced by construction. Now scoped
  to the catalog containing the edited file. (#6)

- **`dekc_link --help` advertised eight relations, none of which produced a
  lineage edge.** The intersection of `DEFAULT_RELATIONS[:8]` with the set
  `build_graph` honours was empty, and `--rel` is unvalidated. Four relations the
  plugin itself emits and documents as flow — `lands_as`, `lands_into`,
  `visualizes`, `consumes_stream` — were also ignored, so packs built from them
  were incomplete. The honoured set is now named constants, those four are
  honoured, and the help names what actually works. `implements`/`documents`
  still produce no edge: `graph.json` is lineage adjacency by design. (#7)

### Added

- A `.gitignore` fragment at `templates/gitignore-fragment` and a README note,
  since nothing previously told users the derived `.index/` should not be
  committed. Uses `**/.index/`, which holds at any depth and for every bundle
  rather than one hardcoded name. (#8)

- `dekc_index` now explains a zero-edge lineage graph instead of writing a bare
  `0` that is indistinguishable from a failed build.

## 0.1.0

Initial release.
