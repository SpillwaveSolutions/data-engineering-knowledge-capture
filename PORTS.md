# Harness ports — DEKC

Shared package is canonical; each host has a small native manifest where required.

## Support matrix

| Harness | Status | What you get |
|---|---|---|
| Claude Code | Canonical | Full: skills, `/dekc-*` commands, agents, PostToolUse curation hook |
| Grok Build | Zero-config Claude compatibility | Same as Claude Code (marketplaces, skills, agents, hooks, CLAUDE.md/AGENTS.md) |
| Codex | Native plugin | `.codex-plugin/plugin.json`, skills, `hooks/codex-hooks.json` |
| OpenCode | Works today | Skills + AGENTS.md policy; `.opencode/plugin/dekc.json` registration |

## Porting table

| Plugin piece | Claude / Grok | Codex | OpenCode |
|---|---|---|---|
| Skills (`skills/`) | Auto-invoked | Native Codex skills | Policy + skill folders |
| Commands (`commands/`) | Slash commands | Invoke via skill prose / shell | Shell + skill prose |
| Agents (`agents/`) | Subagent specialists | Load as skills/prompts | Load as agents if supported |
| Hooks | `hooks/hooks.json` | `hooks/codex-hooks.json` (nested `hooks` key) | Prefer policy; optional project hooks |
| Scripts | `scripts/dekc_*.py` | Same | Same |
| Config | `.dekc/config.yml` | Same | Same |

## Install snippets

```bash
# Claude
claude plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
claude plugin install data-engineering-knowledge-capture@dekc-plugin-marketplace

# Codex
codex plugin marketplace add SpillwaveSolutions/data-engineering-knowledge-capture
```

Grok Build: add the Claude marketplace — no separate Grok-only install.

OpenCode: clone/add this repo and ensure `.opencode/opencode.json` permissions cover `skills/` and `scripts/`.
