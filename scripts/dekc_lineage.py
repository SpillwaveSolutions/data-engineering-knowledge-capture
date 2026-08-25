#!/usr/bin/env python3
"""Lineage extraction and graph helpers for DEKC."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_capture import capture_lineage_path  # noqa: E402
from dekc_common import (  # noqa: E402
    iter_typed_edges,
    list_concepts,
    parse_frontmatter,
    resolve_knowledge_root,
)

SQL_FROM_RE = re.compile(
    r"\b(?:from|join)\s+([`\"\[]?[\w.-]+[`\"\]]?(?:\.[`\"\[]?[\w.-]+[`\"\]]?){0,2})",
    re.IGNORECASE,
)
SQL_TARGET_RE = re.compile(
    r"\b(?:insert\s+into|merge\s+into|create\s+(?:or\s+replace\s+)?table|create\s+(?:or\s+replace\s+)?view)\s+([`\"\[]?[\w.-]+[`\"\]]?)",
    re.IGNORECASE,
)


def extract_edges_from_sql(sql: str) -> list[tuple[str, str]]:
    """Return (upstream, downstream) pairs when a write target is present."""
    sources = []
    for m in SQL_FROM_RE.finditer(sql):
        name = m.group(1).strip('`"[]').split(".")[-1]
        if name.lower() not in {"select", "where", "lateral"}:
            sources.append(name)
    targets = []
    for m in SQL_TARGET_RE.finditer(sql):
        name = m.group(1).strip('`"[]').split(".")[-1]
        targets.append(name)
    edges: list[tuple[str, str]] = []
    for t in targets:
        for s in sources:
            if s != t:
                edges.append((s, t))
    return edges


# Relations that mean "data moves from source to target". These are the ones
# dekc_platform and dekc_capture actually emit and that docs/typed-edges.md
# documents as flow -- lands_as, lands_into, visualizes and consumes_stream were
# written by the plugin and then ignored here, so packs built from them came out
# incomplete with no indication anything was dropped.
FORWARD_FLOW = (
    "feeds", "transforms_to", "writes_to", "promotes_to",
    "lands_as", "lands_into", "refreshes",
)
# Relations that mean the opposite: the TARGET feeds the source.
REVERSE_FLOW = (
    "reads_from", "queries", "sourced_from", "derived_from",
    "visualizes", "consumes_stream",
    "ingested_by", "ingests_from",
)

def build_graph(
    bundle: Path,
    *,
    types: set[str] | frozenset[str] | None = None,
    prefixes: list[str] | None = None,
    tags: list[str] | None = None,
    since: str | None = None,
) -> dict[str, list[str]]:
    """Adjacency from typed flow edges in `links[]` and PKC `rel:` maps (#40)."""
    adj: dict[str, list[str]] = defaultdict(list)
    for path, fm, body in list_concepts(bundle, types=types, prefixes=prefixes, tags=tags, since=since):
        rel = "/" + path.relative_to(bundle).as_posix()
        for tgt, r in iter_typed_edges(fm):
            if not tgt:
                continue
            if r in FORWARD_FLOW:
                adj[rel].append(tgt)
            elif r in REVERSE_FLOW:
                adj[tgt].append(rel)
        # also parse SQL blocks for edges
        if "```sql" in body.lower() or "```sql" in body:
            m = re.search(r"```sql\n(.*?)```", body, re.DOTALL | re.IGNORECASE)
            if m:
                sql = m.group(1)
                edges = extract_edges_from_sql(sql)
                if not edges and _is_ddl_only(sql):
                    # CREATE TABLE with no FROM is not "no lineage" — it is DDL-only (#38).
                    continue
                for up, down in edges:
                    up_ref = _resolve_name(bundle, up)
                    down_ref = _resolve_name(bundle, down)
                    if up_ref and down_ref:
                        adj[up_ref].append(down_ref)
    return {k: list(dict.fromkeys(v)) for k, v in adj.items()}


def _is_ddl_only(sql: str) -> bool:
    low = sql.lower()
    has_write = bool(SQL_TARGET_RE.search(sql))
    has_from = bool(SQL_FROM_RE.search(sql))
    return has_write and not has_from and "create" in low

def _resolve_name(bundle: Path, name: str) -> str | None:
    slug_bits = name.lower().replace("_", "-")
    for folder in ("tables", "views", "queries"):
        d = bundle / folder
        if not d.is_dir():
            continue
        for p in d.glob("*.md"):
            if p.name == "index.md":
                continue
            if p.stem == slug_bits or p.stem.endswith("-" + slug_bits) or slug_bits in p.stem:
                return f"/{folder}/{p.name}"
    return None


def upstream(graph: dict[str, list[str]], start: str, hops: int = 5) -> list[str]:
    # reverse graph
    rev: dict[str, list[str]] = defaultdict(list)
    for s, tgts in graph.items():
        for t in tgts:
            rev[t].append(s)
    return _bfs(rev, start, hops)


def downstream(graph: dict[str, list[str]], start: str, hops: int = 5) -> list[str]:
    return _bfs(graph, start, hops)


def _bfs(adj: dict[str, list[str]], start: str, hops: int) -> list[str]:
    if not start.startswith("/"):
        start = "/" + start
    seen = {start}
    q = deque([(start, 0)])
    order = [start]
    while q:
        node, d = q.popleft()
        if d >= hops:
            continue
        for nxt in adj.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                q.append((nxt, d + 1))
    return order


def path_between(graph: dict[str, list[str]], src: str, dst: str, max_hops: int = 8) -> list[str] | None:
    if not src.startswith("/"):
        src = "/" + src
    if not dst.startswith("/"):
        dst = "/" + dst
    q = deque([(src, [src])])
    seen = {src}
    while q:
        node, path = q.popleft()
        if len(path) > max_hops + 1:
            continue
        if node == dst:
            return path
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, path + [nxt]))
    return None


