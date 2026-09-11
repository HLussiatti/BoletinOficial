from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from epe_boletin.backup import create_backup, restore_backup
from epe_boletin.db import Database


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
            rules = root / "rules.json"
            rules.write_text('{"version":"test"}', encoding="utf-8")
            output = root / "backup.zip"

            result = create_backup(data, output, rules)

            self.assertEqual(3, result["files"])
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))
                restored_db = root / "restored.sqlite3"
                restored_db.write_bytes(archive.read("boletin.sqlite3"))
            self.assertIn("documents/2026/09/sample.pdf", names)
            self.assertIn("config/relevance_rules.json", names)
            self.assertEqual(3, len(manifest["files"]))
            restored = Database(restored_db)
            self.assertEqual(date(2026, 9, 11), restored.last_complete_date())

            restored_dir = root / "restored-data"
            restore_result = restore_backup(output, restored_dir)
            self.assertEqual(3, restore_result["files"])
            restored = Database(restored_dir / "boletin.sqlite3")
            self.assertEqual(date(2026, 9, 11), restored.last_complete_date())
            self.assertEqual(
                document.read_bytes(),
                (restored_dir / "documents" / "2026" / "09" / "sample.pdf").read_bytes(),
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
