#!/usr/bin/env python3
"""Walk a data lake / warehouse filesystem and capture DEKC concepts.

Discovers:
  - SQL files (*.sql) → Query + SqlArtifact + inferred table reads
  - DAX files (*.dax, *.dax.cs) → Query + DaxArtifact
  - YAML/JSON table specs (schema.yml, *.table.json)
  - Medallion folder conventions: bronze/, silver/, gold/, raw/
  - dbt models (models/**/*.sql + schema.yml)
  - Spark/Delta path markers (_delta_log, *.parquet dir names)
  - DuckDB files (*.duckdb) and notebook SQL (*.ipynb)
  - Orchestration / ELT / DQ markers (Airflow, Glue, ADF, dbt, GE/Soda)

Agents orchestrate this script; subagents specialize on schema, lineage, semantic.
Cheap discovery writes live here. `dekc_plan.py` is presence-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_capture import (  # noqa: E402
    capture_dashboard,
    capture_query,
    capture_report,
    capture_semantic_model,
    capture_source,
    capture_table,
    capture_transformation,
    capture_view,
)
from dekc_common import (  # noqa: E402
    append_log,
    ensure_bundle,
    looks_like_view,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    slugify,
    utc_now,
    write_knowledge,
)
from dekc_platform import (  # noqa: E402
    capture_data_catalog,
    capture_data_lake,
    capture_dq_rule,
    capture_ingestion_job,
    capture_storage,
    capture_stream,
)

SQL_FROM_RE = re.compile(
    r"\b(?:from|join)\s+([`\"\[]?[\w.-]+[`\"\]]?(?:\.[`\"\[]?[\w.-]+[`\"\]]?){0,2})",
    re.IGNORECASE,
)
LAYER_HINTS = ("raw", "bronze", "silver", "gold", "platinum", "staging", "curated", "marts")


@dataclass
class WalkResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    discovered: dict[str, int] = field(default_factory=dict)

    def record(self, path: str, action: str) -> None:
        if action == "created":
            self.created.append(path)
        elif action == "updated":
            self.updated.append(path)
        else:
            self.skipped.append(path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "discovered": self.discovered,
            "counts": {
                "created": len(self.created),
                "updated": len(self.updated),
                "skipped": len(self.skipped),
                "errors": len(self.errors),
            },
        }


def infer_layer(path: Path, root: Path) -> str:
    parts = [p.lower() for p in path.relative_to(root).parts]
    for layer in LAYER_HINTS:
        if layer in parts:
            if layer == "staging":
                return "bronze"
            if layer == "curated":
                return "silver"
            if layer == "marts":
                return "gold"
            return layer
    return "silver"


def extract_sql_tables(sql: str) -> list[str]:
    found: list[str] = []
    for m in SQL_FROM_RE.finditer(sql):
        raw = m.group(1)
        cleaned = raw.strip('`"[]')
        # skip CTE-ish single tokens that look like keywords
        if cleaned.lower() in {"select", "where", "lateral", "unnest", "values"}:
            continue
        # use last segment as table name
        name = cleaned.split(".")[-1]
        if name and name not in found:
            found.append(name)
    return found


def walk_lake(
    lake_root: Path,
    bundle: Path,
    *,
    source_name: str | None = None,
    max_files: int = 500,
    dry_run: bool = False,
) -> WalkResult:
    result = WalkResult()
    if not lake_root.is_dir():
        result.errors.append(f"not a directory: {lake_root}")
        return result

    src_name = source_name or lake_root.name
    if not dry_run:
        for rel, action in capture_source(
            bundle,
            name=src_name,
            kind="lake",
            uri=str(lake_root.resolve()),
            description=f"Walked data lake at {lake_root}",
        ):
            result.record(rel, action)

    sql_files = list(lake_root.rglob("*.sql"))[:max_files]
    dax_files = list(lake_root.rglob("*.dax"))[: max_files // 4]
    # parquet "tables" as directory markers
    parquet_dirs = [p for p in lake_root.rglob("*.parquet") if p.is_file()][:max_files]
    table_names_from_paths: set[str] = set()

    result.discovered["sql_files"] = len(sql_files)
    result.discovered["dax_files"] = len(dax_files)
    result.discovered["parquet_files"] = len(parquet_dirs)

    # Capture tables from path structure: .../layer/schema/table/...
    for sql_path in sql_files:
        layer = infer_layer(sql_path, lake_root)
        sql = sql_path.read_text(encoding="utf-8", errors="replace")
        refs = extract_sql_tables(sql)
        name = sql_path.stem
        is_view = "create view" in sql.lower() or "/views/" in str(sql_path).lower()

        if dry_run:
            result.skipped.append(str(sql_path))
            continue

        if is_view:
            for rel, action in capture_view(
                bundle,
                name=name,
                layer=layer if layer in LAYER_HINTS else "gold",
                sql=sql,
                description=f"Discovered view from {sql_path.relative_to(lake_root)}",
                reads_from=refs,
            ):
                result.record(rel, action)
        else:
            # model as query + optional output table named after file
            for rel, action in capture_query(
                bundle,
                name=name,
                dialect="sql",
                body_sql=sql,
                description=f"Discovered SQL from {sql_path.relative_to(lake_root)}",
                reads_from=refs,
            ):
                result.record(rel, action)
            # If path implies a table write target
            if any(x in sql.lower() for x in ("create table", "insert into", "merge into", "create or replace table")):
                has_from = bool(extract_sql_tables(sql))
                desc = f"Inferred table from {sql_path.relative_to(lake_root)}"
                if not has_from:
                    desc += " (DDL-only, no FROM — no invented lineage)"
                for rel, action in capture_table(
                    bundle,
                    name=name,
                    layer=layer if layer in ("bronze", "silver", "gold", "raw") else "silver",
                    description=desc,
                    source=src_name if has_from else None,
                    sql=sql,
                    evidence=has_from,
                ):
                    result.record(rel, action)
                    table_names_from_paths.add(name)

        for ref in refs:
            if ref not in table_names_from_paths:
                # lightweight stub tables for lineage anchors
                if dry_run:
                    continue
                for rel, action in capture_table(
                    bundle,
                    name=ref,
                    layer="bronze" if layer in ("silver", "gold") else layer,
                    description=f"Referenced by {name}",
                ):
                    result.record(rel, action)
                table_names_from_paths.add(ref)

    for dax_path in dax_files:
        if dry_run:
            result.skipped.append(str(dax_path))
            continue
        body = dax_path.read_text(encoding="utf-8", errors="replace")
        for rel, action in capture_query(
            bundle,
            name=dax_path.stem,
            dialect="dax",
            body_sql=body,
            description=f"Discovered DAX from {dax_path.relative_to(lake_root)}",
        ):
            result.record(rel, action)

    # Parent dirs of parquet as tables
    seen_dirs: set[str] = set()
    for pq in parquet_dirs:
        parent = pq.parent
        key = str(parent.relative_to(lake_root))
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        layer = infer_layer(parent, lake_root)
        tname = parent.name
        if tname.startswith("_"):
            continue
        if dry_run:
            result.skipped.append(key)
            continue
        for rel, action in capture_table(
            bundle,
            name=tname,
            layer=layer if layer in ("bronze", "silver", "gold", "raw") else "bronze",
            description=f"Parquet dataset at {key}",
            source=src_name,
        ):
            result.record(rel, action)

    # Delta table directories (_delta_log sibling of parquet)
    seen_delta: set[str] = set()
    for delta_dir in lake_root.rglob("_delta_log"):
        if not delta_dir.is_dir():
            continue
        parent = delta_dir.parent
        try:
            key = str(parent.relative_to(lake_root))
        except ValueError:
            continue
        if key in seen_delta or key in seen_dirs:
            continue
        seen_delta.add(key)
        tname = parent.name
        if tname.startswith("_"):
            continue
        result.discovered["delta_tables"] = result.discovered.get("delta_tables", 0) + 1
        if dry_run:
            result.skipped.append(key)
            continue
        layer = infer_layer(parent, lake_root)
        for rel, action in capture_table(
            bundle,
            name=tname,
            layer=layer if layer in ("bronze", "silver", "gold", "raw") else "bronze",
            description=f"Delta table at {key}",
            source=src_name,
        ):
            result.record(rel, action)

    # Infer bronze→silver→gold promotions when same basename appears in multiple layers
    by_base: dict[str, list[str]] = {}
    for rel in result.created + result.updated + result.skipped:
        if rel.startswith("tables/") and rel.endswith(".md"):
            stem = Path(rel).stem
            # stem like silver-orders
            for layer in ("bronze", "silver", "gold", "raw"):
                if stem.startswith(layer + "-"):
                    base = stem[len(layer) + 1 :]
                    by_base.setdefault(base, []).append(layer)
    if not dry_run:
        for base, layers in by_base.items():
            ordered = [L for L in ("raw", "bronze", "silver", "gold") if L in layers]
            for a, b in zip(ordered, ordered[1:]):
                for rel, action in capture_transformation(
                    bundle,
                    name=f"promote-{base}-{a}-to-{b}",
                    from_layer=a,
                    to_layer=b,
                    description=f"Medallion promotion of {base}: {a} → {b}",
                    inputs=[f"{a}-{base}"],
                    outputs=[f"{b}-{base}"],
                ):
                    result.record(rel, action)

    # Agent walk receipt
    if not dry_run:
        receipt_rel = path_for_type("AgentNode", f"walk-{slugify(src_name)}-{utc_now()[:10]}")
        # shorter stable key
        receipt_rel = path_for_type("AgentNode", f"walk-{slugify(src_name)}")
        fm = {
            "type": "AgentNode",
            "title": f"Lake walk: {src_name}",
            "description": f"DEKC walk of {lake_root}",
            "role": "data-lake-walker",
            "tags": ["agent", "walk", "dekc"],
            "timestamp": utc_now(),
            "status": "completed",
            "verified": True,
            "generated": True,
            "stable_timestamp": True,
            "wiki_key": f"walk-{slugify(src_name)}",
            "truth_state": "current",
            "stats": result.to_dict()["counts"],
        }
        body = (
            f"# Lake walk: {src_name}\n\n"
            f"Root: `{lake_root}`\n\n"
            f"## Stats\n\n```json\n{json.dumps(result.to_dict()['counts'], indent=2)}\n```\n"
        )
        _, action = write_knowledge(bundle, receipt_rel, fm, body)
        result.record(receipt_rel, action)
        refresh_catalog_index(bundle, "agents")
        append_log(
            bundle,
            f"Walked lake {src_name}: +{len(result.created)} ~{len(result.updated)} skip {len(result.skipped)}",
        )

    return result


FABRIC_TYPE_MAP = {
    "lakehouse": ("DataLake", "lakes"),
    "warehouse": ("DataLake", "lakes"),
    "semanticmodel": ("SemanticModel", "semantic"),
    "dataset": ("SemanticModel", "semantic"),
    "report": ("Report", "reports"),
    "dashboard": ("Dashboard", "dashboards"),
    "datapipeline": ("IngestionJob", "ingestion"),
    "pipeline": ("IngestionJob", "ingestion"),
    "notebook": ("IngestionJob", "ingestion"),
    "eventstream": ("Stream", "streams"),
    "kqldatabase": ("DataLake", "lakes"),
    "sqlendpoint": ("SemanticModel", "semantic"),
}


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("value", "items", "data", "tables"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        return [data]
    return []


def walk_fabric_items(
    items_path: Path,
    bundle: Path,
    *,
    workspace: str = "",
    workspace_id: str = "",
    dry_run: bool = False,
) -> WalkResult:
    """Ingest a Fabric workspace items JSON (REST list). Docs-only until #38."""
    result = WalkResult()
    if not items_path.is_file():
        result.errors.append(f"not a file: {items_path}")
        return result
    items = _load_json_list(items_path)
    result.discovered["fabric_items"] = len(items)
    if dry_run:
        result.skipped.extend(str(it.get("displayName") or it.get("name") or it.get("id")) for it in items)
        return result

    for it in items:
        display = it.get("displayName") or it.get("name") or ""
        fid = str(it.get("id") or it.get("itemId") or "")
        raw_type = str(it.get("type") or it.get("kind") or "")
        ftype = raw_type.replace(" ", "").lower()
        ws = workspace or it.get("workspaceName") or ""
        ws_id = workspace_id or str(it.get("workspaceId") or "")
        ident = {
            "fabric_item_id": fid,
            "fabric_workspace": ws,
            "fabric_workspace_id": ws_id,
            "fabric_type": raw_type or None,
        }
        ident = {k: v for k, v in ident.items() if v}
        mapped = FABRIC_TYPE_MAP.get(ftype)
        if not display:
            result.errors.append(f"fabric item missing displayName: {fid or raw_type}")
            continue
        try:
            if mapped and mapped[0] == "DataLake":
                recs = capture_data_lake(
                    bundle,
                    name=display,
                    platform="fabric-onelake",
                    layers=["bronze"],
                    description=f"Fabric {raw_type} (filesystem walk did not inventory tables).",
                    **ident,
                )
            elif mapped and mapped[0] == "SemanticModel":
                sql_endpoint = ftype in {"sqlendpoint"} or display.lower().endswith("_lh") or display.lower().endswith(" lh")
                desc = "Fabric SemanticModel."
                if sql_endpoint:
                    desc = "Default SQL-endpoint model — not curated gold."
                recs = capture_semantic_model(
                    bundle,
                    name=display,
                    description=desc,
                    **ident,
                )
            elif mapped and mapped[0] == "Report":
                recs = capture_report(
                    bundle,
                    name=display,
                    description="Fabric Report (not automatically a DEKC Dashboard).",
                    tool="powerbi",
                    **ident,
                )
            elif mapped and mapped[0] == "Dashboard":
                recs = capture_dashboard(
                    bundle,
                    name=display,
                    description="Fabric Dashboard.",
                    tool="powerbi",
                    **ident,
                )
            elif mapped and mapped[0] == "IngestionJob":
                recs = capture_ingestion_job(
                    bundle,
                    name=display,
                    description=f"Fabric {raw_type}.",
                    orchestrator="fabric-pipeline" if "pipeline" in ftype else "fabric-notebook",
                    mode="batch",
                    target_layer="",
                    **ident,
                )
            elif mapped and mapped[0] == "Stream":
                recs = capture_stream(
                    bundle,
                    name=display,
                    platform="fabric-eventstream",
                    description=f"Fabric {raw_type}.",
                )
            else:
                recs = capture_source(
                    bundle,
                    name=display,
                    kind="fabric",
                    description=f"Unmapped Fabric type {raw_type or 'unknown'}.",
                    **ident,
                )
            for rel, action in recs:
                result.record(rel, action)
        except SystemExit as exc:
            result.errors.append(f"{display}: {exc}")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{display}: {exc}")
    return result