def materialize_all_paths(bundle: Path) -> list[dict[str, Any]]:
    graph = build_graph(bundle)
    # find roots (no inbound)
    inbound = set()
    for s, tgts in graph.items():
        for t in tgts:
            inbound.add(t)
    roots = [n for n in graph if n not in inbound]
    results = []
    for root in roots:
        chain = downstream(graph, root, hops=6)
        if len(chain) < 2:
            continue
        name = f"path-{Path(root).stem}-to-{Path(chain[-1]).stem}"
        capture_lineage_path(bundle, name=name, nodes=chain, description="Auto-extracted lineage")
        results.append({"name": name, "nodes": chain})
    return results


def mermaid(graph: dict[str, list[str]], focus: str | None = None, hops: int = 2) -> str:
    if focus:
        nodes = set(downstream(graph, focus, hops)) | set(upstream(graph, focus, hops))
    else:
        nodes = set(graph.keys())
        for vs in graph.values():
            nodes.update(vs)
    lines = ["flowchart LR"]
    id_map = {}
    for i, n in enumerate(sorted(nodes)):
        nid = f"n{i}"
        id_map[n] = nid
        lines.append(f'  {nid}["{Path(n).stem}"]')
    for s, tgts in graph.items():
        if s not in id_map:
            continue
        for t in tgts:
            if t in id_map:
                lines.append(f"  {id_map[s]} --> {id_map[t]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC lineage tools")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("graph")
    p = sub.add_parser("upstream")
    p.add_argument("concept")
    p.add_argument("--hops", type=int, default=5)
    p = sub.add_parser("downstream")
    p.add_argument("concept")
    p.add_argument("--hops", type=int, default=5)
    p = sub.add_parser("path")
    p.add_argument("src")
    p.add_argument("dst")
    sub.add_parser("materialize")
    p = sub.add_parser("mermaid")
    p.add_argument("--focus", default=None)
    p.add_argument("--hops", type=int, default=2)
    p = sub.add_parser("from-sql")
    p.add_argument("--file", required=True)

    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    graph = build_graph(bundle)

    if args.cmd == "graph":
        print(json.dumps(graph, indent=2))
    elif args.cmd == "upstream":
        print(json.dumps(upstream(graph, args.concept, args.hops), indent=2))
    elif args.cmd == "downstream":
        print(json.dumps(downstream(graph, args.concept, args.hops), indent=2))
    elif args.cmd == "path":
        print(json.dumps(path_between(graph, args.src, args.dst), indent=2))
    elif args.cmd == "materialize":
        print(json.dumps(materialize_all_paths(bundle), indent=2))
    elif args.cmd == "mermaid":
        print(mermaid(graph, focus=args.focus, hops=args.hops))
    elif args.cmd == "from-sql":
        sql = Path(args.file).read_text(encoding="utf-8")
        print(json.dumps(extract_edges_from_sql(sql), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
