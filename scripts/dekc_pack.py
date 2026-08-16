#!/usr/bin/env python3
"""Progressive disclosure context packs for DEKC concepts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    list_concepts,
    parse_frontmatter,
    path_for_type,
    resolve_knowledge_root,
    utc_now,
    write_knowledge,
    refresh_catalog_index,
    append_log,
)
from dekc_lineage import build_graph, mermaid  # noqa: E402


def load_map(bundle: Path) -> dict[str, tuple[dict, str]]:
    out = {}
    for path, fm, body in list_concepts(bundle):
        rel = "/" + path.relative_to(bundle).as_posix()
        out[rel] = (fm, body)
    return out


def pack(
    bundle: Path,
    focus: str,
    *,
    hops: int = 2,
    max_nodes: int = 20,
) -> dict:
    if not focus.startswith("/"):
        # try resolve
        candidate = focus if focus.endswith(".md") else focus + ".md"
        if (bundle / candidate).is_file():
            focus = "/" + candidate
        else:
            # search by stem
            for path, fm, _ in list_concepts(bundle):
                if path.stem == Path(focus).stem or fm.get("title") == focus:
                    focus = "/" + path.relative_to(bundle).as_posix()
                    break
            else:
                focus = "/" + candidate.lstrip("/")

    graph = build_graph(bundle)
    concepts = load_map(bundle)
    # undirected expansion for packs
    undirected: dict[str, list[str]] = {}
    for s, tgts in graph.items():
        undirected.setdefault(s, [])
        for t in tgts:
            undirected.setdefault(s, []).append(t)
            undirected.setdefault(t, []).append(s)
    # also include typed links from focus frontmatter
    if focus in concepts:
        for link in concepts[focus][0].get("links") or []:
            if isinstance(link, dict) and link.get("target"):
                undirected.setdefault(focus, []).append(link["target"])
                undirected.setdefault(link["target"], []).append(focus)

    seen = {focus}
    order = [focus]
    q = deque([(focus, 0)])
    while q and len(order) < max_nodes:
        node, d = q.popleft()
        if d >= hops:
            continue
        for nxt in undirected.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                q.append((nxt, d + 1))
                if len(order) >= max_nodes:
                    break

    nodes = []
    md = [f"# Context pack: {Path(focus).stem}", "", f"Hops: {hops} · Nodes: {len(order)}", ""]
    for rel in order:
        fm, body = concepts.get(rel, ({}, ""))
        title = fm.get("title") or Path(rel).stem
        typ = fm.get("type") or "?"
        layer = fm.get("layer")
        nodes.append(
            {
                "path": rel,
                "title": title,
                "type": typ,
                "layer": layer,
                "description": fm.get("description") or "",
            }
        )
        md.append(f"## {title} (`{typ}`{f', {layer}' if layer else ''})")
        md.append("")
        md.append(f"- Path: `{rel}`")
        if fm.get("description"):
            md.append(f"- {fm['description']}")
        md.append("")
        # include short body excerpt
        excerpt = "\n".join(
            line for line in body.splitlines() if line.strip() and not line.startswith("#")
        )[:400]
        if excerpt:
            md.append(excerpt)
            md.append("")

    md.append("## Lineage diagram")
    md.append("")
    md.append("```mermaid")
    md.append(mermaid(graph, focus=focus, hops=hops))
    md.append("```")
    md.append("")

    return {
        "focus": focus,
        "hops": hops,
        "max_nodes": max_nodes,
        "node_count": len(nodes),
        "nodes": nodes,
        "markdown": "\n".join(md),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("focus")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=20)
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mermaid", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write pack under packs/")
    parser.add_argument("--author", default="")
    args = parser.parse_args(argv)
    from dekc_common import resolve_author
    if getattr(args, 'write', False):
        resolve_author(args.author)

    if args.tiny:
        args.hops = 1
        args.max_nodes = 8

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    result = pack(bundle, args.focus, hops=args.hops, max_nodes=args.max_nodes)

    if args.write:
        slug = Path(result["focus"]).stem
        rel = path_for_type("ContextPack", f"pack-{slug}")
        fm = {
            "type": "ContextPack",
            "title": f"Pack: {slug}",
            "description": f"Progressive disclosure pack for {result['focus']}",
            "focus": result["focus"],
            "hops": result["hops"],
            "node_count": result["node_count"],
            "tags": ["pack", "dekc"],
            "timestamp": utc_now(),
            "status": "active",
            "verified": True,
            "generated": True,
            "wiki_key": f"pack-{slug}",
            "truth_state": "current",
        }
        write_knowledge(bundle, rel, fm, result["markdown"])
        refresh_catalog_index(bundle, "packs")
        append_log(bundle, f"Wrote context pack for {result['focus']}")

    if args.mermaid:
        graph = build_graph(bundle)
        print(mermaid(graph, focus=result["focus"], hops=result["hops"]))
    elif args.json:
        print(json.dumps({k: v for k, v in result.items() if k != "markdown"}, indent=2))
    else:
        print(result["markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
