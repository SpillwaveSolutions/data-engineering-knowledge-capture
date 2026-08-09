#!/usr/bin/env python3
"""Second-brain retrieval for DEKC — intent packs for design work.

Use when designing reports, landing new data, defining metrics, or assessing impact.
Pulls schema-typed concepts from the indexed OKF graph into progressive-disclosure packs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    append_log,
    list_concepts,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    slugify,
    utc_now,
    write_concept,
)
from dekc_index import build_index, search_index  # noqa: E402
from dekc_lineage import build_graph, mermaid  # noqa: E402
from dekc_pack import pack as graph_pack  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "schemas" / "okf-concepts" / "registry.json"

INTENTS = {
    "design-report": {
        "title": "Design a report / dashboard",
        "types": [
            "Dashboard",
            "Report",
            "Metric",
            "SemanticModel",
            "BusinessObject",
            "GlossaryTerm",
            "Table",
            "View",
            "DaxArtifact",
            "Query",
            "Wireframe",
            "Diagram",
            "DataMart",
        ],
        "prefer_layers": ["gold", "silver"],
        "checklist": [
            "Capture or update wireframe (PlantUML) for the report layout",
            "Identify business objects and glossary terms the report must use",
            "Bind visuals to existing metrics or propose new Metric concepts",
            "Prefer gold/mart tables; document silver only if grain requires it",
            "Trace lineage for critical measures (blast radius if tables change)",
            "Capture new Report/Dashboard concepts and links (visualizes, measures)",
            "Re-index second brain after capture",
        ],
    },
    "land-data": {
        "title": "Land new data (stream or batch)",
        "types": [
            "SourceSystem",
            "Workflow",
            "Transformation",
            "Table",
            "Layer",
            "DataContract",
            "LineagePath",
            "Schema",
            "Column",
        ],
        "prefer_layers": ["bronze", "raw", "silver"],
        "checklist": [
            "Register SourceSystem (stream vs batch/api/file)",
            "Define bronze landing table + schema/columns when known",
            "Capture Workflow/job that lands or processes the data",
            "Link stream/job → bronze with feeds/lands_as/writes_to",
            "Note contract/SLA/freshness expectations",
            "Plan silver cleanse as Transformation (do not invent edges)",
            "Grade landing with stream-job rubric when reverse-engineering",
        ],
    },
    "design-metric": {
        "title": "Design a metric / measure",
        "types": [
            "Metric",
            "BusinessObject",
            "GlossaryTerm",
            "Table",
            "DaxArtifact",
            "SqlArtifact",
            "SemanticModel",
            "Query",
        ],
        "prefer_layers": ["gold", "silver"],
        "checklist": [
            "Define GlossaryTerm with non-vacuous business definition",
            "Link Metric → BusinessObject (measures) and technical table/query",
            "Prefer certified gold sources; cite grain and filters",
            "If DAX/SQL exists, capture DaxArtifact/SqlArtifact implements links",
            "Avoid conflicting metric names without supersedes/related_to notes",
        ],
    },
    "design-job": {
        "title": "Design a job / pipeline",
        "types": [
            "Workflow",
            "Transformation",
            "Diagram",
            "DQRule",
            "Table",
            "Stream",
            "StorageLocation",
            "DataLake",
        ],
        "prefer_layers": ["bronze", "silver", "gold"],
        "checklist": [
            "Capture Workflow with orchestrator and mode",
            "Attach activity/state/class diagrams via dekc_diagram job-pack",
            "Link reads/writes to tables; streams/storage when landing",
            "Add DQ rules on outputs",
            "Do not invent lineage edges without SQL/job evidence",
        ],
    },
    "impact": {
        "title": "Impact / blast radius of a change",
        "types": [
            "Table",
            "View",
            "Query",
            "Transformation",
            "Workflow",
            "Dashboard",
            "Report",
            "Metric",
            "BusinessObject",
            "LineagePath",
        ],
        "prefer_layers": [],
        "checklist": [
            "Start from the changing asset path",
            "Walk downstream lineage (feeds, transforms_to, visualizes)",
            "List reports/dashboards/metrics that break",
            "Notify owners linked via owns/related_to when present",
            "Capture decision or run impact pack into packs/",
        ],
    },
    "general": {
        "title": "General second-brain search",
        "types": [],
        "prefer_layers": [],
        "checklist": [
            "Search, open 2-hop pack on best hit, refine query",
        ],
    },
}


def load_registry_intents() -> dict:
    if REGISTRY_PATH.is_file():
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return reg.get("intents") or {}
    return {}


def ensure_index(bundle: Path) -> None:
    if not (bundle / ".index" / "search.json").is_file():
        build_index(bundle)


def tokenize(q: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9_]+", q.lower()) if len(t) >= 2]


def score_concept(fm: dict, body: str, tokens: list[str], intent: dict) -> float:
    blob = " ".join(
        [
            str(fm.get("title") or ""),
            str(fm.get("description") or ""),
            str(fm.get("fqn") or ""),
            str(fm.get("layer") or ""),
            " ".join(str(t) for t in (fm.get("tags") or [])),
            body[:2000],
        ]
    ).lower()
    if not tokens:
        s = 0.1
    else:
        hits = sum(1 for t in tokens if t in blob)
        s = hits / len(tokens)
    types = intent.get("types") or []
    t = fm.get("type")
    if types and t in types:
        s += 0.35
    elif types and t not in types:
        s *= 0.45
    layer = (fm.get("layer") or "").lower()
    prefer = intent.get("prefer_layers") or []
    if prefer and layer in prefer:
        s += 0.15
    if fm.get("type") in ("BusinessObject", "GlossaryTerm", "Metric") and str(
        intent.get("title") or ""
    ).startswith("Design"):
        s += 0.05
    return s


def brain_query(
    bundle: Path,
    query: str,
    *,
    intent_name: str = "general",
    limit: int = 12,
    hops: int = 2,
) -> dict:
    intent = dict(INTENTS.get(intent_name) or INTENTS["general"])
    reg_types = load_registry_intents().get(intent_name)
    if reg_types:
        intent["types"] = list(dict.fromkeys([*(intent.get("types") or []), *reg_types]))

    ensure_index(bundle)
    tokens = tokenize(query)

    hits = search_index(bundle, query, limit=max(limit * 3, 20))
    hit_paths = {("/" + h["path"]) if not str(h.get("path", "")).startswith("/") else h["path"] for h in hits}
    # also bare paths
    hit_paths |= {h.get("path") for h in hits if h.get("path")}

    scored: list[tuple[float, str, dict, str]] = []
    for path, fm, body in list_concepts(bundle):
        rel = "/" + path.relative_to(bundle).as_posix()
        s = score_concept(fm, body, tokens, intent)
        if rel in hit_paths or path.relative_to(bundle).as_posix() in hit_paths:
            s += 0.25
        if s <= 0:
            continue
        scored.append((s, rel, fm, body))

    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]

    focus = None
    preferred = set(intent.get("types") or [])
    for _, rel, fm, _ in top:
        if not preferred or fm.get("type") in preferred or fm.get("type") in (
            "Table",
            "Metric",
            "Dashboard",
            "BusinessObject",
            "SourceSystem",
        ):
            focus = rel
            break
    if not focus and top:
        focus = top[0][1]

    pack_result = graph_pack(bundle, focus, hops=hops, max_nodes=18) if focus else None
    type_counts = Counter((fm.get("type") or "?") for _, _, fm, _ in top)
    graph = build_graph(bundle)

    lines = [
        f"# Second brain · {intent['title']}",
        "",
        f"**Query:** {query}",
        f"**Intent:** `{intent_name}`",
        f"**Focus:** `{focus or '—'}`",
        "",
        "## Design checklist",
        "",
    ]
    for item in intent.get("checklist") or []:
        lines.append(f"- [ ] {item}")
    lines += ["", "## Ranked concepts (schema-typed)", ""]
    for s, rel, fm, body in top:
        typ = fm.get("type")
        layer = fm.get("layer")
        layer_s = f", layer={layer}" if layer else ""
        lines.append(f"### {fm.get('title')} (`{typ}`{layer_s}) · score {s:.2f}")
        lines.append("")
        lines.append(f"- Path: `{rel}`")
        if fm.get("description"):
            lines.append(f"- {fm['description']}")
        links = fm.get("links") or []
        if links:
            lines.append(
                "- Links: "
                + ", ".join(
                    f"{l.get('rel', 'related_to')}→`{l.get('target')}`"
                    for l in links[:6]
                    if isinstance(l, dict)
                )
            )
        lines.append("")

    if pack_result:
        lines += [
            "## Progressive disclosure pack",
            "",
            f"Hops={pack_result['hops']} nodes={pack_result['node_count']} focus=`{pack_result['focus']}`",
            "",
        ]
        for n in pack_result["nodes"][:12]:
            lines.append(f"- `{n['path']}` · {n['type']} · {n['title']}")
        lines += [
            "",
            "### Lineage",
            "",
            "```mermaid",
            mermaid(graph, focus=focus, hops=hops),
            "```",
            "",
        ]

    lines += [
        "## Next capture (keep schema-aligned)",
        "",
        "Use `dekc_capture.py` / skills so new concepts match `schemas/okf-concepts/*.schema.json`.",
        "",
        f"- Intent types: {', '.join(intent.get('types') or ['(any)'])}",
        "",
    ]

    return {
        "query": query,
        "intent": intent_name,
        "intent_title": intent["title"],
        "focus": focus,
        "checklist": intent.get("checklist") or [],
        "preferred_types": intent.get("types") or [],
        "type_counts": dict(type_counts),
        "results": [
            {
                "score": round(s, 3),
                "path": rel,
                "type": fm.get("type"),
                "title": fm.get("title"),
                "layer": fm.get("layer"),
                "description": fm.get("description"),
            }
            for s, rel, fm, _ in top
        ],
        "pack": {
            "focus": pack_result["focus"],
            "node_count": pack_result["node_count"],
            "nodes": pack_result["nodes"],
        }
        if pack_result
        else None,
        "markdown": "\n".join(lines),
        "schemas": "schemas/okf-concepts/",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DEKC second brain — query knowledge for design-report, land-data, metrics, impact"
    )
    parser.add_argument("query", nargs="?", help="Natural language or keywords")
    parser.add_argument(
        "--intent",
        choices=sorted(INTENTS.keys()),
        default="general",
        help="Design intent (filters/boosts schema types)",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write ContextPack under packs/")
    parser.add_argument("--list-intents", action="store_true")
    args = parser.parse_args(argv)

    if args.list_intents:
        print(json.dumps({k: v["title"] for k, v in INTENTS.items()}, indent=2))
        return 0

    if not args.query:
        parser.error("query required unless --list-intents")

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    result = brain_query(
        bundle, args.query, intent_name=args.intent, limit=args.limit, hops=args.hops
    )

    if args.write:
        slug = slugify(f"{args.intent}-{args.query}")[:60]
        rel = path_for_type("ContextPack", f"brain-{slug}")
        fm = {
            "type": "ContextPack",
            "title": f"Brain: {args.intent} · {args.query[:60]}",
            "description": f"Second-brain pack for intent={args.intent}",
            "focus": result.get("focus") or "",
            "hops": args.hops,
            "node_count": len(result.get("results") or []),
            "intent": args.intent,
            "tags": ["pack", "second-brain", "dekc", args.intent],
            "timestamp": utc_now(),
            "status": "active",
            "verified": True,
            "generated": True,
            "wiki_key": f"brain-{slug}",
            "truth_state": "current",
        }
        write_concept(bundle, rel, fm, result["markdown"], force=True)
        refresh_catalog_index(bundle, "packs")
        append_log(bundle, f"Second-brain pack intent={args.intent} query={args.query!r}")
        result["written"] = rel

    if args.json:
        out = {k: v for k, v in result.items() if k != "markdown"}
        print(json.dumps(out, indent=2))
    else:
        print(result["markdown"])
        if args.write:
            print(f"\n<!-- written {result.get('written')} -->")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
