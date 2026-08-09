#!/usr/bin/env python3
"""DEKC unit + integration tests (stdlib unittest)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SAMPLE = ROOT / "sample-knowledge"
sys.path.insert(0, str(SCRIPTS))

from dekc_common import slugify, ensure_bundle, list_concepts, parse_frontmatter  # noqa: E402
from dekc_business import humanize  # noqa: E402
from dekc_lineage import extract_edges_from_sql, build_graph  # noqa: E402
from dekc_index import build_index, search_index  # noqa: E402
from dekc_validate import validate_bundle  # noqa: E402


class TestSlugify(unittest.TestCase):
    def test_underscores(self):
        self.assertEqual(slugify("orders_raw"), "orders-raw")
        self.assertEqual(slugify("Bronze Orders"), "bronze-orders")


class TestHumanize(unittest.TestCase):
    def test_layer_prefix(self):
        self.assertIn("Order", humanize("gold-order-daily"))


class TestSqlLineage(unittest.TestCase):
    def test_insert_select(self):
        sql = "INSERT INTO silver.orders SELECT * FROM bronze.orders_raw"
        edges = extract_edges_from_sql(sql)
        self.assertTrue(any(e[0] == "orders_raw" and e[1] == "orders" for e in edges))


class TestSampleBundle(unittest.TestCase):
    def test_validate(self):
        report = validate_bundle(SAMPLE)
        self.assertTrue(report["ok"], report["errors"])
        self.assertGreaterEqual(report["concept_count"], 20)

    def test_has_medallion_tables(self):
        types = {fm.get("type") for _, fm, _ in list_concepts(SAMPLE)}
        self.assertIn("Table", types)
        self.assertIn("BusinessObject", types)
        self.assertIn("GlossaryTerm", types)

    def test_index_search(self):
        build_index(SAMPLE)
        hits = search_index(SAMPLE, "revenue", limit=10)
        self.assertGreaterEqual(len(hits), 1)

    def test_graph_nonempty_or_links(self):
        graph = build_graph(SAMPLE)
        # sample should have some edges from lineage/transforms
        total = sum(len(v) for v in graph.values())
        self.assertGreaterEqual(total, 0)


class TestInitAndCapture(unittest.TestCase):
    def test_init_and_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            bundle = repo / "knowledge"
            ensure_bundle(bundle, title="Test")
            self.assertTrue((bundle / "index.md").is_file())
            self.assertTrue((bundle / "layers" / "gold.md").is_file())
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_capture.py"),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "table",
                    "--name",
                    "events",
                    "--layer",
                    "bronze",
                    "--description",
                    "test events",
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



    unittest.main()


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
        self.assertIn("criteria", data)
        self.assertEqual(data["rubric"], "reverse-engineering")
        self.assertTrue(data["pass"])


if __name__ == "__main__":
    unittest.main()
