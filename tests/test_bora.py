from __future__ import annotations

import base64
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.bora import (
    BoraClient,
    BoraError,
    BoraNetworkError,
    EditionNotPublished,
    document_stem,
    parse_expected_count,
    parse_publications,
)
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
            selected = data / "selected.csv"
            audit = data / "audit.csv"
            self.assertEqual(1, database.export_csv(selected))
            self.assertEqual(90, database.export_csv(audit, include_all=True))

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
            self.assertEqual("2025_05_29_Decreto_366.pdf", path.name)
            self.assertEqual(64, len(digest))
            self.assertEqual(size, path.stat().st_size)
            self.assertFalse(path.with_suffix(".pdf.part").exists())

    def test_transient_http_failure_is_retried(self):
        class Response:
            url = "https://example.test/edition"
            text = "ok"

            def __init__(self, status_code):
                self.status_code = status_code

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}
                self.calls = 0

            def get(self, *args, **kwargs):
                self.calls += 1
                return Response(503 if self.calls < 3 else 200)

        session = Session()
        client = BoraClient(session, max_attempts=3, sleep=lambda _: None)
        text, _ = client._get_text("https://example.test/edition")
        self.assertEqual("ok", text)
        self.assertEqual(3, session.calls)

    def test_transient_http_failure_stops_after_configured_attempts(self):
        class Response:
            status_code = 503

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}
                self.calls = 0

            def get(self, *args, **kwargs):
                self.calls += 1
                return Response()

        session = Session()
        client = BoraClient(session, max_attempts=2, sleep=lambda _: None)
        with self.assertRaises(BoraNetworkError):
            client._get_text("https://example.test/edition")
        self.assertEqual(2, session.calls)

    def test_absent_edition_is_identified_without_parsing_redirected_day(self):
        class Response:
            status_code = 200
            url = "https://www.boletinoficial.gob.ar/seccion/primera/20260910"
            text = "<script>fechaSeleccionadaYMD = '20260910';</script>"

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}

            def get(self, *args, **kwargs):
                return Response()

        with self.assertRaises(EditionNotPublished):
            BoraClient(Session()).fetch_edition(date(2026, 9, 11))

    def test_invalid_pdf_is_rejected_without_creating_a_file(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"pdfBase64": base64.b64encode(b"not-a-pdf").decode("ascii")}

        class Session:
            def __init__(self):
                self.headers = {}

            def post(self, *args, **kwargs):
                return Response()

        item = parse_publications(SAMPLE.read_text(encoding="utf-8"), date(2025, 5, 29))[0]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            with self.assertRaises(BoraError):
                BoraClient(Session()).download_pdf(item, output)
            self.assertEqual([], list(output.iterdir()))

    def test_failed_source_is_persisted_in_run_and_coverage(self):
        class FailingClient:
            def fetch_edition(self, *args, **kwargs):
                raise BoraNetworkError("servicio no disponible")

        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            database = Database(data / "boletin.sqlite3")
            result = run(database, FailingClient(), data, "daily",
                         date(2026, 9, 11), date(2026, 9, 11), download=False)
            self.assertEqual("partial", result["status"])
            self.assertEqual(1, result["failed"])
            with database.connect() as connection:
                coverage = connection.execute(
                    "SELECT status,error FROM coverage WHERE publication_date = ?",
                    ("2026-09-11",),
                ).fetchone()
                recorded_run = connection.execute(
                    "SELECT status,error FROM runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertEqual("failed", coverage["status"])
            self.assertIn("servicio no disponible", coverage["error"])
            self.assertEqual("partial", recorded_run["status"])
            self.assertIn("servicio no disponible", recorded_run["error"])

    def test_generic_energy_agency_requires_review(self):
        item = Publication(
            source_id="1", publication_date=date(2025, 5, 30), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 1/2025", reference="RESOL-2025-1",
            description="", detail_url="https://example.test/1",
        )
        self.assertEqual("needs_review", classify(item)[0])

    def test_unqualified_transport_is_not_relevant(self):
        item = Publication(
            source_id="2", publication_date=date(2026, 9, 11), section="primera",
            category="AVISOS OFICIALES", agency="SECRETARÍA DE TRANSPORTE",
            title="Aviso Oficial", reference="", description="",
            detail_url="https://example.test/2",
        )
        self.assertEqual("not_relevant", classify(item)[0])

    def test_full_text_can_promote_pending_energy_resolution(self):
        item = Publication(
            source_id="3", publication_date=date(2026, 9, 11), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 3/2026", reference="RESOL-2026-3",
            description="", detail_url="https://example.test/3",
        )
        relevance, _ = classify(
            item, "Se establecen reglas para el mercado eléctrico mayorista."
        )
        self.assertEqual("potential_sector_impact", relevance)

    def test_annex_contract_is_parsed_from_detail(self):
        class Response:
            url = "https://www.boletinoficial.gob.ar/detalleAviso/primera/3/20260911"
            text = """<div onclick='descargarPDFAnexo("primera","1", "7768089",
                "20260911", "/pdf/download_anexo");'>Anexo - 1</div>"""

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}

            def get(self, *args, **kwargs):
                return Response()

        item = Publication(
            source_id="3", publication_date=date(2026, 9, 11), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 238/2026", reference="RESOL-2026-238",
            description="", detail_url=Response.url, has_annexes=True,
        )
        annexes = BoraClient(Session()).fetch_annexes(item)
        self.assertEqual(1, len(annexes))
        self.assertEqual("annex:1:7768089", annexes[0].kind)
        self.assertEqual("/pdf/download_anexo", annexes[0].endpoint)

    def test_document_name_preserves_accents(self):
        item = Publication(
            source_id="347303", publication_date=date(2026, 9, 11), section="primera",
            category="RESOLUCIONES", agency="SECRETARÍA DE ENERGÍA",
            title="Resolución 238/2026", reference="RESOL-2026-238",
            description="", detail_url="https://example.test/347303",
        )
        self.assertEqual("2026_09_11_Resolución_238", document_stem(item))

    def test_non_local_electric_notice_is_discarded_after_reading(self):
        item = Publication(
            source_id="347338", publication_date=date(2026, 9, 11), section="primera",
            category="AVISOS OFICIALES", agency="SUBSECRETARÍA DE ENERGÍA ELÉCTRICA",
            title="Aviso Oficial", reference="", description="",
            detail_url="https://example.test/347338",
        )
        relevance, _ = classify(
            item, "Una generadora de Neuquén solicita una autorización en el MEM."
        )
        self.assertEqual("not_relevant", relevance)


if __name__ == "__main__":
    unittest.main()
