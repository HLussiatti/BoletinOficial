from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from epe_boletin.backup import create_backup, restore_backup
from epe_boletin.db import Database
from epe_boletin.models import Publication


class BackupTest(unittest.TestCase):
    def test_backup_contains_consistent_database_documents_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / "data"
            database = Database(data / "boletin.sqlite3")
            database.migrate()
            database.save_coverage(date(2026, 9, 11), "complete", 1, 90)
            document = data / "documents" / "2026" / "09" / "sample.pdf"
            document.parent.mkdir(parents=True)
            document.write_bytes(b"%PDF-1.4\n%%EOF\n")
            item = Publication(
                "test-1", date(2026, 9, 11), "Primera", "Resolución",
                "Organismo", "Prueba", "1/2026", "", "https://example.test",
            )
            publication_id = database.upsert_publications(((item, True),))["test-1"]
            database.save_document(
                publication_id,
                Path("var/operacion/documents/2026/09/sample.pdf"),
                hashlib.sha256(document.read_bytes()).hexdigest(),
                document.stat().st_size, "https://example.test",
            )
            outbox = data / "outbox" / "draft.eml"
            outbox.parent.mkdir()
            outbox.write_text("Subject: Prueba\n", encoding="utf-8")
            with database.connect() as connection:
                connection.execute("""
                    INSERT INTO deliveries(message_id,publication_date,batch_number,
                        total_batches,path,recipients_json,status,created_at)
                    VALUES(?,?,?,?,?,?,?,?)
                """, ("test@example.test", "2026-09-11", 1, 1,
                      "var/operacion/outbox/draft.eml", "[]", "prepared",
                      "2026-09-11T00:00:00+00:00"))
            rules = root / "rules.json"
            rules.write_text('{"version":"test"}', encoding="utf-8")
            output = root / "backup.zip"

            result = create_backup(data, output, rules)

            self.assertEqual(4, result["files"])
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))
                restored_db = root / "restored.sqlite3"
                restored_db.write_bytes(archive.read("boletin.sqlite3"))
            self.assertIn("documents/2026/09/sample.pdf", names)
            self.assertIn("outbox/draft.eml", names)
            self.assertIn("config/relevance_rules.json", names)
            self.assertEqual(4, len(manifest["files"]))
            restored = Database(restored_db)
            self.assertEqual(date(2026, 9, 11), restored.last_complete_date())

            restored_dir = root / "restored-data"
            restore_result = restore_backup(output, restored_dir)
            self.assertEqual(4, restore_result["files"])
            restored = Database(restored_dir / "boletin.sqlite3")
            self.assertEqual(date(2026, 9, 11), restored.last_complete_date())
            self.assertEqual(
                document.read_bytes(),
                (restored_dir / "documents" / "2026" / "09" / "sample.pdf").read_bytes(),
            )
            with restored.connect() as connection:
                document_path = connection.execute(
                    "SELECT path FROM documents"
                ).fetchone()["path"]
                email_path = connection.execute(
                    "SELECT path FROM deliveries"
                ).fetchone()["path"]
            self.assertEqual(
                (restored_dir / "documents/2026/09/sample.pdf").resolve(),
                Path(document_path).resolve(),
            )
            self.assertEqual(
                (restored_dir / "outbox/draft.eml").resolve(),
                Path(email_path).resolve(),
            )

    def test_restore_rejects_a_modified_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / "data"
            database = Database(data / "boletin.sqlite3")
            database.migrate()
            original = root / "original.zip"
            create_backup(data, original)
            damaged = root / "damaged.zip"
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(damaged, "w") as target:
                for info in source.infolist():
                    content = source.read(info.filename)
                    if info.filename == "boletin.sqlite3":
                        content += b"damage"
                    target.writestr(info, content)
            with self.assertRaisesRegex(ValueError, "Tamaño inválido"):
                restore_backup(damaged, root / "restored")


if __name__ == "__main__":
    unittest.main()
