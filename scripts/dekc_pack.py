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
    find_rg,
    is_concept_path,
    iter_typed_edges,
    list_concepts,
    parse_frontmatter,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    rg_list_files,
    utc_now,
    write_knowledge,
)
from dekc_lineage import FORWARD_FLOW, REVERSE_FLOW, build_graph, mermaid  # noqa: E402
from dekc_index import LINEAGE_RELS, open_graph  # noqa: E402

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


def _parse_rel(bundle: Path, rel: str) -> tuple[dict, str]:
    fp = bundle / rel.lstrip("/")
    if not fp.is_file():
        return {}, ""
    try:
        return parse_frontmatter(fp.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}, ""


def _lineage_neighbors_from_file(bundle: Path, rel: str, fm: dict, body: str) -> list[str]:
    """Undirected lineage neighbors authored on this file (typed edges + SQL)."""
    from dekc_index import extract_dekc_edges

    out: list[str] = []
    seen: set[str] = set()
    for src, dst, r, _label in extract_dekc_edges(bundle, rel, fm, body):
        if r not in LINEAGE_RELS and r not in FORWARD_FLOW and r not in REVERSE_FLOW:
            continue
        other = dst if src == rel else src
        if other == rel or other in seen:
            continue
        seen.add(other)
        out.append(other)
    return out


def _inbound_via_rg(bundle: Path, target: str) -> list[str] | None:
    """Undirected lineage neighbors via rg.

    rg only finds files that *mention* `target`. The target file itself almost
    never contains its own path (SQL lineage lives in a fenced block of table
    names), so we always parse it. None = rg missing/failed → fall back.
    """
    needles = [target]
    if target.startswith("/"):
        needles.append(target.lstrip("/"))
    hits = rg_list_files(bundle, needles[:1], fixed_string=True, ignore_case=False)
    if hits is None:
        return None
    neighbors: list[str] = []
    seen: set[str] = set()

    def _consider(src: str, nxt: str) -> None:
        if nxt == target and src != target and src not in seen:
            seen.add(src)
            neighbors.append(src)
        elif src == target and nxt != target and nxt not in seen:
            seen.add(nxt)
            neighbors.append(nxt)

    target_path = bundle / target.lstrip("/")
    files: list[Path] = []
    seen_paths: set[Path] = set()
    if target_path.is_file():
        files.append(target_path.resolve())
        seen_paths.add(target_path.resolve())
    for path in hits:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        files.append(path)

    for path in files:
        if not is_concept_path(bundle, path) and path.resolve() != target_path.resolve():
            continue
        try:
            src = "/" + path.relative_to(bundle).as_posix()
        except ValueError:
            continue
        fm, body = _parse_rel(bundle, src)
        for nxt in _lineage_neighbors_from_file(bundle, src, fm, body):
            _consider(src, nxt)
    return neighbors


class ReverseIndex:
    """Lineage neighbors: SQLite index → rg → full scan."""

    def __init__(
        self,
        bundle: Path,
        *,
        use_rg: bool | None = None,
        use_index: bool | None = None,
    ):
        self.bundle = bundle
        self._full: dict[str, list[str]] | None = None
        self._memo: dict[str, list[str]] = {}
        self._graph = None
        if use_index is False:
            self._index = False
        else:
            self._graph = open_graph(bundle)
            self._index = self._graph is not None
            if use_index is True and not self._index:
                self._index = False
        if use_rg is False:
            self._rg = False
        else:
            self._rg = bool(find_rg())

    @property
    def engine(self) -> str:
        if self._index:
            return "index"
        return "rg" if self._rg else "scan"

    def close(self) -> None:
        if self._graph is not None:
            self._graph.close()
            self._graph = None

    def get(self, target: str) -> list[str]:
        if target in self._memo:
            return self._memo[target]
        if self._index and self._graph is not None:
            found = self._graph.neighbors(target, lineage_only=True)
            self._memo[target] = found
            return found
        if self._rg:
            found = _inbound_via_rg(self.bundle, target)
            if found is not None:
                self._memo[target] = found
                return found
            self._rg = False
        if self._full is None:
            graph = build_graph(self.bundle)
            undirected: dict[str, list[str]] = {}
            for s, tgts in graph.items():
                undirected.setdefault(s, [])
                for t in tgts:
                    undirected.setdefault(s, []).append(t)
                    undirected.setdefault(t, []).append(s)
            self._full = {k: list(dict.fromkeys(v)) for k, v in undirected.items()}
        edges = self._full.get(target, [])
        self._memo[target] = edges
        return edges


