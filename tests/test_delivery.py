from __future__ import annotations

import smtplib
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.delivery import DeliveryError, SmtpSettings, send_eml
from epe_boletin.mail import BulletinItem, build_email_batches


def prepared_email(directory: Path) -> Path:
    pdf = directory / "document.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    item = BulletinItem(
        source_id="1", title="Resolución 1/2026", agency="Secretaría",
        publication_date="2026-09-11", conceptual_summary="Resumen",
        epesf_relationship="Relación", effective_date="Publicación",
        detail_url="https://example.test", documents=(pdf,),
    )
    output = directory / "message.eml"
    build_email_batches(
        [item], date(2026, 9, 11), output,
        sender="sender@example.test", recipients=("recipient@example.test",),
    )
    return output


class DeliveryTest(unittest.TestCase):
    def test_smtp_transport_uses_tls_login_and_message_id(self):
        class FakeSmtp:
            instance = None

            def __init__(self, host, port, timeout):
                self.events = [("connect", host, port, timeout)]
                FakeSmtp.instance = self

            def ehlo(self):
                self.events.append(("ehlo",))

            def starttls(self, context):
                self.events.append(("starttls", bool(context)))

            def login(self, username, password):
                self.events.append(("login", username, password))

            def send_message(self, message):
                self.events.append(("send", str(message["Message-ID"])))
                return {}

            def quit(self):
                self.events.append(("quit",))

        with tempfile.TemporaryDirectory() as folder:
            path = prepared_email(Path(folder))
            message_id = send_eml(
                path, SmtpSettings("smtp.example.test", 587, "user", "password"),
                smtp_factory=FakeSmtp,
            )
        events = FakeSmtp.instance.events
        self.assertTrue(message_id.startswith("<epesf-20260911-"))
        self.assertEqual(2, sum(event[0] == "ehlo" for event in events))
        self.assertIn(("login", "user", "password"), events)
        self.assertEqual("quit", events[-1][0])

    def test_disconnect_while_sending_is_reported_as_uncertain(self):
        class DisconnectingSmtp:
            def __init__(self, *args, **kwargs):
                pass

            def ehlo(self):
                pass

            def send_message(self, message):
                raise smtplib.SMTPServerDisconnected("connection lost")

            def quit(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            path = prepared_email(Path(folder))
            with self.assertRaises(DeliveryError) as raised:
                send_eml(
                    path, SmtpSettings("smtp.example.test", 25, starttls=False),
                    smtp_factory=DisconnectingSmtp,
                )
        self.assertEqual("uncertain", raised.exception.status)


if __name__ == "__main__":
    unittest.main()
