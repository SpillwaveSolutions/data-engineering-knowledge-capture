---
name: grok-bot-data-engineering-knowledge-capture
description: Bind a Grok Bot agent to Data Engineering Knowledge Capture. Isolation, identity, deterministic writes.
---

# Grok Bot / Data Engineering Knowledge Capture

Read `docs/ONBOARDING.md` first, then follow `docs/GROK_BOT.md`.

1. Identity: `grok-bot/data-engineering-knowledge-capture`
2. Open an isolation session before knowledge writes (`scripts/brain_session.py open`) unless the human already pointed `SECOND_BRAIN_ROOT` at a session worktree.
3. Pack 2 hops, then write owned types only via this plugin's scripts.
4. Close the session to PR. Report path + validation result.
5. Never document a private remote. Never write raw Markdown into the tree.