def walk_pbi_bindings(
    bindings_path: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
) -> WalkResult:
    """Ingest Power BI report→dataset bindings. Does not invent COUNT metrics."""
    result = WalkResult()
    if not bindings_path.is_file():
        result.errors.append(f"not a file: {bindings_path}")
        return result
    items = _load_json_list(bindings_path)
    result.discovered["pbi_bindings"] = len(items)
    if dry_run:
        return result
    for it in items:
        name = it.get("name") or it.get("displayName") or ""
        rid = str(it.get("id") or "")
        dataset_id = str(it.get("datasetId") or it.get("dataset_id") or "")
        ds_status = it.get("datasources_status") or it.get("datasourcesStatus") or ""
        if not name:
            continue
        recs = capture_report(
            bundle,
            name=name,
            description="Power BI report binding.",
            tool="powerbi",
            fabric_item_id=rid,
            pbi_dataset_id=dataset_id,
            datasources_status=str(ds_status) if ds_status != "" else "",
            fabric_type="Report",
        )
        for rel, action in recs:
            result.record(rel, action)
        if dataset_id:
            recs = capture_semantic_model(
                bundle,
                name=f"dataset-{dataset_id[:8]}",
                description="Bound Power BI dataset (name unknown unless also in fabric-items).",
                fabric_item_id=dataset_id,
                fabric_type="SemanticModel",
            )
            for rel, action in recs:
                result.record(rel, action)
    return result


