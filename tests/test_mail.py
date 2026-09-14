from __future__ import annotations

import tempfile
import unittest
from datetime import date
from email import policy
from email.parser import BytesParser
from pathlib import Path

from epe_boletin.mail import BulletinItem, build_email_batches


class MailTest(unittest.TestCase):
    def test_eml_contains_summary_source_and_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            pdf = directory / "2026_09_11_Resolución_10.pdf"
            pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            item = BulletinItem(
                source_id="10", title="Resolución 10/2026",
                agency="Secretaría de Energía", publication_date="2026-09-11",
                conceptual_summary="Establece un régimen eléctrico.",
                epesf_relationship="Puede incidir en la distribuidora.",
                effective_date="Desde su publicación.",
                detail_url="https://example.test/10", documents=(pdf,),
            )
            output = directory / "boletin.eml"
            artifacts = build_email_batches(
                [item], date(2026, 9, 11), output,
                recipients=("prueba@example.test",),
            )
            message = BytesParser(policy=policy.default).parsebytes(output.read_bytes())
            attachments = list(message.iter_attachments())
            self.assertEqual(1, len(artifacts))
            self.assertEqual(str(message["Message-ID"]), artifacts[0].message_id)
            self.assertEqual(("10",), artifacts[0].source_ids)
            self.assertEqual("prueba@example.test", message["To"])
            self.assertIsNone(message["From"])
            self.assertIn("Resolución 10/2026", message.get_body(preferencelist=("plain",)).get_content())
            self.assertEqual(pdf.name, attachments[0].get_filename())

    def test_oversized_batches_are_split_by_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            items = []
            for number in (1, 2):
                pdf = directory / f"document_{number}.pdf"
                pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 800 + b"%%EOF\n")
                items.append(BulletinItem(
                    source_id=str(number), title=f"Resolución {number}/2026",
                    agency="Secretaría", publication_date="2026-09-11",
                    conceptual_summary="Resumen", epesf_relationship="Relación",
                    effective_date="Vigencia", detail_url="https://example.test",
                    documents=(pdf,),
                ))
            single_size = len(build_email_batches(
                [items[0]], date(2026, 9, 11), directory / "single.eml"
            )[0].path.read_bytes())
            artifacts = build_email_batches(
                items, date(2026, 9, 11), directory / "split.eml",
                max_bytes=single_size + 100,
            )
            self.assertEqual(2, len(artifacts))
            self.assertTrue(artifacts[0].path.name.endswith("_1_de_2.eml"))


if __name__ == "__main__":
    unittest.main()
