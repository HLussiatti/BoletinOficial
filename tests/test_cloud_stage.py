from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from epe_boletin.bora import NoticeContent
from epe_boletin.cloud_stage import StageError, _official_url, create_stage
from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.summaries import ConceptualSummary


DAY = date(2026, 9, 24)
DETAIL = "https://www.boletinoficial.gob.ar/detalleAviso/primera/123/20260924"
PDF = "https://www.boletinoficial.gob.ar/pdf/aviso/primera/123/20260924"


class CloudStageTest(unittest.TestCase):
    def test_only_expected_supplement_query_is_allowed(self):
        self.assertTrue(_official_url(DETAIL + "?suplemento=1", "/detalleAviso/"))
        self.assertFalse(_official_url(DETAIL + "?token=secret", "/detalleAviso/"))
        self.assertFalse(_official_url(PDF + "?suplemento=1", "/pdf/aviso/"))

    def test_stage_keeps_public_fields_and_omits_local_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operacion.sqlite3"
            output = root / "stage.sqlite3"
            db = Database(source)
            db.migrate()
            publication_id = db.upsert_publication(Publication(
                source_id="123", publication_date=DAY, section="primera",
                category="RESOLUCIONES", agency="Secretaría de Energía",
                title="Resolución 1/2026", reference="RES 1/2026",
                description="Norma eléctrica", detail_url=DETAIL,
                relevance="potential_sector_impact",
            ), True)
            db.save_coverage(DAY, "complete", 1, 1)
            db.save_document(publication_id, Path("C:/private/never-upload.pdf"),
                             "pdf-hash", 100, DETAIL, "Texto extraído del PDF",
                             1, "complete")
            db.save_notice(publication_id, NoticeContent(
                "HTML público", DETAIL, PDF, "available", "none"))
            candidate = db.summary_candidates("test-model", "test-prompt")[0]
            db.save_summary(candidate, ConceptualSummary(
                "Resumen público", "Impacto potencial", "No especificada", True,
            ), "test-model", "test-prompt")
            source_digest = hashlib.sha256(source.read_bytes()).hexdigest()

            result = create_stage(source, output)

            self.assertEqual({"publications": 1, "coverage": 1,
                              "notice_contents": 1, "legacy_pdf_texts": 1,
                              "summaries": 1}, result["counts"])
            self.assertEqual(source_digest,
                             hashlib.sha256(source.read_bytes()).hexdigest())
            with closing(sqlite3.connect(output)) as connection:
                tables = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertNotIn("documents", tables)
                self.assertNotIn("deliveries", tables)
                self.assertEqual("Texto extraído del PDF", connection.execute(
                    "SELECT extracted_text FROM legacy_pdf_texts").fetchone()[0])
            self.assertNotIn(b"never-upload.pdf", output.read_bytes())
            with self.assertRaises(StageError):
                create_stage(source, output)

    def test_rejects_nonofficial_urls_without_writing_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            output = root / "stage.sqlite3"
            db = Database(source)
            db.migrate()
            db.upsert_publication(Publication(
                source_id="fake", publication_date=DAY, section="primera",
                category="PRUEBA", agency="Prueba", title="Prueba",
                reference="", description="", detail_url="https://example.invalid/fake",
            ), False)
            with self.assertRaisesRegex(StageError, "URL no oficial"):
                create_stage(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
