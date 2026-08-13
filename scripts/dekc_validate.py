#!/usr/bin/env python3
"""Validate a DEKC OKF bundle structure and links."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import CATALOGS, list_concepts, parse_frontmatter, resolve_knowledge_root  # noqa: E402

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def validate_bundle(bundle: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    if not (bundle / "index.md").is_file():
        errors.append("missing root index.md")
    else:
        text = (bundle / "index.md").read_text(encoding="utf-8")
        if "okf_version" not in text:
            warnings.append("root index.md missing okf_version")

    if not (bundle / "log.md").is_file():
        warnings.append("missing log.md")

    for catalog in CATALOGS:
        d = bundle / catalog
        if d.is_dir() and not (d / "index.md").is_file():
            warnings.append(f"catalog {catalog}/ missing index.md")

    concepts = list_concepts(bundle)
    paths = {path.relative_to(bundle).as_posix() for path, _, _ in concepts}
    paths.add("index.md")
    paths.add("log.md")
    for catalog in CATALOGS:
        paths.add(f"{catalog}/index.md")

    required = ("type", "title")
    for path, fm, body in concepts:
        rel = path.relative_to(bundle).as_posix()
        for field in required:
            if field not in fm:
                errors.append(f"{rel}: missing frontmatter field `{field}`")
        for link in fm.get("links") or []:
            if not isinstance(link, dict):
                warnings.append(f"{rel}: non-object link entry")
                continue
            tgt = (link.get("target") or "").lstrip("/")
            if tgt and tgt not in paths and not (bundle / tgt).is_file():
                errors.append(f"{rel}: broken typed link → /{tgt}")
        for m in LINK_RE.finditer(body):
            href = m.group(2).split("#")[0].split("?")[0]
            if not href.startswith("/") or href.startswith("//"):
                continue
            tgt = href.lstrip("/")
            if tgt and not (bundle / tgt).is_file():
                errors.append(f"{rel}: broken markdown link → {href}")

    # medallion presence
    for layer in ("bronze", "silver", "gold"):
        if not (bundle / "layers" / f"{layer}.md").is_file():
            warnings.append(f"missing medallion layer concept layers/{layer}.md")

    return {
        "bundle": str(bundle),
        "concept_count": len(concepts),
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "ok": len(errors) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    report = validate_bundle(bundle)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"DEKC validate: {bundle}")
        print(f"  concepts: {report['concept_count']}")
        print(f"  errors:   {len(report['errors'])}")
        print(f"  warnings: {len(report['warnings'])}")
        for e in report["errors"]:
            print(f"  ERROR  {e}")
        for w in report["warnings"]:
            print(f"  WARN   {w}")
        print("OK" if report["ok"] else "FAILED")
    if not report["ok"]:
        return 1
    if args.strict and report["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