def walk_inventory_json(
    inventory_path: Path,
    bundle: Path,
    *,
    layer: str = "gold",
    dry_run: bool = False,
) -> WalkResult:
    """INFORMATION_SCHEMA / live inventory JSON. Never invents COUNT metrics (#38)."""
    result = WalkResult()
    if not inventory_path.is_file():
        result.errors.append(f"not a file: {inventory_path}")
        return result
    rows = _load_json_list(inventory_path)
    result.discovered["inventory_rows"] = len(rows)
    if dry_run:
        return result
    for row in rows:
        name = row.get("name") or row.get("TABLE_NAME") or row.get("table") or ""
        schema = row.get("schema") or row.get("TABLE_SCHEMA") or ""
        ttype = str(row.get("table_type") or row.get("TABLE_TYPE") or row.get("type") or "").upper()
        if not name:
            continue
        kind = "view" if ttype in {"VIEW", "V"} or looks_like_view(name) else "table"
        desc = "Name from catalog. No SQL."
        recs = capture_table(
            bundle,
            name=name,
            layer=layer,
            schema=schema,
            description=desc,
            kind=kind,
        )
        for rel, action in recs:
            result.record(rel, action)
    return result


def extract_notebook_sql(text_or_path: str | Path) -> list[str]:
    """Pull SQL-ish cells from an .ipynb (%%sql, spark.sql, duckdb, SELECT)."""
    if isinstance(text_or_path, Path):
        try:
            data = json.loads(text_or_path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError):
            return []
    else:
        try:
            data = json.loads(text_or_path)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, dict):
        return []
    found: list[str] = []
    for cell in data.get("cells") or []:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        src = cell.get("source") or ""
        if isinstance(src, list):
            src = "".join(src)
        blob = str(src).strip()
        if not blob:
            continue
        low = blob.lower()
        if (
            "%%sql" in low
            or "spark.sql" in low
            or "duckdb.sql" in low
            or "duckdb.execute" in low
            or re.search(r"\bselect\b", blob, re.IGNORECASE)
        ):
            found.append(blob)
    return found


