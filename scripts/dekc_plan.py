#!/usr/bin/env python3
"""Breadth-first reverse-engineering plan (presence and counts only).

Maps scan roots plus optional control-plane export files, ranks focus areas,
and emits a Markdown checklist plus JSON the orchestrator and specialists consume.

This is not a full walk: no live Glue/S3/Fabric calls, no GE runtime.
Query-time retrieve (data-retriever / dekc-retrieve) is a different path.

DEKC owns data orchestration + ELT/ETL. SAC owns CI/CD. Actions that only
trigger Glue/dbt are recorded as a cross-link note, not a Pipeline noun.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import slugify  # noqa: E402

PLAN_VERSION = "1"
DEKC_DIRNAME = ".dekc"
PLAN_JSON_NAME = "re-plan.json"
PLAN_MD_NAME = "re-plan.md"
PLAN_PROGRESS_NAME = "re-plan-progress.json"

DOT_WALK = frozenset({".github", ".gitlab", ".circleci"})
PLAN_IGNORE = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
        ".terraform",
        ".git",
        ".grok",
        ".output",
        ".tanstack",
        ".nitro",
        ".vinxi",
    }
)

MAX_DEPTH = 5
MAX_FILES = 2500
PEEK_BYTES = 2048
MAX_HITS = 24

MAJOR_DIR_NAMES = {
    "bronze",
    "silver",
    "gold",
    "raw",
    "staging",
    "curated",
    "marts",
    "models",
    "dags",
    "airflow",
    "glue",
    "adf",
    "pipelines",
    "notebooks",
    "sql",
    "warehouse",
    "lake",
    "lakehouse",
    "dbt",
    "spark",
    "emr",
    "quality",
    "gx",
    "great_expectations",
    "soda",
    "storage",
    "catalog",
    "k8s",
    "cron",
    "composer",
    "stepfunctions",
    "analytics",
}

LAKE_DIR_HINTS = {
    "bronze",
    "silver",
    "gold",
    "raw",
    "staging",
    "curated",
    "marts",
    "lake",
    "lakehouse",
    "warehouse",
}

SQL_SUFFIXES = {".sql"}
DAX_SUFFIXES = {".dax"}
YAML_SUFFIXES = {".yml", ".yaml"}
JSON_SUFFIXES = {".json"}


def _checklist(pairs: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"id": i, "text": t, "status": "pending", "note": ""} for i, t in pairs]


AREA_SPECS: dict[str, dict[str, Any]] = {
    "lake": {
        "title": "Lake / SQL / parquet / Delta",
        "kind": "domain",
        "agent": "schema-scout",
        "scan_domains": ["lake"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory SQL trees, parquet datasets, and Delta _delta_log markers"),
                ("layers", "Map medallion folders (bronze / silver / gold / raw)"),
                ("capture", "Capture tables/views/queries via filesystem walk (script-owned write)"),
                ("stubs", "Record referenced tables as stubs only when SQL evidence exists"),
                ("enrich", "Enrich schema/column contracts (agent judgment; no invented columns)"),
            ]
        ),
    },
    "elt": {
        "title": "ELT / ETL (dbt, Spark/EMR, warehouse SQL)",
        "kind": "domain",
        "agent": "stream-job-scout",
        "scan_domains": ["elt"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory dbt projects, Spark/EMR job defs, and warehouse SQL trees"),
                ("capture", "Capture IngestionJob / Transformation markers (script-owned write)"),
                ("models", "Note dbt models vs ad-hoc warehouse SQL"),
                ("link", "Join jobs to landing tables only when evidenced"),
                ("enrich", "Enrich purpose and cadence; do not invent lineage"),
            ]
        ),
    },
    "orchestration": {
        "title": "Data orchestration (Airflow / ADF / Glue / Fabric / cron)",
        "kind": "domain",
        "agent": "stream-job-scout",
        "scan_domains": ["orchestration"],
        "weight": 4,
        "checklist": _checklist(
            [
                ("inventory", "Inventory Airflow DAGs, ADF, Glue scripts, Step Functions, Fabric pipelines, cron loaders"),
                ("capture", "Capture IngestionJob concepts for evidenced orchestrators (script-owned write)"),
                ("schedule", "Note schedules / DAG ids / state machines when present in files"),
                ("link", "Join jobs to bronze/silver landings only with evidence"),
                ("enrich", "Enrich ownership; SAC owns CI/CD — do not capture Actions as Pipeline"),
            ]
        ),
    },
    "catalogs": {
        "title": "Catalogs / StorageLocation",
        "kind": "domain",
        "agent": "schema-scout",
        "scan_domains": ["catalogs"],
        "weight": 2,
        "checklist": _checklist(
            [
                ("inventory", "Inventory catalog JSON / INFORMATION_SCHEMA exports and storage path conventions"),
                ("capture", "Capture DataCatalog / StorageLocation (script-owned write)"),
                ("link", "Join storage to layers when path prefixes evidence a zone"),
                ("enrich", "Do not call live Glue/S3 APIs — exports and mirrors only"),
            ]
        ),
    },
    "bi": {
        "title": "Reports / DAX / Power BI / Fabric serve",
        "kind": "domain",
        "agent": "report-cataloger",
        "scan_domains": ["bi"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory DAX, Power BI bindings, and Fabric Report / SemanticModel exports"),
                ("capture", "Capture Report / Dashboard / SemanticModel (script-owned write)"),
                ("bind", "Join reports to datasets only when binding JSON evidences it"),
                ("enrich", "Fabric Report ≠ DEKC Dashboard unless the export says Dashboard"),
            ]
        ),
    },
    "lineage": {
        "title": "SQL / job lineage",
        "kind": "domain",
        "agent": "lineage-tracer",
        "scan_domains": [],
        "weight": 2,
        "checklist": _checklist(
            [
                ("sql", "Extract FROM/JOIN edges from walked SQL (no invented edges)"),
                ("jobs", "Materialize job → table landings only with evidence"),
                ("promote", "Record bronze→silver→gold promotions when the same basename appears"),
                ("enrich", "Retract unproven edges rather than inventing them for grade"),
            ]
        ),
    },
    "semantic": {
        "title": "Business objects / gold semantics",
        "kind": "domain",
        "agent": "semantic-mapper",
        "scan_domains": [],
        "weight": 2,
        "checklist": _checklist(
            [
                ("gold", "Identify gold / mart tables and curated semantic models"),
                ("promote", "Promote gold → BusinessObject + glossary when meaning is evidenced"),
                ("metrics", "Capture metrics only with DAX/SQL definitions"),
                ("enrich", "Do not invent business names for bronze stubs"),
            ]
        ),
    },
    "dq": {
        "title": "Data quality markers (GE / Soda / dbt tests)",
        "kind": "domain",
        "agent": "dq-scout",
        "scan_domains": ["dq"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory Great Expectations suites, Soda YAML, and dbt tests"),
                ("capture", "Capture DQRule nouns from filenames / suite ids (cheap; no GE runtime)"),
                ("link", "Join rules to tables only when the suite names a table"),
                ("enrich", "Do not fake expectation results or Soda scan output"),
            ]
        ),
    },
}

SPECIALIST_SPECS: dict[str, dict[str, Any]] = {
    "orch-airflow": {
        "title": "Airflow / DAG folders",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "airflow-scout",
        "scan_domains": [],
        "weight": 4,
        "checklist": _checklist(
            [
                ("inventory", "Inventory dags/ and DAG( / airflow imports"),
                ("dag-ids", "Record dag_id values from source when present"),
                ("enrich", "Enrich IngestionJob purpose (do not re-walk the whole lake)"),
                ("link", "Join DAGs to landing tables only with SQL/task evidence"),
            ]
        ),
    },
    "orch-glue": {
        "title": "Glue job scripts",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "glue-job-scout",
        "scan_domains": [],
        "weight": 4,
        "checklist": _checklist(
            [
                ("inventory", "Inventory Glue job scripts (awsglue / GlueJob path conventions)"),
                ("enrich", "Enrich IngestionJob purpose from comments / job names"),
                ("link", "Join jobs to S3/StorageLocation only when the script names a path"),
                ("boundary", "No live Glue API — export/mirror only"),
            ]
        ),
    },
    "orch-fabric": {
        "title": "Fabric pipelines / notebooks (export)",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "fabric-pipeline-scout",
        "scan_domains": [],
        "weight": 4,
        "checklist": _checklist(
            [
                ("inventory", "Inventory Fabric pipeline / notebook items from export JSON"),
                ("enrich", "Enrich IngestionJob (fabric-pipeline vs fabric-notebook)"),
                ("serve", "Leave Report / SemanticModel to report-cataloger"),
                ("boundary", "dekc_walk does not call Fabric REST"),
            ]
        ),
    },
    "orch-adf": {
        "title": "Azure Data Factory",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "adf-scout",
        "scan_domains": [],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory ADF pipeline ARM / factory JSON"),
                ("enrich", "Enrich IngestionJob orchestrator=adf"),
            ]
        ),
    },
    "orch-stepfunctions": {
        "title": "Step Functions ASL",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "stepfunctions-scout",
        "scan_domains": [],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory ASL state machines (StartAt + States)"),
                ("enrich", "Enrich IngestionJob orchestrator=stepfunctions"),
            ]
        ),
    },
    "orch-composer": {
        "title": "Cloud Composer",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "composer-scout",
        "scan_domains": [],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory Composer markers (composer.googleapis.com / composer/)"),
                ("airflow", "Composer still runs Airflow — do not drop airflow-scout if DAGs exist"),
                ("enrich", "Enrich IngestionJob orchestrator=composer"),
            ]
        ),
    },
    "orch-cron": {
        "title": "Cron / K8s CronJob loaders",
        "kind": "orchestration",
        "parent": "orchestration",
        "agent": "cron-loader-scout",
        "scan_domains": [],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory crontab and kind: CronJob loaders (dbt / spark-submit / python)"),
                ("enrich", "Enrich IngestionJob orchestrator=cron or k8s-cronjob"),
                ("skip-ci", "Scheduled GitHub Actions stay on SAC unless they only trigger a data job"),
            ]
        ),
    },
    "elt-dbt": {
        "title": "dbt ELT",
        "kind": "elt-tool",
        "parent": "elt",
        "agent": "dbt-elt-scout",
        "scan_domains": [],
        "weight": 4,
        "checklist": _checklist(
            [
                ("project", "Map dbt_project.yml, models/, and sources"),
                ("tests", "Note dbt tests (hand to dq-scout; do not fake run results)"),
                ("enrich", "Enrich IngestionJob / Transformation purpose (walk already captured model SQL)"),
            ]
        ),
    },
    "duckdb": {
        "title": "DuckDB",
        "kind": "elt-tool",
        "parent": "lake",
        "agent": "duckdb-scout",
        "scan_domains": ["duckdb"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory *.duckdb / *.ddb and duckdb SQL"),
                ("capture", "Capture SourceSystem kind=duckdb (script-owned write)"),
                ("enrich", "Do not open the binary as a live catalog unless a SQL export exists"),
            ]
        ),
    },
    "notebooks": {
        "title": "Notebooks (.ipynb / Fabric notebooks)",
        "kind": "elt-tool",
        "parent": "elt",
        "agent": "notebook-scout",
        "scan_domains": ["notebooks"],
        "weight": 3,
        "checklist": _checklist(
            [
                ("inventory", "Inventory .ipynb and Fabric notebook exports"),
                ("sql", "Extract SQL cells (%%sql / spark.sql / SELECT) — cheap capture"),
                ("enrich", "Do not invent lineage from incomplete notebook cells"),
            ]
        ),
    },
}


def plan_paths(bundle: Path) -> dict[str, Path]:
    d = bundle / DEKC_DIRNAME
    return {
        "dir": d,
        "json": d / PLAN_JSON_NAME,
        "md": d / PLAN_MD_NAME,
        "progress": d / PLAN_PROGRESS_NAME,
    }


def resolve_plan_files(plan_or_bundle: Path) -> dict[str, Path]:
    p = Path(plan_or_bundle)
    if p.is_file() and p.suffix == ".json":
        d = p.parent
        return {"dir": d, "json": p, "md": d / PLAN_MD_NAME, "progress": d / PLAN_PROGRESS_NAME}
    if p.is_dir() and (p / PLAN_JSON_NAME).is_file():
        return {
            "dir": p,
            "json": p / PLAN_JSON_NAME,
            "md": p / PLAN_MD_NAME,
            "progress": p / PLAN_PROGRESS_NAME,
        }
    return plan_paths(p)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _should_skip(name: str) -> bool:
    if name in DOT_WALK:
        return False
    if name in PLAN_IGNORE:
        return True
    if name.startswith(".git"):
        return True
    if name.startswith(".") and name not in DOT_WALK:
        return True
    return False


def bfs_walk(root: Path, *, max_depth: int = MAX_DEPTH, max_files: int = MAX_FILES) -> list[Path]:
    """Breadth-first file listing. Cheap presence scan, not a full lake dump."""
    root = root.resolve()
    out: list[Path] = []
    q: deque[tuple[Path, int]] = deque([(root, 0)])
    while q and len(out) < max_files:
        cur, depth = q.popleft()
        if depth > max_depth:
            continue
        try:
            entries = sorted(cur.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except (OSError, PermissionError):
            continue
        child_dirs: list[Path] = []
        for p in entries:
            if _should_skip(p.name):
                continue
            if p.is_dir():
                child_dirs.append(p)
            elif p.is_file():
                out.append(p)
                if len(out) >= max_files:
                    break
        if depth < max_depth:
            for d in child_dirs:
                q.append((d, depth + 1))
    return out


def _peek(path: Path, limit: int = PEEK_BYTES) -> str:
    try:
        if path.stat().st_size > 1_000_000:
            return ""
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def _name_has_any(name: str, needles: tuple[str, ...]) -> bool:
    low = name.lower()
    return any(n in low for n in needles)


def _hit(kind: str, rel: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {"kind": kind, "path": rel}
    if extra:
        row.update(extra)
    return row


def _trim_hits(groups: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    trimmed: dict[str, list[dict[str, Any]]] = {}
    for key, rows in groups.items():
        seen: set[tuple[str, str]] = set()
        uniq: list[dict[str, Any]] = []
        for row in rows:
            k = (row.get("kind", ""), row.get("path", ""))
            if k in seen:
                continue
            seen.add(k)
            uniq.append(row)
        trimmed[key] = uniq[:MAX_HITS]
    return trimmed


def _looks_like_cicd_handoff(text: str) -> bool:
    low = text.lower()
    return any(
        n in low
        for n in (
            "glue",
            "dbt ",
            "dbt-",
            "airflow",
            "awsglue",
            "databricks",
            "spark-submit",
            "fabric",
            "datafactory",
        )
    )


def inspect_export(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Presence-only read of a control-plane JSON/YAML export (no live APIs)."""
    hits: dict[str, list[dict[str, Any]]] = {k: [] for k in list(AREA_SPECS) + list(SPECIALIST_SPECS)}
    path = Path(path)
    if not path.is_file():
        return hits
    rel = path.name
    text = _peek(path, 8000)
    low = text.lower()
    suffix = path.suffix.lower()
    if suffix not in {".json", ".yml", ".yaml"}:
        return hits

    fabric_needles = (
        "lakehouse",
        "datapipeline",
        "semanticmodel",
        "sqlendpoint",
        "eventstream",
        '"notebook"',
    )
    if any(n in low for n in fabric_needles) and ("displayname" in low or '"type"' in low):
        hits["orchestration"].append(_hit("fabric-export", rel))
        hits["orch-fabric"].append(_hit("fabric-export", rel))
        if any(n in low for n in ("report", "semanticmodel", "dashboard", "dataset")):
            hits["bi"].append(_hit("fabric-serve", rel))
        if "notebook" in low:
            hits["notebooks"].append(_hit("fabric-notebook", rel))

    if any(n in text for n in ("TABLE_NAME", "table_name", "TABLE_SCHEMA", "information_schema")):
        hits["catalogs"].append(_hit("inventory-json", rel))
    elif '"tables"' in low and ("schema" in low or "layer" in low):
        hits["catalogs"].append(_hit("inventory-json", rel))

    if "datasetid" in low or "dataset_id" in low or "datasources_status" in low:
        hits["bi"].append(_hit("pbi-bindings", rel))

    if "awstemplateformatversion" in low and "datafactory" in low:
        hits["orchestration"].append(_hit("adf-export", rel))
        hits["orch-adf"].append(_hit("adf-export", rel))

    return hits


