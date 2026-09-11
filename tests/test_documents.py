from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.db import Database
from epe_boletin.documents import structure_pages
from epe_boletin.models import Publication


class DocumentStructureTest(unittest.TestCase):
    def test_sections_keep_page_ranges_and_article_boundaries(self):
        pages = (
            "Resolución 10/2026\nVISTO el expediente, y\nCONSIDERANDO:\n"
            "Que corresponde adoptar una medida.",
            "Que el servicio jurídico intervino.\nPor ello,\nLA SECRETARIA\n"
            "RESUELVE:\nARTÍCULO 1°.- Apruébase el régimen que se agrega",
            "como Anexo I.\nARTÍCULO 2°.- La medida rige desde su publicación.\n"
            "ARTÍCULO 3°.- Comuníquese y archívese.",
        )

        sections = structure_pages(pages)

        considerations = next(
            section for section in sections if section.section_type == "considerations"
        )
        dispositive = next(
            section for section in sections if section.section_type == "dispositive"
        )
        articles = [section for section in sections if section.section_type == "article"]
        self.assertEqual((1, 2), (considerations.page_from, considerations.page_to))
        self.assertEqual((2, 3), (dispositive.page_from, dispositive.page_to))
        self.assertEqual(3, len(articles))
        self.assertEqual((2, 3), (articles[0].page_from, articles[0].page_to))
        self.assertIn("como Anexo I", articles[0].text)
        self.assertEqual("ARTÍCULO 2°", articles[1].heading)
        self.assertEqual((3, 3), (articles[2].page_from, articles[2].page_to))

    def test_document_sections_are_persisted(self):
        pages = (
            "CONSIDERANDO:\nQue corresponde resolver.\nRESUELVE:\n"
            "ARTÍCULO 1°.- Apruébase la medida.",
        )
        sections = structure_pages(pages)
        item = Publication(
            source_id="10", publication_date=date(2026, 9, 11), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 10/2026", reference="RESOL-2026-10",
            description="", detail_url="https://example.test/10",
        )
        with tempfile.TemporaryDirectory() as folder:
            database = Database(Path(folder) / "boletin.sqlite3")
            database.migrate()
            publication_id = database.upsert_publication(item, True)
            document_id = database.save_document(
                publication_id, Path(folder) / "document.pdf", "a" * 64, 123,
                item.detail_url, "\n".join(pages), 1, "complete",
                sections=sections,
            )
            with database.connect() as connection:
                version = connection.execute(
                    "SELECT version FROM schema_info"
                ).fetchone()["version"]
                stored = connection.execute("""
                    SELECT section_type,heading,page_from,page_to
                    FROM document_sections WHERE document_id=?
                    ORDER BY id
                """, (document_id,)).fetchall()
                status = connection.execute(
                    "SELECT structure_status FROM documents WHERE id=?",
                    (document_id,),
                ).fetchone()["structure_status"]
            self.assertEqual(4, version)
            self.assertEqual("complete", status)
            self.assertEqual(3, len(stored))
            self.assertEqual("considerations", stored[0]["section_type"])
            self.assertEqual("ARTÍCULO 1°", stored[2]["heading"])


if __name__ == "__main__":
    unittest.main()
