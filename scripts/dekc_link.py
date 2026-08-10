#!/usr/bin/env python3
"""Add typed edges between DEKC concepts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_lineage import FORWARD_FLOW, REVERSE_FLOW
from dekc_common import (  # noqa: E402
    DEFAULT_RELATIONS,
    add_typed_link,
    append_log,
    dump_frontmatter,
    parse_frontmatter,
    resolve_knowledge_root,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="Source concept path")
    parser.add_argument("tgt", help="Target concept path or absolute /ref")
    parser.add_argument("--rel", required=True, help=(
            "Relation. Lineage-bearing values (these produce graph edges): "
            + ", ".join(FORWARD_FLOW + REVERSE_FLOW)
            + f". Any of the {len(DEFAULT_RELATIONS)} documented relations is "
            "accepted; the rest are recorded in frontmatter but do not appear "
            "in the lineage graph."
        ))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    args = parser.parse_args(argv)

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    src = args.src.lstrip("/")
    path = bundle / src
    if not path.is_file():
        print(f"missing source {src}", file=sys.stderr)
        return 1
    tgt = args.tgt if args.tgt.startswith("/") else "/" + args.tgt.lstrip("/")
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, tgt, args.rel)
    # ensure body link
    if tgt not in body:
        body = body.rstrip() + f"\n\n- [{Path(tgt).stem}]({tgt}) (`{args.rel}`)\n"
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")
    append_log(bundle, f"Linked {src} -[{args.rel}]-> {tgt}")
    print(f"linked {src} -[{args.rel}]-> {tgt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