def _job_name_from_file(path: Path, root: Path, text: str = "") -> str:
    m = re.search(r"dag_id\s*=\s*['\"]([^'\"]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"expectation_suite_name['\"]\s*:\s*['\"]([^'\"]+)", text)
    if m:
        return m.group(1)
    return path.stem


def walk_duckdb(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
) -> WalkResult:
    result = WalkResult()
    files = list(lake_root.rglob("*.duckdb")) + list(lake_root.rglob("*.ddb"))
    result.discovered["duckdb_files"] = len(files)
    for f in files[:200]:
        name = f.stem
        if dry_run:
            result.skipped.append(str(f))
            continue
        for rel, action in capture_source(
            bundle,
            name=name,
            kind="duckdb",
            uri=str(f.resolve()),
            description=f"DuckDB file at {f.relative_to(lake_root)} (binary not opened).",
        ):
            result.record(rel, action)
    return result


def walk_notebooks(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
    max_files: int = 80,
) -> WalkResult:
    result = WalkResult()
    nbs = list(lake_root.rglob("*.ipynb"))[:max_files]
    result.discovered["notebooks"] = len(nbs)
    for nb in nbs:
        sqls = extract_notebook_sql(nb)
        if dry_run:
            result.skipped.append(str(nb))
            continue
        if not sqls:
            for rel, action in capture_query(
                bundle,
                name=nb.stem,
                dialect="notebook",
                body_sql="",
                description=f"Notebook {nb.relative_to(lake_root)} (no SQL cells extracted).",
            ):
                result.record(rel, action)
            continue
        for i, sql in enumerate(sqls):
            qname = nb.stem if len(sqls) == 1 else f"{nb.stem}-cell-{i + 1}"
            refs = extract_sql_tables(sql)
            for rel, action in capture_query(
                bundle,
                name=qname,
                dialect="sql",
                body_sql=sql,
                description=f"SQL cell from {nb.relative_to(lake_root)}",
                reads_from=refs,
            ):
                result.record(rel, action)
    return result


def walk_dq_markers(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
    max_files: int = 80,
) -> WalkResult:
    """Cheap DQRule capture from GE / Soda / dbt test files. No runtime."""
    result = WalkResult()
    candidates: list[Path] = []
    for pat in (
        "**/great_expectations.yml",
        "**/great_expectations.yaml",
        "**/expectations/*.json",
        "**/soda*.yml",
        "**/soda*.yaml",
        "**/checks.yml",
        "**/schema.yml",
    ):
        candidates.extend(lake_root.glob(pat))
    seen: set[str] = set()
    for f in candidates:
        if not f.is_file():
            continue
        key = str(f)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > max_files:
            break
        text = f.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        name = f.stem
        rule_type = "expectation"
        if "great_expectation" in str(f).lower() or "expectation_suite" in low:
            rule_type = "great-expectations"
            suite = _job_name_from_file(f, lake_root, text)
            name = suite or name
        elif "soda" in str(f).lower() or "checks for" in low:
            rule_type = "soda"
        elif "tests:" in text or "data_tests:" in text:
            if "dbt" not in str(f).lower() and "models" not in f.parts:
                continue
            rule_type = "dbt-test"
        else:
            if f.name.startswith("great_expectations"):
                rule_type = "great-expectations"
            elif f.name.startswith("soda") or f.name == "checks.yml":
                rule_type = "soda"
            else:
                continue
        result.discovered["dq_files"] = result.discovered.get("dq_files", 0) + 1
        if dry_run:
            result.skipped.append(str(f))
            continue
        expr = ""
        if '"expectation_type"' in text:
            m = re.search(r'"expectation_type"\s*:\s*"([^"]+)"', text)
            if m:
                expr = m.group(1)
        for rel, action in capture_dq_rule(
            bundle,
            name=name,
            description=f"DQ marker from {f.relative_to(lake_root)} (not executed).",
            rule_type=rule_type,
            expression=expr,
        ):
            result.record(rel, action)
    return result


def walk_elt(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
) -> WalkResult:
    result = WalkResult()
    for proj in list(lake_root.rglob("dbt_project.yml")) + list(lake_root.rglob("dbt_project.yaml")):
        result.discovered["dbt_projects"] = result.discovered.get("dbt_projects", 0) + 1
        if dry_run:
            result.skipped.append(str(proj))
            continue
        name = proj.parent.name
        for rel, action in capture_ingestion_job(
            bundle,
            name=f"dbt-{name}",
            description=f"dbt project at {proj.relative_to(lake_root)}",
            orchestrator="dbt",
            mode="batch",
            target_layer="",
        ):
            result.record(rel, action)
    spark_hits = 0
    for py in lake_root.rglob("*.py"):
        if spark_hits >= 40:
            break
        try:
            text = py.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        if "SparkSession" in text or "spark-submit" in text:
            if "awsglue" in text:
                continue
            spark_hits += 1
            if dry_run:
                result.skipped.append(str(py))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=py.stem,
                description=f"Spark/EMR job script {py.relative_to(lake_root)}",
                orchestrator="spark",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)
    result.discovered["spark_jobs"] = spark_hits
    return result


