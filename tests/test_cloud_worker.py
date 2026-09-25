from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.bora import NoticeContent
from epe_boletin.cloud_db import TursoDatabase
from epe_boletin.cloud_worker import execute
from epe_boletin.models import Edition, Publication
from epe_boletin.relevance import DEFAULT_RULES
from epe_boletin.summaries import ConceptualSummary


class CloudWorkerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "pilot.sqlite3"
        self.db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                                connector=lambda **_: sqlite3.connect(path))
        self.db.migrate()
        self.day = date(2026, 9, 24)
        self.item = Publication(
            source_id="123", publication_date=self.day, section="primera",
            category="RESOLUCIONES", agency="Secretaría de Energía",
            title="Resolución 1/2026", reference="RES 1/2026", description="Electricidad",
            detail_url="https://www.boletinoficial.gob.ar/detalleAviso/primera/123/20260924",
            relevance="potential_sector_impact", relevance_reason="Sector eléctrico",
        )

    def test_consult_claims_only_once_and_records_result(self):
        class Client:
            rules = DEFAULT_RULES

            def fetch_edition(inner, requested_day, fixture):
                return Edition(requested_day, (self.item,), False, 1)

            def fetch_notice(inner, publication, fixture=None):
                return NoticeContent("La resolución regula el sector eléctrico.",
                                     publication.detail_url,
                                     "https://www.boletinoficial.gob.ar/pdf/aviso/primera/123/20260924",
                                     "unknown", "none")

        job_id, created = self.db.enqueue_job("consult", self.day.isoformat(), "ana")
        self.assertTrue(created)
        self.assertEqual((job_id, False), self.db.enqueue_job("consult", self.day.isoformat(), "bea"))
        result = execute(self.db, job_id, client=Client())
        self.assertEqual(1, result["seen"])
        self.assertEqual("complete", self.db.job(job_id)["status"])
        self.assertEqual(1, self.db.status()["publications"]["total"])
        with self.assertRaisesRegex(ValueError, "no está pendiente"):
            execute(self.db, job_id, client=Client())

    def test_summary_uses_notice_and_marks_complete(self):
        publication_id = self.db.upsert_publication(self.item, False)
        self.db.save_notice(publication_id, NoticeContent(
            "La resolución regula el sector eléctrico.", self.item.detail_url,
            "https://www.boletinoficial.gob.ar/pdf/aviso/primera/123/20260924",
            "unknown", "none"))

        class Summarizer:
            def summarize(self, candidate):
                self_candidate = candidate
                assert self_candidate.publication_id == publication_id
                return ConceptualSummary("Regula el sector", "Posible efecto en EPESF",
                                         "No indicada", True)

        job_id, _ = self.db.enqueue_job("summary", str(publication_id), "ana")
        result = execute(self.db, job_id, summarizer=Summarizer())
        self.assertEqual(publication_id, result["publication_id"])
        self.assertEqual("complete", self.db.job(job_id)["status"])
        self.assertEqual(1, self.db.status()["summaries"]["ready"])

    def test_failed_summary_releases_active_slot(self):
        job_id, _ = self.db.enqueue_job("summary", "999", "ana")
        with self.assertRaisesRegex(ValueError, "no admite resumen"):
            execute(self.db, job_id)
        self.assertEqual("failed", self.db.job(job_id)["status"])
        next_id, created = self.db.enqueue_job("summary", "999", "ana")
        self.assertTrue(created)
        self.assertNotEqual(job_id, next_id)

    def test_abandoned_request_can_be_retried(self):
        job_id, _ = self.db.enqueue_job("consult", "2026-09-23", "ana")
        with self.db.connect() as connection:
            connection.execute("UPDATE cloud_jobs SET created_at='2020-01-01T00:00:00+00:00' WHERE id=?",
                               (job_id,))
        next_id, created = self.db.enqueue_job("consult", "2026-09-23", "ana")
        self.assertTrue(created)
        self.assertNotEqual(job_id, next_id)
        self.assertEqual("failed", self.db.job(job_id)["status"])


if __name__ == "__main__":
    unittest.main()
