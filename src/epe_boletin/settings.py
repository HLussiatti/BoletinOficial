from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class SummarySettings:
    model: str
    api_key_env: str


@dataclass(frozen=True, slots=True)
class SmtpConfiguration:
    host: str
    port: int
    username: str
    password_env: str
    security: str


@dataclass(frozen=True, slots=True)
class EmailSettings:
    sender: str
    recipients: tuple[str, ...]
    max_mb: float
    smtp: SmtpConfiguration


@dataclass(frozen=True, slots=True)
class OperationSettings:
    notification_start_date: date | None
    summary: SummarySettings
    email: EmailSettings
    schedule_time: str


def load_operation_settings(path: Path) -> OperationSettings:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        summary = raw["summary"]
        email = raw["email"]
        smtp = email["smtp"]
        start = raw.get("notification_start_date")
        settings = OperationSettings(
            notification_start_date=date.fromisoformat(start) if start else None,
            summary=SummarySettings(
                model=str(summary.get("model", "")).strip(),
                api_key_env=str(summary.get("api_key_env", "OPENAI_API_KEY")).strip(),
            ),
            email=EmailSettings(
                sender=str(email.get("sender", "")).strip(),
                recipients=tuple(str(item).strip() for item in email.get("recipients", [])),
                max_mb=float(email.get("max_mb", 20)),
                smtp=SmtpConfiguration(
                    host=str(smtp.get("host", "")).strip(),
                    port=int(smtp.get("port", 587)),
                    username=str(smtp.get("username", "")).strip(),
                    password_env=str(smtp.get("password_env", "EPE_SMTP_PASSWORD")).strip(),
                    security=str(smtp.get("security", "starttls")).strip().lower(),
                ),
            ),
            schedule_time=str(raw.get("schedule_time", "05:30")).strip(),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Configuración operativa inválida: {path}") from exc
    return settings


def readiness_issues(settings: OperationSettings,
                     environment: Mapping[str, str]) -> list[str]:
    issues: list[str] = []
    if settings.notification_start_date is None:
        issues.append("Falta definir notification_start_date")
    if not settings.summary.model:
        issues.append("Falta definir summary.model")
    if not settings.summary.api_key_env or not environment.get(
        settings.summary.api_key_env
    ):
        issues.append(
            f"Falta la variable de entorno {settings.summary.api_key_env or 'OPENAI_API_KEY'}"
        )
    if not EMAIL_RE.fullmatch(settings.email.sender):
        issues.append("Falta un email.sender válido")
    if not settings.email.recipients:
        issues.append("Falta al menos un destinatario")
    elif any(not EMAIL_RE.fullmatch(value) for value in settings.email.recipients):
        issues.append("Hay destinatarios con formato inválido")
    if settings.email.max_mb <= 0:
        issues.append("email.max_mb debe ser positivo")
    smtp = settings.email.smtp
    if not smtp.host:
        issues.append("Falta definir email.smtp.host")
    if not 1 <= smtp.port <= 65535:
        issues.append("email.smtp.port está fuera de rango")
    if smtp.security not in {"starttls", "ssl", "none"}:
        issues.append("email.smtp.security debe ser starttls, ssl o none")
    if smtp.username and (not smtp.password_env or not environment.get(smtp.password_env)):
        issues.append(
            f"Falta la variable de entorno {smtp.password_env or 'EPE_SMTP_PASSWORD'}"
        )
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", settings.schedule_time):
        issues.append("schedule_time debe tener formato HH:MM")
    return issues