def walk_orchestration(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
    kinds: set[str] | None = None,
) -> WalkResult:
    """Cheap IngestionJob capture for evidenced orchestrators. No live APIs."""
    result = WalkResult()
    want = kinds or {
        "airflow",
        "glue",
        "adf",
        "stepfunctions",
        "composer",
        "cron",
        "fabric",
    }

    if "airflow" in want:
        for py in lake_root.rglob("*.py"):
            parts = {p.lower() for p in py.parts}
            try:
                text = py.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if not (
                "dags" in parts
                or "from airflow" in text
                or "import airflow" in text
                or "DAG(" in text
            ):
                continue
            result.discovered["airflow_dags"] = result.discovered.get("airflow_dags", 0) + 1
            if dry_run:
                result.skipped.append(str(py))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=_job_name_from_file(py, lake_root, text),
                description=f"Airflow DAG {py.relative_to(lake_root)}",
                orchestrator="airflow",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)

    if "glue" in want:
        for py in lake_root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if "awsglue" not in text and "GlueContext" not in text:
                continue
            result.discovered["glue_jobs"] = result.discovered.get("glue_jobs", 0) + 1
            if dry_run:
                result.skipped.append(str(py))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=py.stem,
                description=f"Glue job script {py.relative_to(lake_root)}",
                orchestrator="glue",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)

    if "stepfunctions" in want:
        for jf in list(lake_root.rglob("*.json")) + list(lake_root.rglob("*.asl.json")):
            try:
                text = jf.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if '"StartAt"' not in text or '"States"' not in text:
                continue
            result.discovered["stepfunctions"] = result.discovered.get("stepfunctions", 0) + 1
            if dry_run:
                result.skipped.append(str(jf))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=jf.stem.replace(".asl", ""),
                description=f"Step Functions ASL {jf.relative_to(lake_root)}",
                orchestrator="stepfunctions",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)

    if "adf" in want:
        for jf in list(lake_root.rglob("*.json")) + list(lake_root.rglob("*.yml")):
            try:
                text = jf.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if "Microsoft.DataFactory" not in text:
                continue
            result.discovered["adf_pipelines"] = result.discovered.get("adf_pipelines", 0) + 1
            if dry_run:
                result.skipped.append(str(jf))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=jf.stem,
                description=f"ADF pipeline {jf.relative_to(lake_root)}",
                orchestrator="adf",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)

    if "composer" in want:
        for yf in list(lake_root.rglob("*.yml")) + list(lake_root.rglob("*.yaml")):
            try:
                text = yf.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if "composer.googleapis.com" not in text and "composer" not in {p.lower() for p in yf.parts}:
                continue
            if "composer.googleapis.com" not in text and "airflowConfigOverrides" not in text:
                continue
            result.discovered["composer"] = result.discovered.get("composer", 0) + 1
            if dry_run:
                result.skipped.append(str(yf))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=yf.parent.name or yf.stem,
                description=f"Cloud Composer marker {yf.relative_to(lake_root)}",
                orchestrator="composer",
                mode="batch",
                target_layer="",
            ):
                result.record(rel, action)

    if "cron" in want:
        for yf in list(lake_root.rglob("*.yml")) + list(lake_root.rglob("*.yaml")):
            try:
                text = yf.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if "kind: CronJob" not in text:
                continue
            low = text.lower()
            if not any(n in low for n in ("dbt", "spark-submit", "python", "glue", "airflow")):
                continue
            result.discovered["cronjobs"] = result.discovered.get("cronjobs", 0) + 1
            if dry_run:
                result.skipped.append(str(yf))
                continue
            for rel, action in capture_ingestion_job(
                bundle,
                name=yf.stem,
                description=f"K8s CronJob loader {yf.relative_to(lake_root)}",
                orchestrator="k8s-cronjob",
                mode="batch",
                schedule="",
                target_layer="",
            ):
                result.record(rel, action)

    return result