def pack(
    bundle: Path,
    focus: str,
    *,
    hops: int = 2,
    max_nodes: int = 20,
    use_rg: bool | None = None,
    use_index: bool | None = None,
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

    inbound = ReverseIndex(bundle, use_rg=use_rg, use_index=use_index)
    try:
        focus_fm, focus_body = _parse_rel(bundle, focus)
        extra: list[str] = []
        for tgt, _rel in iter_typed_edges(focus_fm):
            if tgt and tgt != focus:
                extra.append(tgt if tgt.startswith("/") else "/" + tgt.lstrip("/"))

        seen = {focus}
        order = [focus]
        q = deque([(focus, 0)])
        while q and len(order) < max_nodes:
            node, d = q.popleft()
            if d >= hops:
                continue
            # Outbound lineage is authored on this file (typed flow + SQL) and
            # is invisible to `rg -lF <path>` because the file rarely mentions
            # its own path. Union with inbound (index / rg / scan).
            fm, body = _parse_rel(bundle, node)
            outbound = _lineage_neighbors_from_file(bundle, node, fm, body)
            neighbors = list(dict.fromkeys(list(outbound) + list(inbound.get(node))))
            if node == focus:
                neighbors.extend(extra)
            for nxt in neighbors:
                if nxt not in seen:
                    seen.add(nxt)
                    order.append(nxt)
                    q.append((nxt, d + 1))
                    if len(order) >= max_nodes:
                        break

        nodes = []
        for rel in order:
            if inbound.engine == "index" and inbound._graph is not None:
                row = inbound._graph.node(rel)
                if row is not None:
                    fm = row.frontmatter()
                    body = row.body
                    title = row.title or Path(rel).stem
                    typ = row.type
                    layer = row.layer or fm.get("layer")
                else:
                    fm, body = _parse_rel(bundle, rel)
                    title = fm.get("title") or Path(rel).stem
                    typ = fm.get("type") or "?"
                    layer = fm.get("layer")
            else:
                fm, body = _parse_rel(bundle, rel)
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
                    "description": (fm.get("description") if isinstance(fm, dict) else "") or "",
                    "body": body if is_root else "",
                }
            )

        return {
            "focus": focus,
            "hops": hops,
            "max_nodes": max_nodes,
            "node_count": len(nodes),
            "nodes": nodes,
            "reverse_index": inbound.engine,
            "excluded_note": (
                "Nodes beyond hops/max_nodes omitted for progressive disclosure. "
                "Node clip is not a token budget."
            ),
        }
    finally:
        inbound.close()


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
    parser.add_argument("--rg", action="store_true", help="Use ripgrep for inbound discovery")
    parser.add_argument("--no-rg", action="store_true", help="Disable ripgrep")
    parser.add_argument("--no-index", action="store_true", help="Disable the SQLite index")
    args = parser.parse_args(argv)
    from dekc_common import resolve_author

    if getattr(args, "write", False):
        resolve_author(args.author)

    if args.tiny:
        args.hops = 1
        args.max_nodes = 8

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    use_index: bool | None = False if args.no_index else None
    use_rg: bool | None = False if args.no_rg else (True if args.rg else None)
    result = pack(
        bundle,
        args.focus,
        hops=args.hops,
        max_nodes=args.max_nodes,
        use_rg=use_rg,
        use_index=use_index,
    )

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
