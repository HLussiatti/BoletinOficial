from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.bora import BoraClient, BoraError, parse_notice_html
from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.pipeline import run
from epe_boletin.summaries import ConceptualSummary, _apply_review_guard


DAY = date(2026, 9, 11)
DETAIL = "https://www.boletinoficial.gob.ar/detalleAviso/primera/123/20260911"
HTML = """<html><div id="tituloDetalleAviso"><h1>SECRETARÍA DE ENERGÍA</h1>
<h2>Resolución 3/2026</h2></div><div id="cuerpoDetalleAviso">
<p><style>oculto</style></p><p>Buenos Aires, 11/09/2026</p>
<p>CONSIDERANDO:</p><p>Se establecen reglas para el mercado eléctrico mayorista.</p>
<p>RESUELVE:</p><p>ARTÍCULO 1°.- Apruébase el régimen eléctrico.</p>
<p>NOTA: El/los Anexo/s que integra/n esta Resolución se publican en la edición web.</p>
</div><div onclick='descargarPDFAnexo("primera","1","444","20260911","/pdf/download_anexo")'>Anexo</div></html>"""


def publication() -> Publication:
    return Publication("123", DAY, "primera", "RESOLUCIONES", "SECRETARÍA DE ENERGÍA",
                       "Resolución 3/2026", "RESOL-2026-3", "", DETAIL)


class CloudNoticeTest(unittest.TestCase):
    def test_parser_scopes_text_and_marks_unread_annex(self):
        notice = parse_notice_html(HTML, publication())
        self.assertIn("CONSIDERANDO:\nSe establecen", notice.text)
        self.assertNotIn("oculto", notice.text)
        self.assertEqual("unread", notice.annex_status)
        self.assertEqual("unknown", notice.pdf_availability)
        self.assertEqual("https://www.boletinoficial.gob.ar/pdf/aviso/primera/123/20260911",
                         notice.pdf_url)
        with self.assertRaises(BoraError):
            parse_notice_html("<html>Sin aviso</html>", publication())

    def test_fetch_checks_pdf_with_head_without_getting_pdf(self):
        class Response:
            status_code = 200
            url = DETAIL
            text = HTML

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}
                self.get_urls = []
                self.head_urls = []

            def get(self, url, **kwargs):
                self.get_urls.append(url)
                return Response()

            def head(self, url, **kwargs):
                self.head_urls.append(url)
                response = Response()
                response.url = url
                response.headers = {"Content-Type": "application/pdf"}
                return response

        session = Session()
        notice = BoraClient(session).fetch_notice(publication())
        self.assertEqual([DETAIL], session.get_urls)
        self.assertEqual([notice.pdf_url], session.head_urls)
        self.assertEqual("available", notice.pdf_availability)

    def test_cloud_run_uses_html_for_classification_and_summaries(self):
        index = """<script>fechaSeleccionadaYMD = '20260911';</script>
        <h5 class="seccion-rubro">RESOLUCIONES</h5>
        <a href="/detalleAviso/primera/123/20260911"><div class="linea-aviso">
        <span class="item">SECRETARÍA DE ENERGÍA</span>
        <span class="item-detalle">Resolución 3/2026</span>
        <span class="item-detalle">RESOL-2026-3</span></div></a>"""

        class Client(BoraClient):
            def download_pdf(self, *args, **kwargs):
                raise AssertionError("cloud no debe descargar PDF")

            def download_annex(self, *args, **kwargs):
                raise AssertionError("cloud no debe descargar anexos")

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "primera_20260911.html").write_text(index, encoding="utf-8")
            (fixtures / "detalle_123_20260911.html").write_text(HTML, encoding="utf-8")
            db = Database(root / "boletin.sqlite3")
            result = run(db, Client(), root, "simulation", DAY, DAY,
                         fixture_dir=fixtures, source_mode="cloud")
            self.assertEqual("complete", result["status"])
            self.assertEqual(0, result["downloaded"])
            with db.connect() as connection:
                row = connection.execute("""SELECT p.relevance,p.classification_status,
                    n.annex_status,n.pdf_url FROM publications p
                    JOIN notice_contents n ON n.publication_id=p.id""").fetchone()
                self.assertEqual("potential_sector_impact", row["relevance"])
                self.assertEqual("html_text", row["classification_status"])
                self.assertEqual("unread", row["annex_status"])
                self.assertEqual(0, connection.execute("SELECT count(*) FROM documents").fetchone()[0])
            candidates = db.summary_candidates("model", "prompt")
            self.assertEqual(1, len(candidates))
            self.assertIn("anexos no analizados", candidates[0].source_limitations)
            guarded = _apply_review_guard(candidates[0], ConceptualSummary(
                "Resumen", "EPESF", "Desde publicación", False))
            self.assertTrue(guarded.needs_review)

            repeated = run(db, Client(), root, "simulation", DAY, DAY,
                           fixture_dir=fixtures, source_mode="cloud")
            self.assertEqual("complete", repeated["status"])
            with db.connect() as connection:
                self.assertEqual(1, connection.execute(
                    "SELECT count(*) FROM notice_contents").fetchone()[0])

    def test_version_six_copy_migrates_without_documents(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "copy.sqlite3")
            db.migrate()
            with db.connect() as connection:
                connection.execute("DROP TABLE notice_contents")
                connection.execute("UPDATE schema_info SET version=6")
            db.migrate()
            with db.connect() as connection:
                self.assertEqual(7, connection.execute(
                    "SELECT version FROM schema_info").fetchone()[0])
                self.assertIsNotNone(connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='notice_contents'").fetchone())


if __name__ == "__main__":
    unittest.main()
