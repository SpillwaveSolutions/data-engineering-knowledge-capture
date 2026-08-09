#!/usr/bin/env python3
"""One-screen health check for a DEKC bundle."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import list_concepts, resolve_knowledge_root  # noqa: E402
from dekc_validate import validate_bundle  # noqa: E402
from dekc_lineage import build_graph  # noqa: E402


def doctor(bundle: Path) -> dict:
    concepts = list_concepts(bundle)
    types = Counter((fm.get("type") or "?") for _, fm, _ in concepts)
    layers = Counter((fm.get("layer") or "—") for _, fm, _ in concepts if fm.get("type") in ("Table", "View"))
    graph = build_graph(bundle)
    orphans = []
    linked = set()
    for s, tgts in graph.items():
        linked.add(s)
        linked.update(tgts)
    for path, fm, _ in concepts:
        rel = "/" + path.relative_to(bundle).as_posix()
        if fm.get("type") in ("Table", "View", "Query", "BusinessObject") and rel not in linked:
            orphans.append(rel)
    validation = validate_bundle(bundle)
    bo_count = types.get("BusinessObject", 0)
    gloss = types.get("GlossaryTerm", 0)
    tables = types.get("Table", 0)
    coverage = round(bo_count / tables, 2) if tables else 0.0
    index_ok = (bundle / ".index" / "manifest.json").is_file()

    return {
        "bundle": str(bundle),
        "concept_count": len(concepts),
        "types": dict(types),
        "layers": dict(layers),
        "edge_count": sum(len(v) for v in graph.values()),
        "orphan_technical": orphans[:20],
        "business_coverage": coverage,
        "business_objects": bo_count,
        "glossary_terms": gloss,
        "index_built": index_ok,
        "validation_ok": validation["ok"],
        "errors": validation["errors"][:10],
        "warnings": validation["warnings"][:10],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    report = doctor(bundle)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"DEKC doctor · {report['bundle']}")
        print(f"  concepts:     {report['concept_count']}")
        print(f"  edges:        {report['edge_count']}")
        print(f"  tables→BO:    {report['business_coverage']} ({report['business_objects']} objects)")
        print(f"  glossary:     {report['glossary_terms']}")
        print(f"  index:        {'yes' if report['index_built'] else 'NO — run dekc_index.py build'}")
        print(f"  validation:   {'OK' if report['validation_ok'] else 'FAILED'}")
        print("  types:")
        for t, n in sorted(report["types"].items(), key=lambda kv: -kv[1]):
            print(f"    {t:20} {n}")
        if report["orphan_technical"]:
            print("  orphan technical (no lineage edges):")
            for o in report["orphan_technical"][:8]:
                print(f"    - {o}")
        for e in report["errors"]:
            print(f"  ERROR {e}")
        for w in report["warnings"]:
            print(f"  WARN  {w}")
    return 0 if report["validation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
