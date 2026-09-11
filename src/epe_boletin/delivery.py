from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path


class DeliveryError(RuntimeError):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True, slots=True)
class SmtpSettings:
    host: str
    port: int
    username: str = ""
    password: str = ""
    starttls: bool = True
    ssl: bool = False
    timeout: float = 60


def send_eml(path: Path, settings: SmtpSettings, smtp_factory=None) -> str:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    message_id = str(message.get("Message-ID", "")).strip()
    if not message_id:
        raise DeliveryError("El correo no tiene Message-ID")
    if not message.get("From") or not message.get_all("To", []):
        raise DeliveryError("El correo debe tener remitente y destinatarios")
    if settings.ssl and settings.starttls:
        raise DeliveryError("Use SSL directo o STARTTLS, no ambos")
    factory = smtp_factory or (smtplib.SMTP_SSL if settings.ssl else smtplib.SMTP)
    connection = None
    sending = False
    try:
        connection = factory(settings.host, settings.port, timeout=settings.timeout)
        connection.ehlo()
        if settings.starttls:
            connection.starttls(context=ssl.create_default_context())
            connection.ehlo()
        if settings.username:
            connection.login(settings.username, settings.password)
        sending = True
        refused = connection.send_message(message)
        sending = False
        if refused:
            raise DeliveryError(
                f"El servidor rechazó {len(refused)} destinatarios", "error"
            )
        return message_id
    except DeliveryError:
        raise
    except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as exc:
        status = "uncertain" if sending else "error"
        raise DeliveryError(f"Falló la conexión SMTP: {exc}", status) from exc
    except smtplib.SMTPException as exc:
        raise DeliveryError(f"El servidor SMTP rechazó el envío: {exc}") from exc
    finally:
        if connection is not None:
            try:
                connection.quit()
            except (smtplib.SMTPException, OSError):
                pass
