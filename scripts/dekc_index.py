#!/usr/bin/env python3
"""Build a local indexed second-brain over the DEKC OKF bundle.

Produces:
  knowledge/.index/inventory.json  — all concepts
  knowledge/.index/search.json     — inverted token index
  knowledge/.index/graph.json      — adjacency for lineage packs
  knowledge/.index/embeddings.jsonl — bag-of-tokens pseudo-vectors (no API key required)
  knowledge/.index/manifest.json   — build metadata

Optional: if OPENAI_API_KEY or XAI_API_KEY is set and --embed-api is passed,
writes richer embeddings (not required for default operation).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import list_concepts, resolve_knowledge_root  # noqa: E402
from dekc_lineage import FORWARD_FLOW, REVERSE_FLOW, build_graph  # noqa: E402

TOKEN_RE = re.compile(r"[a-z0-9_]{2,}", re.I)
STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "are",
    "was",
    "were",
    "have",
    "has",
    "not",
    "but",
    "you",
    "all",
    "can",
    "into",
    "type",
    "title",
    "description",
    "tags",
    "status",
    "true",
    "false",
    "null",
    "markdown",
    "none",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOP]


def build_index(bundle: Path) -> dict[str, Any]:
    index_dir = bundle / ".index"
    index_dir.mkdir(parents=True, exist_ok=True)

    inventory: list[dict[str, Any]] = []
    inverted: dict[str, list[str]] = defaultdict(list)
    emb_lines: list[str] = []

    for path, fm, body in list_concepts(bundle):
        rel = path.relative_to(bundle).as_posix()
        text = f"{fm.get('title','')} {fm.get('description','')} {fm.get('type','')} {' '.join(fm.get('tags') or [])} {body}"
        tokens = tokenize(text)
        # term frequencies
        tf: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        # L2-normalized sparse bag as pseudo embedding (deterministic, local)
        norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
        sparse = {k: round(v / norm, 6) for k, v in sorted(tf.items()) if v > 0}
        # keep top 64 dims by weight
        sparse = dict(sorted(sparse.items(), key=lambda kv: -kv[1])[:64])

        entry = {
            "path": rel,
            "type": fm.get("type"),
            "title": fm.get("title") or path.stem,
            "description": fm.get("description") or "",
            "layer": fm.get("layer"),
            "tags": fm.get("tags") or [],
            "verified": bool(fm.get("verified")),
            "status": fm.get("status"),
            "wiki_key": fm.get("wiki_key"),
            "token_count": len(tokens),
            "hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        }
        inventory.append(entry)
        for tok in set(tokens):
            inverted[tok].append(rel)
        emb_lines.append(
            json.dumps({"path": rel, "type": entry["type"], "title": entry["title"], "vector": sparse})
        )

    graph = build_graph(bundle)

    (index_dir / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (index_dir / "search.json").write_text(
        json.dumps({k: v for k, v in sorted(inverted.items())}, indent=2), encoding="utf-8"
    )
    _edge_count = sum(len(v) for v in graph.values())
    if _edge_count == 0 and concepts:
        # An empty lineage graph is indistinguishable from a failed build unless
        # we say why. graph.json is lineage adjacency, not the general OKF graph,
        # so a bundle authored with a non-lineage vocabulary legitimately yields
        # nothing -- but silently writing 0 makes that look broken.
        print(
            f"dekc: no lineage relations found across {len(concepts)} concepts; "
            "graph.json is empty. Lineage edges come from "
            f"{', '.join(FORWARD_FLOW + REVERSE_FLOW)} — a bundle using a "
            "non-lineage vocabulary will produce none.",
            file=sys.stderr,
        )
    (index_dir / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (index_dir / "embeddings.jsonl").write_text("\n".join(emb_lines) + ("\n" if emb_lines else ""), encoding="utf-8")

    manifest = {
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "concept_count": len(inventory),
        "token_count": len(inverted),
        "edge_count": _edge_count,
        "bundle": str(bundle),
        "engine": "dekc-local-bow-v1",
        "files": [
            ".index/inventory.json",
            ".index/search.json",
            ".index/graph.json",
            ".index/embeddings.jsonl",
        ],
    }
    (index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def search_index(bundle: Path, query: str, limit: int = 20) -> list[dict[str, Any]]:
    index_dir = bundle / ".index"
    inv_path = index_dir / "inventory.json"
    search_path = index_dir / "search.json"
    if not inv_path.is_file() or not search_path.is_file():
        build_index(bundle)
    inventory = {e["path"]: e for e in json.loads(inv_path.read_text(encoding="utf-8"))}
    inverted = json.loads(search_path.read_text(encoding="utf-8"))
    q_tokens = tokenize(query)
    scores: dict[str, float] = defaultdict(float)
    for tok in q_tokens:
        for path in inverted.get(tok, []):
            scores[path] += 1.0
        # prefix soft match
        for k, paths in inverted.items():
            if k.startswith(tok) and k != tok:
                for path in paths:
                    scores[path] += 0.25
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
    out = []
    for path, score in ranked:
        e = dict(inventory.get(path) or {"path": path})
        e["score"] = score
        out.append(e)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC second-brain index")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)

    if args.cmd == "build":
        manifest = build_index(bundle)
        print(json.dumps(manifest, indent=2))
    elif args.cmd == "search":
        print(json.dumps(search_index(bundle, args.query, args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
