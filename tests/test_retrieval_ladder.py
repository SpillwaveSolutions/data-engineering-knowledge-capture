#!/usr/bin/env python3
"""Retrieval ladder: index → rg → scan. Scores and pack graphs stay identical."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dekc_common import find_rg  # noqa: E402
from dekc_doctor import doctor  # noqa: E402
from dekc_index import drop_index, refresh, status  # noqa: E402
from dekc_pack import pack  # noqa: E402
from dekc_search import candidate_files, search  # noqa: E402

FAKE_RG = ROOT / "tests/fixtures/fake_rg.py"
SAMPLE = ROOT / "sample-knowledge"


class TestRipgrepAccelerator(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("DEKC_RG_PATH")
        FAKE_RG.chmod(0o755)
        os.environ["DEKC_RG_PATH"] = str(FAKE_RG)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("DEKC_RG_PATH", None)
        else:
            os.environ["DEKC_RG_PATH"] = self._saved

    def test_find_rg_honors_env(self):
        self.assertEqual(Path(find_rg()).resolve(), FAKE_RG.resolve())

    def test_search_rg_matches_scan_ranking(self):
        scan, scan_engine = search(SAMPLE, "revenue", limit=10, use_rg=False, use_index=False)
        accel, accel_engine = search(SAMPLE, "revenue", limit=10, use_rg=True, use_index=False)
        self.assertGreaterEqual(len(scan), 1)
        self.assertEqual([h["path"] for h in scan], [h["path"] for h in accel])
        self.assertEqual([h["score"] for h in scan], [h["score"] for h in accel])
        self.assertEqual(accel_engine, "rg")
        self.assertEqual(scan_engine, "scan")

    def test_search_and_terms_intersect(self):
        files, engine = candidate_files(
            SAMPLE, ["revenue", "zzzz-no-such-term"], use_rg=True, use_index=False
        )
        self.assertEqual(engine, "rg")
        self.assertEqual(files, [])

    def test_pack_rg_matches_scan_graph(self):
        # Sample 2-hop subgraph is >20 nodes; cap would make BFS order a
        # false identity failure. Identity is the set, not the clip.
        scan = pack(SAMPLE, "tables/gold-order-daily.md", hops=2, max_nodes=80, use_rg=False, use_index=False)
        accel = pack(SAMPLE, "tables/gold-order-daily.md", hops=2, max_nodes=80, use_rg=True, use_index=False)
        self.assertEqual(scan["node_count"], accel["node_count"])
        self.assertEqual(
            sorted(n["path"] for n in scan["nodes"]),
            sorted(n["path"] for n in accel["nodes"]),
        )
        self.assertEqual(accel["reverse_index"], "rg")
        self.assertEqual(scan["reverse_index"], "scan")
        self.assertGreaterEqual(scan["node_count"], 5)

    def test_lineage_pack_survives_a_symlink_aliased_bundle(self):
        """rg_list_files resolves its hits. mkdtemp hands back the /var alias
        on macOS, so relative_to raised and the lineage neighbor was dropped —
        while the pack still reported `reverse_index: rg`."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        if tmp == tmp.resolve():
            self.skipTest("no path alias on this platform")
        (tmp / "index.md").write_text(
            "---\ntype: Bundle\ntitle: T\n---\n\n# T\n", encoding="utf-8"
        )
        tables = tmp / "tables"
        tables.mkdir()
        (tables / "root.md").write_text(
            "---\ntype: Table\ntitle: Root\n---\n\n# Root\n", encoding="utf-8"
        )
        (tables / "caller.md").write_text(
            "---\ntype: Table\ntitle: Caller\nlinks:\n"
            "  - target: /tables/root.md\n    rel: reads_from\n---\n\n# Caller\n",
            encoding="utf-8",
        )
        scan = pack(tmp, "tables/root.md", hops=1, max_nodes=8, use_rg=False, use_index=False)
        accel = pack(tmp, "tables/root.md", hops=1, max_nodes=8, use_rg=True, use_index=False)
        scan_paths = {n["path"] for n in scan["nodes"]}
        accel_paths = {n["path"] for n in accel["nodes"]}
        self.assertIn("/tables/caller.md", scan_paths)
        self.assertEqual(scan_paths, accel_paths)
        self.assertEqual(accel["reverse_index"], "rg")


class TestSqliteIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "index.md").write_text(
            '---\nokf_version: "0.2"\ntitle: t\n---\n', encoding="utf-8"
        )
        (self.tmp / "log.md").write_text("# log\n", encoding="utf-8")
        tables = self.tmp / "tables"
        tables.mkdir()
        (tables / "root.md").write_text(
            "---\n"
            "type: Table\n"
            "title: Lumenfield Orders\n"
            "description: gold revenue fact\n"
            "layer: gold\n"
            "tags: [orders, revenue]\n"
            "links:\n"
            "  - target: /tables/neighbor.md\n"
            "    rel: feeds\n"
            "---\n"
            "# Lumenfield Orders\n\nDaily GMV.\n",
            encoding="utf-8",
        )
        (tables / "neighbor.md").write_text(
            "---\n"
            "type: Table\n"
            "title: Neighbor\n"
            "description: upstream bronze\n"
            "layer: bronze\n"
            "---\n"
            "# Neighbor\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_refresh_then_noop(self):
        first = refresh(self.tmp, force=True)
        self.assertIsNotNone(first)
        self.assertTrue(first.ok)
        self.assertEqual(first.parsed, 2)
        second = refresh(self.tmp)
        self.assertEqual(second.parsed, 0)
        self.assertEqual(second.unchanged, 2)

    def test_search_index_matches_scan(self):
        scan, scan_engine = search(self.tmp, "revenue", use_index=False, use_rg=False)
        idx, idx_engine = search(self.tmp, "revenue", use_index=True, use_rg=False)
        self.assertEqual(idx_engine, "index")
        self.assertEqual(scan_engine, "scan")
        self.assertGreaterEqual(len(scan), 1)
        self.assertEqual([h["path"] for h in scan], [h["path"] for h in idx])
        self.assertEqual([h["score"] for h in scan], [h["score"] for h in idx])

    def test_pack_index_matches_scan(self):
        scan = pack(self.tmp, "tables/root.md", hops=1, max_nodes=8, use_rg=False, use_index=False)
        idx = pack(self.tmp, "tables/root.md", hops=1, max_nodes=8, use_rg=False, use_index=True)
        self.assertEqual(idx["reverse_index"], "index")
        self.assertEqual(scan["reverse_index"], "scan")
        self.assertEqual(
            sorted(n["path"] for n in scan["nodes"]),
            sorted(n["path"] for n in idx["nodes"]),
        )
        self.assertIn("/tables/neighbor.md", [n["path"] for n in idx["nodes"]])

    def test_touch_reparses_one_file(self):
        refresh(self.tmp, force=True)
        target = self.tmp / "tables/root.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
        stats = refresh(self.tmp)
        self.assertEqual(stats.parsed, 1)
        self.assertEqual(stats.unchanged, 1)

    def test_delete_drops_row(self):
        refresh(self.tmp, force=True)
        (self.tmp / "tables/neighbor.md").unlink()
        stats = refresh(self.tmp)
        self.assertEqual(stats.deleted, 1)
        self.assertEqual(status(self.tmp)["nodes"], 1)

    def test_drop_removes_sqlite(self):
        refresh(self.tmp, force=True)
        self.assertTrue(status(self.tmp)["present"])
        self.assertTrue(drop_index(self.tmp))
        self.assertFalse(status(self.tmp)["present"])

    def test_no_json_index_written(self):
        refresh(self.tmp, force=True)
        self.assertFalse((self.tmp / ".index").exists())
        self.assertTrue((self.tmp / ".dekc" / "index.sqlite").is_file())


class TestDoctorToolchain(unittest.TestCase):
    def test_doctor_reports_sqlite_index(self):
        report = doctor(SAMPLE)
        self.assertIn("toolchain", report)
        self.assertIn("fts5", report["toolchain"]["sqlite"])
        self.assertIn("index", report)
        self.assertTrue(str(report["index"]["path"]).endswith("index.sqlite"))


class TestSampleSearchCompat(unittest.TestCase):
    def test_revenue_still_hits(self):
        hits, engine = search(SAMPLE, "revenue", limit=5)
        self.assertTrue(hits)
        self.assertIn(engine, {"index", "rg", "scan"})


if __name__ == "__main__":
    unittest.main()
