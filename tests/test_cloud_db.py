from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from importlib.util import find_spec
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from epe_boletin.bora import NoticeContent
from epe_boletin.cloud_db import TursoDatabase
from epe_boletin.models import Edition, Publication
from epe_boletin.pipeline import run
from epe_boletin.summaries import ConceptualSummary
from epe_boletin.turso_setup import main as setup_main
from epe_boletin.turso_smoke import smoke_turso


class TursoDatabaseTest(unittest.TestCase):
    def test_synthetic_notice_summary_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "pilot.sqlite3"
            db = TursoDatabase(
                "libsql://pilot.turso.io", "test-token",
                connector=lambda **_: sqlite3.connect(db_path),
            )
            db.migrate()
            db.migrate()
            day = date(2026, 9, 24)
            run_id = db.start_run("simulation", day, day)
            item = Publication(
                source_id="synthetic-1", publication_date=day, section="primera",
                category="Resoluciones", agency="Organismo de prueba",
                title="Aviso sintético", reference="RES 1/2026",
                description="Sólo para la prueba", detail_url="https://example.invalid/1",
                relevance="potential_sector_impact", relevance_reason="Prueba",
            )
            first = db.upsert_publication(item, True)
            self.assertEqual(first, db.upsert_publication(item, True))
            with db.connect() as connection:
                self.assertEqual("not_requested", connection.execute(
                    "SELECT document_status FROM publications WHERE id=?",
                    (first,)).fetchone()["document_status"])
            db.save_notice(first, NoticeContent(
                text="Texto sintético del aviso.",
                notice_url="https://example.invalid/1",
                pdf_url="https://example.invalid/1.pdf",
                pdf_availability="unknown", annex_status="unread",
            ))
            db.update_classification(first, "potential_sector_impact",
                                     "Prueba", "html_text", "test-rules")
            candidates = db.summary_candidates("test-model", "test-prompt")
            self.assertEqual(1, len(candidates))
            self.assertIn("anexos no analizados", candidates[0].source_limitations)
            db.save_summary(candidates[0], ConceptualSummary(
                "Resumen sintético", "Relación potencial", "Sin fecha", True,
            ), "test-model", "test-prompt")
            self.assertEqual([], db.summary_candidates("test-model", "test-prompt"))
            db.save_coverage(day, "complete", 1, 1)
            db.finish_run(run_id, "complete", 1, 1)
            self.assertEqual(day, db.last_complete_date())
            status = db.status()
            self.assertEqual(1, status["publications"]["total"])
            self.assertEqual(1, status["summaries"]["ready"])
            with db.connect() as connection:
                names = {row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("documents", names)
            self.assertNotIn("deliveries", names)

    def test_rejects_unrelated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "other.sqlite3"
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute("CREATE TABLE existing_user_data(value TEXT)")
                connection.commit()
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: sqlite3.connect(db_path))
            with self.assertRaisesRegex(RuntimeError, "tablas ajenas"):
                db.migrate()

    def test_setup_reports_only_safe_schema_result(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "pilot.sqlite3"
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: sqlite3.connect(db_path))
            output = StringIO()
            with patch("epe_boletin.turso_setup.TursoDatabase.from_env",
                       return_value=db), patch("sys.stdout", output):
                self.assertEqual(0, setup_main(["--init"]))
            self.assertIn('"table_count": 7', output.getvalue())
            self.assertNotIn("test-token", output.getvalue())
            self.assertNotIn("pilot.turso.io", output.getvalue())

    def test_cloud_pipeline_writes_no_file_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: sqlite3.connect(root / "pilot.sqlite3"))
            day = date(2026, 9, 24)
            item = Publication(
                source_id="synthetic-2", publication_date=day, section="primera",
                category="Resoluciones", agency="Organismo de prueba",
                title="Régimen eléctrico", reference="RES 2/2026",
                description="Reglas del mercado eléctrico",
                detail_url="https://example.invalid/2",
                relevance="potential_sector_impact", relevance_reason="Prueba",
            )

            class Client:
                def fetch_edition(self, requested_day, fixture):
                    return Edition(requested_day, (item,), False, 1)

                def fetch_notice(self, publication, fixture):
                    return NoticeContent(
                        text="Se regulan las instalaciones eléctricas.",
                        notice_url=publication.detail_url,
                        pdf_url="https://example.invalid/2.pdf",
                        pdf_availability="unknown", annex_status="none",
                    )

                def download_pdf(self, *args, **kwargs):
                    raise AssertionError("No se debe descargar un PDF")

            first = run(db, Client(), root, "simulation", day, day,
                        source_mode="cloud")
            second = run(db, Client(), root, "simulation", day, day,
                         source_mode="cloud")
            self.assertEqual("complete", first["status"])
            self.assertEqual("complete", second["status"])
            with db.connect() as connection:
                count = connection.execute("SELECT COUNT(*) count FROM publications").fetchone()
                self.assertEqual(1, count["count"])
                self.assertEqual(1, connection.execute(
                    "SELECT COUNT(*) count FROM notice_contents").fetchone()["count"])

    def test_remote_smoke_cleans_up_synthetic_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "smoke.sqlite3"
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: sqlite3.connect(db_path))
            db.migrate()
            self.assertEqual("ok", smoke_turso(db)["status"])
            self.assertEqual("ok", smoke_turso(db)["cleanup"])
            with db.connect() as connection:
                for table in ("publications", "notice_contents", "summaries"):
                    count = connection.execute(
                        f"SELECT COUNT(*) count FROM {table}").fetchone()["count"]
                    self.assertEqual(0, count)

    def test_version_one_upgrade_and_legacy_pdf_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "upgrade.sqlite3"
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: sqlite3.connect(db_path))
            db.migrate()
            with db.connect() as connection:
                connection.execute("DROP TABLE legacy_pdf_texts")
                connection.execute("UPDATE cloud_schema_info SET version=1")
            db.migrate()
            with db.connect() as connection:
                self.assertEqual(2, connection.execute(
                    "SELECT version FROM cloud_schema_info").fetchone()["version"])
            item = Publication(
                source_id="legacy-1", publication_date=date(2025, 9, 24),
                section="primera", category="RESOLUCIONES", agency="Prueba",
                title="Texto heredado", reference="RES 1/2025", description="",
                detail_url="https://example.invalid/legacy",
                relevance="potential_sector_impact",
            )
            publication_id = db.upsert_publication(item, False)
            with db.connect() as connection:
                connection.execute("""
                    INSERT INTO legacy_pdf_texts
                        (publication_id,kind,sha256,extracted_text,page_count,extraction_status)
                    VALUES(?,?,?,?,?,?)
                """, (publication_id, "main", "pdf-hash", "PDF histórico", 2, "complete"))
            candidate = db.summary_candidates("model", "prompt")[0]
            self.assertEqual("PDF histórico", candidate.full_text.splitlines()[-1])
            self.assertIn("PDF", candidate.source_limitations)

    @unittest.skipUnless(find_spec("libsql"), "libsql no está instalado")
    def test_installed_libsql_driver_returns_named_rows(self):
        import libsql

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "libsql-pilot.sqlite3"
            db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                               connector=lambda **_: libsql.connect(str(db_path)))
            db.migrate()
            run_id = db.start_run("simulation", date(2026, 9, 24),
                                  date(2026, 9, 24))
            with db.connect() as connection:
                row = connection.execute("SELECT id,status FROM runs WHERE id=?",
                                         (run_id,)).fetchone()
            self.assertEqual({"id": run_id, "status": "running"}, row)
            self.assertEqual("ok", smoke_turso(db)["cleanup"])
            with db.connect() as connection:
                connection.executemany("""
                    INSERT INTO coverage(source,publication_date,status,checked_at)
                    VALUES(?,?,?,?)
                """, [("BORA", "2026-09-23", "complete", "now"),
                      ("BORA", "2026-09-24", "complete", "now")])
            with db.connect() as connection:
                self.assertEqual(2, connection.execute(
                    "SELECT COUNT(*) count FROM coverage").fetchone()["count"])
                self.assertEqual(2, len(list(connection.execute(
                    "SELECT publication_date FROM coverage ORDER BY publication_date"))))


if __name__ == "__main__":
    unittest.main()
