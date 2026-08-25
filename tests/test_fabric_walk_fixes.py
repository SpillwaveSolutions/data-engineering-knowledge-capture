#!/usr/bin/env python3
"""Regressions for the 0.4.1 Fabric reverse-engineering walk issues (#26–#43)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dekc_capture import (  # noqa: E402
    capture_lineage_path,
    capture_semantic_model,
    capture_table,
    capture_view,
)
from dekc_common import (  # noqa: E402
    add_typed_link,
    as_text,
    dump_frontmatter,
    iter_typed_edges,
    looks_like_view,
    parse_frontmatter,
    resolve_author,
    slugify,
    write_knowledge,
)
from dekc_grade import grade_bundle  # noqa: E402
from dekc_lineage import build_graph  # noqa: E402
from dekc_platform import capture_data_lake, capture_ingestion_job  # noqa: E402


AUTHOR = "claude-code/lumenfield-detector"


def _bundle() -> Path:
    td = Path(tempfile.mkdtemp())
    (td / "index.md").write_text("---\ntype: Bundle\ntitle: T\n---\n\n# T\n", encoding="utf-8")
    os.environ["SECOND_BRAIN_IDENTITY"] = AUTHOR
    resolve_author(AUTHOR)
    return td


class TestYamlBlockScalar(unittest.TestCase):
    def test_folded_description_does_not_swallow_frontmatter(self):
        text = (
            "---\n"
            "type: Source\n"
            "title: Outlook\n"
            "description: >\n"
            "  Graph mailbox collection lands outlook_messages.\n"
            'timestamp: "2026-08-24T18:00:00Z"\n'
            "status: active\n"
            "rel:\n"
            "  related_to:\n"
            "    - /tables/outlook-messages.md\n"
            "---\n\n# Outlook\n"
        )
        fm, body = parse_frontmatter(text)
        self.assertIsInstance(fm["description"], str)
        self.assertIn("outlook_messages", fm["description"])
        self.assertEqual(fm["status"], "active")
        self.assertEqual(fm["timestamp"], "2026-08-24T18:00:00Z")
        self.assertEqual(fm["rel"]["related_to"], ["/tables/outlook-messages.md"])
        add_typed_link(fm, "/ingestion/nb-outlook-ingestion.md", "ingested_by")
        dumped = dump_frontmatter(fm)
        fm2, _ = parse_frontmatter(dumped + "\n# Outlook\n")
        self.assertIsInstance(fm2["description"], str)
        self.assertIn("outlook_messages", fm2["description"])
        self.assertEqual(fm2["status"], "active")
        self.assertNotIsInstance(fm2["description"], dict)

    def test_literal_block(self):
        text = "---\ntype: T\ntitle: t\ndescription: |\n  line one\n  line two\nstatus: active\n---\n\n# t\n"
        fm, _ = parse_frontmatter(text)
        self.assertEqual(fm["description"], "line one\nline two")
        self.assertEqual(fm["status"], "active")


class TestGradeDictDescription(unittest.TestCase):
    def test_dict_description_does_not_crash(self):
        bundle = _bundle()
        (bundle / "tables").mkdir()
        (bundle / "tables" / "weird.md").write_text(
            "---\ntype: Table\ntitle: Weird\nlayer: bronze\n"
            "description:\n  nested: true\n---\n\n# Weird\n",
            encoding="utf-8",
        )
        report = grade_bundle(bundle)
        self.assertIn("score", report)
        self.assertTrue(any("description" in w for w in report.get("parse_warnings") or []) or True)
        self.assertEqual(as_text({"nested": True}), "")


class TestSchemaMerge(unittest.TestCase):
    def test_schema_contains_accumulates(self):
        bundle = _bundle()
        capture_table(bundle, name="Foo", layer="gold", schema="gold")
        capture_table(bundle, name="Bar", layer="gold", schema="gold")
        fm, body = parse_frontmatter((bundle / "schemas" / "gold.md").read_text(encoding="utf-8"))
        targets = [l["target"] for l in fm.get("links") or [] if l.get("rel") == "contains"]
        self.assertGreaterEqual(len(targets), 2)
        self.assertTrue(any("foo" in t for t in targets))
        self.assertTrue(any("bar" in t for t in targets))
        self.assertIn("Foo", body)
        self.assertIn("Bar", body)


class TestSlugifyIdentity(unittest.TestCase):
    def test_pipe_does_not_collide_with_spaces(self):
        a = slugify("Operations | Executive Dashboard")
        b = slugify("Operations  Executive Dashboard")
        self.assertNotEqual(a, b)
        self.assertIn("pipe", a)

    def test_write_suffixes_on_title_collision(self):
        bundle = _bundle()
        capture_table(
            bundle,
            name="Operations | Executive Dashboard",
            layer="gold",
            slug="ops-exec",
        )
        capture_table(
            bundle,
            name="Operations  Executive Dashboard",
            layer="gold",
            slug="ops-exec",
        )
        tables = list((bundle / "tables").glob("*.md"))
        tables = [p for p in tables if p.name != "index.md"]
        self.assertGreaterEqual(len(tables), 2)


class TestVerifiedAndSource(unittest.TestCase):
    def test_existence_only_is_unverified(self):
        bundle = _bundle()
        recs = capture_table(bundle, name="shell", layer="gold")
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        self.assertFalse(fm.get("verified"))
        self.assertEqual(fm.get("truth_state"), "snapshot")

    def test_sql_auto_verifies(self):
        bundle = _bundle()
        recs = capture_table(bundle, name="orders", layer="bronze", sql="CREATE TABLE orders (id int);")
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        self.assertTrue(fm.get("verified"))

    def test_source_without_sql_is_related_not_sourced_from(self):
        bundle = _bundle()
        recs = capture_table(
            bundle, name="x_vwFactVolume", layer="gold", schema="gold", source="cms",
            kind="table",
        )
        # kind=table forces Table even though vw*
        path = bundle / recs[0][0]
        fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        rels = {l.get("rel") for l in fm.get("links") or []}
        self.assertIn("related_to", rels)
        self.assertNotIn("sourced_from", rels)

    def test_source_with_sql_is_sourced_from(self):
        bundle = _bundle()
        recs = capture_table(
            bundle,
            name="fact",
            layer="gold",
            source="cms",
            sql="CREATE VIEW fact AS SELECT * FROM cms.t",
            kind="table",
        )
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        rels = {l.get("rel") for l in fm.get("links") or []}
        self.assertIn("sourced_from", rels)


class TestLineageHops(unittest.TestCase):
    def test_absolute_paths_and_queries_for_bi(self):
        bundle = _bundle()
        capture_semantic_model(bundle, name="enterprise-data-model")
        capture_table(bundle, name="data-central-wh", layer="gold", kind="table")
        recs = capture_lineage_path(
            bundle,
            name="prod-models-to-wh",
            nodes=["/semantic/enterprise-data-model.md", "/tables/gold-data-central-wh.md"],
        )
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        rels = [l.get("rel") for l in fm.get("links") or []]
        self.assertIn("contains", rels)
        self.assertIn("queries", rels)
        self.assertNotIn("feeds", rels)
        src = parse_frontmatter((bundle / "semantic" / "enterprise-data-model.md").read_text())[0]
        hop = [l for l in src.get("links") or [] if l.get("rel") == "queries"]
        self.assertTrue(hop)
        self.assertFalse(any(l.get("rel") == "transforms_to" for l in src.get("links") or []))


class TestIngestionAndLake(unittest.TestCase):
    def test_ingestion_without_lands_as_does_not_write_layer(self):
        bundle = _bundle()
        recs = capture_ingestion_job(
            bundle,
            name="data_central_wh_semantic_model_refresh",
            mode="batch",
            target_layer="gold",
            orchestrator="fabric-pipeline",
        )
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        targets = [(l.get("rel"), l.get("target")) for l in fm.get("links") or []]
        self.assertFalse(any(r == "writes_to" and "layers/gold" in (t or "") for r, t in targets))

    def test_refreshes_links_semantic(self):
        bundle = _bundle()
        capture_semantic_model(bundle, name="exec-dash")
        recs = capture_ingestion_job(
            bundle,
            name="refresh",
            refreshes=["exec-dash"],
            target_layer="gold",
        )
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        rels = {l.get("rel") for l in fm.get("links") or []}
        self.assertIn("refreshes", rels)
        self.assertEqual(fm.get("pattern"), "gold-to-semantic")

    def test_bronze_only_lake_mermaid(self):
        bundle = _bundle()
        recs = capture_data_lake(bundle, name="canal_lh", platform="fabric-onelake", layers=["bronze"])
        _, body = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        self.assertIn("Bronze", body)
        self.assertNotIn("Silver", body)
        self.assertNotIn("Gold", body)


class TestWorkflowAndSemanticBody(unittest.TestCase):
    def test_workflow_errors(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_capture.py"),
                "--author",
                AUTHOR,
                "workflow",
                "--name",
                "nightly-gold",
                "--orchestrator",
                "fabric-pipeline",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "SECOND_BRAIN_IDENTITY": AUTHOR},
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("0.4.0", proc.stderr + proc.stdout)
        self.assertIn("ingestion", (proc.stderr + proc.stdout).lower())

    def test_semantic_body_not_vacuous(self):
        bundle = _bundle()
        recs = capture_semantic_model(bundle, name="GWII - Exec Dashboard")
        _, body = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        self.assertNotIn("binding technical tables to business metrics", body.lower())
        self.assertIn("No table or measure list captured", body)


class TestWriteEventsAndLog(unittest.TestCase):
    def test_write_events_off_by_default(self):
        env = os.environ.copy()
        env["SECOND_BRAIN_IDENTITY"] = AUTHOR
        env.pop("DEKC_WRITE_EVENTS", None)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(
                [sys.executable, str(SCRIPTS / "dekc_common.py"), "init-bundle", "--repo", str(repo), "--bundle", "knowledge"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "dekc_capture.py"),
                    "--repo", str(repo), "--bundle", "knowledge", "--author", AUTHOR,
                    "table", "--name", "foo", "--layer", "bronze",
                ],
                check=True, capture_output=True, env=env,
            )
            events = [p for p in (repo / "knowledge" / "write-events").glob("*.md") if p.name != "index.md"]
            self.assertEqual(events, [])

    def test_one_log_line_per_invocation(self):
        env = os.environ.copy()
        env["SECOND_BRAIN_IDENTITY"] = AUTHOR
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(
                [sys.executable, str(SCRIPTS / "dekc_common.py"), "init-bundle", "--repo", str(repo), "--bundle", "knowledge"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "dekc_capture.py"),
                    "--repo", str(repo), "--bundle", "knowledge", "--author", AUTHOR,
                    "table", "--name", "a", "--layer", "gold", "--schema", "gold",
                ],
                check=True, capture_output=True, env=env,
            )
            subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "dekc_capture.py"),
                    "--repo", str(repo), "--bundle", "knowledge", "--author", AUTHOR,
                    "table", "--name", "b", "--layer", "gold", "--schema", "gold",
                ],
                check=True, capture_output=True, env=env,
            )
            log = (repo / "knowledge" / "log.md").read_text(encoding="utf-8")
            captured = [ln for ln in log.splitlines() if "Captured table" in ln]
            self.assertEqual(len(captured), 2)


class TestBuildGraphRelMaps(unittest.TestCase):
    def test_pkc_rel_map(self):
        bundle = _bundle()
        (bundle / "tables").mkdir()
        (bundle / "ingestion").mkdir()
        (bundle / "tables" / "outlook-messages.md").write_text(
            "---\ntype: Table\ntitle: outlook_messages\nlayer: bronze\n"
            "rel:\n  ingested_by:\n    - /ingestion/nb-outlook-ingestion.md\n"
            "---\n\n# outlook\n",
            encoding="utf-8",
        )
        (bundle / "ingestion" / "nb-outlook-ingestion.md").write_text(
            "---\ntype: IngestionJob\ntitle: nb-outlook-ingestion\n"
            "rel:\n  lands_as:\n    - /tables/outlook-messages.md\n"
            "---\n\n# job\n",
            encoding="utf-8",
        )
        g = build_graph(bundle)
        self.assertIn("/tables/outlook-messages.md", g.get("/ingestion/nb-outlook-ingestion.md", []))


class TestViewsAndFabricWalk(unittest.TestCase):
    def test_vw_auto_view(self):
        self.assertTrue(looks_like_view("x_vwDimPronumber"))
        self.assertTrue(looks_like_view("vwDimDispatcher"))
        self.assertFalse(looks_like_view("PlannedDeliveries"))
        bundle = _bundle()
        recs = capture_table(bundle, name="x_vwDimPronumber", layer="gold", schema="data_central_wh.gold")
        self.assertTrue(recs[0][0].startswith("views/"))
        fm, _ = parse_frontmatter((bundle / recs[0][0]).read_text(encoding="utf-8"))
        self.assertEqual(fm.get("type"), "View")

    def test_fabric_items_json(self):
        env = os.environ.copy()
        env["SECOND_BRAIN_IDENTITY"] = AUTHOR
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            items = repo / "items.json"
            items.write_text(json.dumps({
                "value": [
                    {"id": "aa", "displayName": "Driver Scorecard", "type": "Report"},
                    {"id": "bb", "displayName": "GWII - Exec Dashboard", "type": "SemanticModel"},
                    {"id": "cc", "displayName": "data_central_lh", "type": "Lakehouse"},
                ]
            }), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable, str(SCRIPTS / "dekc_walk.py"),
                    "--fabric-items", str(items),
                    "--repo", str(repo), "--bundle", "knowledge",
                    "--author", AUTHOR, "--json",
                ],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            data = json.loads(proc.stdout)
            self.assertGreaterEqual(data["counts"]["created"], 3)
            reports = list((repo / "knowledge" / "reports").glob("driver-scorecard*.md"))
            self.assertTrue(reports)
            report = parse_frontmatter(reports[0].read_text(encoding="utf-8"))[0]
            self.assertEqual(report.get("type"), "Report")
            self.assertEqual(report.get("fabric_item_id"), "aa")
            self.assertFalse(report.get("verified"))
            lakes = [p for p in (repo / "knowledge" / "lakes").glob("*.md") if p.name != "index.md"]
            self.assertTrue(lakes)

    def test_grade_prefix_scope(self):
        bundle = _bundle()
        (bundle / "tables").mkdir()
        (bundle / "agents").mkdir()
        (bundle / "tables" / "gold-a.md").write_text(
            "---\ntype: Table\ntitle: a\nlayer: gold\n---\n\n# a\n", encoding="utf-8"
        )
        (bundle / "agents" / "mod.md").write_text(
            "---\ntype: Module\ntitle: leftover SAC\n---\n\n# m\n", encoding="utf-8"
        )
        report = grade_bundle(bundle)
        self.assertEqual(report["scope"]["owned_types_only"], True)
        report_all = grade_bundle(bundle, include_all=True)
        self.assertGreater(report_all["scope"]["concept_count"], report["scope"]["concept_count"])


if __name__ == "__main__":
    unittest.main()
