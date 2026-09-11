from __future__ import annotations

import base64
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.bora import BoraClient, parse_expected_count, parse_publications
from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.pipeline import run
from epe_boletin.relevance import classify

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "primera_20250529.html"


class BoraParserTest(unittest.TestCase):
    def test_parse_complete_known_edition(self):
        items = parse_publications(SAMPLE.read_text(encoding="utf-8"), date(2025, 5, 29))
        self.assertEqual(90, len(items))
        self.assertEqual(90, parse_expected_count(SAMPLE.read_text(encoding="utf-8")))
        self.assertEqual(90, len({item.source_id for item in items}))
        self.assertTrue(any(item.source_id == "326158" for item in items))
        energy_notice = next(item for item in items if item.source_id == "326158")
        self.assertEqual("potential_sector_impact", energy_notice.relevance)
        self.assertIn("ENERGÍA ELÉCTRICA", energy_notice.agency)

    def test_pipeline_is_idempotent_and_records_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            fixture_dir = SAMPLE.parent
            database = Database(data / "boletin.sqlite3")
            for _ in range(2):
                result = run(database, BoraClient(), data, "simulation",
                             date(2025, 5, 29), date(2025, 5, 29),
                             download=False, fixture_dir=fixture_dir)
                self.assertEqual("complete", result["status"])
            with database.connect() as connection:
                total = connection.execute("SELECT COUNT(*) FROM publications").fetchone()[0]
                coverage = connection.execute(
                    "SELECT status,publication_count FROM coverage"
                ).fetchone()
            self.assertEqual(90, total)
            self.assertEqual(("complete", 90), tuple(coverage))

    def test_pdf_download_is_validated_and_named_safely(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
                return {"pdfBase64": base64.b64encode(content).decode("ascii")}

        class Session:
            def __init__(self):
                self.headers = {}

            def post(self, *args, **kwargs):
                return Response()

        item = parse_publications(SAMPLE.read_text(encoding="utf-8"), date(2025, 5, 29))[0]
        with tempfile.TemporaryDirectory() as folder:
            path, digest, size = BoraClient(Session()).download_pdf(item, Path(folder))
            self.assertTrue(path.name.startswith("NACION_Decreto_366_2025_BORA_326096"))
            self.assertEqual(64, len(digest))
            self.assertEqual(size, path.stat().st_size)
            self.assertFalse(path.with_suffix(".pdf.part").exists())

    def test_generic_energy_agency_requires_review(self):
        item = Publication(
            source_id="1", publication_date=date(2025, 5, 30), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 1/2025", reference="RESOL-2025-1",
            description="", detail_url="https://example.test/1",
        )
        self.assertEqual("needs_review", classify(item)[0])


if __name__ == "__main__":
    unittest.main()
