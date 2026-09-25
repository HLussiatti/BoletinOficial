from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.bora import NoticeContent
from epe_boletin.cloud_inventory import inventory
from epe_boletin.db import Database
from epe_boletin.models import Publication


class CloudInventoryTest(unittest.TestCase):
    def test_counts_without_exposing_local_path_or_text(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source copy.sqlite3"
            db = Database(source)
            db.migrate()
            publication_id = db.upsert_publication(Publication(
                source_id="123", publication_date=date(2026, 9, 24),
                section="primera", category="PRUEBA", agency="Prueba",
                title="Título secreto", reference="ref", description="desc",
                detail_url="https://example.invalid/123",
                relevance="potential_sector_impact",
            ), True)
            db.save_document(publication_id, Path("C:/private/fake.pdf"),
                             "sha256-test", 10, "https://example.invalid/123",
                             extracted_text="Texto privado de prueba",
                             extraction_status="complete")
            db.save_notice(publication_id, NoticeContent(
                "HTML de prueba", "https://example.invalid/123",
                "https://example.invalid/123.pdf", "unknown", "none"))
            result = inventory(source)
            self.assertEqual(1, result["publications"])
            self.assertEqual(1, result["html_notices"])
            self.assertEqual(1, result["legacy_pdf_text_publications"])
            self.assertEqual(7, result["source_schema_version"])
            self.assertNotIn("private", str(result))
            self.assertNotIn("Texto privado", str(result))


if __name__ == "__main__":
    unittest.main()
