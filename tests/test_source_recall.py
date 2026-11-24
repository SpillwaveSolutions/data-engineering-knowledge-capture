"""Offline capture-to-citation regression on a synthetic bundle."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dekc_capture import capture_source
from dekc_common import ensure_bundle, parse_frontmatter
from dekc_index import refresh
from dekc_search import search
from dekc_validate import validate_bundle


class SourceRecallTests(unittest.TestCase):
    @patch.dict("os.environ", {"SECOND_BRAIN_IDENTITY": "Fixture"})
    def test_capture_recall_and_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "knowledge"
            sources = root / "sources"
            sources.mkdir()
            ensure_bundle(bundle)

            def capture(label, value):
                source = sources / f"{label}-{value}.txt"
                fact = f"The {label} relay archives amber samples for {value} evenings."
                source.write_text(fact + "\n", encoding="utf-8")
                title = "East relay retention" if label == "east" else "West relay schedule"
                capture_source(
                    bundle, name=title, kind="lake",
                    uri=f"sources/{source.name}", description=source.read_text(encoding="utf-8").strip() + " Retention record.",
                )

            capture("east", 12)
            capture("west", 81)
            for expected in (12, 37):
                if expected == 37:
                    capture("east", expected)
                self.assertTrue(refresh(bundle).ok)
                self.assertTrue(validate_bundle(bundle)["ok"])
                expected_path = "sources/east-relay-retention.md"
                for query in ("east relay retention", "amber samples east", "east archives evenings", "amber retention"):
                    with self.subTest(query=query, expected=expected):
                        hits, _ = search(bundle, query, types=["SourceSystem"], limit=3)
                        paths = [hit["path"].lstrip("/") for hit in hits]
                        self.assertEqual(paths[:1], [expected_path], paths)
                        if query == "amber retention":
                            self.assertEqual(paths[1:], ["sources/west-relay-schedule.md"])
                            self.assertGreater(hits[0]["score"], hits[1]["score"])
                        hit = hits[0]
                        node = (bundle / hit["path"].lstrip("/")).read_text(encoding="utf-8")
                        frontmatter, _ = parse_frontmatter(node)
                        cited = root / frontmatter["uri"]
                        self.assertEqual(cited.resolve(), (sources / f"east-{expected}.txt").resolve())
                        fact = f"The east relay archives amber samples for {expected} evenings."
                        self.assertEqual(cited.read_text(encoding="utf-8").strip(), fact)
                        self.assertIn(fact, node)
                        self.assertNotIn("81 evenings", node)
                        if expected == 37:
                            self.assertNotIn("12 evenings", node)
                            self.assertIn("12 evenings", (sources / "east-12.txt").read_text(encoding="utf-8"))
                self.assertEqual(search(bundle, "ultraviolet glacier", limit=3)[0], [])


if __name__ == "__main__":
    unittest.main()
