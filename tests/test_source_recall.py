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
                source = sources / f"{label}.txt"
                fact = f"The {label} relay archives amber samples for {value} evenings."
                source.write_text(fact + "\n", encoding="utf-8")
                capture_source(
                    bundle, name=f"{label.title()} relay retention", kind="lake",
                    uri=f"sources/{source.name}", description=source.read_text(encoding="utf-8").strip(),
                )

            capture("east", 12)
            capture("west", 81)
            for expected in (12, 37):
                if expected == 37:
                    capture("east", expected)
                self.assertTrue(refresh(bundle).ok)
                self.assertTrue(validate_bundle(bundle)["ok"])
                expected_path = "sources/east-relay-retention.md"
                for query in ("east relay retention", "amber samples east", "east archives evenings"):
                    with self.subTest(query=query, expected=expected):
                        hits, _ = search(bundle, query, types=["SourceSystem"], limit=3)
                        paths = [hit["path"].lstrip("/") for hit in hits]
                        self.assertIn(expected_path, paths[:3], paths)
                        hit = next(row for row in hits if row["path"].lstrip("/") == expected_path)
                        node = (bundle / hit["path"].lstrip("/")).read_text(encoding="utf-8")
                        frontmatter, _ = parse_frontmatter(node)
                        cited = root / frontmatter["uri"]
                        self.assertEqual(cited.resolve(), (sources / "east.txt").resolve())
                        fact = f"The east relay archives amber samples for {expected} evenings."
                        self.assertEqual(cited.read_text(encoding="utf-8").strip(), fact)
                        self.assertIn(fact, node)
                        self.assertNotIn("81 evenings", node)
                        if expected == 37:
                            self.assertNotIn("12 evenings", node)
                self.assertEqual(search(bundle, "ultraviolet glacier", limit=3)[0], [])


if __name__ == "__main__":
    unittest.main()