def walk_storage_markers(
    lake_root: Path,
    bundle: Path,
    *,
    dry_run: bool = False,
) -> WalkResult:
    result = WalkResult()
    for hint in ("storage", "s3", "adls"):
        for d in lake_root.rglob(hint):
            if not d.is_dir():
                continue
            result.discovered["storage_dirs"] = result.discovered.get("storage_dirs", 0) + 1
            if dry_run:
                result.skipped.append(str(d))
                continue
            for rel, action in capture_storage(
                bundle,
                name=d.name,
                kind="prefix",
                uri=str(d.resolve()),
                description=f"Storage path convention {d.relative_to(lake_root)}",
            ):
                result.record(rel, action)
    catalogs = list(lake_root.rglob("catalog.json"))[:8]
    for c in catalogs:
        result.discovered["catalog_json"] = result.discovered.get("catalog_json", 0) + 1
        if dry_run:
            result.skipped.append(str(c))
            continue
        for rel, action in capture_data_catalog(
            bundle,
            name=c.parent.name or c.stem,
            description=f"Catalog export {c.relative_to(lake_root)}",
        ):
            result.record(rel, action)
    return result


def walk_scoped(
    lake_root: Path | None,
    bundle: Path,
    *,
    domains: list[str],
    source_name: str | None = None,
    fabric_items: Path | None = None,
    pbi_bindings: Path | None = None,
    inventory: Path | None = None,
    workspace: str = "",
    workspace_id: str = "",
    inventory_layer: str = "gold",
    max_files: int = 500,
    dry_run: bool = False,
) -> WalkResult:
    """Domain-scoped capture used by `--from-plan --area` / orchestrate."""
    result = WalkResult()
    wanted = set(domains or [])
    if lake_root and "lake" in wanted:
        _merge_walk(
            result,
            walk_lake(
                lake_root,
                bundle,
                source_name=source_name,
                max_files=max_files,
                dry_run=dry_run,
            ),
        )
    if lake_root and "elt" in wanted:
        _merge_walk(result, walk_elt(lake_root, bundle, dry_run=dry_run))
    if lake_root and "orchestration" in wanted:
        _merge_walk(result, walk_orchestration(lake_root, bundle, dry_run=dry_run))
    if lake_root and "catalogs" in wanted:
        _merge_walk(result, walk_storage_markers(lake_root, bundle, dry_run=dry_run))
    if inventory and "catalogs" in wanted:
        _merge_walk(
            result,
            walk_inventory_json(inventory, bundle, layer=inventory_layer, dry_run=dry_run),
        )
    if pbi_bindings and "bi" in wanted:
        _merge_walk(result, walk_pbi_bindings(pbi_bindings, bundle, dry_run=dry_run))
    if fabric_items and wanted.intersection({"bi", "orchestration", "orch-fabric", "notebooks"}):
        _merge_walk(
            result,
            walk_fabric_items(
                fabric_items,
                bundle,
                workspace=workspace,
                workspace_id=workspace_id,
                dry_run=dry_run,
            ),
        )
    if lake_root and "dq" in wanted:
        _merge_walk(result, walk_dq_markers(lake_root, bundle, dry_run=dry_run))
    if lake_root and "duckdb" in wanted:
        _merge_walk(result, walk_duckdb(lake_root, bundle, dry_run=dry_run))
    if lake_root and "notebooks" in wanted:
        _merge_walk(result, walk_notebooks(lake_root, bundle, dry_run=dry_run))
    return result


