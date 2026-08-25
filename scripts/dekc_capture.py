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
    attach_identity,
    capture_truth_state,
    capture_verified,
    concept_ref,
    dump_frontmatter,
    ensure_bundle,
    looks_like_view,
    parse_frontmatter,
    path_for_type,
    refresh_catalog_index,
    resolve_concept_ref,
    resolve_knowledge_root,
    scrub_text,
    slug_for_capture,
    slugify,
    unique_rel_path,
    utc_now,
    write_knowledge,
)

BI_CATALOGS = frozenset({"semantic", "reports", "dashboards"})


def _scrub(text: str) -> str:
    clean, _ = scrub_text(text)
    return clean


def _stamp(
    fm: dict[str, Any],
    *,
    verified: bool | None = None,
    truth_state: str = "",
    sql: str = "",
    columns: Any = None,
    evidence: bool = False,
    **identity: Any,
) -> dict[str, Any]:
    ver = capture_verified(verified=verified, sql=sql, columns=columns, evidence=evidence)
    fm["verified"] = ver
    fm["truth_state"] = capture_truth_state(ver, truth_state)
    attach_identity(fm, **identity)
    return fm


def _identity_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "verified": getattr(args, "verified", None),
        "truth_state": getattr(args, "truth_state", "") or "",
        "slug": getattr(args, "slug", "") or "",
        "fabric_item_id": getattr(args, "fabric_item_id", "") or "",
        "fabric_workspace": getattr(args, "fabric_workspace", "") or "",
        "fabric_workspace_id": getattr(args, "fabric_workspace_id", "") or "",
        "pbi_dataset_id": getattr(args, "pbi_dataset_id", "") or "",
        "datasources_status": getattr(args, "datasources_status", "") or "",
        "fabric_type": getattr(args, "fabric_type", "") or "",
    }


def add_identity_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--verified",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override verified flag. Default: true only when SQL/columns/evidence is supplied (#30).",
    )
    p.add_argument("--truth-state", default="", help="current|snapshot|historical|proposed")
    p.add_argument("--slug", default="", help="Override file identity slug (#29)")
    p.add_argument("--fabric-id", dest="fabric_item_id", default="", help="Fabric item GUID")
    p.add_argument("--workspace", dest="fabric_workspace", default="")
    p.add_argument("--workspace-id", dest="fabric_workspace_id", default="")
    p.add_argument("--dataset-id", dest="pbi_dataset_id", default="")
    p.add_argument("--datasources-status", default="")
    p.add_argument("--fabric-type", default="", help="Fabric type (Report, SemanticModel, Lakehouse, …)")


