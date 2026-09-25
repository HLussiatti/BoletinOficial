from __future__ import annotations

import io
import csv
import json
import re
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from epe_boletin.cloud_auth import CloudAuth, main as auth_main, password_hash
from epe_boletin.cloud_db import TursoDatabase
from epe_boletin.cloud_web import CloudWeb


class CloudAuthCliTest(unittest.TestCase):
    def test_generates_one_json_for_three_users(self):
        output = io.StringIO()
        with patch("sys.argv", ["cloud_auth", "--user", "ana", "--user", "bea",
                                "--user", "caro"]), \
             patch("epe_boletin.cloud_auth.getpass", side_effect=[
                 "clave-ana", "clave-ana", "clave-bea", "clave-bea",
                 "clave-caro", "clave-caro"]), redirect_stdout(output):
            auth_main()
        users = json.loads(output.getvalue())
        self.assertEqual({"ana", "bea", "caro"}, set(users))
        auth = CloudAuth(users, "session-secret-for-tests-at-least-32-characters")
        self.assertTrue(auth.verify_password("caro", "clave-caro"))
        with self.assertRaises(ValueError):
            CloudAuth({}, "session-secret-for-tests-at-least-32-characters")


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
            "caro": password_hash("tercera-clave-larga", salt=b"3" * 16),
        }, "session-secret-for-tests-at-least-32-characters")
        self.app = CloudWeb(self.db, self.auth)

    def request(self, query="", *, method="GET", data=None, cookie="",
                origin="http://localhost:8000", fetch_site=""):
        body = urlencode(data or {}, doseq=True).encode() if data is not None else b""
        environ = {"REQUEST_METHOD": method, "QUERY_STRING": query,
                   "HTTP_HOST": "localhost:8000", "HTTP_ORIGIN": origin,
                   "HTTP_SEC_FETCH_SITE": fetch_site,
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

    def login_form(self):
        page = self.request()
        match = re.search(rb'name="login_csrf" value="([^"]+)"', page["body"])
        self.assertIsNotNone(match)
        return page["headers"]["Set-Cookie"].split(";", 1)[0], match.group(1).decode()

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
        login_cookie, login_csrf = self.login_form()
        wrong = self.request("action=login", method="POST", cookie=login_cookie,
                             data={"user": "ana", "password": "incorrecta",
                                   "login_csrf": login_csrf})
        self.assertEqual(401, int(wrong["status"][:3]))
        login_cookie, login_csrf = self.login_form()
        login = self.request("action=login", method="POST", cookie=login_cookie,
                             data={"user": "ana", "password": "clave-de-prueba-larga",
                                   "login_csrf": login_csrf})
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

        login_cookie, login_csrf = self.login_form()
        third_login = self.request("action=login", method="POST", cookie=login_cookie,
                                   data={"user": "caro", "password": "tercera-clave-larga",
                                         "login_csrf": login_csrf})
        self.assertEqual(303, int(third_login["status"][:3]))
        third_cookie = third_login["headers"]["Set-Cookie"].split(";", 1)[0]
        self.assertIn(b"Resoluci", self.request(cookie=third_cookie)["body"])

    def test_login_requires_cookie_bound_token_without_request_headers(self):
        login_cookie, login_csrf = self.login_form()
        login = self.request("action=login", method="POST", origin="", cookie=login_cookie,
                             data={"user": "ana", "password": "clave-de-prueba-larga",
                                   "login_csrf": login_csrf})
        self.assertEqual(303, int(login["status"][:3]))
        missing_token = self.request("action=login", method="POST", cookie=login_cookie,
                                     data={"user": "ana", "password": "clave-de-prueba-larga"})
        self.assertEqual(403, int(missing_token["status"][:3]))
        missing_cookie = self.request("action=login", method="POST", origin="",
                                      data={"user": "ana", "password": "clave-de-prueba-larga",
                                            "login_csrf": login_csrf})
        self.assertEqual(403, int(missing_cookie["status"][:3]))
        tampered_token = self.request("action=login", method="POST", cookie=login_cookie,
                                      data={"user": "ana", "password": "clave-de-prueba-larga",
                                            "login_csrf": login_csrf + "x"})
        self.assertEqual(403, int(tampered_token["status"][:3]))

    def test_draft_is_in_memory_and_rejects_csrf_or_other_day(self):
        ticket = self.ticket()
        cookie = "epe_session=" + ticket
        body = {"date": "2026-09-24", "selected": [str(self.publication_id)],
                "csrf": self.auth.csrf_token(ticket)}
        denied = self.request("action=draft", method="POST", cookie=cookie,
                              data={**body, "csrf": "wrong"})
        self.assertEqual(403, int(denied["status"][:3]))
        wrong_day = self.request("action=draft", method="POST", cookie=cookie,
                                 data={**body, "date": "2026-09-23"})
        self.assertEqual(400, int(wrong_day["status"][:3]))
        draft = self.request("action=draft", method="POST", cookie=cookie,
                             origin="", data=body)
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

    def test_local_style_views_range_category_calendar_and_selected_csv(self):
        with self.db.connect() as connection:
            connection.execute("""
                INSERT INTO publications(source,source_id,publication_date,section,
                    category,agency,title,reference,description,detail_url,
                    relevance,relevance_reason,first_seen_at,last_seen_at)
                VALUES('BORA','124','2026-09-23','primera','DISPOSICIONES',
                    'Organismo de prueba','Disposición de prueba','DISP 2/2026',
                    'Texto de prueba','https://www.boletinoficial.gob.ar/detalleAviso/primera/124/20260923',
                    'needs_review','Pendiente','2026-09-23T10:00:00','2026-09-23T10:00:00')
            """)
            connection.execute("""
                INSERT INTO coverage(source,publication_date,status,checked_at,error)
                VALUES('BORA','2026-09-22','failed','2026-09-22T10:00:00','Prueba de falla')
            """)
            connection.execute("UPDATE publications SET summary_status='error' WHERE id=?",
                               (self.publication_id,))
        cookie = "epe_session=" + self.ticket()
        day = self.request("date=2026-09-24", cookie=cookie)
        self.assertEqual(200, int(day["status"][:3]))
        self.assertIn(b'class="topbar"', day["body"])
        self.assertIn(b'class="metrics"', day["body"])
        self.assertIn(b'class="column-head"', day["body"])
        self.assertIn("script-src 'self'", day["headers"]["Content-Security-Policy"])
        period = self.request("date=2026-09-23&to=2026-09-24", cookie=cookie)
        self.assertIn(b"Disposici", period["body"])
        self.assertIn(b"Resoluci", period["body"])
        category = self.request("date=2026-09-23&to=2026-09-24&category=DISPOSICIONES", cookie=cookie)
        self.assertIn(b"Disposici", category["body"])
        self.assertNotIn(b"Resoluci\xc3\xb3n de prueba", category["body"])
        calendar = self.request("view=history&month=2026-09", cookie=cookie)
        self.assertEqual(200, int(calendar["status"][:3]))
        self.assertIn(b'class="calendar-grid"', calendar["body"])
        failures = self.request("view=failures", cookie=cookie)
        self.assertIn(b"Prueba de falla", failures["body"])
        self.assertIn(b"Revisar: resumen", failures["body"])
        selected = self.request(f"date=2026-09-24&action=export&selected={self.publication_id}", cookie=cookie)
        self.assertEqual(200, int(selected["status"][:3]))
        self.assertEqual(1, len(list(csv.DictReader(io.StringIO(selected["body"].decode("utf-8-sig"))))))
        script = self.request("action=ui", cookie=cookie)
        self.assertEqual("text/javascript; charset=utf-8", script["headers"]["Content-Type"])
        self.assertIn(b"range-picker", script["body"])
        self.assertNotIn(b"/prepare-email", script["body"])


if __name__ == "__main__":
    unittest.main()
