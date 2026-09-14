from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SummarySettings:
    provider: str
    model: str
    api_key_env: str


@dataclass(frozen=True, slots=True)
class EmailSettings:
    max_mb: float


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
        start = raw.get("notification_start_date")
        settings = OperationSettings(
            notification_start_date=date.fromisoformat(start) if start else None,
            summary=SummarySettings(
                provider=str(summary.get("provider", "gemini")).strip().lower(),
                model=str(summary.get("model", "")).strip(),
                api_key_env=str(summary.get("api_key_env", "GEMINI_API_KEY")).strip(),
            ),
            email=EmailSettings(
                max_mb=float(email.get("max_mb", 20)),
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
    if settings.summary.provider not in {"gemini", "openai"}:
        issues.append("summary.provider debe ser gemini u openai")
    if not settings.summary.api_key_env or not environment.get(
        settings.summary.api_key_env
    ):
        issues.append(
            f"Falta la variable de entorno {settings.summary.api_key_env or 'GEMINI_API_KEY'}"
        )
    if settings.email.max_mb <= 0:
        issues.append("email.max_mb debe ser positivo")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", settings.schedule_time):
        issues.append("schedule_time debe tener formato HH:MM")
    return issues
