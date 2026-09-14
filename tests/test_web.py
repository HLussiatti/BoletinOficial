from __future__ import annotations

import tempfile
import unittest
from datetime import date
from email import policy
from email.parser import BytesParser
from pathlib import Path

from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.summaries import ConceptualSummary
from epe_boletin.web import Query, WebApplication, render_page


class WebApplicationTest(unittest.TestCase):
    def test_default_view_hides_discarded_publications(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            database = Database(data_dir / "boletin.sqlite3")
            database.migrate()
            relevant = Publication(
                source_id="10", publication_date=date(2026, 9, 14),
                section="primera", category="RESOLUCIONES",
                agency="SECRETARÍA DE ENERGÍA", title="Resolución 10/2026",
                reference="RESOL-2026-10", description="Régimen eléctrico",
                detail_url="https://example.test/10",
                relevance="potential_sector_impact", relevance_reason="Sector eléctrico",
            )
            discarded = Publication(
                source_id="11", publication_date=date(2026, 9, 14),
                section="primera", category="RESOLUCIONES",
                agency="MINISTERIO DE SALUD", title="Resolución 11/2026",
                reference="RESOL-2026-11", description="Materia sanitaria",
                detail_url="https://example.test/11",
                relevance="not_relevant", relevance_reason="Sin indicios eléctricos",
            )
            database.upsert_publication(relevant, True)
            database.upsert_publication(discarded, False)
            app = WebApplication(database, data_dir)

            rows = app.publications(Query(day="2026-09-14"))
            rows_by_type = app.publications(Query(
                day="2026-09-14", relevance="all", text="resoluciones"
            ))
            page = render_page(app, Query(day="2026-09-14")).decode("utf-8")

            self.assertEqual(["10"], [row["source_id"] for row in rows])
            self.assertEqual(2, len(rows_by_type))
            self.assertEqual(
                {"total": 2, "relevant": 1, "downloaded": 0},
                app.date_stats("2026-09-14"),
            )
            self.assertIn("Resolución 10/2026", page)
            self.assertNotIn("Resolución 11/2026", page)

    def test_document_must_be_registered_inside_data_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            database = Database(data_dir / "boletin.sqlite3")
            database.migrate()
            publication = Publication(
                source_id="20", publication_date=date(2026, 9, 14),
                section="primera", category="RESOLUCIONES",
                agency="SECRETARÍA DE ENERGÍA", title="Resolución 20/2026",
                reference="RESOL-2026-20", description="",
                detail_url="https://example.test/20",
                relevance="potential_sector_impact", relevance_reason="Sector eléctrico",
            )
            publication_id = database.upsert_publication(publication, True)
            pdf = data_dir / "documents" / "document.pdf"
            pdf.parent.mkdir(); pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            document_id = database.save_document(
                publication_id, pdf, "a" * 64, pdf.stat().st_size,
                publication.detail_url, page_count=1,
                extraction_status="complete",
            )
            app = WebApplication(database, data_dir)

            stored = app.document(document_id)
            with database.connect() as connection:
                connection.execute(
                    "UPDATE publications SET summary_status='error' WHERE id=?",
                    (publication_id,),
                )
            issues = app.operational_issues()

            self.assertIsNotNone(stored)
            self.assertEqual(pdf.resolve(), stored[0])
            self.assertEqual("Revisar: resumen", issues[0]["detail"])

    def test_prepares_and_opens_email_from_filtered_ready_publications(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            database = Database(data_dir / "boletin.sqlite3")
            database.migrate()
            publication = Publication(
                source_id="30", publication_date=date(2026, 9, 14),
                section="primera", category="RESOLUCIONES",
                agency="SECRETARÍA DE ENERGÍA", title="Resolución 30/2026",
                reference="RESOL-2026-30", description="Régimen eléctrico",
                detail_url="https://example.test/30", relevance="direct_epesf",
                relevance_reason="Menciona a EPESF",
            )
            publication_id = database.upsert_publication(publication, True)
            pdf = data_dir / "documents" / "2026_09_14_Resolución_30.pdf"
            pdf.parent.mkdir(); pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            database.save_document(
                publication_id, pdf, "a" * 64, pdf.stat().st_size,
                publication.detail_url, page_count=1, extraction_status="complete",
            )
            candidate = database.summary_candidates("test", "test", 1)[0]
            database.save_summary(
                candidate,
                ConceptualSummary("Resumen", "Incidencia directa", "Publicación", False),
                "test", "test",
            )
            opened: list[Path] = []
            app = WebApplication(database, data_dir, opened.append)
            query = Query(
                day="2026-09-14", text="30/2026",
                selected_ids=(publication_id,),
            )

            artifacts = app.prepare_email(query)
            message = BytesParser(policy=policy.default).parsebytes(
                artifacts[0].path.read_bytes()
            )

            self.assertEqual([artifacts[0].path.resolve()], opened)
            self.assertEqual(("30",), artifacts[0].source_ids)
            self.assertIsNone(message["From"])
            self.assertIsNone(message["To"])
            page = render_page(app, query).decode("utf-8")
            self.assertIn("Generar correo con seleccionadas", page)
            self.assertIn(f'value="{publication_id}"', page)

    def test_email_requires_an_explicit_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            database = Database(data_dir / "boletin.sqlite3")
            database.migrate()
            app = WebApplication(database, data_dir, lambda _: None)

            with self.assertRaisesRegex(ValueError, "Seleccioná"):
                app.prepare_email(Query(day="2026-09-14"))

    def test_historical_view_aggregates_all_dates(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            database = Database(data_dir / "boletin.sqlite3")
            database.migrate()
            for source_id, day in (("40", date(2025, 11, 1)), ("41", date(2026, 9, 14))):
                database.upsert_publication(Publication(
                    source_id=source_id, publication_date=day,
                    section="primera", category="RESOLUCIONES",
                    agency="SECRETARÍA DE ENERGÍA", title=f"Resolución {source_id}/2026",
                    reference=f"RESOL-2026-{source_id}", description="Régimen eléctrico",
                    detail_url=f"https://example.test/{source_id}",
                    relevance="potential_sector_impact", relevance_reason="Sector eléctrico",
                ), True)
            app = WebApplication(database, data_dir)

            page = render_page(app, Query(history=True)).decode("utf-8")

            self.assertEqual(2, len(app.publications(Query(history=True))))
            self.assertEqual(2, app.date_stats()["total"])
            self.assertIn("Histórico desde noviembre de 2025", page)


if __name__ == "__main__":
    unittest.main()