def merge_schema_contains(
    bundle: Path,
    schema: str,
    child_rel: str,
    child_name: str,
) -> tuple[str, str]:
    """Create or append a Schema `contains` edge. Never last-write-wins (#28)."""
    srel = path_for_type("Schema", slugify(schema))
    spath = bundle / srel
    child_ref = f"/{child_rel}"
    bullet = f"- [{child_name}]({child_ref})"
    if spath.is_file():
        fm, body = parse_frontmatter(spath.read_text(encoding="utf-8"))
        add_typed_link(fm, child_ref, "contains")
        if bullet not in body:
            body = body.rstrip() + f"\n{bullet}\n"
        _, action = write_knowledge(bundle, srel, fm, body, force=True)
        refresh_catalog_index(bundle, "schemas")
        return srel, action
    fm = {
        "type": "Schema",
        "title": schema,
        "description": f"Schema {schema}",
        "tags": ["schema", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": False,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"schema-{slugify(schema)}",
        "truth_state": "snapshot",
        "links": [{"target": child_ref, "rel": "contains"}],
    }
    body = f"# {schema}\n\nTables and views in this schema.\n\n{bullet}\n"
    _, action = write_knowledge(bundle, srel, fm, body)
    refresh_catalog_index(bundle, "schemas")
    return srel, action


def capture_source(
    bundle: Path,
    *,
    name: str,
    kind: str = "lake",
    uri: str = "",
    description: str = "",
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"source-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, evidence=bool(uri), **identity)
    rel = unique_rel_path(bundle, rel, fm)
    body = f"# {name}\n\n## Kind\n\n{kind}\n\n## URI\n\n`{uri or 'n/a'}`\n\n## Notes\n\n{description or '_No notes._'}\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "sources")
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
    kind: str = "auto",
    evidence: bool = False,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    if looks_like_view(name, sql, kind):
        return capture_view(
            bundle,
            name=name,
            layer=layer,
            sql=sql,
            description=description,
            schema=schema,
            source=source,
            columns=columns,
            tags=tags,
            verified=verified,
            truth_state=truth_state,
            slug=slug,
            evidence=evidence,
            **identity,
        )
    results: list[tuple[str, str]] = []
    slug = slug_for_capture(
        name,
        slug=slug,
        fabric_item_id=identity.get("fabric_item_id", ""),
        prefix=layer,
    )
    rel = path_for_type("Table", slug)
    fm_preview = {"title": name, "fabric_item_id": identity.get("fabric_item_id", "")}
    rel = unique_rel_path(bundle, rel, fm_preview)
    links: list[dict[str, str]] = []
    if layer:
        links.append({"target": f"/layers/{slugify(layer)}.md", "rel": "layered_as"})
    if schema:
        srel, sa = merge_schema_contains(bundle, schema, rel, name)
        links.append({"target": f"/{srel}", "rel": "defines"})
        results.append((srel, sa))
    if source:
        src_ref = concept_ref(source, "sources")
        if sql or evidence:
            links.append({"target": src_ref, "rel": "sourced_from"})
        else:
            # Hint only — sourced_from is a lineage edge lineage-skeptic will attack (#31).
            links.append({"target": src_ref, "rel": "related_to"})

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
            "truth_state": "snapshot",
            "links": [{"target": f"/{rel}", "rel": "defines"}],
        }
        cbody = (
            f"# {name}.{cname}\n\n"
            f"- Type: `{cfm['data_type']}`\n"
            f"- Nullable: {cfm['nullable']}\n\n"
            f"{col.get('description') or ''}\n"
        )
        _, ca = write_knowledge(bundle, crel, cfm, cbody)
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"table-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, sql=sql, columns=col_docs, evidence=evidence, **identity)
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
    _, action = write_knowledge(bundle, rel, fm, body)
    results.insert(0, (rel, action))
    refresh_catalog_index(bundle, "tables")
    refresh_catalog_index(bundle, "columns")
    return results


def capture_view(
    bundle: Path,
    *,
    name: str,
    layer: str = "gold",
    sql: str = "",
    description: str = "",
    reads_from: list[str] | None = None,
    schema: str = "",
    source: str | None = None,
    columns: list[dict[str, str]] | None = None,
    tags: list[str] | None = None,
    evidence: bool = False,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slug_for_capture(
        name,
        slug=slug,
        fabric_item_id=identity.get("fabric_item_id", ""),
        prefix=layer,
    )
    rel = path_for_type("View", slug)
    fm_preview = {"title": name, "fabric_item_id": identity.get("fabric_item_id", "")}
    rel = unique_rel_path(bundle, rel, fm_preview)
    links: list[dict[str, str]] = [{"target": f"/layers/{slugify(layer)}.md", "rel": "layered_as"}]
    if schema:
        srel, sa = merge_schema_contains(bundle, schema, rel, name)
        links.append({"target": f"/{srel}", "rel": "defines"})
        results.append((srel, sa))
    if source:
        src_ref = concept_ref(source, "sources")
        if sql or evidence:
            links.append({"target": src_ref, "rel": "sourced_from"})
        else:
            links.append({"target": src_ref, "rel": "related_to"})
    for src in reads_from or []:
        links.append({"target": resolve_concept_ref(bundle, src, "tables"), "rel": "reads_from"})
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
            "truth_state": "snapshot",
            "links": [{"target": f"/{rel}", "rel": "defines"}],
        }
        cbody = (
            f"# {name}.{cname}\n\n"
            f"- Type: `{cfm['data_type']}`\n"
            f"- Nullable: {cfm['nullable']}\n\n"
            f"{col.get('description') or ''}\n"
        )
        _, ca = write_knowledge(bundle, crel, cfm, cbody)
        results.append((crel, ca))
        links.append({"target": f"/{crel}", "rel": "contains"})
    fm: dict[str, Any] = {
        "type": "View",
        "title": name,
        "description": description or f"View {name}",
        "layer": layer,
        "schema": schema,
        "fqn": f"{schema}.{name}" if schema else name,
        "tags": list(dict.fromkeys(["view", "dekc", layer] + (tags or []))),
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"view-{slug}",
        "links": links,
    }
    _stamp(fm, verified=verified, truth_state=truth_state, sql=sql, columns=col_docs, evidence=evidence, **identity)
    body = f"# {name}\n\n{description or ''}\n"
    if schema:
        body += f"\n**Schema:** `{schema}`\n"
    if col_docs:
        body += "\n## Columns\n\n| Name | Type | Description |\n|------|------|-------------|\n"
        for col in col_docs:
            cname = col.get("name") or col.get("column") or ""
            ctype = col.get("type") or col.get("data_type") or ""
            cdesc = (col.get("description") or "").replace("|", "\\|")
            body += f"| `{cname}` | `{ctype}` | {cdesc} |\n"
    if sql:
        body += f"\n## SQL\n\n```sql\n{_scrub(sql).strip()}\n```\n"
    if reads_from:
        body += "\n## Reads from\n\n"
        for src in reads_from:
            body += f"- [{src}]({resolve_concept_ref(bundle, src, 'tables')})\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    results.insert(0, (rel, action))
    refresh_catalog_index(bundle, "views")
    refresh_catalog_index(bundle, "columns")
    return results


def capture_query(
    bundle: Path,
    *,
    name: str,
    dialect: str = "sql",
    body_sql: str = "",
    description: str = "",
    reads_from: list[str] | None = None,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("Query", slug)
    links: list[dict[str, str]] = []
    for src in reads_from or []:
        links.append({"target": resolve_concept_ref(bundle, src, "tables"), "rel": "queries"})

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
            "truth_state": "snapshot",
            "links": [{"target": f"/{rel}", "rel": "implements"}],
        }
        sbody = f"# {name} (SQL)\n\n```sql\n{_scrub(body_sql).strip()}\n```\n"
        _, sa = write_knowledge(bundle, srel, sfm, sbody)
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
            "truth_state": "snapshot",
            "links": [{"target": f"/{rel}", "rel": "implements"}],
        }
        dbody = f"# {name} (DAX)\n\n```dax\n{_scrub(body_sql).strip()}\n```\n"
        _, da = write_knowledge(bundle, drel, dfm, dbody)
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"query-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, sql=body_sql, **identity)
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n## {dialect.upper()}\n\n```{dialect}\n{_scrub(body_sql).strip()}\n```\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    results.insert(0, (rel, action))
    refresh_catalog_index(bundle, "queries")
    return results


