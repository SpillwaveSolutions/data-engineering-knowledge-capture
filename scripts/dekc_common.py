#!/usr/bin/env python3
"""Shared helpers for Data Engineering Knowledge Capture (DEKC).

DEKC extends Project Knowledge Capture (PKC) and stores everything as OKF
concepts (Markdown + YAML frontmatter). It specializes catalogs for data
platforms: schemas, tables, views, queries, lineage, medallion layers,
semantic models, SQL/DAX, dashboards, diagrams/wireframes (Mermaid/PlantUML), data lakes/marts/catalogs, DQ rules, business objects, and glossary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATALOGS = (
    "sources",
    "lakes",
    "marts",
    "catalogs",
    "domains",
    "products",
    "streams",
    "storage",
    "layers",
    "schemas",
    "tables",
    "views",
    "queries",
    "columns",
    "sql",
    "dax",
    "transformations",
    "workflows",
    "lineage",
    "contracts",
    "quality",
    "semantic",
    "metrics",
    "reports",
    "dashboards",
    "diagrams",
    "wireframes",
    "business-objects",
    "glossary",
    "packs",
    "agents",
)

TYPE_TO_DIR = {
    "SourceSystem": "sources",
    "DataLake": "lakes",
    "DataMart": "marts",
    "DataCatalog": "catalogs",
    "DataDomain": "domains",
    "DataProduct": "products",
    "Stream": "streams",
    "StorageLocation": "storage",
    "Layer": "layers",
    "Schema": "schemas",
    "Table": "tables",
    "View": "views",
    "Query": "queries",
    "Column": "columns",
    "SqlArtifact": "sql",
    "DaxArtifact": "dax",
    "Transformation": "transformations",
    "Workflow": "workflows",
    "LineagePath": "lineage",
    "DataContract": "contracts",
    "DQRule": "quality",
    "SemanticModel": "semantic",
    "Metric": "metrics",
    "Report": "reports",
    "Dashboard": "dashboards",
    "Diagram": "diagrams",
    "Wireframe": "wireframes",
    "BusinessObject": "business-objects",
    "GlossaryTerm": "glossary",
    "ContextPack": "packs",
    "AgentNode": "agents",
    "Dataset": "tables",
    "DesignPattern": "packs",
}

DEFAULT_RELATIONS = (
    "depends_on",
    "routes_to",
    "implements",
    "documents",
    "uses",
    "owns",
    "supersedes",
    "related_to",
    "tracks",
    "maps_to",
    "lands_as",
    "feeds",
    "transforms_to",
    "promotes_to",
    "derived_from",
    "reads_from",
    "writes_to",
    "defines",
    "contains",
    "queries",
    "joins",
    "models",
    "measures",
    "visualizes",
    "part_of_mart",
    "part_of_lake",
    "quality_of",
    "validates",
    "consumes_stream",
    "publishes",
    "belongs_to_domain",
    "cataloged_in",
    "stored_in",
    "documents_diagram",
    "implements_contract",
    "glosses",
    "businessizes",
    "sourced_from",
    "layered_as",
    "computes",
    "aggregates",
)

LAYER_ORDER = ("raw", "bronze", "silver", "gold", "platinum")

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)\b(sk|pk|api[_-]?key|token|secret|password|passwd|pwd)[-_]?[a-z0-9]*\s*[:=]\s*['\"]?[^\s'\"\n]{8,}"
        ),
        "[REDACTED_SECRET]",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]

PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (
        re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(text: str, max_len: int = 80) -> str:
    text = text.strip().lower().replace("_", "-")
    text = re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[.\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        text = "untitled"
    return text[:max_len].rstrip("-")


def scrub_text(text: str, *, pii: bool = True, secrets: bool = True) -> tuple[str, list[str]]:
    found: list[str] = []
    out = text
    if secrets:
        for pat, repl in SECRET_PATTERNS:
            if pat.search(out):
                found.append(repl)
            out = pat.sub(repl, out)
    if pii:
        for pat, repl in PII_PATTERNS:
            if pat.search(out):
                found.append(repl)
            out = pat.sub(repl, out)
    labels: list[str] = []
    seen: set[str] = set()
    for f in found:
        if f not in seen:
            seen.add(f)
            labels.append(f)
    return out, labels


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset parser (maps, lists, scalars) — no PyYAML required.

    Supports OKF frontmatter list shapes::

        links:
        - target: /tables/foo.md
          rel: feeds
    """
    root: dict[str, Any] = {}
    # stack entries: (indent, container)
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending_key: str | None = None
    pending_indent = -1

    def pop_to(indent: int) -> None:
        while len(stack) > 1 and stack[-1][0] > indent:
            stack.pop()

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        if line.startswith("- "):
            item = line[2:].strip()
            # Close nested maps until a list or the map that owns pending_key
            while len(stack) > 1 and isinstance(stack[-1][1], dict) and stack[-1][0] >= indent:
                # keep root
                if stack[-1][0] < 0:
                    break
                stack.pop()
            parent = stack[-1][1]

            # Begin list under bare key: (pending)
            if pending_key is not None and indent >= pending_indent:
                owner = None
                for _ind, node in reversed(stack):
                    if isinstance(node, dict) and pending_key in node:
                        owner = node
                        break
                if owner is None and isinstance(parent, dict):
                    owner = parent
                if owner is not None:
                    existing = owner.get(pending_key)
                    if isinstance(existing, list):
                        lst = existing
                    else:
                        lst = []
                        owner[pending_key] = lst
                    # drop empty placeholder dict if still on stack
                    while len(stack) > 1 and stack[-1][1] is existing:
                        stack.pop()
                    stack.append((indent, lst))
                    parent = lst
                    pending_key = None

            # Empty dict placeholder sitting as current parent (value of bare key)
            if isinstance(parent, dict) and len(parent) == 0 and len(stack) >= 2:
                grand = stack[-2][1]
                empty = parent
                if isinstance(grand, dict):
                    for gk, gv in list(grand.items()):
                        if gv is empty:
                            lst = []
                            grand[gk] = lst
                            stack.pop()
                            stack.append((indent, lst))
                            parent = lst
                            pending_key = None
                            break

            if not isinstance(parent, list):
                continue

            if ":" in item and not item.startswith("{"):
                k, _, v = item.partition(":")
                k, v = k.strip(), v.strip()
                obj: dict[str, Any] = {k: _scalar(v) if v and v not in ("|", ">") else None}
                if v in ("|", ">"):
                    obj[k] = ""
                parent.append(obj)
                stack.append((indent, obj))
            else:
                parent.append(_scalar(item))
            continue

        # key: value line
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()

        parent = stack[-1][1]

        # Field of current list-item object (must be MORE indented than `-`)
        if isinstance(parent, dict) and len(stack) >= 2 and isinstance(stack[-2][1], list):
            item_indent = stack[-1][0]
            if indent > item_indent:
                if v == "" or v in ("|", ">"):
                    child: dict[str, Any] = {}
                    parent[k] = child
                    stack.append((indent, child))
                    pending_key = k
                    pending_indent = indent
                elif v.startswith("[") and v.endswith("]"):
                    inner = v[1:-1].strip()
                    items = [_scalar(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
                    parent[k] = items
                    pending_key = None
                else:
                    parent[k] = _scalar(v)
                    pending_key = None
                continue

        # Close list-item dicts and list containers when dedenting to sibling keys
        while len(stack) > 1:
            top_ind, top = stack[-1]
            if isinstance(top, dict) and len(stack) >= 2 and isinstance(stack[-2][1], list):
                if indent <= top_ind:
                    stack.pop()
                    continue
            if isinstance(top, list) and indent <= top_ind:
                stack.pop()
                continue
            if top_ind > indent:
                stack.pop()
                continue
            break
        parent = stack[-1][1]

        if isinstance(parent, list):
            continue

        if not isinstance(parent, dict):
            continue

        if v == "" or v in ("|", ">"):
            child = {}
            parent[k] = child
            stack.append((indent, child))
            pending_key = k
            pending_indent = indent
        elif v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            items = [_scalar(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
            parent[k] = items
            pending_key = None
        else:
            parent[k] = _scalar(v)
            pending_key = None
    return root



def _scalar(v: str) -> Any:
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v in ("null", "Null", "~", ""):
        return None
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def load_config(repo_root: Path) -> dict[str, Any]:
    for path in (
        repo_root / ".dekc" / "config.yml",
        repo_root / ".dekc" / "config.yaml",
        repo_root / ".pkc" / "config.yml",
        repo_root / ".work" / "config.yml",
    ):
        if path.is_file():
            data = _parse_simple_yaml(path.read_text(encoding="utf-8"))
            return data.get("dekc") or data.get("pkc") or {}
    return {}


def resolve_knowledge_root(repo_root: Path, override: str | None = None) -> Path:
    if override:
        root = Path(override)
        return root if root.is_absolute() else (repo_root / root)
    cfg = load_config(repo_root)
    name = cfg.get("knowledge_root") or "knowledge"
    for candidate in (
        repo_root / name,
        repo_root / "sample-knowledge",
        repo_root / ".okf",
        repo_root / "knowledge",
    ):
        if candidate.is_dir() and (candidate / "index.md").is_file():
            return candidate
    return repo_root / name


def path_for_type(type_name: str, slug: str) -> str:
    directory = TYPE_TO_DIR.get(type_name, "tables")
    return f"{directory}/{slug}.md"


def concept_ref(target: str, default_catalog: str = "tables") -> str:
    t = target.strip()
    if t.startswith("/"):
        return t
    if "/" in t and t.endswith(".md"):
        return "/" + t.lstrip("/")
    if t.endswith(".md"):
        return f"/{default_catalog}/{slugify(t[:-3])}.md"
    return f"/{default_catalog}/{slugify(t)}.md"


def dump_frontmatter(fm: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fm.items():
        lines.append(_yaml_line(key, value, 0))
    lines.append("---")
    return "\n".join(lines) + "\n"


def _yaml_line(key: str, value: Any, indent: int) -> str:
    pad = "  " * indent
    if isinstance(value, bool):
        return f"{pad}{key}: {'true' if value else 'false'}"
    if value is None:
        return f"{pad}{key}: null"
    if isinstance(value, (int, float)):
        return f"{pad}{key}: {value}"
    if isinstance(value, str):
        if value == "" or any(c in value for c in ":#{}[]&*!|>%@`\'\"\n") or value.lower() in (
            "true",
            "false",
            "null",
        ):
            esc = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'{pad}{key}: "{esc}"'
        return f"{pad}{key}: {value}"
    if isinstance(value, list):
        if not value:
            return f"{pad}{key}: []"
        if all(isinstance(x, str) for x in value) and len(value) <= 8 and all(
            len(x) < 40 and not any(c in x for c in ":#[]{}") for x in value
        ):
            return f"{pad}{key}: [{', '.join(value)}]"
        out = [f"{pad}{key}:"]
        for item in value:
            if isinstance(item, dict):
                first = True
                for ik, iv in item.items():
                    if first:
                        line = _yaml_line(ik, iv, indent + 1)
                        stripped = line[len(pad) + 2 :] if line.startswith(pad + "  ") else line.lstrip()
                        out.append(f"{pad}- {stripped}")
                        first = False
                    else:
                        out.append(_yaml_line(ik, iv, indent + 1))
            else:
                out.append(f"{pad}- {_scalar_dump(item)}")
        return "\n".join(out)
    if isinstance(value, dict):
        if not value:
            return f"{pad}{key}: {{}}"
        out = [f"{pad}{key}:"]
        for ik, iv in value.items():
            out.append(_yaml_line(ik, iv, indent + 1))
        return "\n".join(out)
    return f"{pad}{key}: {value}"


def _scalar_dump(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in ":#{}[]&*!|>%@`\'\"\n") or s.lower() in ("true", "false", "null"):
        esc = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'
    return s


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = _parse_simple_yaml(m.group(1))
    body = text[m.end() :]
    return fm, body


def write_concept(
    bundle: Path,
    rel_path: str,
    frontmatter: dict[str, Any],
    body: str,
    *,
    force: bool = False,
) -> tuple[Path, str]:
    path = bundle / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    stable = frontmatter.pop("stable_timestamp", False)
    if path.is_file() and not force:
        old_fm, old_body = parse_frontmatter(path.read_text(encoding="utf-8"))
        for keep in ("timestamp", "wiki_key"):
            if keep in old_fm and keep in frontmatter and stable:
                frontmatter[keep] = old_fm[keep]

        def fingerprint(fm: dict[str, Any], b: str) -> str:
            copy = {k: v for k, v in fm.items() if k != "timestamp"}
            raw = json.dumps(copy, sort_keys=True, default=str) + "\n" + b.strip()
            return hashlib.sha256(raw.encode()).hexdigest()

        if fingerprint(old_fm, old_body) == fingerprint(frontmatter, body):
            return path, "skipped"
        if stable and "timestamp" in old_fm:
            frontmatter["timestamp"] = old_fm["timestamp"]
        fm = {k: v for k, v in frontmatter.items()}
        path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")
        return path, "updated"
    fm = {k: v for k, v in frontmatter.items()}
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")
    return path, "created"


def add_typed_link(fm: dict[str, Any], target: str, rel: str) -> dict[str, Any]:
    links = list(fm.get("links") or [])
    target = target if target.startswith("/") else f"/{target.lstrip('/')}"
    for link in links:
        if isinstance(link, dict) and link.get("target") == target and link.get("rel") == rel:
            return fm
    links.append({"target": target, "rel": rel})
    fm["links"] = links
    return fm


def ensure_catalog_index(bundle: Path, catalog: str, title: str | None = None) -> Path:
    cat_dir = bundle / catalog
    cat_dir.mkdir(parents=True, exist_ok=True)
    index = cat_dir / "index.md"
    if index.is_file():
        return index
    t = title or catalog.replace("-", " ").title()
    fm = {
        "type": "Catalog",
        "title": t,
        "description": f"Catalog of {t.lower()} concepts",
        "timestamp": utc_now(),
        "tags": ["catalog", catalog, "dekc"],
    }
    body = f"# {t}\n\nConcepts in this catalog:\n\n_None yet._\n"
    index.write_text(dump_frontmatter(fm) + "\n" + body, encoding="utf-8")
    return index


def refresh_catalog_index(bundle: Path, catalog: str) -> None:
    cat_dir = bundle / catalog
    if not cat_dir.is_dir():
        return
    ensure_catalog_index(bundle, catalog)
    index = cat_dir / "index.md"
    fm, _ = parse_frontmatter(index.read_text(encoding="utf-8"))
    title = fm.get("title") or catalog.replace("-", " ").title()
    fm["timestamp"] = fm.get("timestamp") or utc_now()
    fm.setdefault("type", "Catalog")
    entries = []
    for p in sorted(cat_dir.glob("*.md")):
        if p.name == "index.md":
            continue
        fm_c, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        label = fm_c.get("title") or p.stem
        layer = fm_c.get("layer")
        suffix = f" · {layer}" if layer else ""
        entries.append(f"- [{label}](/{catalog}/{p.name}){suffix}")
    body = f"# {title}\n\nConcepts in this catalog:\n\n"
    body += "\n".join(entries) + ("\n" if entries else "_None yet._\n")
    index.write_text(dump_frontmatter(fm) + "\n" + body, encoding="utf-8")


def append_log(bundle: Path, message: str) -> None:
    log = bundle / "log.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"- {utc_now()}: {message}\n"
    if not log.is_file():
        log.write_text(
            f"---\ntitle: Change log\ndescription: DEKC knowledge bundle log\ntimestamp: {utc_now()}\ntags: [dekc, log]\n---\n\n# Change log\n\n## {today}\n\n{entry}",
            encoding="utf-8",
        )
        return
    text = log.read_text(encoding="utf-8")
    heading = f"## {today}"
    if heading in text:
        text = text.replace(heading + "\n", heading + "\n\n" + entry, 1)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = text.rstrip() + f"\n\n{heading}\n\n{entry}"
    log.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def ensure_bundle(bundle: Path, title: str = "Data Engineering Knowledge") -> None:
    bundle.mkdir(parents=True, exist_ok=True)
    for catalog in CATALOGS:
        ensure_catalog_index(bundle, catalog)
    for layer in ("bronze", "silver", "gold"):
        rel = path_for_type("Layer", layer)
        if not (bundle / rel).is_file():
            fm = {
                "type": "Layer",
                "title": f"{layer.title()} layer",
                "description": f"Medallion {layer} zone",
                "layer": layer,
                "tags": ["layer", "medallion", layer],
                "timestamp": utc_now(),
                "status": "active",
                "verified": True,
                "wiki_key": f"layer-{layer}",
                "truth_state": "current",
            }
            body = f"# {layer.title()} layer\n\nMedallion **{layer}** zone for curated data products.\n"
            write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "layers")

    index = bundle / "index.md"
    if not index.is_file():
        catalogs_md = "\n".join(
            f"- [{c.replace('-', ' ').title()}](/{c}/index.md)" for c in CATALOGS if c != "packs"
        )
        content = f"""---
okf_version: "0.2"
title: {title}
description: Data Engineering Knowledge Capture bundle — schemas, lineage, medallion layers, semantic models, and business glossary as an OKF graph. Depends on PKC + OKF.
timestamp: {utc_now()}
tags: [dekc, pkc, okf, data-engineering, medallion]
depends_on: [project-knowledge-capture, okf-graph-eng]
---

# {title}

Git-native second brain for data platforms. Agents walk lakes and warehouses,
capture technical assets, reconstruct lineage, and materialize **business objects**
with glossary definitions.

## Stack

| Layer | Role |
|-------|------|
| **OKF** | Graph format + impact / pack / validate |
| **PKC** | Project reasoning capture (meetings, decisions, features) |
| **DEKC (this)** | Data assets, lineage, semantic layer, business glossary |

## Medallion

- [Bronze](/layers/bronze.md) · [Silver](/layers/silver.md) · [Gold](/layers/gold.md)

## Catalogs

{catalogs_md}

## Change log

See [log.md](/log.md).
"""
        index.write_text(content, encoding="utf-8")
    if not (bundle / "log.md").is_file():
        append_log(bundle, "Bundle created for Data Engineering Knowledge Capture")


def list_concepts(bundle: Path) -> list[tuple[Path, dict[str, Any], str]]:
    out: list[tuple[Path, dict[str, Any], str]] = []
    for path in sorted(bundle.rglob("*.md")):
        if path.name in ("log.md",) or path.name.startswith("."):
            continue
        rel = path.relative_to(bundle).as_posix()
        if rel == "index.md":
            continue
        # skip .index folder
        if ".index" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if not fm:
            continue
        if fm.get("type") == "Catalog":
            continue
        out.append((path, fm, body))
    return out


def cmd_init_bundle(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    bundle = repo / args.bundle
    ensure_bundle(bundle, title=args.title)
    print(f"Initialized DEKC bundle at {bundle}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC common utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init-bundle", help="Scaffold a DEKC OKF knowledge bundle")
    p.add_argument("--repo", default=".")
    p.add_argument("--bundle", default="knowledge")
    p.add_argument("--title", default="Data Engineering Knowledge")
    p.set_defaults(func=cmd_init_bundle)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
