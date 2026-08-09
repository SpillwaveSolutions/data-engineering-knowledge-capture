#!/usr/bin/env python3
"""Capture platform concepts: data lakes, marts, catalogs, domains, products,
streams, storage locations, and data quality rules.
"""

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
    slugify,
    utc_now,
    write_concept,
    parse_frontmatter,
    dump_frontmatter,
)


def _patch(bundle: Path, src: str, dst: str, rel: str) -> None:
    path = bundle / src.lstrip("/")
    if not path.is_file():
        return
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, dst, rel)
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")


def capture_data_lake(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    platform: str = "",
    uri: str = "",
    layers: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DataLake", slug)
    links: list[dict[str, str]] = []
    for layer in layers or ["bronze", "silver", "gold"]:
        links.append({"target": f"/layers/{slugify(layer)}.md", "rel": "contains"})
    fm: dict[str, Any] = {
        "type": "DataLake",
        "title": name,
        "description": description or f"Data lake: {name}",
        "platform": platform,
        "uri": uri,
        "tags": ["data-lake", "dekc", platform or "platform"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"lake-{slug}",
        "truth_state": "current",
        "links": links,
    }
    body = f"# {name}\n\n{description or ''}\n\n"
    if platform:
        body += f"**Platform:** {platform}\n\n"
    if uri:
        body += f"**URI:** `{uri}`\n\n"
    body += "## Layers\n\n"
    for layer in layers or ["bronze", "silver", "gold"]:
        body += f"- [{layer}](/layers/{slugify(layer)}.md)\n"
    body += "\n## Architecture\n\n```mermaid\nflowchart LR\n  S[Sources] --> B[Bronze] --> V[Silver] --> G[Gold]\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "lakes")
    append_log(bundle, f"Captured data lake: {name}")
    return [(rel, action)]


def capture_data_mart(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    domain: str = "",
    tables: list[str] | None = None,
    lake: str | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DataMart", slug)
    links: list[dict[str, str]] = []
    if domain:
        dref = concept_ref(domain, "domains")
        links.append({"target": dref, "rel": "belongs_to_domain"})
    if lake:
        lref = concept_ref(lake, "lakes")
        links.append({"target": lref, "rel": "part_of_lake"})
    for t in tables or []:
        links.append({"target": concept_ref(t, "tables"), "rel": "contains"})
    fm: dict[str, Any] = {
        "type": "DataMart",
        "title": name,
        "description": description or f"Data mart: {name}",
        "domain": domain,
        "tags": ["data-mart", "gold", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"mart-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\nCurated business-facing mart (typically gold).\n"
    if tables:
        body += "\n## Tables\n\n" + "\n".join(f"- {concept_ref(t, 'tables')}" for t in tables) + "\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "marts")
    append_log(bundle, f"Captured data mart: {name}")
    return [(rel, action)]


def capture_data_catalog(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    engine: str = "",
    uri: str = "",
    schemas: list[str] | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DataCatalog", slug)
    links: list[dict[str, str]] = []
    for s in schemas or []:
        links.append({"target": concept_ref(s, "schemas"), "rel": "contains"})
    fm: dict[str, Any] = {
        "type": "DataCatalog",
        "title": name,
        "description": description or f"Data catalog: {name}",
        "engine": engine,
        "uri": uri,
        "tags": ["data-catalog", "dekc", engine or "catalog"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"catalog-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n"
    body += f"**Engine:** {engine or 'n/a'}  \n**URI:** `{uri or 'n/a'}`\n\n"
    body += "System of record for schemas/tables (Glue, Unity, Purview, DataHub, …).\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "catalogs")
    append_log(bundle, f"Captured data catalog: {name}")
    return [(rel, action)]


def capture_data_domain(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    owner: str = "",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DataDomain", slug)
    fm: dict[str, Any] = {
        "type": "DataDomain",
        "title": name,
        "description": description or f"Data domain: {name}",
        "owner": owner,
        "tags": ["data-domain", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"domain-{slug}",
        "truth_state": "current",
    }
    body = f"# {name}\n\n{description or ''}\n\n"
    if owner:
        body += f"**Owner:** {owner}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "domains")
    append_log(bundle, f"Captured data domain: {name}")
    return [(rel, action)]


def capture_data_product(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    domain: str = "",
    outputs: list[str] | None = None,
    contract: str = "",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DataProduct", slug)
    links: list[dict[str, str]] = []
    if domain:
        links.append({"target": concept_ref(domain, "domains"), "rel": "belongs_to_domain"})
    for o in outputs or []:
        links.append({"target": concept_ref(o, "tables"), "rel": "publishes"})
    if contract:
        links.append({"target": concept_ref(contract, "contracts"), "rel": "implements_contract"})
    fm: dict[str, Any] = {
        "type": "DataProduct",
        "title": name,
        "description": description or f"Data product: {name}",
        "tags": ["data-product", "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"product-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\nPublishable data product for consumers (reports, apps, downstream domains).\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "products")
    append_log(bundle, f"Captured data product: {name}")
    return [(rel, action)]


def capture_stream(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    platform: str = "",
    uri: str = "",
    format: str = "",
    lands_as: str | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("Stream", slug)
    links: list[dict[str, str]] = []
    if lands_as:
        tref = concept_ref(lands_as, "tables")
        links.append({"target": tref, "rel": "lands_as"})
        links.append({"target": tref, "rel": "feeds"})
        _patch(bundle, tref, f"/{rel}", "sourced_from")
    fm: dict[str, Any] = {
        "type": "Stream",
        "title": name,
        "description": description or f"Stream: {name}",
        "platform": platform,
        "uri": uri,
        "format": format,
        "tags": ["stream", "dekc", platform or "streaming"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"stream-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n"
    body += f"**Platform:** {platform or 'n/a'}  \n**URI:** `{uri or 'n/a'}`  \n**Format:** {format or 'n/a'}\n\n"
    if lands_as:
        body += f"**Lands as:** {concept_ref(lands_as, 'tables')}\n\n"
    body += "```mermaid\nflowchart LR\n  P[Producers] --> S[Stream] --> B[Bronze landing]\n```\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "streams")
    append_log(bundle, f"Captured stream: {name}")
    return [(rel, action)]


def capture_storage(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    kind: str = "bucket",
    uri: str = "",
    format: str = "",
    layer: str = "",
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("StorageLocation", slug)
    links: list[dict[str, str]] = []
    if layer:
        links.append({"target": f"/layers/{slugify(layer)}.md", "rel": "layered_as"})
    fm: dict[str, Any] = {
        "type": "StorageLocation",
        "title": name,
        "description": description or f"Storage: {name}",
        "storage_kind": kind,
        "uri": uri,
        "format": format,
        "layer": layer,
        "tags": ["storage", kind, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"storage-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n"
    body += f"**Kind:** {kind}  \n**URI:** `{uri or 'n/a'}`  \n**Format:** {format or 'n/a'}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "storage")
    append_log(bundle, f"Captured storage: {name}")
    return [(rel, action)]


def capture_dq_rule(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    rule_type: str = "freshness",
    severity: str = "error",
    expression: str = "",
    target: str | None = None,
) -> list[tuple[str, str]]:
    slug = slugify(name)
    rel = path_for_type("DQRule", slug)
    links: list[dict[str, str]] = []
    if target:
        tref = concept_ref(target, "tables")
        links.append({"target": tref, "rel": "validates"})
        links.append({"target": tref, "rel": "quality_of"})
        _patch(bundle, tref, f"/{rel}", "validated_by")
    fm: dict[str, Any] = {
        "type": "DQRule",
        "title": name,
        "description": description or f"DQ rule: {name}",
        "rule_type": rule_type,
        "severity": severity,
        "expression": expression,
        "tags": ["dq", "quality", rule_type, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"dq-{slug}",
        "truth_state": "current",
    }
    if links:
        fm["links"] = links
    body = f"# {name}\n\n{description or ''}\n\n"
    body += f"**Type:** `{rule_type}` · **Severity:** `{severity}`\n\n"
    if expression:
        body += f"## Expression\n\n```\n{expression.strip()}\n```\n"
    if target:
        body += f"\n**Target:** {concept_ref(target, 'tables')}\n"
    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "quality")
    append_log(bundle, f"Captured DQ rule: {name}")
    return [(rel, action)]



def capture_ingestion_job(
    bundle: Path,
    *,
    name: str,
    description: str = "",
    mode: str = "batch",
    pattern: str = "",
    orchestrator: str = "",
    schedule: str = "",
    connector: str = "",
    source_format: str = "",
    target_format: str = "",
    target_layer: str = "bronze",
    sources: list[str] | None = None,
    streams: list[str] | None = None,
    lands_as: list[str] | None = None,
    storage: list[str] | None = None,
    watermark_column: str = "",
    checkpoint: str = "",
    idempotent: bool = True,
    sla_minutes: float | None = None,
    steps: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Capture a data ingestion job (landing into bronze/paths from sources/streams)."""
    slug = slugify(name)
    rel = path_for_type("IngestionJob", slug)
    links: list[dict[str, str]] = []
    if target_layer:
        links.append({"target": f"/layers/{slugify(target_layer)}.md", "rel": "writes_to"})
        links.append({"target": f"/layers/{slugify(target_layer)}.md", "rel": "layered_as"})
    for s in sources or []:
        ref = concept_ref(s, "sources")
        links.append({"target": ref, "rel": "ingests_from"})
        links.append({"target": ref, "rel": "reads_from"})
        _patch(bundle, ref, f"/{rel}", "ingested_by")
    for s in streams or []:
        ref = concept_ref(s, "streams")
        links.append({"target": ref, "rel": "ingests_from"})
        links.append({"target": ref, "rel": "consumes_stream"})
        _patch(bundle, ref, f"/{rel}", "ingested_by")
    for tname in lands_as or []:
        ref = concept_ref(tname, "tables")
        links.append({"target": ref, "rel": "lands_as"})
        links.append({"target": ref, "rel": "writes_to"})
        links.append({"target": ref, "rel": "lands_into"})
        _patch(bundle, ref, f"/{rel}", "sourced_from")
        _patch(bundle, ref, f"/{rel}", "ingested_by")
    for st in storage or []:
        ref = concept_ref(st, "storage")
        links.append({"target": ref, "rel": "writes_to"})
        links.append({"target": ref, "rel": "stored_in"})

    pattern = pattern or f"{mode}-to-{target_layer}"
    fm: dict[str, Any] = {
        "type": "IngestionJob",
        "title": name,
        "description": description or f"Ingestion job: {name}",
        "ingestion_mode": mode,
        "pattern": pattern,
        "orchestrator": orchestrator,
        "schedule": schedule,
        "connector": connector,
        "source_format": source_format,
        "target_format": target_format,
        "target_layer": target_layer,
        "idempotent": idempotent,
        "watermark_column": watermark_column,
        "checkpoint": checkpoint,
        "tags": ["ingestion", "job", mode, target_layer, "dekc"],
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"ingest-{slug}",
        "truth_state": "current",
    }
    if sla_minutes is not None:
        fm["sla_minutes"] = sla_minutes
    if links:
        fm["links"] = links

    body = f"# {name}\n\n{description or ''}\n\n"
    body += f"**Mode:** `{mode}` · **Pattern:** `{pattern}` · **Target layer:** `{target_layer}`\n\n"
    if orchestrator:
        body += f"**Orchestrator:** {orchestrator}\n"
    if schedule:
        body += f"**Schedule:** `{schedule}`\n"
    if connector:
        body += f"**Connector:** {connector}\n"
    if source_format or target_format:
        body += f"**Formats:** {source_format or '?'} → {target_format or '?'}\n"
    if watermark_column:
        body += f"**Watermark:** `{watermark_column}`\n"
    if checkpoint:
        body += f"**Checkpoint:** `{checkpoint}`\n"
    body += f"**Idempotent:** {idempotent}\n"
    if sla_minutes is not None:
        body += f"**SLA:** {sla_minutes} minutes\n"

    if sources or streams:
        body += "\n## Sources\n\n"
        for s in sources or []:
            body += f"- Source: {concept_ref(s, 'sources')}\n"
        for s in streams or []:
            body += f"- Stream: {concept_ref(s, 'streams')}\n"
    if lands_as:
        body += "\n## Lands as (tables)\n\n"
        for tname in lands_as:
            body += f"- {concept_ref(tname, 'tables')}\n"
    if storage:
        body += "\n## Storage\n\n"
        for st in storage:
            body += f"- {concept_ref(st, 'storage')}\n"
    if steps:
        body += "\n## Steps\n\n"
        for i, step in enumerate(steps, 1):
            body += f"{i}. {step}\n"

    body += "\n## Ingestion flow\n\n```mermaid\nflowchart LR\n"
    body += "  SRC[Source / Stream] --> JOB[Ingestion Job]\n"
    body += f"  JOB --> LAND[{target_layer} landing]\n"
    body += "  JOB --> DQ[Optional DQ]\n"
    body += "```\n"

    _, action = write_concept(bundle, rel, fm, body)
    refresh_catalog_index(bundle, "ingestion")
    append_log(bundle, f"Captured ingestion job: {name}")
    return [(rel, action)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC platform concept capture")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lake")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--platform", default="")
    p.add_argument("--uri", default="")
    p.add_argument("--layers", nargs="*", default=["bronze", "silver", "gold"])

    p = sub.add_parser("mart")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--domain", default="")
    p.add_argument("--lake", default=None)
    p.add_argument("--tables", nargs="*", default=[])

    p = sub.add_parser("catalog")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--engine", default="")
    p.add_argument("--uri", default="")
    p.add_argument("--schemas", nargs="*", default=[])

    p = sub.add_parser("domain")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--owner", default="")

    p = sub.add_parser("product")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--domain", default="")
    p.add_argument("--outputs", nargs="*", default=[])
    p.add_argument("--contract", default="")

    p = sub.add_parser("stream")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--platform", default="")
    p.add_argument("--uri", default="")
    p.add_argument("--format", default="")
    p.add_argument("--lands-as", default=None)

    p = sub.add_parser("storage")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--kind", default="bucket")
    p.add_argument("--uri", default="")
    p.add_argument("--format", default="")
    p.add_argument("--layer", default="")

    p = sub.add_parser("ingestion")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--mode", default="batch",
                   choices=["batch", "microbatch", "streaming", "cdc", "full_load",
                            "incremental", "file_drop", "api_pull", "unknown"])
    p.add_argument("--pattern", default="")
    p.add_argument("--orchestrator", default="")
    p.add_argument("--schedule", default="")
    p.add_argument("--connector", default="")
    p.add_argument("--source-format", default="")
    p.add_argument("--target-format", default="")
    p.add_argument("--target-layer", default="bronze")
    p.add_argument("--sources", nargs="*", default=[])
    p.add_argument("--streams", nargs="*", default=[])
    p.add_argument("--lands-as", nargs="*", default=[])
    p.add_argument("--storage", nargs="*", default=[])
    p.add_argument("--watermark", default="")
    p.add_argument("--checkpoint", default="")
    p.add_argument("--sla-minutes", type=float, default=None)
    p.add_argument("--no-idempotent", action="store_true")
    p.add_argument("--steps", nargs="*", default=[])

    p = sub.add_parser("dq-rule")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--rule-type", default="freshness")
    p.add_argument("--severity", default="error")
    p.add_argument("--expression", default="")
    p.add_argument("--target", default=None)

    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    ensure_bundle(bundle)

    results: list[tuple[str, str]] = []
    if args.cmd == "lake":
        results = capture_data_lake(
            bundle,
            name=args.name,
            description=args.description,
            platform=args.platform,
            uri=args.uri,
            layers=args.layers,
        )
    elif args.cmd == "mart":
        results = capture_data_mart(
            bundle,
            name=args.name,
            description=args.description,
            domain=args.domain,
            tables=args.tables,
            lake=args.lake,
        )
    elif args.cmd == "catalog":
        results = capture_data_catalog(
            bundle,
            name=args.name,
            description=args.description,
            engine=args.engine,
            uri=args.uri,
            schemas=args.schemas,
        )
    elif args.cmd == "domain":
        results = capture_data_domain(
            bundle, name=args.name, description=args.description, owner=args.owner
        )
    elif args.cmd == "product":
        results = capture_data_product(
            bundle,
            name=args.name,
            description=args.description,
            domain=args.domain,
            outputs=args.outputs,
            contract=args.contract,
        )
    elif args.cmd == "stream":
        results = capture_stream(
            bundle,
            name=args.name,
            description=args.description,
            platform=args.platform,
            uri=args.uri,
            format=args.format,
            lands_as=args.lands_as,
        )
    elif args.cmd == "storage":
        results = capture_storage(
            bundle,
            name=args.name,
            description=args.description,
            kind=args.kind,
            uri=args.uri,
            format=args.format,
            layer=args.layer,
        )
    elif args.cmd == "ingestion":
        results = capture_ingestion_job(
            bundle,
            name=args.name,
            description=args.description,
            mode=args.mode,
            pattern=args.pattern,
            orchestrator=args.orchestrator,
            schedule=args.schedule,
            connector=args.connector,
            source_format=args.source_format,
            target_format=args.target_format,
            target_layer=args.target_layer,
            sources=args.sources,
            streams=args.streams,
            lands_as=args.lands_as,
            storage=args.storage,
            watermark_column=args.watermark,
            checkpoint=args.checkpoint,
            idempotent=not args.no_idempotent,
            sla_minutes=args.sla_minutes,
            steps=args.steps,
        )
    elif args.cmd == "dq-rule":
        results = capture_dq_rule(
            bundle,
            name=args.name,
            description=args.description,
            rule_type=args.rule_type,
            severity=args.severity,
            expression=args.expression,
            target=args.target,
        )

    if args.json:
        print(json.dumps([{"path": p, "action": a} for p, a in results], indent=2))
    else:
        for pth, act in results:
            print(f"{act:8} {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
