from __future__ import annotations

import re
import unittest

from epe_boletin.turso_preflight import check_turso


class TursoPreflightTest(unittest.TestCase):
    def test_read_only_queries_and_no_token_in_result(self):
        calls = []

        class Cursor:
            def __init__(self, rows):
                self.rows = rows

            def fetchone(self):
                return self.rows[0]

            def fetchall(self):
                return self.rows

        class Connection:
            def execute(self, sql):
                calls.append(sql)
                return Cursor([("3.45.0",)] if "sqlite_version" in sql else [])

            def close(self):
                calls.append("close")

        def connect(**kwargs):
            self.assertEqual("libsql://example.turso.io", kwargs["database"])
            self.assertEqual("secret", kwargs["auth_token"])
            return Connection()

        result = check_turso("libsql://example.turso.io", "secret", connect)
        self.assertEqual({"status": "ok", "engine": "libsql",
                          "sqlite_version": "3.45.0", "table_count": 0}, result)
        self.assertNotIn("secret", str(result))
        self.assertTrue(all(sql.lstrip().startswith("SELECT") for sql in calls[:-1]))
        self.assertEqual("close", calls[-1])

    def test_rejects_credential_in_url_before_connect(self):
        for url in ("http://example.turso.io", "libsql://secret@example.turso.io",
                    "libsql://example.turso.io?authToken=secret",
                    "libsql://example.invalid", ""):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_turso(url, "secret", lambda **_: self.fail("Se conectó"))

    def test_requires_token(self):
        with self.assertRaises(ValueError):
            check_turso("libsql://example.turso.io", "")

    def test_url_errors_identify_safe_cause(self):
        cases = (
            ("", "Falta TURSO_DATABASE_URL"),
            (" turso://example.turso.io", "espacios"),
            ("turso://example.turso.io", "motor Turso"),
            ("example.turso.io", "libsql://"),
            ("libsql://example.invalid", "*.turso.io"),
            ("libsql://secret@example.turso.io", "sin credenciales"),
        )
        for url, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, re.escape(expected)):
                check_turso(url, "secret", lambda **_: self.fail("Se conectó"))


if __name__ == "__main__":
    unittest.main()
