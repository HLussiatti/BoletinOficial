from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BulletinItem:
    source_id: str
    title: str
    agency: str
    publication_date: str
    conceptual_summary: str
    epesf_relationship: str
    effective_date: str
    detail_url: str
    documents: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class EmailArtifact:
    path: Path
    item_count: int
    attachment_count: int
    byte_size: int


def _message(items: list[BulletinItem], day: date, sender: str,
             recipients: tuple[str, ...], batch: int, total_batches: int) -> EmailMessage:
    message = EmailMessage()
    suffix = f" ({batch}/{total_batches})" if total_batches > 1 else ""
    message["Subject"] = (
        f"EPESF | Novedades normativas nacionales | {day:%d/%m/%Y}{suffix}"
    )
    message["From"] = sender
    if recipients:
        message["To"] = ", ".join(recipients)

    plain_parts = [
        f"Novedades normativas nacionales publicadas el {day:%d/%m/%Y}.",
        f"Publicaciones seleccionadas: {len(items)}.",
    ]
    html_parts = [
        "<h1>Novedades normativas nacionales</h1>",
        f"<p>Publicadas el {day:%d/%m/%Y}. "
        f"Se seleccionaron {len(items)} publicaciones.</p>",
    ]
    for item in items:
        plain_parts.extend([
            "", item.title, item.agency, item.conceptual_summary,
            f"Relación con EPESF: {item.epesf_relationship}",
            f"Vigencia: {item.effective_date}", f"Fuente: {item.detail_url}",
        ])
        html_parts.extend([
            f"<h2>{html.escape(item.title)}</h2>",
            f"<p><strong>{html.escape(item.agency)}</strong></p>",
            f"<p>{html.escape(item.conceptual_summary)}</p>",
            "<p><strong>Relación con EPESF:</strong> "
            f"{html.escape(item.epesf_relationship)}</p>",
            f"<p><strong>Vigencia:</strong> {html.escape(item.effective_date)}</p>",
            f'<p><a href="{html.escape(item.detail_url, quote=True)}">Fuente oficial</a></p>',
        ])
    message.set_content("\n".join(plain_parts))
    message.add_alternative("\n".join(html_parts), subtype="html")
    for item in items:
        for path in item.documents:
            content = path.read_bytes()
            message.add_attachment(
                content, maintype="application", subtype="pdf", filename=path.name
            )
    return message


def build_email_batches(items: list[BulletinItem], day: date, output: Path,
                        sender: str = "boletin-epesf@localhost",
                        recipients: tuple[str, ...] = (),
                        max_bytes: int = 20 * 1024 * 1024) -> list[EmailArtifact]:
    if not items:
        raise ValueError("No hay publicaciones resumidas para preparar el correo")
    for item in items:
        for path in item.documents:
            if not path.is_file():
                raise FileNotFoundError(f"No se encontró el adjunto: {path}")

    batches: list[list[BulletinItem]] = []
    current: list[BulletinItem] = []
    for item in items:
        proposal = [*current, item]
        if len(_message(proposal, day, sender, recipients, 1, 1).as_bytes()) <= max_bytes:
            current = proposal
            continue
        if not current:
            raise ValueError(f"Los adjuntos de {item.title} exceden el límite del correo")
        batches.append(current)
        current = [item]
        if len(_message(current, day, sender, recipients, 1, 1).as_bytes()) > max_bytes:
            raise ValueError(f"Los adjuntos de {item.title} exceden el límite del correo")
    if current:
        batches.append(current)

    output.parent.mkdir(parents=True, exist_ok=True)
    artifacts: list[EmailArtifact] = []
    total = len(batches)
    for index, batch_items in enumerate(batches, 1):
        path = output if total == 1 else output.with_name(
            f"{output.stem}_{index}_de_{total}{output.suffix or '.eml'}"
        )
        message = _message(batch_items, day, sender, recipients, index, total)
        content = message.as_bytes()
        path.write_bytes(content)
        artifacts.append(EmailArtifact(
            path=path, item_count=len(batch_items),
            attachment_count=sum(len(item.documents) for item in batch_items),
            byte_size=len(content),
        ))
    return artifacts
