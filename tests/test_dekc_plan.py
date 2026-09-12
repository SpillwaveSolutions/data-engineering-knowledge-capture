#!/usr/bin/env python3
"""Breadth-first RE plan + scoped orchestrate."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "re-plan-lake"
SQL_ONLY = ROOT / "tests" / "fixtures" / "re-plan-sql-only"
AUTHOR = "claude-code/lumenfield-detector"

sys.path.insert(0, str(SCRIPTS))

from dekc_common import iter_concept_paths, resolve_author  # noqa: E402
from dekc_plan import (  # noqa: E402
    build_plan,
    load_plan,
    mark_checklist,
    write_plan,
)
from dekc_orchestrate import orchestrate  # noqa: E402
from dekc_walk import extract_notebook_sql  # noqa: E402


class TestPlan(unittest.TestCase):
    def test_plan_fixture_detects_domains_and_specialists(self):
        exports = [
            FIXTURE / "exports" / "fabric-items.json",
            FIXTURE / "exports" / "inventory.json",
        ]
        plan = build_plan([FIXTURE], system_name="Lumenfield Orders", exports=exports)
        self.assertEqual(plan["version"], "1")
        self.assertEqual(plan["roots"][0]["layout"], "lake")
        ecos = set(plan["ecosystems"])
        self.assertTrue({"sql", "dbt", "airflow", "glue", "duckdb", "delta"} <= ecos)
        area_ids = {a["id"] for a in plan["focus_areas"]}
        for needed in (
            "lake",
            "elt",
            "orchestration",
            "lineage",
            "dq",
            "bi",
            "semantic",
            "catalogs",
        ):
            self.assertIn(needed, area_ids, area_ids)
        ranked = [a["id"] for a in sorted(plan["focus_areas"], key=lambda x: x["rank"])]
        self.assertEqual(ranked, [a["id"] for a in plan["focus_areas"]])
        agents = {a["id"]: a["agent"] for a in plan["focus_areas"]}
        self.assertEqual(agents["lake"], "schema-scout")
        self.assertEqual(agents["orchestration"], "stream-job-scout")
        self.assertEqual(agents["elt"], "stream-job-scout")
        self.assertEqual(agents["lineage"], "lineage-tracer")
        self.assertEqual(agents["dq"], "dq-scout")
        spec_ids = {s["id"] for s in plan.get("specialists") or []}
        for needed in (
            "orch-airflow",
            "orch-glue",
            "orch-fabric",
            "orch-adf",
            "orch-stepfunctions",
            "orch-composer",
            "orch-cron",
            "elt-dbt",
            "duckdb",
            "notebooks",
        ):
            self.assertIn(needed, spec_ids, spec_ids)
        self.assertEqual(agents["orch-airflow"], "airflow-scout")
        self.assertEqual(agents["duckdb"], "duckdb-scout")
        self.assertEqual(next(a for a in plan["focus_areas"] if a["id"] == "duckdb")["scan_domains"], ["duckdb"])
        self.assertEqual(next(a for a in plan["focus_areas"] if a["id"] == "orch-airflow")["scan_domains"], [])
        self.assertTrue(plan.get("cicd_handoff"))
        self.assertIn("run-glue.yml", plan["cicd_handoff"][0]["path"])
        for area in plan["focus_areas"]:
            self.assertGreaterEqual(area["signal"], 1)
            self.assertTrue(area["checklist"])
            for item in area["checklist"]:
                self.assertEqual(item["status"], "pending")

    def test_plan_does_not_spawn_absent_specialists(self):
        plan = build_plan([SQL_ONLY], system_name="SQL Only")
        ids = {a["id"] for a in plan["focus_areas"]}
        self.assertIn("lake", ids)
        self.assertNotIn("orch-airflow", ids)
        self.assertNotIn("orch-glue", ids)
        self.assertNotIn("duckdb", ids)
        self.assertNotIn("notebooks", ids)
        self.assertNotIn("dq", ids)
        self.assertEqual((plan.get("specialists") or []), [])
        self.assertEqual(plan.get("cicd_handoff") or [], [])

    def test_plan_writes_and_mark_progress(self):
        with tempfile.TemporaryDirectory() as td:
            bundle = Path(td) / "knowledge"
            bundle.mkdir()
            written = write_plan(bundle, [FIXTURE], system_name="Lumenfield Orders")
            md = bundle / ".dekc" / "re-plan.md"
            js = bundle / ".dekc" / "re-plan.json"
            self.assertTrue(md.is_file())
            self.assertTrue(js.is_file())
            text = md.read_text(encoding="utf-8")
            self.assertIn("# Reverse-engineering plan: Lumenfield Orders", text)
            self.assertIn("airflow-scout", text)
            self.assertIn("SAC owns", text)
            self.assertIn("- [ ] `inventory`", text)
            self.assertNotIn("- [x]", text)
            marked = mark_checklist(bundle, area="lake", item="inventory", status="done")
            self.assertGreaterEqual(marked["checklist"]["done"], 1)
            blocked = mark_checklist(
                bundle, area="dq", item="capture", status="blocked", note="GE runtime not executed"
            )
            self.assertEqual(blocked["checklist"]["blocked"], 1)
            reloaded = load_plan(bundle)
            lake = next(a for a in reloaded["focus_areas"] if a["id"] == "lake")
            inv = next(i for i in lake["checklist"] if i["id"] == "inventory")
            self.assertEqual(inv["status"], "done")
            text2 = md.read_text(encoding="utf-8")
            self.assertIn("- [x] `inventory`", text2)
            self.assertIn("blocked", text2)
            for p in iter_concept_paths(bundle):
                self.assertNotIn(".dekc", p.parts)

    def test_notebook_sql_extract(self):
        nb = FIXTURE / "notebooks" / "clean_orders.ipynb"
        sqls = extract_notebook_sql(nb)
        self.assertGreaterEqual(len(sqls), 2)
        blob = "\n".join(sqls).lower()
        self.assertIn("select", blob)
        self.assertIn("orders", blob)


class TestOrchestrate(unittest.TestCase):
    def setUp(self):
        resolve_author(AUTHOR)

    def test_orchestrate_plan_only(self):
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            result = orchestrate(
                host,
                [FIXTURE],
                system_name="Lumenfield Orders",
                bundle_name="knowledge",
                author=AUTHOR,
                exports=[FIXTURE / "exports" / "fabric-items.json"],
                plan_only=True,
            )
            self.assertEqual(result["phases"], ["init-bundle", "plan"])
            self.assertIsNone(result["walk"])
            areas = {a["id"] for a in result["plan"]["focus_areas"]}
            self.assertIn("lake", areas)
            self.assertIn("orch-airflow", areas)
            spec_ids = {s["id"] for s in result["plan"].get("specialists") or []}
            self.assertIn("orch-airflow", spec_ids)
            self.assertIn("duckdb", spec_ids)
            md = Path(result["bundle"]) / ".dekc" / "re-plan.md"
            text = md.read_text(encoding="utf-8")
            self.assertIn("- [ ]", text)
            self.assertIn("airflow-scout", text)
            self.assertIn("re-adversary-judge", text)
            for p in iter_concept_paths(Path(result["bundle"])):
                self.assertNotIn(".dekc", p.parts)

    def test_orchestrate_from_plan_area_scoped(self):
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            planned = orchestrate(
                host,
                [FIXTURE],
                system_name="Lumenfield Orders",
                bundle_name="knowledge",
                author=AUTHOR,
                plan_only=True,
            )
            plan_json = Path(planned["bundle"]) / ".dekc" / "re-plan.json"
            result = orchestrate(
                host,
                [FIXTURE],
                system_name="Lumenfield Orders",
                bundle_name="knowledge",
                author=AUTHOR,
                from_plan=plan_json,
                area="duckdb",
            )
            self.assertIn("walk", result["phases"])
            domains = (result["walk"] or {}).get("domains") or []
            self.assertEqual(domains, ["duckdb"])
            sources = list((Path(result["bundle"]) / "sources").glob("*.md"))
            sources = [p for p in sources if p.name != "index.md"]
            self.assertGreater(len(sources), 0)
            text = "\n".join(p.read_text(encoding="utf-8") for p in sources)
            self.assertIn("duckdb", text.lower())

    def test_orchestrate_from_plan_specialist_is_enrichment_only(self):
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            planned = orchestrate(
                host,
                [FIXTURE],
                system_name="Lumenfield Orders",
                bundle_name="knowledge",
                author=AUTHOR,
                plan_only=True,
            )
            plan_json = Path(planned["bundle"]) / ".dekc" / "re-plan.json"
            result = orchestrate(
                host,
                [FIXTURE],
                system_name="Lumenfield Orders",
                bundle_name="knowledge",
                author=AUTHOR,
                from_plan=plan_json,
                area="orch-airflow",
            )
            self.assertIn("enrichment", result["phases"])
            self.assertNotIn("walk", result["phases"])
            self.assertEqual((result["walk"] or {}).get("domains"), [])

    def test_cli_plan_only_and_mark(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_walk.py"),
                    str(SQL_ONLY),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "--plan-only",
                    "--system",
                    "SQL Only",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            data = json.loads(proc.stdout)
            ids = {a["id"] for a in data["focus_areas"]}
            self.assertIn("lake", ids)
            self.assertNotIn("orch-airflow", ids)
            mark = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_plan.py"),
                    "mark",
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "--area",
                    "lake",
                    "--item",
                    "inventory",
                    "--status",
                    "done",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(mark.returncode, 0, mark.stderr + mark.stdout)
            marked = json.loads(mark.stdout)
            self.assertEqual(marked["status"], "done")


if __name__ == "__main__":
    unittest.main()
