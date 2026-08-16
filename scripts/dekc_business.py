#!/usr/bin/env python3
"""Promote technical tables/views/queries into business objects + glossary terms."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_capture import capture_business_object, capture_glossary_term  # noqa: E402
from dekc_common import list_concepts, parse_frontmatter, resolve_knowledge_root, slugify  # noqa: E402

# Simple heuristics for humanizing technical names
STOP = {"dim", "fct", "fact", "stg", "raw", "bronze", "silver", "gold", "vw", "tbl", "tmp"}


def humanize(name: str) -> str:
    base = Path(name).stem if name.endswith(".md") else name
    # strip layer prefix
    for layer in ("raw-", "bronze-", "silver-", "gold-", "stg_", "dim_", "fct_", "fact_"):
        if base.lower().startswith(layer):
            base = base[len(layer) :]
            break
    parts = re.split(r"[_\-\s]+", base)
    parts = [p for p in parts if p and p.lower() not in STOP]
    if not parts:
        parts = [base]
    return " ".join(p.capitalize() for p in parts)


def infer_definition(title: str, fm: dict, body: str) -> str:
    desc = (fm.get("description") or "").strip()
    if desc and not desc.lower().startswith("table ") and not desc.lower().startswith("referenced"):
        return desc
    # first non-header prose line
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("```") or line.startswith("**"):
            continue
        if line.startswith("-"):
            continue
        return line
    layer = fm.get("layer") or "curated"
    return (
        f"**{title}** is a business entity materialized from the {layer} data layer. "
        f"It represents the canonical business meaning of the technical asset "
        f"`{fm.get('fqn') or fm.get('title') or title}`."
    )


def promote_concept(
    bundle: Path,
    rel_path: str,
    *,
    name: str | None = None,
    definition: str | None = None,
    owner: str = "",
    also_glossary: bool = True,
) -> list[tuple[str, str]]:
    path = bundle / rel_path.lstrip("/")
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    tech_title = fm.get("title") or path.stem
    bo_name = name or humanize(tech_title)
    bo_def = definition or infer_definition(bo_name, fm, body)
    results = capture_business_object(
        bundle,
        name=bo_name,
        definition=bo_def,
        derived_from=[rel_path],
        glossary_terms=[bo_name] if also_glossary else [],
        owner=owner,
    )
    if also_glossary:
        results.extend(
            capture_glossary_term(
                bundle,
                term=bo_name,
                definition=bo_def,
                synonyms=_synonyms(tech_title, bo_name),
                related_objects=[bo_name],
            )
        )
    return results


def _synonyms(tech: str, business: str) -> list[str]:
    syn = {tech, tech.replace("-", "_"), Path(tech).stem}
    syn.discard(business)
    return sorted(syn)[:6]


def promote_layer(bundle: Path, layer: str = "gold", *, limit: int = 50) -> list[dict]:
    out = []
    for path, fm, body in list_concepts(bundle):
        if fm.get("type") not in ("Table", "View"):
            continue
        if (fm.get("layer") or "").lower() != layer.lower():
            continue
        rel = path.relative_to(bundle).as_posix()
        # skip if already businessized
        links = fm.get("links") or []
        if any(isinstance(l, dict) and l.get("rel") == "businessizes" for l in links):
            continue
        results = promote_concept(bundle, rel)
        out.append({"source": rel, "results": [{"path": p, "action": a} for p, a in results]})
        if len(out) >= limit:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote technical assets to business objects")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--author", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("promote")
    p.add_argument("concept", help="Relative path e.g. tables/gold-orders.md")
    p.add_argument("--name", default=None)
    p.add_argument("--definition", default=None)
    p.add_argument("--owner", default="")
    p.add_argument("--no-glossary", action="store_true")

    p = sub.add_parser("promote-layer")
    p.add_argument("--layer", default="gold")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("humanize")
    p.add_argument("name")

    args = parser.parse_args(argv)
    if args.cmd == "humanize":
        print(humanize(args.name))
        return 0

    from dekc_common import resolve_author
    resolve_author(args.author)
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)

    if args.cmd == "promote":
        results = promote_concept(
            bundle,
            args.concept,
            name=args.name,
            definition=args.definition,
            owner=args.owner,
            also_glossary=not args.no_glossary,
        )
        print(json.dumps([{"path": p, "action": a} for p, a in results], indent=2))
    elif args.cmd == "promote-layer":
        print(json.dumps(promote_layer(bundle, args.layer, limit=args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
