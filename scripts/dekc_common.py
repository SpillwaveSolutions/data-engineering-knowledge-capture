#!/usr/bin/env python3
"""Shared helpers for Data Engineering Knowledge Capture (DEKC).

DEKC extends Project Knowledge Capture (PKC) and stores everything as OKF
concepts (Markdown + YAML frontmatter). It specializes catalogs for data
platforms: schemas, tables, views, queries, lineage, medallion layers,
semantic models, SQL/DAX, dashboards, diagrams/wireframes (Mermaid/PlantUML), data lakes/marts/catalogs, DQ rules, business objects, and glossary.
"""

from __future__ import annotations

import argparse
import contextvars
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
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
    "ingestion",
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
    "write-events",
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
    "IngestionJob": "ingestion",
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
    "WriteEvent": "write-events",
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
    "ingested_by",
    "lands_into",
    "ingests_from",
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
    "refreshes",
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
    """Stable filename slug.

    `|` is kept as a `pipe` token so ``Operations | Executive`` and
    ``Operations  Executive`` (two spaces) do not collide (#29).
    """
    text = text.strip().lower().replace("_", "-")
    text = text.replace("|", "-pipe-")
    text = re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[.\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        text = "untitled"
    return text[:max_len].rstrip("-")


DEKC_OWNED_TYPES = frozenset(
    {
        "BusinessObject",
        "Column",
        "DQRule",
        "Dashboard",
        "DataCatalog",
        "DataContract",
        "DataDomain",
        "DataLake",
        "DataMart",
        "DataProduct",
        "Dataset",
        "DaxArtifact",
        "DesignPattern",
        "GlossaryTerm",
        "IngestionJob",
        "Layer",
        "LineagePath",
        "Metric",
        "Query",
        "Report",
        "Schema",
        "SemanticModel",
        "SourceSystem",
        "SqlArtifact",
        "StorageLocation",
        "Stream",
        "Table",
        "Transformation",
        "View",
    }
)

VIEW_NAME_RE = re.compile(r"(?i)^(x[_-]?)?vw[_-]?")


def looks_like_view(name: str, sql: str = "", kind: str | None = None) -> bool:
    """Warehouse gold `vw*` / `x_vw*` and CREATE VIEW are Views, not Tables (#42)."""
    k = (kind or "auto").strip().lower()
    if k == "view":
        return True
    if k == "table":
        return False
    if sql and re.search(r"(?i)create\s+(or\s+replace\s+)?view\b", sql):
        return True
    return bool(VIEW_NAME_RE.search((name or "").strip()))


def capture_verified(*, verified: bool | None, sql: str = "", columns: Any = None, evidence: bool = False) -> bool:
    """Existence-only captures default unverified. SQL/columns/evidence auto-verify (#30)."""
    if verified is not None:
        return bool(verified)
    return bool(sql) or bool(columns) or evidence


def capture_truth_state(verified: bool, truth_state: str = "") -> str:
    if truth_state:
        return truth_state
    return "current" if verified else "snapshot"


def attach_identity(fm: dict[str, Any], **fields: Any) -> dict[str, Any]:
    """Copy optional Fabric / Power BI identity keys when non-empty (#41)."""
    mapping = {
        "fabric_item_id": ("fabric_item_id", "fabric_id", "id"),
        "fabric_workspace": ("fabric_workspace", "workspace"),
        "fabric_workspace_id": ("fabric_workspace_id", "workspace_id"),
        "pbi_dataset_id": ("pbi_dataset_id", "dataset_id"),
        "datasources_status": ("datasources_status",),
        "fabric_type": ("fabric_type",),
    }
    for dest, keys in mapping.items():
        for k in keys:
            val = fields.get(k)
            if val not in (None, ""):
                fm[dest] = val
                break
    return fm


def slug_for_capture(
    name: str,
    *,
    slug: str = "",
    fabric_item_id: str = "",
    prefix: str = "",
    max_len: int = 80,
) -> str:
    if slug:
        return slugify(slug, max_len=max_len)
    base = slugify(f"{prefix}-{name}" if prefix else name, max_len=max_len if not fabric_item_id else max_len - 9)
    if fabric_item_id:
        short = re.sub(r"[^a-fA-F0-9]", "", fabric_item_id)[:8].lower()
        if short:
            return slugify(f"{base}-{short}", max_len=max_len)
    return base


def write_events_enabled(explicit: bool | None = None) -> bool:
    """WriteEvents are opt-in. Default off so bulk capture does not flood git (#37)."""
    if explicit is not None:
        return bool(explicit)
    val = (os.environ.get("DEKC_WRITE_EVENTS") or "0").strip().lower()
    return val in ("1", "true", "yes", "on")


def as_text(value: Any) -> str:
    """Coerce frontmatter fields to str so mixed-bundle dicts cannot crash graders (#27)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return ""
    return str(value)


def iter_typed_edges(fm: dict[str, Any]) -> list[tuple[str, str]]:
    """Yield (target, rel) from OKF `links[]` and PKC `rel:` maps (#40)."""
    out: list[tuple[str, str]] = []
    for link in fm.get("links") or []:
        if isinstance(link, dict):
            tgt = link.get("target") or ""
            if tgt:
                out.append((tgt, link.get("rel") or "related_to"))
        elif isinstance(link, str) and link:
            out.append((link, "related_to"))
    rel_map = fm.get("rel")
    if isinstance(rel_map, dict):
        for rel, targets in rel_map.items():
            if isinstance(targets, str):
                targets = [targets]
            if not isinstance(targets, list):
                continue
            for t in targets:
                if isinstance(t, str) and t:
                    tgt = t if t.startswith("/") else "/" + t.lstrip("/")
                    out.append((tgt, rel))
                elif isinstance(t, dict) and t.get("target"):
                    out.append((t["target"], rel))
    return out


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


def _fold_block(lines: list[str]) -> str:
    """YAML `>` folding: newlines → spaces, blank lines → paragraph breaks."""
    paragraphs: list[str] = []
    para: list[str] = []
    for line in lines:
        if line == "":
            if para:
                paragraphs.append(" ".join(para))
                para = []
            # keep paragraph break; consecutive blanks collapse later
            if paragraphs and paragraphs[-1] != "":
                paragraphs.append("")
        else:
            para.append(line.rstrip())
    if para:
        paragraphs.append(" ".join(para))
    while paragraphs and paragraphs[-1] == "":
        paragraphs.pop()
    return "\n\n".join(p for p in paragraphs if p != "" or True).replace("\n\n\n", "\n\n").strip()


def _read_block_scalar(
    lines: list[str], start: int, parent_indent: int, *, folded: bool
) -> tuple[str, int]:
    """Collect a `|` / `>` block. Returns (value, next_index)."""
    i = start
    collected: list[str] = []
    content_indent: int | None = None
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            if content_indent is None:
                i += 1
                continue
            collected.append("")
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent <= parent_indent:
            break
        if content_indent is None:
            content_indent = indent
        collected.append(raw[content_indent:] if len(raw) >= content_indent else raw.lstrip())
        i += 1
    while collected and collected[-1] == "":
        collected.pop()
    if folded:
        return _fold_block(collected), i
    return "\n".join(collected), i


def _is_block_scalar(v: str) -> str | None:
    """Return 'folded' / 'literal' / None. Accepts `>`, `|`, `>-`, `|+`, etc."""
    if not v:
        return None
    m = re.match(r"^([|>])[+-]?\d*$", v)
    if not m:
        return None
    return "folded" if m.group(1) == ">" else "literal"


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset parser (maps, lists, scalars) — no PyYAML required.

    Supports OKF frontmatter list shapes::

        links:
        - target: /tables/foo.md
          rel: feeds

    And PKC folded/literal scalars (#26)::

        description: >
          Graph mailbox collection lands outlook_messages.
        rel:
          related_to:
            - /tables/outlook-messages.md
    """
    raw_lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending_key: str | None = None
    pending_indent = -1
    i = 0
    n = len(raw_lines)

    while i < n:
        raw = raw_lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        if line.startswith("- "):
            item = line[2:].strip()
            while len(stack) > 1 and isinstance(stack[-1][1], dict) and stack[-1][0] >= indent:
                if stack[-1][0] < 0:
                    break
                stack.pop()
            parent = stack[-1][1]

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
                    while len(stack) > 1 and stack[-1][1] is existing:
                        stack.pop()
                    stack.append((indent, lst))
                    parent = lst
                    pending_key = None

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
                i += 1
                continue

            if ":" in item and not item.startswith("{"):
                k, _, v = item.partition(":")
                k, v = k.strip(), v.strip()
                style = _is_block_scalar(v)
                obj: dict[str, Any]
                if style:
                    block, i = _read_block_scalar(
                        raw_lines, i + 1, indent, folded=style == "folded"
                    )
                    obj = {k: block}
                    parent.append(obj)
                    stack.append((indent, obj))
                    continue
                obj = {k: _scalar(v) if v else None}
                parent.append(obj)
                stack.append((indent, obj))
            else:
                parent.append(_scalar(item))
            i += 1
            continue

        if ":" not in line:
            i += 1
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()

        parent = stack[-1][1]

        if isinstance(parent, dict) and len(stack) >= 2 and isinstance(stack[-2][1], list):
            item_indent = stack[-1][0]
            if indent > item_indent:
                style = _is_block_scalar(v)
                if style:
                    block, i = _read_block_scalar(
                        raw_lines, i + 1, indent, folded=style == "folded"
                    )
                    parent[k] = block
                    pending_key = None
                    continue
                if v == "":
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
                i += 1
                continue

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
            i += 1
            continue

        if not isinstance(parent, dict):
            i += 1
            continue

        style = _is_block_scalar(v)
        if style:
            block, i = _read_block_scalar(
                raw_lines, i + 1, indent, folded=style == "folded"
            )
            parent[k] = block
            pending_key = None
            continue
        if v == "":
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
        i += 1
    return root



def _unescape(s: str) -> str:
    """Reverse the escaping the dumper applies to a quoted scalar.

    Without this, `parse(dump(x)) != x` for any value containing a quote or a
    backslash: the dumper escapes, the reader only strips the quotes, and every
    read-modify-write cycle re-escapes what was already escaped. Backslash count
    doubles per pass, so a script that edits one field corrupts every quoted
    string in the file -- and `write_concept` and `refresh_catalog_index` both
    do exactly that read-modify-write.

    Self-concealing: reading the file back with this same parser returns a value
    that looks right, so the damage lives only in the bytes on disk.

    Single-pass, so a literal backslash-quote in the source survives intact.
    """
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in ('"', "'", "\\"):
            out.append(s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _scalar(v: str) -> Any:
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v in ("null", "Null", "~", ""):
        return None
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return _unescape(v[1:-1])
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
    intended = repo_root / name
    for candidate in (
        intended,
        repo_root / "sample-knowledge",
        repo_root / ".okf",
        repo_root / "knowledge",
    ):
        if candidate.is_dir() and (candidate / "index.md").is_file():
            # Say so when we did NOT land on the intended root. There are 16
            # call sites and only dekc_doctor announced the bundle it used, so
            # with any other command you could not tell. This repo ships a
            # sample-knowledge/, so a capture run inside a clone before
            # initializing a bundle silently wrote there.
            if candidate != intended:
                print(
                    f"dekc: '{intended}' is not an initialized bundle; "
                    f"using '{candidate}' instead. Pass --bundle to be explicit.",
                    file=sys.stderr,
                )
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


def resolve_concept_ref(
    bundle: Path | None,
    target: str,
    default_catalog: str = "tables",
) -> str:
    """Resolve a name or path. Absolute paths win; else search catalogs (#32, #41)."""
    t = target.strip()
    if t.startswith("/") or ("/" in t and t.endswith(".md")):
        return concept_ref(t, default_catalog)
    if bundle is None:
        return concept_ref(t, default_catalog)
    slug = slugify(t)
    catalogs = [
        default_catalog,
        "tables",
        "views",
        "lakes",
        "semantic",
        "reports",
        "dashboards",
        "sources",
        "ingestion",
        "metrics",
        "layers",
    ]
    seen: set[str] = set()
    for cat in catalogs:
        if cat in seen:
            continue
        seen.add(cat)
        d = bundle / cat
        if not d.is_dir():
            continue
        exact = d / f"{slug}.md"
        if exact.is_file():
            return f"/{cat}/{exact.name}"
        for p in d.glob("*.md"):
            if p.name == "index.md":
                continue
            if p.stem == slug or p.stem.endswith("-" + slug):
                return f"/{cat}/{p.name}"
    return concept_ref(t, default_catalog)


def dump_frontmatter(fm: dict[str, Any]) -> str:
    # Fail closed on corrupted description maps (#26): never write a nested
    # description back out and swallow timestamp/rel/status.
    safe = dict(fm)
    desc = safe.get("description")
    if desc is not None and not isinstance(desc, str):
        safe["description"] = as_text(desc)
    lines = ["---"]
    for key, value in safe.items():
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


def same_identity(old_fm: dict[str, Any], new_fm: dict[str, Any]) -> bool:
    old_id = old_fm.get("fabric_item_id") or ""
    new_id = new_fm.get("fabric_item_id") or ""
    if old_id and new_id:
        return old_id == new_id
    return (old_fm.get("title") or "") == (new_fm.get("title") or "")


def unique_rel_path(bundle: Path, rel_path: str, frontmatter: dict[str, Any]) -> str:
    """If dest exists with a different title / fabric_item_id, suffix -2, -3 (#29)."""
    rel_path = rel_path.lstrip("/")
    path = Path(rel_path)
    stem, suffix, parent = path.stem, path.suffix, path.parent
    candidate = rel_path
    n = 2
    while n <= 50:
        dest = bundle / candidate
        if not dest.is_file():
            return candidate
        old_fm, _ = parse_frontmatter(dest.read_text(encoding="utf-8"))
        if same_identity(old_fm, frontmatter):
            return candidate
        candidate = str(parent / f"{stem}-{n}{suffix}")
        n += 1
    return candidate


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


_AUTHOR: contextvars.ContextVar[str] = contextvars.ContextVar("dekc_author", default="")


def resolve_author(explicit: str | None = None) -> str:
    """Fail-closed identity claim. Prefer --author, else SECOND_BRAIN_IDENTITY."""
    author = (explicit or os.environ.get("SECOND_BRAIN_IDENTITY") or "").strip()
    if not author:
        print(
            json.dumps(
                {
                    "error": "claim an identity first",
                    "hint": "pass --author or set SECOND_BRAIN_IDENTITY",
                }
            )
        )
        raise SystemExit(1)
    _AUTHOR.set(author)
    return author


def emit_write_event(
    bundle: Path,
    *,
    author: str,
    typ: str,
    dest: Path,
    host: str = "",
) -> Path | None:
    """Record a WriteEvent node for a successful knowledge write. Skip self."""
    if typ == "WriteEvent":
        return None
    try:
        rel = "/" + str(dest.relative_to(bundle)).replace("\\", "/")
    except ValueError:
        rel = "/" + dest.name
    event_id = f"{int(datetime.now(timezone.utc).timestamp())}-{secrets.token_hex(3)}"
    ev_rel = f"write-events/{event_id}.md"
    fm = {
        "type": "WriteEvent",
        "title": f"write {typ} {dest.name}",
        "status": "recorded",
        "timestamp": utc_now(),
        "author": author,
        "tags": ["write-event", typ.lower()],
        "links": [{"target": rel, "rel": "documents"}],
    }
    body = (
        f"# Write {typ}\n\n"
        f"- actor: `{author}`\n"
        f"- host: `{host or 'unknown'}`\n"
        f"- path: `{rel}`\n"
        f"- type: `{typ}`\n"
    )
    write_concept(bundle, ev_rel, fm, body, force=True)
    ensure_catalog_index(bundle, "write-events", "Write Events")
    return bundle / ev_rel


def write_knowledge(
    bundle: Path,
    rel_path: str,
    frontmatter: dict[str, Any],
    body: str,
    *,
    author: str | None = None,
    host: str | None = None,
    force: bool = False,
    emit_event: bool | None = None,
) -> tuple[Path, str]:
    """Stamp author, write via write_concept, emit WriteEvent on created/updated.

    write_concept stays pure. Callers that own a knowledge write go through here.
    WriteEvents are opt-in (`DEKC_WRITE_EVENTS=1` or emit_event=True) so a 67-item
    Fabric capture does not mint 70 gitignored-or-not files (#37).
    """
    claimed = (author or "").strip() or _AUTHOR.get()
    if not claimed:
        claimed = resolve_author(author)
    fm = {**frontmatter, "author": claimed}
    rel_path = unique_rel_path(bundle, rel_path, fm)
    path, action = write_concept(bundle, rel_path, fm, body, force=force)
    if write_events_enabled(emit_event) and action in ("created", "updated"):
        emit_write_event(
            bundle,
            author=claimed,
            typ=str(fm.get("type") or "Concept"),
            dest=path,
            host=host if host is not None else os.environ.get("SECOND_BRAIN_HOST", ""),
        )
    return path, action


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


# Catalogs the sibling capture plugins also declare. Their renderers emit a bare
# `- [label](path)` with no annotation, so adding ours to a shared catalog makes
# the file flip on every alternation between plugins. Scope the annotation to
# catalogs only this plugin owns; correctness of a shared bundle beats a nicety.
_SAC_SHARED_CATALOGS = frozenset(
    {"agents", "diagrams", "domains", "glossary", "packs", "products",
     "storage", "workflows"}
)


def _escape_link_label(label: Any) -> str:
    """Make a concept title safe to use as a Markdown link label.

    An unescaped `[AREA]` title renders as `[[AREA]](/cat/x.md)`, which the OKF
    graph reader's link regex cannot match. That yields a MISSING edge rather
    than a broken one, and validate reports only broken edges -- so the concept
    silently loses its catalog backlink.

    YAML titles may also be typed scalars (for example integers or booleans),
    so normalize to text at this rendering boundary. Untyped, one bad title
    aborts the whole catalog refresh after ingestion already wrote concepts.
    """
    return str(label).replace("[", "\\[").replace("]", "\\]")


def refresh_catalog_index(bundle: Path, catalog: str) -> None:
    # Refuse catalogs this plugin does not declare, so an outside caller cannot
    # drive this renderer over a sibling plugin's catalog. Note this alone does
    # NOT stabilise a shared bundle -- for a catalog two plugins both declare it
    # passes in both. That is what the annotation scoping below is for.
    if catalog not in CATALOGS:
        return
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
        # `or` alone sends a falsy-but-real title (`0`, `false`) to the stem.
        title_value = fm_c.get("title")
        label = _escape_link_label(
            p.stem if title_value is None or title_value == "" else title_value
        )
        layer = fm_c.get("layer")
        # Only annotate catalogs no sibling plugin renders. On a shared catalog
        # the annotation is what makes the file churn back and forth.
        suffix = (
            f" · {layer}" if layer and catalog not in _SAC_SHARED_CATALOGS else ""
        )
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


# ── ripgrep accelerator (optional; never a dependency) ──────────────────

RG_ENV_VARS = ("DEKC_RG_PATH", "PKC_RG_PATH", "OKF_RG_PATH", "SECOND_BRAIN_RG_PATH")

RG_INSTALL_HINTS = {
    "darwin": ["brew install ripgrep"],
    "linux": [
        "sudo apt-get install -y ripgrep",
        "sudo dnf install -y ripgrep",
        "cargo install ripgrep",
    ],
    "win32": ["winget install BurntSushi.ripgrep.MSVC"],
}

RG_DEFAULT_GLOBS = ["*.md", "!**/packs/**"]


def find_rg(*, env_vars: tuple[str, ...] = RG_ENV_VARS) -> str | None:
    """Return an rg binary path, or None. Override with DEKC_RG_PATH / OKF_RG_PATH."""
    for var in env_vars:
        override = (os.environ.get(var) or "").strip()
        if not override:
            continue
        p = Path(override)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
        found = shutil.which(override)
        if found:
            return found
    return shutil.which("rg")


def rg_install_hints() -> list[str]:
    if sys.platform == "darwin":
        return list(RG_INSTALL_HINTS["darwin"])
    if sys.platform.startswith("linux"):
        return list(RG_INSTALL_HINTS["linux"])
    if sys.platform == "win32":
        return list(RG_INSTALL_HINTS["win32"])
    return ["cargo install ripgrep"]


def toolchain_report() -> dict[str, Any]:
    """Doctor payload: python, rg, sqlite FTS5. Zero pip deps."""
    rg = find_rg()
    fts5 = False
    sqlite_version = None
    try:
        import sqlite3

        sqlite_version = sqlite3.sqlite_version
        con = sqlite3.connect(":memory:")
        opts = [row[0] for row in con.execute("pragma compile_options")]
        fts5 = any("FTS5" in opt.upper() for opt in opts)
        con.close()
    except Exception:
        pass
    return {
        "python": sys.version.split()[0],
        "rg": {
            "found": bool(rg),
            "path": rg,
            "hints": rg_install_hints(),
        },
        "sqlite": {"version": sqlite_version, "fts5": fts5},
    }


def is_concept_path(bundle: Path, path: Path) -> bool:
    """Same skip rules as iter_concept_paths: not index.md, log.md, packs/, or cache dirs."""
    if path.suffix.lower() not in {".md", ".markdown"}:
        return False
    if path.name in {"index.md", "log.md"}:
        return False
    try:
        parts = path.resolve().relative_to(bundle.resolve()).parts
    except ValueError:
        return False
    if any(part in {".index", ".dekc", ".pkc", "packs"} for part in parts):
        return False
    return True


def iter_concept_paths(bundle: Path) -> list[Path]:
    """Markdown concept files. Skips catalogs (index.md), logs, packs, disposable caches."""
    files: list[Path] = []
    skip_names = {"index.md", "log.md"}
    skip_dirs = {".index", ".dekc", ".pkc", "packs"}
    for p in sorted(bundle.rglob("*.md")):
        if p.name in skip_names or p.name.startswith("."):
            continue
        if any(part in skip_dirs for part in p.parts):
            continue
        files.append(p)
    return files


def rg_list_files(
    root: Path,
    patterns: list[str],
    *,
    fixed_string: bool = False,
    ignore_case: bool = True,
    globs: list[str] | None = None,
    timeout: float = 30.0,
) -> list[Path] | None:
    """AND-intersect `rg -l` results.

    Returns None when rg is missing or the process fails (caller must full-scan).
    Returns [] when rg ran and matched nothing — that is a real empty hit set,
    not a fallback.
    """
    rg = find_rg()
    if not rg:
        return None
    terms = [p for p in patterns if p]
    if not terms:
        return None
    root = root.resolve()
    use_globs = list(RG_DEFAULT_GLOBS if globs is None else globs)
    matched: set[Path] | None = None
    for pat in terms:
        cmd = [rg, "-l", "--no-messages", "--color", "never"]
        if ignore_case:
            cmd.append("-i")
        if fixed_string:
            cmd.append("-F")
        for g in use_globs:
            cmd.extend(["--glob", g])
        cmd.extend(["--", pat, str(root)])
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        # 0 = hits, 1 = no matches, anything else = rg error → fall back
        if proc.returncode not in (0, 1):
            return None
        files: set[Path] = set()
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            p = p.resolve() if p.is_absolute() else (root / p).resolve()
            files.add(p)
        matched = files if matched is None else (matched & files)
        if not matched:
            return []
    return sorted(matched or [])


def list_concepts(
    bundle: Path,
    *,
    types: set[str] | frozenset[str] | None = None,
    prefixes: list[str] | None = None,
    tags: list[str] | None = None,
    since: str | None = None,
) -> list[tuple[Path, dict[str, Any], str]]:
    out: list[tuple[Path, dict[str, Any], str]] = []
    prefix_list = [p.lstrip("/") for p in (prefixes or []) if p]
    tag_set = {t.lower() for t in (tags or []) if t}
    for path in sorted(bundle.rglob("*.md")):
        if path.name in ("log.md",) or path.name.startswith("."):
            continue
        rel = path.relative_to(bundle).as_posix()
        if rel == "index.md":
            continue
        if any(part in {".index", ".dekc", ".pkc"} for part in path.parts):
            continue
        if prefix_list and not any(rel.startswith(p) for p in prefix_list):
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if not fm:
            continue
        if fm.get("type") == "Catalog":
            continue
        t = fm.get("type") or ""
        if types is not None and t not in types:
            continue
        if tag_set:
            fm_tags = {str(x).lower() for x in (fm.get("tags") or [])}
            if not (fm_tags & tag_set):
                continue
        if since:
            ts = str(fm.get("timestamp") or "")
            if ts < since:
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
