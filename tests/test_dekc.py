#!/usr/bin/env python3
"""DEKC unit tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dekc_common import (  # noqa: E402
    CATALOGS,
    dump_frontmatter,
    list_concepts,
    parse_frontmatter,
    refresh_catalog_index,
    resolve_knowledge_root,
    slugify,
)
from dekc_lineage import build_graph  # noqa: E402
from dekc_validate import validate_bundle  # noqa: E402
from dekc_index import build_index, search_index  # noqa: E402
from dekc_walk import extract_sql_tables  # noqa: E402


class TestLineageRelations(unittest.TestCase):
    def test_help_advertises_only_relations_that_produce_edges(self):
        """dekc_link --help used to list DEFAULT_RELATIONS[:8], which had ZERO
        overlap with what build_graph honours — every relation the CLI's own
        help named produced no lineage edge. It now names the honoured set."""
        from dekc_lineage import FORWARD_FLOW, REVERSE_FLOW
        from dekc_common import DEFAULT_RELATIONS

        honoured = set(FORWARD_FLOW) | set(REVERSE_FLOW)
        self.assertTrue(honoured)
        # The old help text: none of it did anything.
        self.assertEqual(set(DEFAULT_RELATIONS[:8]) & honoured, set())

    def test_flow_relations_the_plugin_emits_are_honoured(self):
        """lands_as, lands_into, visualizes and consumes_stream are written by
        dekc_platform and documented in typed-edges.md as flow, but build_graph
        ignored them — so packs built from them were silently incomplete."""
        from dekc_lineage import FORWARD_FLOW, REVERSE_FLOW

        honoured = set(FORWARD_FLOW) | set(REVERSE_FLOW)
        for rel in ("lands_as", "lands_into", "visualizes", "consumes_stream"):
            with self.subTest(rel=rel):
                self.assertIn(rel, honoured)


class TestCatalogIndex(unittest.TestCase):
    STRICT = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    AWARE = re.compile(r"\[((?:\\.|\[[^\[\]]*\]|[^\]])+)\]\(([^)]+)\)")

    def _bundle(self, td, catalog, title, layer=None):
        b = Path(td)
        (b / "index.md").write_text("---\ntype: Bundle\ntitle: T\n---\n\n# T\n", encoding="utf-8")
        (b / catalog).mkdir(parents=True, exist_ok=True)
        lay = f"layer: {layer}\n" if layer else ""
        (b / catalog / "a.md").write_text(
            f"---\ntype: Table\ntitle: {title}\n{lay}---\n\n# A\n", encoding="utf-8")
        refresh_catalog_index(b, catalog)
        body = (b / catalog / "index.md").read_text(encoding="utf-8")
        return [l for l in body.splitlines() if l.startswith("- [")][0]

    def test_bracketed_title_is_escaped(self):
        with tempfile.TemporaryDirectory() as td:
            line = self._bundle(td, "tables", "Fact [Sales]")
        self.assertIn(r"\[Sales\]", line, f"label not escaped: {line!r}")
        self.assertEqual(self.AWARE.findall(line)[0][1], "/tables/a.md")
        # Escaping alone does not rescue a `[^\]]+` reader; that class has no
        # notion of an escape. This half depends on the reader change landing.
        self.assertFalse(self.STRICT.findall(line))

    def test_layer_annotation_only_on_catalogs_we_alone_own(self):
        """A shared catalog must render byte-identically to the sibling
        plugins, or the file flips every time the other one runs."""
        with tempfile.TemporaryDirectory() as td:
            shared = self._bundle(td, "glossary", "Alpha", layer="gold")
        self.assertNotIn("\u00b7 gold", shared, f"annotated a shared catalog: {shared!r}")
        with tempfile.TemporaryDirectory() as td:
            own = self._bundle(td, "layers", "Gold tier", layer="gold")
        self.assertIn("\u00b7 gold", own, f"lost the annotation on our own catalog: {own!r}")

    def test_refuses_a_catalog_this_plugin_does_not_declare(self):
        self.assertNotIn("adrs", CATALOGS)
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            (b / "adrs").mkdir()
            marker = "- [Untouched](/adrs/a.md)\n"
            (b / "adrs" / "index.md").write_text(marker, encoding="utf-8")
            refresh_catalog_index(b, "adrs")
            self.assertEqual((b / "adrs" / "index.md").read_text(encoding="utf-8"), marker)


class TestResolveKnowledgeRoot(unittest.TestCase):
    def test_configured_root_wins_when_initialized(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            for name in ("knowledge", "sample-knowledge"):
                (repo / name).mkdir()
                (repo / name / "index.md").write_text("# x\n", encoding="utf-8")
            self.assertEqual(resolve_knowledge_root(repo).name, "knowledge")

    def test_falls_back_only_when_intended_root_is_not_a_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "knowledge").mkdir()
            (repo / "sample-knowledge").mkdir()
            (repo / "sample-knowledge" / "index.md").write_text("# x\n", encoding="utf-8")
            self.assertEqual(resolve_knowledge_root(repo).name, "sample-knowledge")


class TestFrontmatterRoundTrip(unittest.TestCase):
    """parse(dump(x)) == x.

    Regression: the dumper escaped backslashes and quotes, the reader stripped
    only the surrounding quotes. Every write-modify-write cycle re-escaped
    already-escaped text, doubling the backslash count each pass -- and both
    write_concept and refresh_catalog_index do exactly that read-modify-write,
    so a single edit corrupted every quoted string in the file.
    """

    VALUES = ['[{"a":"b"}]', "back\\slash", 'quote"inside', 'both\\"mixed', "plain"]

    def test_single_round_trip_is_identity(self):
        for v in self.VALUES:
            with self.subTest(value=v):
                fm = {"type": "Concept", "title": "T", "v": v}
                self.assertEqual(parse_frontmatter(dump_frontmatter(fm))[0]["v"], v)

    def test_repeated_round_trips_do_not_grow(self):
        fm = {"type": "Concept", "title": "T", "sources_json": '[{"a":"b"}]'}
        first = None
        for _ in range(5):
            text = dump_frontmatter(fm)
            line = [l for l in text.splitlines() if l.startswith("sources_json")][0]
            if first is None:
                first = line
            self.assertEqual(line, first, "escaping grew across a round trip")
            fm, _ = parse_frontmatter(text)


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
        self.assertIn("Wireframe", data.get("concepts") or [])
        self.assertIn("DataLake", data.get("concepts") or [])

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

    def test_type_and_title_only_is_valid(self):
        from dekc_schemas import validate_frontmatter, load_schema

        schema = load_schema("Table")
        errs = validate_frontmatter({"type": "Table", "title": "orders"}, schema)
        self.assertEqual(errs, [], errs)


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


class TestDiagramsAndPlatform(unittest.TestCase):
    def test_diagram_templates(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dekc_diagram.py"),
                "--json",
                "templates",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("wireframe", data)
        self.assertIn("erd", data)

    def test_sample_has_wireframe_and_lake(self):
        concepts = list_concepts(ROOT / "sample-knowledge")
        types = {fm.get("type") for _, fm, _ in concepts}
        self.assertIn("Wireframe", types)
        self.assertIn("DataLake", types)
        self.assertIn("DQRule", types)
        self.assertIn("Diagram", types)
        self.assertIn("IngestionJob", types)

    def test_capture_wireframe_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_common.py"),
                    "init-bundle",
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                ],
                check=True,
                capture_output=True,
            )
            # dashboard stub
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_capture.py"),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "dashboard",
                    "--name",
                    "Test Dash",
                    "--description",
                    "test",
                ],
                check=True,
                capture_output=True,
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dekc_diagram.py"),
                    "--repo",
                    str(repo),
                    "--bundle",
                    "knowledge",
                    "wireframe",
                    "--name",
                    "Test WF",
                    "--subject",
                    "Test Dash",
                    "--language",
                    "plantuml",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            wfs = list((repo / "knowledge" / "wireframes").glob("*.md"))
            self.assertTrue(any(p.name != "index.md" for p in wfs))
            text = next(p for p in wfs if p.name != "index.md").read_text()
            self.assertIn("```plantuml", text)


class TestVersionConsistency(unittest.TestCase):
    """The plugin version lives in every manifest that ships with a release
    and has drifted before: a 0.1.0 -> 0.2.0 bump landed in package.json and
    three others but left 8 more manifests stale (issue #8 / PR #12)."""

    MANIFESTS = [
        ("package.json", ("version",)),
        ("marketplace.json", ("plugins", 0, "version")),
        (".claude-plugin/plugin.json", ("version",)),
        (".claude-plugin/marketplace.json", ("plugins", 0, "version")),
        (".grok-plugin/marketplace.json", ("version",)),
        (".grok-plugin/marketplace.json", ("plugins", 0, "version")),
        (".codex-plugin/plugin.json", ("version",)),
        (".opencode/plugin/dekc.json", ("version",)),
        ("public/data/catalog.json", ("version",)),
    ]

    def test_version_is_consistent_across_manifests(self):
        found = {}
        for rel, path in self.MANIFESTS:
            f = ROOT / rel
            if not f.exists():
                continue
            node = json.loads(f.read_text())
            for key in path:
                node = node[key]
            found[f"{rel}:{'.'.join(str(p) for p in path)}"] = node
        self.assertEqual(len(set(found.values())), 1, f"version drift: {found}")

    def test_readme_version_matches_package_json(self):
        expected = json.loads((ROOT / "package.json").read_text())["version"]
        readme = (ROOT / "README.md").read_text()
        m = re.search(r"\*\*Version\*\*\s*\|\s*([0-9]+\.[0-9]+\.[0-9]+)\s*\|", readme)
        self.assertIsNotNone(m, "README version row not found")
        self.assertEqual(m.group(1), expected)


if __name__ == "__main__":
    unittest.main()
