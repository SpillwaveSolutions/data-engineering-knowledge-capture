#!/usr/bin/env python3
"""Capture helpers for DEKC technical and business concepts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    add_typed_link,
    append_log,
    concept_ref,
    ensure_bundle,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    scrub_text,
    slugify,
    utc_now,
    write_concept,
)


def _scrub(text: str) -> str:
    clean, _ = scrub_text(text)
    return clean


def capture_source(
    bundle: Path,
    *,
    name: str,
    kind: str = "lake",
    uri: str = "",
    description: str = "",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("SourceSystem", slug)
    fm: dict[str, Any] = {
        "type": "SourceSystem",
        "title": name,
        "description": description or f"Source system: {name}",
        "source_kind": kind,
        "uri": uri,
        "tags": ["source", kind, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"source-{slug}",
        "truth_state": "current",
    }
    body = f"# {name}\n\n## Kind\n\n{kind}\n\n## URI\n\n`{uri or 'n/a'}`\n\n## Notes\n\n{description or '_No notes._'}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "sources")
    append_log(bundle, f"Captured source: {name}")
    return [(rel, action)]


def capture_table(
    bundle: Path,
    *,
    name: str,
    layer: str = "silver",
    schema: str = "",
    columns: list[dict[str, str]] | None = None,
    description: str = "",
    source: str | None = None,
    sql: str = "",
    tags: list[str] | None = None,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slugify(f"{layer}-{name}" if layer else name)
    rel = path_for_type("Table", slug)
    links: list[dict[str, str]] = []
    if layer:
        links.append({"target": f"/layers/{slugify(layer)}.md", "rel": "layered_as"})
    if schema:
        srel = path_for_type("Schema", slugify(schema))
        links.append({"target": f"/{srel}", "rel": "defines"})
        # ensure schema concept
        sfm = {
            "type": "Schema",
            "title": schema,
            "description": f"Schema {schema}",
            "tags": ["schema", "dekc"],
            "timestamp": utc_now(),
            "status": "active",
            "verified": True,
            "generated": True,
            "stable_timestamp": True,
            "wiki_key": f"schema-{slugify(schema)}",
            "truth_state": "current",
            "links": [{"target": f"/{rel}", "rel": "contains"}],
        }
        sbody = f"# {schema}\n\nTables and views in this schema.\n\n- [{name}](/{rel})\n"
        _, sa = write_concept(bundle, srel, sfm, sbody)
        results.append((srel, sa))
        refresh_catalog_index(bundle, "schemas")
    if source:
        links.append({"target": concept_ref(source, "sources"), "rel": "sourced_from"})

    col_docs = columns or []
    for col in col_docs:
        cname = col.get("name") or col.get("column") or "col"
        cslug = slugify(f"{slug}-{cname}")
        crel = path_for_type("Column", cslug)
        cfm = {
            "type": "Column",
            "title": f"{name}.{cname}",
            "description": col.get("description") or f"Column {cname} on {name}",
            "data_type": col.get("type") or col.get("data_type") or "unknown",
            "nullable": col.get("nullable", True),
            "tags": ["column", "dekc", layer],
            "timestamp": utc_now(),
            "status": "active",
            "verified": False,
            "generated": True,
            "stable_timestamp": True,
            "wiki_key": f"col-{cslug}",
            "truth_state": "current",
            "links": [{"target": f"/{rel}", "rel": "defines"}],
        }
        cbody = (
            f"# {name}.{cname}\n\n"
            f"- Type: `{cfm['data_type']}`\n"
            f"- Nullable: {cfm['nullable']}\n\n"
            f"{col.get('description') or ''}\n"
        )
        _, ca = write_concept(bundle, crel, cfm, cbody)
        results.append((crel, ca))
        links.append({"target": f"/{crel}", "rel": "contains"})

    fm: dict[str, Any] = {
        "type": "Table",
        "title": name,
        "description": description or f"Table {name} ({layer})",
        "layer": layer,
        "schema": schema,
        "fqn": f"{schema}.{name}" if schema else name,
        "tags": list(dict.fromkeys(["table", "dekc", layer] + (tags or []))),
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"table-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    if sql:
        fm["sql_fingerprint"] = str(abs(hash(_scrub(sql))))[:12]

    body = f"# {name}\n\n"
    body += f"**Layer:** {layer}  \n"
    if schema:
        body += f"**Schema:** `{schema}`  \n"
    body += f"\n{description or '_No description._'}\n"
    if col_docs:
        body += "\n## Columns\n\n| Name | Type | Description |\n|------|------|-------------|\n"
        for col in col_docs:
            cname = col.get("name") or col.get("column") or ""
            ctype = col.get("type") or col.get("data_type") or ""
            cdesc = (col.get("description") or "").replace("|", "\\|")
            body += f"| `{cname}` | `{ctype}` | {cdesc} |\n"
    if sql:
        body += f"\n## SQL\n\n```sql\n{_scrub(sql).strip()}\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    results.insert(0, (rel, action))
    refresh_catalog_index(bundle, "tables")
    refresh_catalog_index(bundle, "columns")
    append_log(bundle, f"Captured table: {name} ({layer})")
    return results


def capture_view(
    bundle: Path,
    *,
    name: str,
    layer: str = "gold",
    sql: str = "",
    description: str = "",
    reads_from: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(f"{layer}-{name}" if layer else name)
    rel = path_for_type("View", slug)
    links: list[dict[str, str]] = [{"target": f"/layers/{slugify(layer)}.md", "rel": "layered_as"}]
    for src in reads_from or []:
        links.append({"target": concept_ref(src, "tables"), "rel": "reads_from"})
    fm: dict[str, Any] = {
        "type": "View",
        "title": name,
        "description": description or f"View {name}",
        "layer": layer,
        "tags": ["view", "dekc", layer],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"view-{slug}",
        "truth_state": "current",
        "links": links,
    }
    body = f"# {name}\n\n{description or ''}\n"
    if sql:
        body += f"\n## SQL\n\n```sql\n{_scrub(sql).strip()}\n```\n"
    if reads_from:
        body += "\n## Reads from\n\n"
        for src in reads_from:
            body += f"- [{src}]({concept_ref(src, 'tables')})\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "views")
    append_log(bundle, f"Captured view: {name}")
    return [(rel, action)]


def capture_query(
    bundle: Path,
    *,
    name: str,
    dialect: str = "sql",
    body_sql: str = "",
    description: str = "",
    reads_from: list[str] | None = None,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slugify(name)
    rel = path_for_type("Query", slug)
    links: list[dict[str, str]] = []
    for src in reads_from or []:
        links.append({"target": concept_ref(src, "tables"), "rel": "queries"})

    # Also store raw SQL artifact
    if body_sql and dialect.lower() == "sql":
        srel = path_for_type("SqlArtifact", slug)
        sfm = {
            "type": "SqlArtifact",
            "title": f"{name} (SQL)",
            "description": description or name,
            "dialect": dialect,
            "tags": ["sql", "dekc"],
            "timestamp": utc_now(),
            "status": "active",
            "verified": False,
            "generated": True,
            "stable_timestamp": True,
            "wiki_key": f"sql-{slug}",
            "truth_state": "current",
            "links": [{"target": f"/{rel}", "rel": "implements"}],
        }
        sbody = f"# {name} (SQL)\n\n```sql\n{_scrub(body_sql).strip()}\n```\n"
        _, sa = write_concept(bundle, srel, sfm, sbody)
        results.append((srel, sa))
        links.append({"target": f"/{srel}", "rel": "implements"})
        refresh_catalog_index(bundle, "sql")
    if body_sql and dialect.lower() == "dax":
        drel = path_for_type("DaxArtifact", slug)
        dfm = {
            "type": "DaxArtifact",
            "title": f"{name} (DAX)",
            "description": description or name,
            "tags": ["dax", "dekc"],
            "timestamp": utc_now(),
            "status": "active",
            "verified": False,
            "generated": True,
            "stable_timestamp": True,
            "wiki_key": f"dax-{slug}",
            "truth_state": "current",
            "links": [{"target": f"/{rel}", "rel": "implements"}],
        }
        dbody = f"# {name} (DAX)\n\n```dax\n{_scrub(body_sql).strip()}\n```\n"
        _, da = write_concept(bundle, drel, dfm, dbody)
        results.append((drel, da))
        links.append({"target": f"/{drel}", "rel": "implements"})
        refresh_catalog_index(bundle, "dax")

    fm: dict[str, Any] = {
        "type": "Query",
        "title": name,
        "description": description or name,
        "dialect": dialect,
        "tags": ["query", dialect, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"query-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n## {dialect.upper()}\n\n```{dialect}\n{_scrub(body_sql).strip()}\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    results.insert(0, (rel, action))
    refresh_catalog_index(bundle, "queries")
    append_log(bundle, f"Captured query: {name}")
    return results


def capture_dashboard(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    metrics: list[str] | None = None,
    visualizes: list[str] | None = None,
    tool: str = "powerbi",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Dashboard", slug)
    links: list[dict[str, str]] = []
    for m in metrics or []:
        links.append({"target": concept_ref(m, "metrics"), "rel": "visualizes"})
    for t in visualizes or []:
        links.append({"target": concept_ref(t, "tables"), "rel": "visualizes"})
    fm: dict[str, Any] = {
        "type": "Dashboard",
        "title": name,
        "description": description or name,
        "tool": tool,
        "tags": ["dashboard", tool, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"dashboard-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\nTool: **{tool}**\n\n{description or ''}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "dashboards")
    append_log(bundle, f"Captured dashboard: {name}")
    return [(rel, action)]


def capture_report(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    visualizes: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Report", slug)
    links = [{"target": concept_ref(t, "tables"), "rel": "visualizes"} for t in (visualizes or [])]
    fm: dict[str, Any] = {
        "type": "Report",
        "title": name,
        "description": description or name,
        "tags": ["report", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"report-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "reports")
    append_log(bundle, f"Captured report: {name}")
    return [(rel, action)]


def capture_semantic_model(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    tables: list[str] | None = None,
    metrics: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("SemanticModel", slug)
    links: list[dict[str, str]] = []
    for t in tables or []:
        links.append({"target": concept_ref(t, "tables"), "rel": "models"})
    for m in metrics or []:
        links.append({"target": concept_ref(m, "metrics"), "rel": "measures"})
    fm: dict[str, Any] = {
        "type": "SemanticModel",
        "title": name,
        "description": description or name,
        "tags": ["semantic", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"semantic-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\nSemantic layer binding technical tables to business metrics.\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "semantic")
    append_log(bundle, f"Captured semantic model: {name}")
    return [(rel, action)]


def capture_metric(
    bundle: Path,
    *,
    name: str,
    definition: str = "",
    expression: str = "",
    dialect: str = "sql",
    business_object: str | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Metric", slug)
    links: list[dict[str, str]] = []
    if business_object:
        links.append({"target": concept_ref(business_object, "business-objects"), "rel": "measures"})
    fm: dict[str, Any] = {
        "type": "Metric",
        "title": name,
        "description": definition or name,
        "expression": expression,
        "dialect": dialect,
        "tags": ["metric", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"metric-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n## Definition\n\n{definition or '_TBD_'}\n"
    if expression:
        body += f"\n## Expression ({dialect})\n\n```{dialect}\n{expression.strip()}\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "metrics")
    append_log(bundle, f"Captured metric: {name}")
    return [(rel, action)]


def capture_workflow(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    steps: list[str] | None = None,
    orchestrator: str = "airflow",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Workflow", slug)
    fm: dict[str, Any] = {
        "type": "Workflow",
        "title": name,
        "description": description or name,
        "orchestrator": orchestrator,
        "tags": ["workflow", orchestrator, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"workflow-{slug}",
        "truth_state": "current",
    }
    body = f"# {name}\n\nOrchestrator: **{orchestrator}**\n\n{description or ''}\n"
    if steps:
        body += "\n## Steps\n\n"
        for i, step in enumerate(steps, 1):
            body += f"{i}. {step}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "workflows")
    append_log(bundle, f"Captured workflow: {name}")
    return [(rel, action)]


def capture_transformation(
    bundle: Path,
    *,
    name: str,
    from_layer: str,
    to_layer: str,
    description: str = "",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    sql: str = "",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Transformation", slug)
    links: list[dict[str, str]] = [
        {"target": f"/layers/{slugify(from_layer)}.md", "rel": "reads_from"},
        {"target": f"/layers/{slugify(to_layer)}.md", "rel": "writes_to"},
        {"target": f"/layers/{slugify(from_layer)}.md", "rel": "transforms_to"},
    ]
    # promote edge on source layer toward target
    for inp in inputs or []:
        links.append({"target": concept_ref(inp, "tables"), "rel": "reads_from"})
    for out in outputs or []:
        links.append({"target": concept_ref(out, "tables"), "rel": "writes_to"})
    fm: dict[str, Any] = {
        "type": "Transformation",
        "title": name,
        "description": description or f"{from_layer} → {to_layer}: {name}",
        "from_layer": from_layer,
        "to_layer": to_layer,
        "tags": ["transformation", "dekc", from_layer, to_layer],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"xform-{slug}",
        "truth_state": "current",
        "links": links,
    }
    body = f"# {name}\n\n**{from_layer} → {to_layer}**\n\n{description or ''}\n"
    if sql:
        body += f"\n## SQL\n\n```sql\n{_scrub(sql).strip()}\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "transformations")
    append_log(bundle, f"Captured transformation: {name}")
    return [(rel, action)]


def capture_lineage_path(
    bundle: Path,
    *,
    name: str,
    nodes: list[str],
    description: str = "",
) -> list[tuple[str, str]]:
    """nodes: ordered list of concept paths or table names from upstream to downstream."""
    slug = slugify(name)
    rel = path_for_type("LineagePath", slug)
    links: list[dict[str, str]] = []
    resolved = [concept_ref(n, "tables") for n in nodes]
    for i, node in enumerate(resolved):
        rel_type = "feeds" if i < len(resolved) - 1 else "related_to"
        if i < len(resolved) - 1:
            links.append({"target": node, "rel": "contains"})
            # edge from this node to next is represented in body; also store hop
        else:
            links.append({"target": node, "rel": "contains"})
    # hop edges as related
    for a, b in zip(resolved, resolved[1:]):
        links.append({"target": b, "rel": "feeds"})
        # also patch upstream concept with feeds edge
        _patch_feed(bundle, a, b)

    fm: dict[str, Any] = {
        "type": "LineagePath",
        "title": name,
        "description": description or f"Lineage path: {name}",
        "hop_count": max(0, len(nodes) - 1),
        "nodes": resolved,
        "tags": ["lineage", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"lineage-{slug}",
        "truth_state": "current",
        "links": links,
    }
    body = f"# {name}\n\n{description or ''}\n\n## Path\n\n"
    body += " → ".join(f"[{Path(n).stem}]({n})" for n in resolved) + "\n"
    body += "\n```mermaid\nflowchart LR\n"
    for i, n in enumerate(resolved):
        nid = f"n{i}"
        body += f'  {nid}["{Path(n).stem}"]\n'
    for i in range(len(resolved) - 1):
        body += f"  n{i} --> n{i+1}\n"
    body += "```\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "lineage")
    append_log(bundle, f"Captured lineage path: {name}")
    return [(rel, action)]


def _patch_feed(bundle: Path, src_ref: str, dst_ref: str) -> None:
    rel = src_ref.lstrip("/")
    path = bundle / rel
    if not path.is_file():
        return
    from dekc_common import parse_frontmatter, dump_frontmatter  # local

    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, dst_ref, "feeds")
    add_typed_link(fm, dst_ref, "transforms_to")
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")


def capture_business_object(
    bundle: Path,
    *,
    name: str,
    definition: str,
    derived_from: list[str] | None = None,
    glossary_terms: list[str] | None = None,
    owner: str = "",
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slugify(name)
    rel = path_for_type("BusinessObject", slug)
    links: list[dict[str, str]] = []
    for t in derived_from or []:
        links.append({"target": concept_ref(t, "tables"), "rel": "derived_from"})
        # inverse businessizes on table
        _patch_rel(bundle, concept_ref(t, "tables"), f"/{rel}", "businessizes")
    for g in glossary_terms or []:
        gslug = slugify(g) if not g.endswith(".md") else Path(g).stem
        grest = path_for_type("GlossaryTerm", gslug)
        links.append({"target": f"/{grest}", "rel": "glosses"})

    fm: dict[str, Any] = {
        "type": "BusinessObject",
        "title": name,
        "description": definition[:200],
        "owner": owner,
        "tags": ["business-object", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"bo-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n## Business definition\n\n{definition}\n"
    if owner:
        body += f"\n**Owner:** {owner}\n"
    if derived_from:
        body += "\n## Technical sources\n\n"
        for t in derived_from:
            body += f"- [{t}]({concept_ref(t, 'tables')})\n"
    _, action = write_concept(bundle, rel, fm, body)
    results.append((rel, action))
    refresh_catalog_index(bundle, "business-objects")
    append_log(bundle, f"Captured business object: {name}")
    return results


def capture_glossary_term(
    bundle: Path,
    *,
    term: str,
    definition: str,
    synonyms: list[str] | None = None,
    related_objects: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(term)
    rel = path_for_type("GlossaryTerm", slug)
    links = [
        {"target": concept_ref(o, "business-objects"), "rel": "glosses"}
        for o in (related_objects or [])
    ]
    fm: dict[str, Any] = {
        "type": "GlossaryTerm",
        "title": term,
        "description": definition[:200],
        "synonyms": synonyms or [],
        "tags": ["glossary", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"term-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {term}\n\n## Definition\n\n{definition}\n"
    if synonyms:
        body += "\n## Synonyms\n\n" + ", ".join(f"`{s}`" for s in synonyms) + "\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "glossary")
    append_log(bundle, f"Captured glossary term: {term}")
    return [(rel, action)]


def _patch_rel(bundle: Path, src_ref: str, dst_ref: str, rel: str) -> None:
    from dekc_common import parse_frontmatter, dump_frontmatter

    path = bundle / src_ref.lstrip("/")
    if not path.is_file():
        return
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, dst_ref, rel)
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")


def _print_results(results: list[tuple[str, str]], as_json: bool) -> None:
    if as_json:
        print(json.dumps([{"path": p, "action": a} for p, a in results], indent=2))
    else:
        for p, a in results:
            print(f"{a:8} {p}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC capture")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        pass

    p = sub.add_parser("source")
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="lake")
    p.add_argument("--uri", default="")
    p.add_argument("--description", default="")

    p = sub.add_parser("table")
    p.add_argument("--name", required=True)
    p.add_argument("--layer", default="silver")
    p.add_argument("--schema", default="")
    p.add_argument("--description", default="")
    p.add_argument("--source", default=None)
    p.add_argument("--sql", default="")
    p.add_argument("--columns-json", default="[]", help='JSON list of {name,type,description}')

    p = sub.add_parser("view")
    p.add_argument("--name", required=True)
    p.add_argument("--layer", default="gold")
    p.add_argument("--sql", default="")
    p.add_argument("--description", default="")
    p.add_argument("--reads-from", nargs="*", default=[])

    p = sub.add_parser("query")
    p.add_argument("--name", required=True)
    p.add_argument("--dialect", default="sql")
    p.add_argument("--sql", default="")
    p.add_argument("--description", default="")
    p.add_argument("--reads-from", nargs="*", default=[])

    p = sub.add_parser("dashboard")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tool", default="powerbi")
    p.add_argument("--metrics", nargs="*", default=[])
    p.add_argument("--visualizes", nargs="*", default=[])

    p = sub.add_parser("report")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--visualizes", nargs="*", default=[])

    p = sub.add_parser("semantic")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tables", nargs="*", default=[])
    p.add_argument("--metrics", nargs="*", default=[])

    p = sub.add_parser("metric")
    p.add_argument("--name", required=True)
    p.add_argument("--definition", default="")
    p.add_argument("--expression", default="")
    p.add_argument("--dialect", default="sql")
    p.add_argument("--business-object", default=None)

    p = sub.add_parser("workflow")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--orchestrator", default="airflow")
    p.add_argument("--steps", nargs="*", default=[])

    p = sub.add_parser("transformation")
    p.add_argument("--name", required=True)
    p.add_argument("--from-layer", required=True)
    p.add_argument("--to-layer", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--inputs", nargs="*", default=[])
    p.add_argument("--outputs", nargs="*", default=[])
    p.add_argument("--sql", default="")

    p = sub.add_parser("lineage")
    p.add_argument("--name", required=True)
    p.add_argument("--nodes", nargs="+", required=True)
    p.add_argument("--description", default="")

    p = sub.add_parser("business-object")
    p.add_argument("--name", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--derived-from", nargs="*", default=[])
    p.add_argument("--glossary", nargs="*", default=[])
    p.add_argument("--owner", default="")

    p = sub.add_parser("glossary")
    p.add_argument("--term", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--synonyms", nargs="*", default=[])
    p.add_argument("--related", nargs="*", default=[])

    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    ensure_bundle(bundle)

    results: list[tuple[str, str]] = []
    cmd = args.cmd
    if cmd == "source":
        results = capture_source(
            bundle, name=args.name, kind=args.kind, uri=args.uri, description=args.description
        )
    elif cmd == "table":
        cols = json.loads(args.columns_json)
        results = capture_table(
            bundle,
            name=args.name,
            layer=args.layer,
            schema=args.schema,
            columns=cols,
            description=args.description,
            source=args.source,
            sql=args.sql,
        )
    elif cmd == "view":
        results = capture_view(
            bundle,
            name=args.name,
            layer=args.layer,
            sql=args.sql,
            description=args.description,
            reads_from=args.reads_from,
        )
    elif cmd == "query":
        results = capture_query(
            bundle,
            name=args.name,
            dialect=args.dialect,
            body_sql=args.sql,
            description=args.description,
            reads_from=args.reads_from,
        )
    elif cmd == "dashboard":
        results = capture_dashboard(
            bundle,
            name=args.name,
            description=args.description,
            metrics=args.metrics,
            visualizes=args.visualizes,
            tool=args.tool,
        )
    elif cmd == "report":
        results = capture_report(
            bundle, name=args.name, description=args.description, visualizes=args.visualizes
        )
    elif cmd == "semantic":
        results = capture_semantic_model(
            bundle,
            name=args.name,
            description=args.description,
            tables=args.tables,
            metrics=args.metrics,
        )
    elif cmd == "metric":
        results = capture_metric(
            bundle,
            name=args.name,
            definition=args.definition,
            expression=args.expression,
            dialect=args.dialect,
            business_object=args.business_object,
        )
    elif cmd == "workflow":
        results = capture_workflow(
            bundle,
            name=args.name,
            description=args.description,
            steps=args.steps,
            orchestrator=args.orchestrator,
        )
    elif cmd == "transformation":
        results = capture_transformation(
            bundle,
            name=args.name,
            from_layer=args.from_layer,
            to_layer=args.to_layer,
            description=args.description,
            inputs=args.inputs,
            outputs=args.outputs,
            sql=args.sql,
        )
    elif cmd == "lineage":
        results = capture_lineage_path(
            bundle, name=args.name, nodes=args.nodes, description=args.description
        )
    elif cmd == "business-object":
        results = capture_business_object(
            bundle,
            name=args.name,
            definition=args.definition,
            derived_from=args.derived_from,
            glossary_terms=args.glossary,
            owner=args.owner,
        )
    elif cmd == "glossary":
        results = capture_glossary_term(
            bundle,
            term=args.term,
            definition=args.definition,
            synonyms=args.synonyms,
            related_objects=args.related,
        )
    else:
        parser.error(f"unknown command {cmd}")
        return 2

    _print_results(results, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
