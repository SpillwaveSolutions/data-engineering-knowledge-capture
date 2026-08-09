#!/usr/bin/env python3
"""Automated partial scores for DEKC reverse-engineering rubrics.

Produces a baseline Judgment-shaped JSON for re-adversary-judge / orchestrators.
LLM skeptics refine criteria that need semantic judgment (definition quality, etc.).
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
from dekc_doctor import doctor  # noqa: E402
from dekc_lineage import build_graph  # noqa: E402

RE_WEIGHTS = {
    "structural_coverage": 0.20,
    "lineage_integrity": 0.25,
    "stream_job_landing": 0.15,
    "business_fidelity": 0.15,
    "evidence_traceability": 0.15,
    "adversarial_resistance": 0.10,
}
RE_THRESHOLD = 0.75

SECRET_HINT = re.compile(
    r"(?i)(password\s*=\s*\S+|api[_-]?key\s*[:=]\s*\S+|secret\s*[:=]\s*\S+|"
    r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----)"
)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, round(x, 3)))


def _rel(bundle: Path, path: Path) -> str:
    return "/" + path.relative_to(bundle).as_posix()


def _layer_names(fm: dict) -> set[str]:
    found: set[str] = set()
    blob = " ".join(
        str(x)
        for x in (
            fm.get("title"),
            fm.get("name"),
            fm.get("layer"),
            " ".join(str(t) for t in (fm.get("tags") or [])),
        )
        if x
    ).lower()
    for name in ("bronze", "silver", "gold"):
        if name in blob:
            found.add(name)
    return found


def grade_bundle(bundle: Path) -> dict:
    concepts = list_concepts(bundle)
    by_type: Counter[str] = Counter()
    tables: list[tuple[Path, dict, str]] = []
    gold_tables: list[str] = []
    streams: list[str] = []
    workflows: list[str] = []
    bos: list[str] = []
    secrets: list[str] = []
    has_source_cite = 0
    layers_present: set[str] = set()

    for path, fm, body in concepts:
        t = fm.get("type") or "?"
        by_type[t] += 1
        rel = _rel(bundle, path)
        blob = (fm.get("description") or "") + "\n" + (body or "")
        if SECRET_HINT.search(blob):
            secrets.append(rel)
        layers_present |= _layer_names(fm)
        if t == "Table":
            tables.append((path, fm, body))
            layer = (fm.get("layer") or "").lower()
            if layer == "gold" or "gold" in rel or "/mart" in rel:
                gold_tables.append(rel)
        if t == "SourceSystem":
            kind = (fm.get("source_kind") or fm.get("kind") or "").lower()
            tags = [str(x).lower() for x in (fm.get("tags") or [])]
            if kind == "stream" or "stream" in tags:
                streams.append(rel)
        if t == "Workflow":
            workflows.append(rel)
        if t == "BusinessObject":
            bos.append(rel)
        if t in ("Table", "View", "Transformation", "Workflow", "SourceSystem", "LineagePath"):
            if len(blob.strip()) >= 40 or "```" in (body or "") or fm.get("uri") or fm.get("source"):
                has_source_cite += 1

    table_count = len(tables)
    graph = build_graph(bundle)
    edge_count = sum(len(v) for v in graph.values())
    d = doctor(bundle)

    layer_score = min(1.0, len(layers_present & {"bronze", "silver", "gold"}) / 3.0)
    struct = 0.35 * (1.0 if table_count > 0 else 0.0)
    struct += 0.25 * layer_score
    struct += 0.20 * (1.0 if d["validation_ok"] else 0.35)
    orphan_ratio = len(d["orphan_technical"]) / max(table_count, 1)
    struct += 0.20 * _clamp(1.0 - orphan_ratio)
    structural_coverage = _clamp(struct)

    if table_count <= 1:
        lineage_proxy = 0.85
    elif edge_count == 0:
        lineage_proxy = 0.25
    else:
        density = edge_count / max(table_count, 1)
        lineage_proxy = _clamp(0.45 + min(density, 2.0) * 0.25)
        if d["validation_ok"]:
            lineage_proxy = _clamp(lineage_proxy + 0.1)
    if edge_count > 0 and by_type.get("Transformation", 0) + by_type.get("Query", 0) + by_type.get(
        "SqlArtifact", 0
    ) == 0:
        lineage_proxy = _clamp(lineage_proxy * 0.85)
    lineage_integrity = _clamp(lineage_proxy)

    if not streams and not workflows:
        stream_job_landing = 0.75 if table_count else 0.5
        stream_note = "no streams/workflows captured; neutral score (batch-only OK)"
    else:
        linked_streams = 0
        for s in streams:
            if s in graph or any(s in tgts for tgts in graph.values()):
                linked_streams += 1
        stream_part = (linked_streams / len(streams)) if streams else 1.0
        job_part = 1.0 if workflows else 0.6
        bronze = sum(1 for _, fm, _ in tables if (fm.get("layer") or "").lower() == "bronze")
        land_part = 1.0 if bronze or not streams else 0.4
        stream_job_landing = _clamp(0.4 * stream_part + 0.3 * job_part + 0.3 * land_part)
        stream_note = f"streams={len(streams)} workflows={len(workflows)} bronze={bronze}"

    hard_gold = False
    if gold_tables:
        bo_cov = min(1.0, len(bos) / max(len(gold_tables), 1))
        business_fidelity = _clamp(
            0.55 * bo_cov
            + 0.25 * min(1.0, d["glossary_terms"] / max(len(bos), 1))
            + 0.20 * min(1.0, d["business_coverage"])
        )
        if len(bos) == 0:
            business_fidelity = _clamp(min(business_fidelity, 0.35))
            hard_gold = True
    else:
        business_fidelity = 0.8 if bos or table_count == 0 else 0.65

    vacuous = 0
    for path, fm, body in concepts:
        if fm.get("type") != "BusinessObject":
            continue
        desc = (fm.get("description") or body or "").strip().lower()
        if len(desc) < 24 or desc.startswith("data about") or desc in ("todo", "tbd", "n/a"):
            vacuous += 1
    if bos:
        business_fidelity = _clamp(business_fidelity * (1.0 - 0.15 * (vacuous / len(bos))))

    eligible = sum(
        1
        for _, fm, _ in concepts
        if fm.get("type")
        in ("Table", "View", "Transformation", "Workflow", "SourceSystem", "LineagePath", "Query")
    )
    cite_ratio = (has_source_cite / eligible) if eligible else 0.5
    evidence_traceability = _clamp(
        0.5 * cite_ratio
        + 0.3 * (1.0 if d["index_built"] else 0.4)
        + 0.2 * (1.0 if d["validation_ok"] else 0.5)
    )

    hard_fails: list[str] = []
    if secrets:
        hard_fails.append(f"secret_or_pii_pattern in {len(secrets)} concept(s): {secrets[:3]}")
    if hard_gold:
        hard_fails.append("gold_tables_without_business_objects")

    open_issues = len(hard_fails) + vacuous + len(d["errors"])
    adversarial_resistance = _clamp(1.0 - 0.15 * open_issues)
    if hard_fails:
        adversarial_resistance = _clamp(min(adversarial_resistance, 0.4))

    criteria = {
        "structural_coverage": {
            "score": structural_coverage,
            "weight": RE_WEIGHTS["structural_coverage"],
            "notes": f"tables={table_count} layers={sorted(layers_present)} orphans={len(d['orphan_technical'])}",
        },
        "lineage_integrity": {
            "score": lineage_integrity,
            "weight": RE_WEIGHTS["lineage_integrity"],
            "notes": f"edges={edge_count} (automated proxy — skeptics must confirm evidence)",
        },
        "stream_job_landing": {
            "score": stream_job_landing,
            "weight": RE_WEIGHTS["stream_job_landing"],
            "notes": stream_note,
        },
        "business_fidelity": {
            "score": business_fidelity,
            "weight": RE_WEIGHTS["business_fidelity"],
            "notes": f"gold={len(gold_tables)} bos={len(bos)} vacuous_bo={vacuous}",
        },
        "evidence_traceability": {
            "score": evidence_traceability,
            "weight": RE_WEIGHTS["evidence_traceability"],
            "notes": f"cite_ratio={round(cite_ratio, 2)} index={d['index_built']}",
        },
        "adversarial_resistance": {
            "score": adversarial_resistance,
            "weight": RE_WEIGHTS["adversarial_resistance"],
            "notes": f"hard_fails={len(hard_fails)} open_issues≈{open_issues}",
        },
    }

    weighted = sum(c["score"] * c["weight"] for c in criteria.values())
    score = _clamp(weighted)
    passed = score >= RE_THRESHOLD and not hard_fails

    revisions: list[str] = []
    if not d["validation_ok"]:
        revisions.append("fix validation errors before re-grade")
    if d["orphan_technical"]:
        revisions.append(f"link or document {len(d['orphan_technical'])} orphan technical assets")
    if hard_gold:
        revisions.append("promote gold tables to BusinessObjects or mark explicit skips")
    if vacuous:
        revisions.append(f"rewrite {vacuous} vacuous BusinessObject definition(s)")
    if edge_count == 0 and table_count > 1:
        revisions.append("capture lineage edges from SQL/jobs or retract multi-table claims")
    if secrets:
        revisions.append("scrub secret/PII patterns from concept bodies")
    if not d["index_built"]:
        revisions.append("run dekc_index.py build after pass")

    return {
        "type": "Judgment",
        "role": "dekc_grade_automated",
        "rubric": "reverse-engineering",
        "rubric_path": "evaluation/reverse-engineering-rubric.md",
        "threshold": RE_THRESHOLD,
        "score": score,
        "pass": passed,
        "hard_fails": hard_fails,
        "criteria": criteria,
        "revisions": revisions,
        "on_fail": "retry_producer",
        "doctor": {
            "concept_count": d["concept_count"],
            "edge_count": d["edge_count"],
            "business_coverage": d["business_coverage"],
            "validation_ok": d["validation_ok"],
            "index_built": d["index_built"],
        },
        "note": (
            "Automated baseline only. lineage_integrity and definition quality "
            "require lineage-skeptic / business-skeptic / re-adversary-judge."
        ),
    }


def write_judgment(bundle: Path, report: dict) -> str:
    day = utc_now()[:10]
    rel = path_for_type("AgentNode", f"judgment-auto-{slugify(day)}")
    body = (
        f"# Automated RE grade\n\n"
        f"- score: **{report['score']}** (threshold {report['threshold']})\n"
        f"- pass: **{report['pass']}**\n\n"
        f"## Criteria\n\n"
        + "\n".join(f"- **{k}**: {v['score']} — {v['notes']}" for k, v in report["criteria"].items())
        + "\n\n## Revisions\n\n"
        + ("\n".join(f"- {r}" for r in report["revisions"]) or "- none")
        + "\n\n```json\n"
        + json.dumps({k: report[k] for k in ("score", "pass", "hard_fails", "criteria")}, indent=2)
        + "\n```\n"
    )
    fm = {
        "type": "AgentNode",
        "title": f"Automated RE grade {report['score']}",
        "description": "dekc_grade.py reverse-engineering rubric baseline",
        "role": "dekc_grade_automated",
        "tags": ["judgment", "grade", "automated", "dekc"],
        "timestamp": utc_now(),
        "status": "completed" if report["pass"] else "failed",
        "verified": True,
        "generated": True,
        "judgment_score": report["score"],
        "judgment_pass": report["pass"],
        "wiki_key": f"judgment-auto-{day}",
        "truth_state": "current",
    }
    write_concept(bundle, rel, fm, body, force=True)
    refresh_catalog_index(bundle, "agents")
    append_log(bundle, f"Automated RE grade score={report['score']} pass={report['pass']}")
    return rel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grade DEKC reverse-engineering quality (partial automated)")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write judgment under bundle/agents/")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    report = grade_bundle(bundle)

    if args.write:
        rel = write_judgment(bundle, report)
        report["written"] = rel

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("DEKC grade · reverse-engineering rubric")
        print(f"  score:     {report['score']}  (threshold {report['threshold']})")
        print(f"  pass:      {report['pass']}")
        if report["hard_fails"]:
            print("  hard fails:")
            for h in report["hard_fails"]:
                print(f"    - {h}")
        print("  criteria:")
        for k, v in report["criteria"].items():
            print(f"    {k:24} {v['score']:.3f}  w={v['weight']}  {v['notes']}")
        if report["revisions"]:
            print("  revisions:")
            for r in report["revisions"]:
                print(f"    - {r}")
        if args.write:
            print(f"  written:   {report.get('written')}")
        print(f"  note: {report['note']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
