from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.cloud_db import TursoDatabase
from epe_boletin.cloud_import import CloudImportError, import_stage, inspect_stage
from epe_boletin.cloud_stage import create_stage
from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.summaries import ConceptualSummary


class CloudImportTest(unittest.TestCase):
    def test_staged_import_is_verified_and_resumable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = Database(root / "local.sqlite3")
            local.migrate()
            day = date(2025, 5, 29)
            source_id = "456"
            publication_id = local.upsert_publication(Publication(
                source_id=source_id, publication_date=day, section="primera",
                category="RESOLUCIONES", agency="Secretaría de Energía",
                title="Resolución de prueba", reference="RES 1/2025",
                description="Reglas eléctricas",
                detail_url="https://www.boletinoficial.gob.ar/detalleAviso/primera/456/20250529",
                relevance="potential_sector_impact",
            ), True)
            local.save_coverage(day, "complete", 1, 1)
            local.save_document(publication_id, Path("C:/private/document.pdf"),
                                "pdf-hash", 100, "https://example.invalid/source",
                                "Texto PDF de prueba", 1, "complete")
            candidate = local.summary_candidates("model", "prompt")[0]
            local.save_summary(candidate, ConceptualSummary(
                "Resumen de prueba", "Relación posible", "No indicada", True,
            ), "model", "prompt")
            stage_path = root / "stage.sqlite3"
            staged = create_stage(local.path, stage_path)
            remote_path = root / "remote.sqlite3"
            remote = TursoDatabase("libsql://pilot.turso.io", "test-token",
                                   connector=lambda **_: sqlite3.connect(remote_path))
            with self.assertRaisesRegex(CloudImportError, "hash"):
                import_stage(stage_path, remote, "0" * 64)
            self.assertFalse(remote_path.exists())
            self.assertEqual(staged["counts"], inspect_stage(stage_path)["counts"])

            first = import_stage(stage_path, remote, staged["stage_sha256"],
                                 batch_size=1)
            second = import_stage(stage_path, remote, staged["stage_sha256"],
                                  batch_size=1)
            self.assertEqual(staged["counts"], first["verified"])
            self.assertEqual(first["verified"], second["verified"])
            with remote.connect() as connection:
                self.assertEqual(1, connection.execute(
                    "SELECT COUNT(*) count FROM publications").fetchone()["count"])
                row = connection.execute("""
                    SELECT p.summary_status,d.extracted_text FROM publications p
                    JOIN legacy_pdf_texts d ON d.publication_id=p.id
                """).fetchone()
                self.assertEqual("ready", row["summary_status"])
                self.assertEqual("Texto PDF de prueba", row["extracted_text"])
                names = {item["name"] for item in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertNotIn("documents", names)
                self.assertNotIn("deliveries", names)
            with remote.connect() as connection:
                connection.execute("UPDATE summaries SET conceptual_summary='Alterado'")
            with self.assertRaisesRegex(CloudImportError, "summaries"):
                import_stage(stage_path, remote, staged["stage_sha256"], batch_size=1)


if __name__ == "__main__":
    unittest.main()
