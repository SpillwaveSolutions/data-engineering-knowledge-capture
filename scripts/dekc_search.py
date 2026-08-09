#!/usr/bin/env python3
"""Full-text + indexed search over DEKC concepts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import list_concepts, resolve_knowledge_root  # noqa: E402
from dekc_index import search_index, build_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args(argv)

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    if args.rebuild or not (bundle / ".index" / "search.json").is_file():
        build_index(bundle)
    hits = search_index(bundle, args.query, args.limit)

    # fallback scan if empty
    if not hits:
        q = args.query.lower()
        for path, fm, body in list_concepts(bundle):
            blob = f"{fm.get('title','')} {fm.get('description','')} {body}".lower()
            if q in blob:
                hits.append(
                    {
                        "path": path.relative_to(bundle).as_posix(),
                        "title": fm.get("title"),
                        "type": fm.get("type"),
                        "score": 1,
                    }
                )
            if len(hits) >= args.limit:
                break

    if args.json:
        print(json.dumps({"query": args.query, "count": len(hits), "hits": hits}, indent=2))
    else:
        print(f"{len(hits)} hits for {args.query!r}")
        for h in hits:
            print(f"  [{h.get('type')}] {h.get('title')}  ({h.get('path')}) score={h.get('score')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
