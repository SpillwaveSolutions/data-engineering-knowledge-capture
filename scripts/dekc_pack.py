#!/usr/bin/env python3
"""Progressive disclosure context packs for DEKC concepts.

Bodies off unless that node is the pack root. Token budget is fail-closed
(default 1/4 of SECOND_BRAIN_WINDOW_TOKENS). Node clip is not a token budget.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    append_log,
    list_concepts,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    utc_now,
    write_knowledge,
)
from dekc_lineage import build_graph, mermaid  # noqa: E402

DEFAULT_WINDOW_TOKENS = 128_000
PACK_BUDGET_DENOMINATOR = 4


class PackBudgetError(Exception):
    def __init__(self, tokens: int, budget: int, window: int, nodes: list[str]):
        self.tokens = tokens
        self.budget = budget
        self.window = window
        self.nodes = nodes
        super().__init__(f"pack exceeds token budget ({tokens}/{budget})")


def estimate_tokens(text: str) -> int:
    """Cheap chars/4 estimator. Not a model tokenizer."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def resolve_pack_budget(
    max_tokens: str | int | None = None,
    window_tokens: str | int | None = None,
) -> tuple[int, int]:
    raw_window = (
        window_tokens
        if window_tokens not in (None, "")
        else os.environ.get("SECOND_BRAIN_WINDOW_TOKENS") or ""
    )
    window = int(raw_window) if str(raw_window).strip() else DEFAULT_WINDOW_TOKENS
    if window < 1:
        raise SystemExit("error: window tokens must be >= 1")
    raw_budget = (
        max_tokens
        if max_tokens not in (None, "")
        else os.environ.get("SECOND_BRAIN_PACK_MAX_TOKENS") or ""
    )
    budget = int(raw_budget) if str(raw_budget).strip() else max(1, window // PACK_BUDGET_DENOMINATOR)
    if budget < 1:
        raise SystemExit("error: max tokens must be >= 1")
    return window, budget


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
        candidate = focus if focus.endswith(".md") else focus + ".md"
        if (bundle / candidate).is_file():
            focus = "/" + candidate
        else:
            for path, fm, _ in list_concepts(bundle):
                if path.stem == Path(focus).stem or fm.get("title") == focus:
                    focus = "/" + path.relative_to(bundle).as_posix()
                    break
            else:
                focus = "/" + candidate.lstrip("/")

    graph = build_graph(bundle)
    concepts = load_map(bundle)
    undirected: dict[str, list[str]] = {}
    for s, tgts in graph.items():
        undirected.setdefault(s, [])
        for t in tgts:
            undirected.setdefault(s, []).append(t)
            undirected.setdefault(t, []).append(s)
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
    for rel in order:
        fm, body = concepts.get(rel, ({}, ""))
        title = fm.get("title") or Path(rel).stem
        typ = fm.get("type") or "?"
        layer = fm.get("layer")
        is_root = rel == focus
        nodes.append(
            {
                "path": rel,
                "title": title,
                "type": typ,
                "layer": layer,
                "description": fm.get("description") or "",
                "body": body if is_root else "",
            }
        )

    return {
        "focus": focus,
        "hops": hops,
        "max_nodes": max_nodes,
        "node_count": len(nodes),
        "nodes": nodes,
        "excluded_note": (
            "Nodes beyond hops/max_nodes omitted for progressive disclosure. "
            "Node clip is not a token budget."
        ),
    }


def render_markdown(
    result: dict,
    *,
    bundle: Path | None = None,
    tokens: int | None = None,
    budget: int | None = None,
) -> str:
    focus = result["focus"]
    token_bit = f"Tokens: {tokens}/{budget} · " if tokens is not None and budget is not None else ""
    md = [
        f"# Context pack: {Path(focus).stem}",
        "",
        f"{token_bit}Hops: {result['hops']} · Nodes: {result['node_count']}",
        "",
    ]
    for n in result["nodes"]:
        layer = n.get("layer")
        md.append(f"## {n['title']} (`{n['type']}`{f', {layer}' if layer else ''})")
        md.append("")
        md.append(f"- Path: `{n['path']}`")
        if n["path"] == focus:
            body = (n.get("body") or "").strip()
            if body:
                md.append("")
                excerpt = "\n".join(
                    line for line in body.splitlines() if line.strip() and not line.startswith("#")
                )
                if excerpt:
                    md.append(excerpt)
        elif n.get("description"):
            md.append(f"- {n['description']}")
        md.append("")

    graph = build_graph(bundle) if bundle is not None else {}
    md.append("## Lineage diagram")
    md.append("")
    md.append("```mermaid")
    md.append(mermaid(graph, focus=focus, hops=result["hops"]) if graph else "flowchart LR\n  empty[no graph]")
    md.append("```")
    md.append("")
    if result.get("excluded_note"):
        md.append(f"_{result['excluded_note']}_")
        md.append("")
    return "\n".join(md)


def finalize_markdown(
    result: dict,
    *,
    bundle: Path | None = None,
    max_tokens: str | int | None = None,
    window_tokens: str | int | None = None,
) -> tuple[str, dict[str, int]]:
    window, budget = resolve_pack_budget(max_tokens, window_tokens)
    draft = render_markdown(result, bundle=bundle, tokens=0, budget=budget)
    tokens = estimate_tokens(draft)
    md = render_markdown(result, bundle=bundle, tokens=tokens, budget=budget)
    tokens = estimate_tokens(md)
    meta = {"tokens": tokens, "budget": budget, "window": window}
    if tokens > budget:
        raise PackBudgetError(tokens, budget, window, [n["path"] for n in result["nodes"]])
    return md, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("focus")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=20)
    parser.add_argument("--max-tokens", default="")
    parser.add_argument("--window-tokens", default="")
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mermaid", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write pack under packs/")
    parser.add_argument("--author", default="")
    args = parser.parse_args(argv)
    from dekc_common import resolve_author

    if getattr(args, "write", False):
        resolve_author(args.author)

    if args.tiny:
        args.hops = 1
        args.max_nodes = 8

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    result = pack(bundle, args.focus, hops=args.hops, max_nodes=args.max_nodes)

    try:
        if args.mermaid:
            window, budget = resolve_pack_budget(args.max_tokens, args.window_tokens)
            diagram = mermaid(build_graph(bundle), focus=result["focus"], hops=result["hops"])
            tokens = estimate_tokens(diagram)
            if tokens > budget:
                raise PackBudgetError(tokens, budget, window, [n["path"] for n in result["nodes"]])
            print(diagram)
            return 0
        md, meta = finalize_markdown(
            result,
            bundle=bundle,
            max_tokens=args.max_tokens,
            window_tokens=args.window_tokens,
        )
    except PackBudgetError as exc:
        payload = {
            "error": "pack exceeds token budget",
            "tokens": exc.tokens,
            "budget": exc.budget,
            "window": exc.window,
            "nodes": exc.nodes,
            "hint": "narrow --hops / --tiny; node clip is not a token budget",
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"error: pack exceeds token budget ({exc.tokens}/{exc.budget})",
                file=sys.stderr,
            )
        return 1

    result.update(meta)
    result["markdown"] = md

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
            "tokens": result["tokens"],
            "budget": result["budget"],
            "tags": ["pack", "dekc"],
            "timestamp": utc_now(),
            "status": "active",
            "verified": True,
            "generated": True,
            "wiki_key": f"pack-{slug}",
            "truth_state": "current",
        }
        write_knowledge(bundle, rel, fm, md)
        refresh_catalog_index(bundle, "packs")
        append_log(bundle, f"Wrote context pack for {result['focus']}")

    if args.json:
        print(json.dumps({k: v for k, v in result.items() if k != "markdown"}, indent=2))
    elif not args.write:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