def capture_dashboard(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    metrics: list[str] | None = None,
    visualizes: list[str] | None = None,
    tool: str = "powerbi",
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("Dashboard", slug)
    links: list[dict[str, str]] = []
    for m in metrics or []:
        links.append({"target": resolve_concept_ref(bundle, m, "metrics"), "rel": "visualizes"})
    for t in visualizes or []:
        links.append({"target": resolve_concept_ref(bundle, t, "tables"), "rel": "visualizes"})
    if identity.get("pbi_dataset_id") or identity.get("dataset_id"):
        ds = identity.get("pbi_dataset_id") or identity.get("dataset_id")
        links.append({"target": resolve_concept_ref(bundle, str(ds), "semantic"), "rel": "queries"})
    fm: dict[str, Any] = {
        "type": "Dashboard",
        "title": name,
        "description": description or name,
        "tool": tool,
        "tags": ["dashboard", tool, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"dashboard-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, **identity)
    rel = unique_rel_path(bundle, rel, fm)
    if links:
        fm["links"] = links
    body = f"# {name}\n\nTool: **{tool}**\n\n{description or ''}\n"
    fabric_type = identity.get("fabric_type") or ""
    if fabric_type:
        body += f"\n**Fabric type:** `{fabric_type}` (not inferred from DEKC noun).\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "dashboards")
    return [(rel, action)]


def capture_report(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    visualizes: list[str] | None = None,
    tool: str = "",
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("Report", slug)
    links = [
        {"target": resolve_concept_ref(bundle, t, "tables"), "rel": "visualizes"}
        for t in (visualizes or [])
    ]
    if identity.get("pbi_dataset_id") or identity.get("dataset_id"):
        ds = identity.get("pbi_dataset_id") or identity.get("dataset_id")
        links.append({"target": resolve_concept_ref(bundle, str(ds), "semantic"), "rel": "queries"})
    fm: dict[str, Any] = {
        "type": "Report",
        "title": name,
        "description": description or name,
        "tags": ["report", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"report-{slug}",
    }
    if tool:
        fm["tool"] = tool
        fm["tags"] = ["report", tool, "dekc"]
    _stamp(fm, verified=verified, truth_state=truth_state, **identity)
    rel = unique_rel_path(bundle, rel, fm)
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n"
    fabric_type = identity.get("fabric_type") or "Report"
    body += f"\n**Fabric type:** `{fabric_type}`. Fabric Report is not automatically a DEKC Dashboard.\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "reports")
    return [(rel, action)]


def capture_semantic_model(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    tables: list[str] | None = None,
    metrics: list[str] | None = None,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("SemanticModel", slug)
    links: list[dict[str, str]] = []
    for t in tables or []:
        # Allow View / DataLake / absolute paths, not only /tables/ (#41).
        links.append({"target": resolve_concept_ref(bundle, t, "tables"), "rel": "models"})
    for m in metrics or []:
        links.append({"target": resolve_concept_ref(bundle, m, "metrics"), "rel": "measures"})
    fm: dict[str, Any] = {
        "type": "SemanticModel",
        "title": name,
        "description": description or name,
        "tags": ["semantic", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"semantic-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, evidence=bool(tables or metrics), **identity)
    rel = unique_rel_path(bundle, rel, fm)
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n"
    if tables:
        body += "\n## Tables / bindings\n\n"
        for t in tables:
            body += f"- {resolve_concept_ref(bundle, t, 'tables')}\n"
    if metrics:
        body += "\n## Measures\n\n"
        for m in metrics:
            body += f"- {resolve_concept_ref(bundle, m, 'metrics')}\n"
    if not tables and not metrics:
        body += "\nNo table or measure list captured.\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "semantic")
    return [(rel, action)]


def capture_metric(
    bundle: Path,
    *,
    name: str,
    definition: str = "",
    expression: str = "",
    dialect: str = "sql",
    business_object: str | None = None,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"metric-{slug}",
    }
    _stamp(fm, verified=verified, truth_state=truth_state, sql=expression, **identity)
    if links:
        fm["links"] = links
    body = f"# {name}\n\n## Definition\n\n{definition or '_TBD_'}\n"
    if expression:
        body += f"\n## Expression ({dialect})\n\n```{dialect}\n{expression.strip()}\n```\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "metrics")
    return [(rel, action)]


def capture_workflow(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    steps: list[str] | None = None,
    orchestrator: str = "airflow",
    **_kwargs: Any,
) -> list[tuple[str, str]]:
    """Removed in 0.4.0 — AGER owns Workflow. Data jobs are IngestionJob (#35)."""
    raise SystemExit(
        "error: 'workflow' was removed in DEKC 0.4.0 (AGER owns Workflow).\n"
        "Use: python3 scripts/dekc_platform.py ingestion --name "
        f"{name!r} --orchestrator {orchestrator!r}\n"
        "  or: python3 scripts/dekc_capture.py transformation --name "
        f"{name!r} --from-layer bronze --to-layer silver"
    )


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
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("Transformation", slug)
    links: list[dict[str, str]] = [
        {"target": f"/layers/{slugify(from_layer)}.md", "rel": "reads_from"},
        {"target": f"/layers/{slugify(to_layer)}.md", "rel": "writes_to"},
        {"target": f"/layers/{slugify(from_layer)}.md", "rel": "transforms_to"},
    ]
    for inp in inputs or []:
        links.append({"target": resolve_concept_ref(bundle, inp, "tables"), "rel": "reads_from"})
    for out in outputs or []:
        links.append({"target": resolve_concept_ref(bundle, out, "tables"), "rel": "writes_to"})
    fm: dict[str, Any] = {
        "type": "Transformation",
        "title": name,
        "description": description or f"{from_layer} → {to_layer}: {name}",
        "from_layer": from_layer,
        "to_layer": to_layer,
        "tags": ["transformation", "dekc", from_layer, to_layer],
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"xform-{slug}",
        "links": links,
    }
    _stamp(fm, verified=verified, truth_state=truth_state, sql=sql, **identity)
    body = f"# {name}\n\n**{from_layer} → {to_layer}**\n\n{description or ''}\n"
    if sql:
        body += f"\n## SQL\n\n```sql\n{_scrub(sql).strip()}\n```\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "transformations")
    return [(rel, action)]


def _hop_rel(src_ref: str, dst_ref: str, override: str = "") -> str:
    if override:
        return override
    src_cat = src_ref.strip("/").split("/")[0]
    dst_cat = dst_ref.strip("/").split("/")[0]
    if src_cat in BI_CATALOGS or dst_cat in BI_CATALOGS:
        return "queries"
    if src_cat == "views" or dst_cat == "views":
        return "reads_from"
    return "feeds"


def capture_lineage_path(
    bundle: Path,
    *,
    name: str,
    nodes: list[str],
    description: str = "",
    hop_rel: str = "",
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    """nodes: ordered list of concept paths or names from upstream to downstream.

    Absolute paths (`/semantic/…`) are kept. Names resolve across catalogs, not
    only `/tables/` (#32). Hop rel defaults to `feeds` for table→table and
    `queries` for BI binds. Does not stamp `transforms_to`.
    """
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("LineagePath", slug)
    links: list[dict[str, str]] = []
    resolved = [resolve_concept_ref(bundle, n, "tables") for n in nodes]
    for node in resolved:
        links.append({"target": node, "rel": "contains"})
    used_rel = hop_rel
    for a, b in zip(resolved, resolved[1:]):
        r = _hop_rel(a, b, hop_rel)
        used_rel = r
        links.append({"target": b, "rel": r})
        _patch_hop(bundle, a, b, r)

    fm: dict[str, Any] = {
        "type": "LineagePath",
        "title": name,
        "description": description or f"Lineage path: {name}",
        "hop_count": max(0, len(nodes) - 1),
        "nodes": resolved,
        "hop_rel": used_rel or hop_rel or "feeds",
        "tags": ["lineage", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"lineage-{slug}",
        "links": links,
    }
    _stamp(fm, verified=verified, truth_state=truth_state, evidence=len(resolved) >= 2, **identity)
    body = f"# {name}\n\n{description or ''}\n\n## Path\n\n"
    body += " → ".join(f"[{Path(n).stem}]({n})" for n in resolved) + "\n"
    body += "\n```mermaid\nflowchart LR\n"
    for i, n in enumerate(resolved):
        nid = f"n{i}"
        body += f'  {nid}["{Path(n).stem}"]\n'
    for i in range(len(resolved) - 1):
        body += f"  n{i} --> n{i+1}\n"
    body += "```\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "lineage")
    return [(rel, action)]


def _patch_hop(bundle: Path, src_ref: str, dst_ref: str, rel: str) -> None:
    path = bundle / src_ref.lstrip("/")
    if not path.is_file():
        return
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, dst_ref, rel)
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")


def _patch_feed(bundle: Path, src_ref: str, dst_ref: str) -> None:
    """Back-compat wrapper. Does **not** also write transforms_to (#32)."""
    _patch_hop(bundle, src_ref, dst_ref, "feeds")


def capture_business_object(
    bundle: Path,
    *,
    name: str,
    definition: str,
    derived_from: list[str] | None = None,
    glossary_terms: list[str] | None = None,
    owner: str = "",
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    slug = slug_for_capture(name, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
    rel = path_for_type("BusinessObject", slug)
    links: list[dict[str, str]] = []
    for t in derived_from or []:
        links.append({"target": resolve_concept_ref(bundle, t, "tables"), "rel": "derived_from"})
        _patch_rel(bundle, resolve_concept_ref(bundle, t, "tables"), f"/{rel}", "businessizes")
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"bo-{slug}",
    }
    _stamp(fm, verified=verified if verified is not None else True, truth_state=truth_state or "current", **identity)
    if links:
        fm["links"] = links
    body = f"# {name}\n\n## Business definition\n\n{definition}\n"
    if owner:
        body += f"\n**Owner:** {owner}\n"
    if derived_from:
        body += "\n## Technical sources\n\n"
        for t in derived_from:
            body += f"- [{t}]({resolve_concept_ref(bundle, t, 'tables')})\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    results.append((rel, action))
    refresh_catalog_index(bundle, "business-objects")
    return results


def capture_glossary_term(
    bundle: Path,
    *,
    term: str,
    definition: str,
    synonyms: list[str] | None = None,
    related_objects: list[str] | None = None,
    verified: bool | None = None,
    truth_state: str = "",
    slug: str = "",
    **identity: Any,
) -> list[tuple[str, str]]:
    slug = slug_for_capture(term, slug=slug, fabric_item_id=identity.get("fabric_item_id", ""))
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
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"term-{slug}",
    }
    _stamp(fm, verified=verified if verified is not None else True, truth_state=truth_state or "current", **identity)
    if links:
        fm["links"] = links
    body = f"# {term}\n\n## Definition\n\n{definition}\n"
    if synonyms:
        body += "\n## Synonyms\n\n" + ", ".join(f"`{s}`" for s in synonyms) + "\n"
    _, action = write_knowledge(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "glossary")
    return [(rel, action)]


def _patch_rel(bundle: Path, src_ref: str, dst_ref: str, rel: str) -> None:
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
    parser.add_argument("--author", default="")
    parser.add_argument(
        "--write-event",
        action="store_true",
        help="Emit a WriteEvent file (off by default; or set DEKC_WRITE_EVENTS=1) (#37)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("source")
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="lake")
    p.add_argument("--uri", default="")
    p.add_argument("--description", default="")
    add_identity_args(p)

    p = sub.add_parser("table")
    p.add_argument("--name", required=True)
    p.add_argument("--layer", default="silver")
    p.add_argument("--schema", default="")
    p.add_argument("--description", default="")
    p.add_argument("--source", default=None)
    p.add_argument("--sql", default="")
    p.add_argument("--columns-json", default="[]", help='JSON list of {name,type,description}')
    p.add_argument(
        "--kind",
        default="auto",
        choices=["auto", "table", "view"],
        help="auto detects vw* / x_vw* / CREATE VIEW as View (#42)",
    )
    p.add_argument("--evidence", action="store_true", help="Allow sourced_from without SQL (#31)")
    add_identity_args(p)

    p = sub.add_parser("view")
    p.add_argument("--name", required=True)
    p.add_argument("--layer", default="gold")
    p.add_argument("--sql", default="")
    p.add_argument("--description", default="")
    p.add_argument("--reads-from", nargs="*", default=[])
    p.add_argument("--schema", default="")
    p.add_argument("--source", default=None)
    p.add_argument("--columns-json", default="[]")
    p.add_argument("--evidence", action="store_true")
    add_identity_args(p)

    p = sub.add_parser("query")
    p.add_argument("--name", required=True)
    p.add_argument("--dialect", default="sql")
    p.add_argument("--sql", default="")
    p.add_argument("--description", default="")
    p.add_argument("--reads-from", nargs="*", default=[])
    add_identity_args(p)

    p = sub.add_parser("dashboard")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tool", default="powerbi")
    p.add_argument("--metrics", nargs="*", default=[])
    p.add_argument("--visualizes", nargs="*", default=[])
    add_identity_args(p)

    p = sub.add_parser("report")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--visualizes", nargs="*", default=[])
    p.add_argument("--tool", default="powerbi")
    add_identity_args(p)

    p = sub.add_parser("semantic")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tables", nargs="*", default=[])
    p.add_argument("--metrics", nargs="*", default=[])
    add_identity_args(p)

    p = sub.add_parser("metric")
    p.add_argument("--name", required=True)
    p.add_argument("--definition", default="")
    p.add_argument("--expression", default="")
    p.add_argument("--dialect", default="sql")
    p.add_argument("--business-object", default=None)
    add_identity_args(p)

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
    add_identity_args(p)

    p = sub.add_parser("lineage")
    p.add_argument("--name", required=True)
    p.add_argument("--nodes", nargs="+", required=True)
    p.add_argument("--description", default="")
    p.add_argument(
        "--rel",
        dest="hop_rel",
        default="",
        help="Hop relation (feeds|queries|reads_from). Default: feeds for table→table, queries for BI.",
    )
    add_identity_args(p)

    p = sub.add_parser("business-object")
    p.add_argument("--name", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--derived-from", nargs="*", default=[])
    p.add_argument("--glossary", nargs="*", default=[])
    p.add_argument("--owner", default="")
    add_identity_args(p)

    p = sub.add_parser("glossary")
    p.add_argument("--term", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--synonyms", nargs="*", default=[])
    p.add_argument("--related", nargs="*", default=[])
    add_identity_args(p)

    args = parser.parse_args(argv)
    from dekc_common import resolve_author
    resolve_author(args.author)
    if args.write_event:
        import os
        os.environ["DEKC_WRITE_EVENTS"] = "1"
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    ensure_bundle(bundle)

    results: list[tuple[str, str]] = []
    cmd = args.cmd
    ident = _identity_kwargs(args) if cmd != "workflow" else {}
    if cmd == "source":
        results = capture_source(
            bundle, name=args.name, kind=args.kind, uri=args.uri, description=args.description, **ident
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
            kind=args.kind,
            evidence=args.evidence,
            **ident,
        )
    elif cmd == "view":
        cols = json.loads(args.columns_json)
        results = capture_view(
            bundle,
            name=args.name,
            layer=args.layer,
            sql=args.sql,
            description=args.description,
            reads_from=args.reads_from,
            schema=args.schema,
            source=args.source,
            columns=cols,
            evidence=args.evidence,
            **ident,
        )
    elif cmd == "query":
        results = capture_query(
            bundle,
            name=args.name,
            dialect=args.dialect,
            body_sql=args.sql,
            description=args.description,
            reads_from=args.reads_from,
            **ident,
        )
    elif cmd == "dashboard":
        results = capture_dashboard(
            bundle,
            name=args.name,
            description=args.description,
            metrics=args.metrics,
            visualizes=args.visualizes,
            tool=args.tool,
            **ident,
        )
    elif cmd == "report":
        results = capture_report(
            bundle,
            name=args.name,
            description=args.description,
            visualizes=args.visualizes,
            tool=args.tool,
            **ident,
        )
    elif cmd == "semantic":
        results = capture_semantic_model(
            bundle,
            name=args.name,
            description=args.description,
            tables=args.tables,
            metrics=args.metrics,
            **ident,
        )
    elif cmd == "metric":
        results = capture_metric(
            bundle,
            name=args.name,
            definition=args.definition,
            expression=args.expression,
            dialect=args.dialect,
            business_object=args.business_object,
            **ident,
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
            **ident,
        )
    elif cmd == "lineage":
        results = capture_lineage_path(
            bundle,
            name=args.name,
            nodes=args.nodes,
            description=args.description,
            hop_rel=args.hop_rel,
            **ident,
        )
    elif cmd == "business-object":
        results = capture_business_object(
            bundle,
            name=args.name,
            definition=args.definition,
            derived_from=args.derived_from,
            glossary_terms=args.glossary,
            owner=args.owner,
            **ident,
        )
    elif cmd == "glossary":
        results = capture_glossary_term(
            bundle,
            term=args.term,
            definition=args.definition,
            synonyms=args.synonyms,
            related_objects=args.related,
            **ident,
        )
    else:
        parser.error(f"unknown command {cmd}")
        return 2

    if results:
        label = getattr(args, "name", None) or getattr(args, "term", cmd)
        by_type: dict[str, int] = {}
        for pth, _act in results:
            cat = pth.split("/", 1)[0]
            by_type[cat] = by_type.get(cat, 0) + 1
        counts = ", ".join(f"{n} {k}" for k, n in sorted(by_type.items()))
        append_log(bundle, f"Captured {cmd} {label}: {counts}")

    _print_results(results, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