def inspect_root(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = bfs_walk(root)
    top_level: list[str] = []
    try:
        for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
            if p.name in PLAN_IGNORE or p.name == ".git":
                continue
            if p.name.startswith(".") and p.name not in DOT_WALK:
                continue
            top_level.append(p.name + ("/" if p.is_dir() else ""))
    except OSError:
        pass

    major_dirs: list[str] = []
    seen_major: set[str] = set()
    hits: dict[str, list[dict[str, Any]]] = {k: [] for k in AREA_SPECS}
    specialist_hits: dict[str, list[dict[str, Any]]] = {k: [] for k in SPECIALIST_SPECS}
    ecosystems: set[str] = set()
    cicd_handoff: list[dict[str, Any]] = []
    sql_count = 0
    parquet_count = 0
    delta_count = 0

    for f in files:
        rel = _rel(root, f)
        parts = Path(rel).parts
        name = f.name
        suffix = f.suffix.lower()
        low_name = name.lower()
        low_rel = rel.lower()

        for part in parts[:-1]:
            if part in MAJOR_DIR_NAMES and part not in seen_major:
                seen_major.add(part)
                major_dirs.append(part)

        if suffix in SQL_SUFFIXES:
            sql_count += 1
            hits["lake"].append(_hit("sql", rel))
            ecosystems.add("sql")
            peek = _peek(f)
            if "duckdb" in peek.lower() or "duckdb" in low_rel:
                specialist_hits["duckdb"].append(_hit("duckdb-sql", rel))
                ecosystems.add("duckdb")
            if any(p in {"models", "dbt"} for p in parts) or "ref(" in peek:
                hits["elt"].append(_hit("dbt-sql", rel))
                specialist_hits["elt-dbt"].append(_hit("dbt-model", rel))
                ecosystems.add("dbt")
            elif any(p in {"warehouse", "marts", "gold", "silver"} for p in parts):
                hits["elt"].append(_hit("warehouse-sql", rel))

        if suffix in DAX_SUFFIXES or low_name.endswith(".dax.cs"):
            hits["bi"].append(_hit("dax", rel))
            ecosystems.add("dax")

        if suffix == ".parquet" or low_name.endswith(".parquet"):
            parquet_count += 1
            hits["lake"].append(_hit("parquet", rel))
            ecosystems.add("parquet")

        if name == "_delta_log" or "_delta_log" in parts:
            delta_count += 1
            hits["lake"].append(_hit("delta", rel))
            ecosystems.add("delta")
        if low_name == "000.json" and "_delta_log" in parts:
            hits["lake"].append(_hit("delta-log", rel))
            ecosystems.add("delta")

        if suffix in {".duckdb", ".ddb"} or low_name.endswith(".duckdb"):
            specialist_hits["duckdb"].append(_hit("duckdb-file", rel))
            hits["lake"].append(_hit("duckdb-file", rel))
            ecosystems.add("duckdb")

        if suffix == ".ipynb":
            specialist_hits["notebooks"].append(_hit("ipynb", rel))
            hits["elt"].append(_hit("notebook", rel))
            ecosystems.add("notebook")

        if low_name in {"dbt_project.yml", "dbt_project.yaml", "packages.yml", "dependencies.yml"}:
            hits["elt"].append(_hit("dbt-project", rel))
            specialist_hits["elt-dbt"].append(_hit("dbt-project", rel))
            ecosystems.add("dbt")
        if low_name in {"schema.yml", "schema.yaml", "_schema.yml"} and any(
            p in {"models", "dbt"} for p in parts
        ):
            peek = _peek(f)
            specialist_hits["elt-dbt"].append(_hit("dbt-schema", rel))
            if "tests:" in peek or "data_tests:" in peek:
                hits["dq"].append(_hit("dbt-tests", rel))

        spark_name = _name_has_any(low_rel, ("spark", "emr", "glue"))
        if suffix in {".py", ".scala", ".json"} and spark_name:
            peek = _peek(f) if suffix != ".json" else _peek(f)
            if any(
                n in peek
                for n in ("SparkSession", "spark-submit", "awsglue", "EmrJob", "glue.Job")
            ) or any(p in {"spark", "emr"} for p in parts):
                hits["elt"].append(_hit("spark-job", rel))
                ecosystems.add("spark")

        if "dags" in parts or low_name.startswith("dag_") or "airflow" in parts:
            peek = _peek(f) if suffix in {".py", ".yml", ".yaml"} else ""
            if suffix == ".py" or "airflow" in peek.lower() or "dags" in parts:
                specialist_hits["orch-airflow"].append(_hit("airflow", rel))
                hits["orchestration"].append(_hit("airflow", rel))
                ecosystems.add("airflow")
        elif suffix == ".py":
            peek = _peek(f)
            if "from airflow" in peek or "import airflow" in peek or "DAG(" in peek:
                specialist_hits["orch-airflow"].append(_hit("airflow", rel))
                hits["orchestration"].append(_hit("airflow", rel))
                ecosystems.add("airflow")

        if suffix == ".py" and (
            "awsglue" in _peek(f) or "glue" in parts or low_name.startswith("glue_")
        ):
            peek = _peek(f)
            if "awsglue" in peek or "GlueContext" in peek or "glue" in parts:
                specialist_hits["orch-glue"].append(_hit("glue", rel))
                hits["orchestration"].append(_hit("glue", rel))
                ecosystems.add("glue")

        if suffix in JSON_SUFFIXES | YAML_SUFFIXES:
            peek = _peek(f)
            if '"StartAt"' in peek and '"States"' in peek:
                specialist_hits["orch-stepfunctions"].append(_hit("stepfunctions", rel))
                hits["orchestration"].append(_hit("stepfunctions", rel))
                ecosystems.add("stepfunctions")
            if "Microsoft.DataFactory" in peek or "datafactory" in low_rel:
                specialist_hits["orch-adf"].append(_hit("adf", rel))
                hits["orchestration"].append(_hit("adf", rel))
                ecosystems.add("adf")
            if any(n in peek.lower() for n in ("datapipeline", "fabric")) and (
                "pipeline" in low_name or "fabric" in low_rel
            ):
                specialist_hits["orch-fabric"].append(_hit("fabric-file", rel))
                hits["orchestration"].append(_hit("fabric-file", rel))
                ecosystems.add("fabric")
            if "composer.googleapis.com" in peek or "composer" in parts:
                specialist_hits["orch-composer"].append(_hit("composer", rel))
                hits["orchestration"].append(_hit("composer", rel))
                ecosystems.add("composer")
            if "kind: CronJob" in peek or "kind: CronJob" in _peek(f):
                cmdish = peek.lower()
                if any(n in cmdish for n in ("dbt", "spark-submit", "python", "glue", "airflow")):
                    specialist_hits["orch-cron"].append(_hit("k8s-cronjob", rel))
                    hits["orchestration"].append(_hit("k8s-cronjob", rel))
                    ecosystems.add("cron")

        if low_name in {"crontab", "cron"} or "cron.d" in parts or low_name.endswith(".cron"):
            peek = _peek(f)
            if any(n in peek.lower() for n in ("dbt", "spark-submit", "python", "glue")):
                specialist_hits["orch-cron"].append(_hit("cron", rel))
                hits["orchestration"].append(_hit("cron", rel))
                ecosystems.add("cron")

        if low_name in {"great_expectations.yml", "great_expectations.yaml"} or "great_expectations" in parts or "gx" in parts:
            if suffix in YAML_SUFFIXES | JSON_SUFFIXES or low_name.endswith(".json"):
                hits["dq"].append(_hit("great-expectations", rel))
                ecosystems.add("great-expectations")
        if low_name.startswith("soda") or "soda" in parts:
            if suffix in YAML_SUFFIXES:
                hits["dq"].append(_hit("soda", rel))
                ecosystems.add("soda")
        if "expectations" in parts and suffix == ".json":
            hits["dq"].append(_hit("ge-suite", rel))
            ecosystems.add("great-expectations")

        if any(n in low_rel for n in ("s3://", "abfss://", "wasbs://")) or any(
            p in {"storage", "s3", "adls", "warehouse"} for p in parts
        ):
            if suffix in {".sql", ".py", ".json", ".yml", ".yaml", ".md"} or name.endswith(".parquet"):
                hits["catalogs"].append(_hit("storage-path", rel))
        if any(p in {"catalog", "catalogs"} for p in parts) or low_name in {
            "catalog.json",
            "inventory.json",
            "information_schema.json",
        }:
            hits["catalogs"].append(_hit("catalog", rel))

        if ".github" in parts and "workflows" in parts and suffix in YAML_SUFFIXES:
            peek = _peek(f)
            if _looks_like_cicd_handoff(peek):
                cicd_handoff.append(_hit("github-actions", rel, {"owner": "sac"}))

    if any(d in LAKE_DIR_HINTS for d in seen_major):
        for d in sorted(seen_major & LAKE_DIR_HINTS):
            hits["lake"].append(_hit("layer-dir", d + "/"))

    if sql_count or parquet_count or delta_count or hits["elt"] or hits["orchestration"]:
        hits["lineage"].append(
            _hit(
                "sql-or-jobs",
                f"{sql_count} sql / {len(hits['orchestration'])} orch",
                {"count": sql_count + parquet_count + len(hits["orchestration"])},
            )
        )

    if any(d in {"gold", "marts", "semantic"} for d in seen_major) or hits["bi"]:
        hits["semantic"].append(_hit("gold-or-bi", "gold/marts or BI signals"))

    if sql_count:
        hits["lake"].append(_hit("source-files", f"{sql_count} sql", {"count": sql_count}))

    if "bronze" in seen_major or "gold" in seen_major or parquet_count or delta_count:
        layout = "lake"
    elif "dbt" in ecosystems and not hits["orchestration"]:
        layout = "dbt-project"
    elif hits["orchestration"] and not hits["lake"]:
        layout = "orchestration"
    elif sql_count and not parquet_count:
        layout = "warehouse"
    else:
        layout = "mixed"

    return {
        "path": str(root),
        "name": root.name,
        "top_level": top_level,
        "major_dirs": major_dirs,
        "ecosystems": sorted(ecosystems),
        "layout": layout,
        "hits": _trim_hits(hits),
        "specialist_hits": _trim_hits(specialist_hits),
        "cicd_handoff": cicd_handoff[:MAX_HITS],
        "file_count": len(files),
        "sql_count": sql_count,
        "parquet_count": parquet_count,
        "delta_count": delta_count,
    }


def _signal_for(area_id: str, spec: dict[str, Any], rows: list[dict[str, Any]]) -> int:
    weight = int(spec["weight"])
    n = 0
    for row in rows:
        if row.get("kind") in {"source-files", "sql-or-jobs"}:
            n += min(int(row.get("count") or 0), 8)
        else:
            n += 1
    return n * weight


def _combine_hits(inspected: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    combined: dict[str, list[dict[str, Any]]] = {}
    for info in inspected:
        for area_id, rows in (info.get(key) or {}).items():
            bucket = combined.setdefault(area_id, [])
            prefix = info["name"]
            for row in rows:
                item = dict(row)
                item["root"] = prefix
                bucket.append(item)
    return combined


def _area_entry(area_id: str, spec: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    signal = _signal_for(area_id, spec, rows)
    if signal <= 0:
        return None
    return {
        "id": area_id,
        "title": spec["title"],
        "kind": spec.get("kind") or "domain",
        "parent": spec.get("parent"),
        "signal": signal,
        "hit_count": len(rows),
        "agent": spec["agent"],
        "scan_domains": list(spec.get("scan_domains") or []),
        "hits": rows[:MAX_HITS],
        "checklist": [dict(x) for x in (spec.get("checklist") or [])],
        "spawn": True,
    }


def build_plan(
    roots: list[Path],
    *,
    system_name: str,
    exports: list[Path] | None = None,
) -> dict[str, Any]:
    inspected = [inspect_root(Path(r)) for r in roots]
    combined = _combine_hits(inspected, "hits")
    combined_spec = _combine_hits(inspected, "specialist_hits")
    export_notes: list[dict[str, Any]] = []

    for exp in exports or []:
        ep = Path(exp)
        export_notes.append({"path": str(ep.resolve()) if ep.exists() else str(ep), "name": ep.name})
        extra = inspect_export(ep)
        for area_id, rows in extra.items():
            if area_id in AREA_SPECS:
                combined.setdefault(area_id, []).extend(
                    [{**row, "root": ep.name} for row in rows]
                )
            elif area_id in SPECIALIST_SPECS:
                combined_spec.setdefault(area_id, []).extend(
                    [{**row, "root": ep.name} for row in rows]
                )

    focus: list[dict[str, Any]] = []
    for area_id, spec in AREA_SPECS.items():
        entry = _area_entry(area_id, spec, combined.get(area_id) or [])
        if entry:
            focus.append(entry)
    for area_id, spec in SPECIALIST_SPECS.items():
        entry = _area_entry(area_id, spec, combined_spec.get(area_id) or [])
        if entry:
            focus.append(entry)
    focus.sort(key=lambda a: (-int(a["signal"]), a["id"]))
    for i, area in enumerate(focus, start=1):
        area["rank"] = i

    ecosystems: list[str] = []
    cicd_handoff: list[dict[str, Any]] = []
    for info in inspected:
        for eco in info["ecosystems"]:
            if eco not in ecosystems:
                ecosystems.append(eco)
        cicd_handoff.extend(info.get("cicd_handoff") or [])

    slug = slugify(system_name)
    return {
        "version": PLAN_VERSION,
        "system": system_name,
        "system_slug": slug,
        "roots": [
            {
                "path": i["path"],
                "name": i["name"],
                "top_level": i["top_level"],
                "major_dirs": i["major_dirs"],
                "ecosystems": i["ecosystems"],
                "layout": i["layout"],
                "file_count": i["file_count"],
            }
            for i in inspected
        ],
        "exports": export_notes,
        "ecosystems": ecosystems,
        "focus_areas": focus,
        "specialists": [
            {
                "id": a["id"],
                "kind": a.get("kind"),
                "parent": a.get("parent"),
                "agent": a.get("agent"),
                "title": a.get("title"),
                "signal": a.get("signal"),
                "hit_count": a.get("hit_count"),
            }
            for a in focus
            if a.get("kind") in ("orchestration", "elt-tool")
        ],
        "cicd_handoff": cicd_handoff[:MAX_HITS],
        "artifacts": {
            "plan_json": f"{DEKC_DIRNAME}/{PLAN_JSON_NAME}",
            "plan_md": f"{DEKC_DIRNAME}/{PLAN_MD_NAME}",
            "progress": f"{DEKC_DIRNAME}/{PLAN_PROGRESS_NAME}",
        },
    }


def empty_progress(plan: dict[str, Any]) -> dict[str, Any]:
    areas: dict[str, Any] = {}
    for area in plan.get("focus_areas") or []:
        areas[area["id"]] = {
            "items": {
                item["id"]: {"status": item.get("status") or "pending", "note": item.get("note") or ""}
                for item in area.get("checklist") or []
            }
        }
    return {
        "plan": plan.get("artifacts", {}).get("plan_json", f"{DEKC_DIRNAME}/{PLAN_JSON_NAME}"),
        "areas": areas,
    }


def apply_progress(plan: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    areas = progress.get("areas") or {}
    for area in plan.get("focus_areas") or []:
        rec = areas.get(area["id"]) or {}
        items = rec.get("items") or {}
        for item in area.get("checklist") or []:
            st = items.get(item["id"]) or {}
            if st.get("status"):
                item["status"] = st["status"]
            if "note" in st:
                item["note"] = st.get("note") or ""
    return plan


def checklist_summary(plan: dict[str, Any]) -> dict[str, int]:
    done = blocked = pending = total = 0
    for area in plan.get("focus_areas") or []:
        for item in area.get("checklist") or []:
            total += 1
            status = item.get("status") or "pending"
            if status == "done":
                done += 1
            elif status == "blocked":
                blocked += 1
            else:
                pending += 1
    return {"done": done, "blocked": blocked, "pending": pending, "total": total}


def scan_domains_from_plan(plan: dict[str, Any], *, area: str | None = None) -> list[str]:
    domains: list[str] = []
    for focus in plan.get("focus_areas") or []:
        if area and focus["id"] != area:
            continue
        for d in focus.get("scan_domains") or []:
            if d not in domains:
                domains.append(d)
    return domains


def render_plan_markdown(plan: dict[str, Any]) -> str:
    system = plan.get("system") or "Data platform"
    lines: list[str] = [
        f"# Reverse-engineering plan: {system}",
        "",
        "Generated by `dekc_plan.py` (deterministic; presence and counts only).",
        "Walkers populate the graph. Query-time `data-retriever` / `dekc-retrieve` stay separate.",
        "Adversarial skeptics + `re-adversary-judge` still close every walk — this plan does not replace them.",
        "",
        "## Scan map",
        "",
    ]
    for root in plan.get("roots") or []:
        lines.append(f"### `{root.get('name')}` (`{root.get('path')}`)")
        lines.append("")
        lines.append(f"- Layout: **{root.get('layout')}**")
        ecos = ", ".join(root.get("ecosystems") or []) or "_none detected_"
        lines.append(f"- Ecosystems: {ecos}")
        top = ", ".join(f"`{t}`" for t in (root.get("top_level") or []))
        if top:
            lines.append(f"- Top-level: {top}")
        majors = ", ".join(f"`{d}/`" for d in (root.get("major_dirs") or []))
        if majors:
            lines.append(f"- Major dirs: {majors}")
        lines.append(f"- Files visited (BFS cap): {root.get('file_count')}")
        lines.append("")

    exports = plan.get("exports") or []
    if exports:
        lines.extend(["## Export paths (control-plane JSON, no live APIs)", ""])
        for exp in exports:
            lines.append(f"- `{exp.get('name')}` — `{exp.get('path')}`")
        lines.append("")

    def _table(areas: list[dict[str, Any]]) -> None:
        lines.extend(
            [
                "| Rank | Area | Signal | Hits | Agent | Scan domains |",
                "|------|------|--------|------|-------|--------------|",
            ]
        )
        for area in areas:
            domains = ", ".join(area.get("scan_domains") or []) or "enrichment only"
            lines.append(
                f"| {area.get('rank')} | `{area['id']}` — {area.get('title')} | "
                f"{area.get('signal')} | {area.get('hit_count')} | `{area.get('agent')}` | `{domains}` |"
            )
        lines.append("")

    domains_only = [a for a in (plan.get("focus_areas") or []) if a.get("kind", "domain") == "domain"]
    orch_specs = [a for a in (plan.get("focus_areas") or []) if a.get("kind") == "orchestration"]
    elt_specs = [a for a in (plan.get("focus_areas") or []) if a.get("kind") == "elt-tool"]

    lines.extend(["## Focus areas (ranked by signal)", ""])
    if domains_only:
        _table(domains_only)
    else:
        lines.append("_None — no lake / ELT / orchestration signals._")
        lines.append("")

    lines.extend(
        [
            "## Orchestration specialists (signal-gated)",
            "",
            "Spawn **only** when markers exist. No Airflow scout without DAG / `airflow` markers.",
            "No Glue scout without `awsglue` / Glue job scripts. Specialists enrich after the",
            "deterministic walk — they do not replace `dekc_walk.py`.",
            "",
        ]
    )
    if orch_specs:
        _table(orch_specs)
    else:
        lines.append("_None — no orchestration specialist signals._")
        lines.append("")

    lines.extend(
        [
            "## ELT specialists (signal-gated)",
            "",
            "Spawn **only** when markers exist (no DuckDB scout without `*.duckdb` / duckdb SQL;",
            "no notebook scout without `.ipynb` or Fabric notebook export).",
            "",
        ]
    )
    if elt_specs:
        _table(elt_specs)
    else:
        lines.append("_None — no ELT specialist signals._")
        lines.append("")

    handoff = plan.get("cicd_handoff") or []
    lines.extend(
        [
            "## CI/CD boundary (SAC owns pipelines)",
            "",
            "DEKC captures **data jobs** (`IngestionJob`). SAC captures **CI/CD pipelines**.",
            "If Actions only trigger Glue/dbt, cross-link the workflow; do not steal SAC Pipeline nouns.",
            "",
        ]
    )
    if handoff:
        sample = ", ".join(f"`{h.get('path')}`" for h in handoff[:8])
        lines.append(f"Handoff signals: {sample}")
        lines.append("")
    else:
        lines.append("_No CI files that mention Glue/dbt/Airflow were seen._")
        lines.append("")

    lines.extend(
        [
            "## Suggested fan-out",
            "",
            "Parent reviews this plan, then **spawns one child per domain area and each listed specialist**.",
            "Independent domains run in parallel. Then existing **adversarial skeptics** → `re-adversary-judge`.",
            "Do **not** spawn a specialist the plan did not list. Retrievers are not walkers.",
            "",
            "```bash",
            "# Pause after plan",
            'python3 scripts/dekc_orchestrate.py --plan-only --system "Name" --scan-root <mirror>',
            "# Child: one area, domain-scoped walk + capture",
            "python3 scripts/dekc_orchestrate.py --from-plan knowledge/.dekc/re-plan.json --area lake \\",
            '  --system "Name" --scan-root <mirror>',
            "python3 scripts/dekc_plan.py mark --plan knowledge/.dekc/re-plan.json --area lake \\",
            "  --item inventory --status done",
            "# After producers: grade + skeptics + judge (unchanged)",
            "python3 scripts/dekc_grade.py --repo . --bundle knowledge",
            "```",
            "",
            "## Deep-dive checklists",
            "",
        ]
    )
    for area in plan.get("focus_areas") or []:
        kind = area.get("kind") or "domain"
        lines.append(f"### `{area['id']}` — `{area.get('agent')}` ({kind})")
        lines.append("")
        lines.append(area.get("title") or area["id"])
        sample = ", ".join(f"`{h.get('path')}`" for h in (area.get("hits") or [])[:8] if h.get("path"))
        if sample:
            lines.append("")
            lines.append(f"Signals: {sample}")
        lines.append("")
        for item in area.get("checklist") or []:
            status = item.get("status") or "pending"
            box = "x" if status == "done" else " "
            note = item.get("note") or ""
            extra = ""
            if status == "blocked":
                extra = f" *(blocked{': ' + note if note else ''})*"
            elif note and status == "done":
                extra = f" *({note})*"
            lines.append(f"- [{box}] `{item['id']}` — {item['text']}{extra}")
        lines.append("")

    summary = checklist_summary(plan)
    lines.extend(
        [
            "## Checklist summary",
            "",
            f"- done: {summary['done']}",
            f"- blocked: {summary['blocked']}",
            f"- pending: {summary['pending']}",
            f"- total: {summary['total']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_plan(
    bundle: Path,
    roots: list[Path],
    *,
    system_name: str,
    exports: list[Path] | None = None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = Path(bundle)
    plan = build_plan(roots, system_name=system_name, exports=exports)
    if progress:
        apply_progress(plan, progress)
        prog = progress
    else:
        prog = empty_progress(plan)
    paths = plan_paths(bundle)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["json"].write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    paths["md"].write_text(render_plan_markdown(plan), encoding="utf-8")
    paths["progress"].write_text(json.dumps(prog, indent=2) + "\n", encoding="utf-8")
    plan = dict(plan)
    plan["written"] = {k: str(v) for k, v in paths.items()}
    plan["checklist"] = checklist_summary(plan)
    return plan


def load_plan(plan_or_bundle: Path) -> dict[str, Any]:
    files = resolve_plan_files(plan_or_bundle)
    if not files["json"].is_file():
        raise FileNotFoundError(f"RE plan not found: {files['json']}")
    plan = json.loads(files["json"].read_text(encoding="utf-8"))
    if files["progress"].is_file():
        prog = json.loads(files["progress"].read_text(encoding="utf-8"))
        apply_progress(plan, prog)
    return plan


def mark_checklist(
    plan_or_bundle: Path,
    *,
    area: str,
    item: str,
    status: str,
    note: str = "",
) -> dict[str, Any]:
    if status not in {"pending", "done", "blocked"}:
        raise ValueError(f"status must be pending|done|blocked, got {status!r}")
    files = resolve_plan_files(plan_or_bundle)
    plan = load_plan(files["json"])
    focus_ids = {a["id"] for a in plan.get("focus_areas") or []}
    if area not in focus_ids:
        raise KeyError(f"area {area!r} is not in the plan ({sorted(focus_ids)})")
    item_ids: list[str] = []
    for a in plan["focus_areas"]:
        if a["id"] == area:
            item_ids = [i["id"] for i in a.get("checklist") or []]
            break
    if item not in item_ids:
        raise KeyError(f"item {item!r} is not in area {area!r} ({item_ids})")
    if files["progress"].is_file():
        prog = json.loads(files["progress"].read_text(encoding="utf-8"))
    else:
        prog = empty_progress(plan)
    areas = prog.setdefault("areas", {})
    rec = areas.setdefault(area, {"items": {}})
    items = rec.setdefault("items", {})
    items[item] = {"status": status, "note": note}
    apply_progress(plan, prog)
    files["dir"].mkdir(parents=True, exist_ok=True)
    files["json"].write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    files["progress"].write_text(json.dumps(prog, indent=2) + "\n", encoding="utf-8")
    files["md"].write_text(render_plan_markdown(plan), encoding="utf-8")
    return {
        "area": area,
        "item": item,
        "status": status,
        "note": note,
        "checklist": checklist_summary(plan),
        "written": {k: str(v) for k, v in files.items()},
    }


def mark_area_item_if_present(
    plan_or_bundle: Path,
    *,
    area: str,
    item: str,
    status: str = "done",
    note: str = "",
) -> dict[str, Any] | None:
    try:
        return mark_checklist(plan_or_bundle, area=area, item=item, status=status, note=note)
    except (FileNotFoundError, KeyError):
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEKC breadth-first reverse-engineering plan")
    sub = p.add_subparsers(dest="cmd")

    p.add_argument("--repo", default=".", help="Knowledge host repo")
    p.add_argument("--bundle", default=None)
    p.add_argument("--system", default="Data platform")
    p.add_argument("--scan-root", action="append", default=[], help="Lake / SQL / job root(s) to map")
    p.add_argument(
        "--export",
        action="append",
        default=[],
        help="Optional Fabric / PBI / inventory JSON (no live APIs)",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", action="store_true", help="Write .dekc/re-plan.{json,md} into the bundle")

    p_mark = sub.add_parser("mark", help="Check off (or block) a deep-dive checklist item")
    p_mark.add_argument("--plan", default=None, help="Plan JSON, .dekc dir, or bundle")
    p_mark.add_argument("--repo", default=".")
    p_mark.add_argument("--bundle", default=None)
    p_mark.add_argument("--area", required=True)
    p_mark.add_argument("--item", required=True)
    p_mark.add_argument("--status", default="done", choices=("pending", "done", "blocked"))
    p_mark.add_argument("--note", default="")
    p_mark.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Print an existing plan")
    p_show.add_argument("--plan", default=None)
    p_show.add_argument("--repo", default=".")
    p_show.add_argument("--bundle", default=None)
    p_show.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    from dekc_common import resolve_knowledge_root

    if args.cmd == "mark":
        host = Path(args.repo).resolve()
        target = Path(args.plan).resolve() if args.plan else resolve_knowledge_root(host, args.bundle)
        result = mark_checklist(target, area=args.area, item=args.item, status=args.status, note=args.note)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"marked {args.area}/{args.item} -> {args.status}")
            print(f"checklist: {result['checklist']}")
        return 0

    if args.cmd == "show":
        host = Path(args.repo).resolve()
        target = Path(args.plan).resolve() if args.plan else resolve_knowledge_root(host, args.bundle)
        plan = load_plan(target)
        if args.json:
            print(json.dumps(plan, indent=2, default=str))
        else:
            print(render_plan_markdown(plan))
        return 0

    host = Path(args.repo).resolve()
    roots = [Path(r).resolve() for r in (args.scan_root or [str(host)])]
    exports = [Path(e).resolve() for e in (args.export or [])]
    if args.write:
        bundle = resolve_knowledge_root(host, args.bundle)
        bundle.mkdir(parents=True, exist_ok=True)
        plan = write_plan(bundle, roots, system_name=args.system, exports=exports)
    else:
        plan = build_plan(roots, system_name=args.system, exports=exports)
        plan["checklist"] = checklist_summary(plan)
    if args.json:
        print(json.dumps(plan, indent=2, default=str))
    else:
        print(render_plan_markdown(plan))
        if args.write:
            written = plan.get("written") or {}
            print(f"\nWrote {written.get('md')} and {written.get('json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
