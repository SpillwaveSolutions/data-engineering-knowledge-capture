#!/usr/bin/env python3
"""DEKC unit tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dekc_common import slugify, list_concepts, parse_frontmatter  # noqa: E402
from dekc_lineage import build_graph  # noqa: E402
from dekc_validate import validate_bundle  # noqa: E402
from dekc_index import build_index, search_index  # noqa: E402
from dekc_walk import extract_sql_tables  # noqa: E402


class TestSlugify(unittest.TestCase):
    def test_underscores(self):
        self.assertEqual(slugify("order_daily"), "order-daily")
        self.assertEqual(slugify("Foo Bar"), "foo-bar")


class TestSqlLineage(unittest.TestCase):
    def test_insert_select(self):
        refs = extract_sql_tables(
            "INSERT INTO gold.order_daily SELECT * FROM silver.orders"
        )
        self.assertTrue(refs)


class TestSampleBundle(unittest.TestCase):
    def test_validate(self):
        report = validate_bundle(ROOT / "sample-knowledge")
        self.assertTrue(report["ok"], report["errors"])

    def test_has_medallion_tables(self):
        concepts = list_concepts(ROOT / "sample-knowledge")
        layers = {fm.get("layer") for _, fm, _ in concepts if fm.get("type") == "Table"}
        self.assertTrue({"bronze", "silver", "gold"} <= layers)

    def test_graph_nonempty_or_links(self):
        g = build_graph(ROOT / "sample-knowledge")
        self.assertGreater(sum(len(v) for v in g.values()), 0)

    def test_index_search(self):
        build_index(ROOT / "sample-knowledge")
        hits = search_index(ROOT / "sample-knowledge", "revenue", limit=5)
        self.assertTrue(hits)


class TestInitAndCapture(unittest.TestCase):
    def test_init_and_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_common.py"),
                    "init-bundle",
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            bundle = repo / "knowledge"
            self.assertTrue((bundle / "index.md").is_file())
            # parent flags before subcommand
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_capture.py"),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "--json",
                    "table",
                    "--name",
                    "events",
                    "--layer",
                    "bronze",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            path = bundle / "tables" / "bronze-events.md"
            self.assertTrue(path.is_file())
            fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            self.assertEqual(fm.get("type"), "Table")
            self.assertEqual(fm.get("layer"), "bronze")


class TestWalkFixture(unittest.TestCase):
    def test_walk_sample_lake(self):
        lake = ROOT / "tests" / "fixtures" / "sample-lake"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_walk.py"),
                    str(lake),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            data = json.loads(proc.stdout)
            self.assertGreaterEqual(data["counts"]["created"], 1)


class TestGrade(unittest.TestCase):
    def test_grade_sample_knowledge(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_grade.py"),
                "--repo",
                str(ROOT),
                "--bundle",
                "sample-knowledge",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertIn("score", data)
        self.assertTrue(data["pass"])


class TestSchemasAndBrain(unittest.TestCase):
    def test_schema_registry_lists(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "dekc_schemas.py"), "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("Table", data.get("concepts") or [])

    def test_schema_validate_sample(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_schemas.py"),
                "validate",
                "--repo",
                str(ROOT),
                "--bundle",
                "sample-knowledge",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"], data.get("issues"))

    def test_brain_design_report(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_brain.py"),
                "revenue",
                "--intent",
                "design-report",
                "--repo",
                str(ROOT),
                "--bundle",
                "sample-knowledge",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["intent"], "design-report")
        self.assertGreater(len(data["results"]), 0)

    def test_brain_land_data(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_brain.py"),
                "orders",
                "--intent",
                "land-data",
                "--repo",
                str(ROOT),
                "--bundle",
                "sample-knowledge",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["intent"], "land-data")

    def test_yaml_links_list(self):
        sample = (
            "---\ntype: Table\ntitle: t\ndescription: d\ntimestamp: x\n"
            "links:\n- target: /a.md\n  rel: feeds\n---\n\n# t\n"
        )
        fm, _ = parse_frontmatter(sample)
        self.assertIsInstance(fm.get("links"), list)
        self.assertEqual(fm["links"][0]["rel"], "feeds")


if __name__ == "__main__":
    unittest.main()