def _merge_walk(into: WalkResult, other: WalkResult) -> WalkResult:
    into.created.extend(other.created)
    into.updated.extend(other.updated)
    into.skipped.extend(other.skipped)
    into.errors.extend(other.errors)
    for k, v in other.discovered.items():
        into.discovered[k] = into.discovered.get(k, 0) + v
    return into


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Walk a data lake filesystem or ingest Fabric/PBI inventory JSON into DEKC"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to a SQL/parquet filesystem mirror. Optional when --fabric-items is set.",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--source-name", default=None)
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--author", default="")
    parser.add_argument(
        "--fabric-items",
        default=None,
        help="Workspace items JSON from Fabric REST (Report, SemanticModel, Lakehouse, …) (#38)",
    )
    parser.add_argument("--pbi-bindings", default=None, help="Power BI report→dataset JSON")
    parser.add_argument("--inventory", default=None, help="INFORMATION_SCHEMA / table-list JSON (no COUNT metrics)")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--workspace-id", default="")
    parser.add_argument("--inventory-layer", default="gold")
    parser.add_argument("--system", default="Data platform", help="With --plan-only: system name")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Write a breadth-first RE plan for the path, then stop (no capture)",
    )
    parser.add_argument(
        "--from-plan",
        default=None,
        help="Existing .dekc/re-plan.json — scope capture with --area",
    )
    parser.add_argument(
        "--area",
        default=None,
        help="With --from-plan: one focus area (domain-scoped capture)",
    )
    parser.add_argument(
        "--export",
        action="append",
        default=[],
        help="Optional export JSON for --plan-only (Fabric / inventory / PBI)",
    )
    args = parser.parse_args(argv)
    from dekc_common import resolve_author

    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    lake = Path(args.path).resolve() if args.path else None

    if args.plan_only:
        from dekc_plan import write_plan

        roots = [lake] if lake else [repo]
        exports = [Path(e).resolve() for e in (args.export or [])]
        if args.fabric_items:
            exports.append(Path(args.fabric_items).resolve())
        if args.inventory:
            exports.append(Path(args.inventory).resolve())
        if args.pbi_bindings:
            exports.append(Path(args.pbi_bindings).resolve())
        bundle.mkdir(parents=True, exist_ok=True)
        plan = write_plan(bundle, roots, system_name=args.system, exports=exports)
        if args.json:
            print(json.dumps(plan, indent=2, default=str))
        else:
            from dekc_plan import render_plan_markdown

            print(render_plan_markdown(plan))
            written = plan.get("written") or {}
            print(f"\nWrote {written.get('md')} and {written.get('json')}")
        return 0

    if not args.dry_run:
        resolve_author(args.author)

    if args.from_plan:
        from dekc_plan import load_plan, scan_domains_from_plan

        plan = load_plan(Path(args.from_plan).resolve() if args.from_plan else bundle)
        domains = scan_domains_from_plan(plan, area=args.area)
        if args.area and not domains:
            payload = {
                "enrichment_only": True,
                "area": args.area,
                "domains": [],
                "counts": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
            }
            print(json.dumps(payload, indent=2) if args.json else f"enrichment only: area={args.area}")
            return 0
        if not args.path and not args.fabric_items and not args.pbi_bindings and not args.inventory:
            parser.error("provide a filesystem path and/or --fabric-items / --pbi-bindings / --inventory")
        ensure_bundle(bundle)
        result = walk_scoped(
            lake,
            bundle,
            domains=domains or ["lake"],
            source_name=args.source_name,
            fabric_items=Path(args.fabric_items).resolve() if args.fabric_items else None,
            pbi_bindings=Path(args.pbi_bindings).resolve() if args.pbi_bindings else None,
            inventory=Path(args.inventory).resolve() if args.inventory else None,
            workspace=args.workspace,
            workspace_id=args.workspace_id,
            inventory_layer=args.inventory_layer,
            max_files=args.max_files,
            dry_run=args.dry_run,
        )
    else:
        if not args.path and not args.fabric_items and not args.pbi_bindings and not args.inventory:
            parser.error("provide a filesystem path and/or --fabric-items / --pbi-bindings / --inventory")

        ensure_bundle(bundle)
        result = WalkResult()
        if args.path:
            result = walk_lake(
                Path(args.path).resolve(),
                bundle,
                source_name=args.source_name,
                max_files=args.max_files,
                dry_run=args.dry_run,
            )
        if args.fabric_items:
            _merge_walk(
                result,
                walk_fabric_items(
                    Path(args.fabric_items).resolve(),
                    bundle,
                    workspace=args.workspace,
                    workspace_id=args.workspace_id,
                    dry_run=args.dry_run,
                ),
            )
        if args.pbi_bindings:
            _merge_walk(
                result,
                walk_pbi_bindings(Path(args.pbi_bindings).resolve(), bundle, dry_run=args.dry_run),
            )
        if args.inventory:
            _merge_walk(
                result,
                walk_inventory_json(
                    Path(args.inventory).resolve(),
                    bundle,
                    layer=args.inventory_layer,
                    dry_run=args.dry_run,
                ),
            )
    if (args.fabric_items or args.pbi_bindings or args.inventory) and not args.dry_run:
        n = len(result.created) + len(result.updated)
        append_log(
            bundle,
            f"Fabric/control-plane walk: +{len(result.created)} ~{len(result.updated)} "
            f"skip {len(result.skipped)} ({n} writes)",
        )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        c = result.to_dict()["counts"]
        print(
            f"Walk complete: created={c['created']} updated={c['updated']} "
            f"skipped={c['skipped']} errors={c['errors']}"
        )
        if result.discovered:
            print("  discovered:", json.dumps(result.discovered))
        for e in result.errors:
            print(f"ERROR: {e}", file=sys.stderr)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
