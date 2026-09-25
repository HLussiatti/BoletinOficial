from __future__ import annotations

import io
import csv
import sqlite3
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlencode

from epe_boletin.cloud_auth import CloudAuth, password_hash
from epe_boletin.cloud_db import TursoDatabase
from epe_boletin.cloud_web import CloudWeb


class CloudWebTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "cloud.sqlite3"
        self.db = TursoDatabase("libsql://pilot.turso.io", "test-token",
                                connector=lambda **_: sqlite3.connect(path))
        self.db.migrate()
        with self.db.connect() as connection:
            connection.execute("""
                INSERT INTO publications(source,source_id,publication_date,section,
                    category,agency,title,reference,description,detail_url,
                    relevance,relevance_reason,first_seen_at,last_seen_at)
                VALUES('BORA','123','2026-09-24','primera','RESOLUCIONES',
                    'Secretaría de Energía','Resolución de prueba','RES 1/2026',
                    'Texto eléctrico','https://www.boletinoficial.gob.ar/detalleAviso/primera/123/20260924',
                    'direct_epesf','Energía','2026-09-24T10:00:00','2026-09-24T10:00:00')
            """)
            publication_id = connection.execute("SELECT id FROM publications").fetchone()["id"]
            connection.execute("""
                INSERT INTO summaries(publication_id,conceptual_summary,
                    epesf_relationship,effective_date,model,prompt_version,
                    source_sha256,created_at,status)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (publication_id, "Resumen sintético", "Incide en EPESF", "No indicada",
                  "test-model", "test", "a" * 64, "2026-09-24T10:10:00", "complete"))
        self.publication_id = int(publication_id)
        self.auth = CloudAuth({
            "ana": password_hash("clave-de-prueba-larga", salt=b"1" * 16),
            "bea": password_hash("segunda-clave-larga", salt=b"2" * 16),
        }, "session-secret-for-tests-at-least-32-characters")
        self.app = CloudWeb(self.db, self.auth)

    def request(self, query="", *, method="GET", data=None, cookie="", origin="http://localhost:8000"):
        body = urlencode(data or {}, doseq=True).encode() if data is not None else b""
        environ = {"REQUEST_METHOD": method, "QUERY_STRING": query,
                   "HTTP_HOST": "localhost:8000", "HTTP_ORIGIN": origin,
                   "HTTP_COOKIE": cookie, "CONTENT_LENGTH": str(len(body)),
                   "wsgi.input": io.BytesIO(body)}
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)
        captured["body"] = b"".join(self.app(environ, start_response))
        return captured

    def ticket(self):
        return self.auth.new_ticket("ana")

    def test_access_requires_login_and_tampered_cookie_is_rejected(self):
        anonymous = self.request()
        self.assertEqual(200, int(anonymous["status"][:3]))
        self.assertIn(b"Contrase", anonymous["body"])
        self.assertNotIn(b"Resoluci", anonymous["body"])
        self.assertEqual("no-store", anonymous["headers"]["Cache-Control"])
        bad = self.request(cookie="epe_session=" + self.ticket() + "tampered")
        self.assertIn(b"Ingresar", bad["body"])
        self.assertNotIn(b"Resoluci", bad["body"])

    def test_login_filter_export_and_logout(self):
        wrong = self.request("action=login", method="POST",
                             data={"user": "ana", "password": "incorrecta"})
        self.assertEqual(401, int(wrong["status"][:3]))
        login = self.request("action=login", method="POST",
                             data={"user": "ana", "password": "clave-de-prueba-larga"})
        self.assertEqual(303, int(login["status"][:3]))
        self.assertIn("HttpOnly", login["headers"]["Set-Cookie"])
        self.assertIn("Secure", login["headers"]["Set-Cookie"])
        ticket = login["headers"]["Set-Cookie"].split(";", 1)[0]
        listing = self.request("date=2026-09-24", cookie=ticket)
        self.assertEqual(200, int(listing["status"][:3]))
        self.assertIn(b"Resoluci", listing["body"])
        self.assertIn(b"Resumen sint", listing["body"])
        self.assertIn(b"boletinoficial.gob.ar", listing["body"])
        no_matches = self.request("date=2026-09-24&q=ausente", cookie=ticket)
        self.assertIn(b"0 publicaciones", no_matches["body"])
        export = self.request("date=2026-09-24&action=export", cookie=ticket)
        self.assertEqual("text/csv; charset=utf-8", export["headers"]["Content-Type"])
        self.assertIn(b"Resumen sint", export["body"])
        logout = self.request("action=logout", method="POST", cookie=ticket,
                              data={"csrf": self.auth.csrf_token(ticket.split("=", 1)[1])})
        self.assertEqual(303, int(logout["status"][:3]))
        self.assertIn("Max-Age=0", logout["headers"]["Set-Cookie"])

    def test_draft_is_in_memory_and_rejects_csrf_or_other_day(self):
        ticket = self.ticket()
        cookie = "epe_session=" + ticket
        body = {"date": "2026-09-24", "selected": [str(self.publication_id)],
                "csrf": self.auth.csrf_token(ticket)}
        denied = self.request("action=draft", method="POST", cookie=cookie,
                              data={**body, "csrf": "wrong"})
        self.assertEqual(403, int(denied["status"][:3]))
        denied_origin = self.request("action=draft", method="POST", cookie=cookie,
                                     data=body, origin="https://example.invalid")
        self.assertEqual(403, int(denied_origin["status"][:3]))
        wrong_day = self.request("action=draft", method="POST", cookie=cookie,
                                 data={**body, "date": "2026-09-23"})
        self.assertEqual(400, int(wrong_day["status"][:3]))
        draft = self.request("action=draft", method="POST", cookie=cookie, data=body)
        self.assertEqual(200, int(draft["status"][:3]))
        self.assertEqual("message/rfc822", draft["headers"]["Content-Type"])
        self.assertIn("attachment;", draft["headers"]["Content-Disposition"])
        message = BytesParser(policy=policy.default).parsebytes(draft["body"])
        self.assertEqual("1", message["X-Unsent"])
        self.assertIn("Resumen sintético", message.get_body(preferencelist=("plain",)).get_content())
        self.assertFalse(list(message.iter_attachments()))
        self.assertEqual([], list(Path(self.temp.name).glob("*.eml")))

    def test_csv_escapes_spreadsheet_formulas_and_session_expires(self):
        ticket = self.auth.new_ticket("ana", now=100)
        self.assertEqual("ana", self.auth.ticket_user(ticket, now=101))
        self.assertIsNone(self.auth.ticket_user(ticket, now=100 + 12 * 60 * 60))
        with self.db.connect() as connection:
            connection.execute("UPDATE publications SET title='=2+2' WHERE id=?",
                               (self.publication_id,))
        result = self.request("date=2026-09-24&action=export",
                              cookie="epe_session=" + self.ticket())
        rows = list(csv.DictReader(io.StringIO(result["body"].decode("utf-8-sig"))))
        self.assertEqual("'=2+2", rows[0]["titulo"])


if __name__ == "__main__":
    unittest.main()
