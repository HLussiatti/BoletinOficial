from __future__ import annotations

import html
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from email.parser import BytesHeaderParser
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
    message_id: str
    source_ids: tuple[str, ...]


def ensure_editable_draft(path: Path) -> None:
    """Upgrade an older generated .eml before reopening it in a mail client."""
    temporary_name = ""
    try:
        with path.open("rb") as source:
            headers = BytesHeaderParser().parse(source)
            if headers.get("X-Unsent") == "1":
                return
            if "X-Unsent" in headers:
                raise OSError("El borrador tiene una cabecera X-Unsent no compatible. Generá nuevamente el correo.")
            source.seek(0)
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as target:
                temporary_name = target.name
                target.write(b"X-Unsent: 1\r\n")
                shutil.copyfileobj(source, target)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _message(items: list[BulletinItem], day: date, sender: str,
             recipients: tuple[str, ...], batch: int, total_batches: int) -> EmailMessage:
    message = EmailMessage()
    # Thunderbird and other mail clients open saved .eml files for editing when
    # they carry this header; otherwise they display them as received messages.
    message["X-Unsent"] = "1"
    suffix = f" ({batch}/{total_batches})" if total_batches > 1 else ""
    message["Subject"] = (
        f"EPESF | Novedades normativas nacionales | {day:%d/%m/%Y}{suffix}"
    )
    if sender:
        message["From"] = sender
    fingerprint = hashlib.sha256("|".join(
        f"{item.source_id}:{item.conceptual_summary}:{item.epesf_relationship}"
        for item in items
    ).encode("utf-8")).hexdigest()[:16]
    domain = sender.rsplit("@", 1)[-1] if "@" in sender else "localhost"
    message["Message-ID"] = f"<epesf-{day:%Y%m%d}-{batch}-{fingerprint}@{domain}>"
    if recipients:
        message["To"] = ", ".join(recipients)

    plain_parts: list[str] = []
    html_parts: list[str] = []
    for item in items:
        plain_parts.extend([
            item.title, item.agency, item.conceptual_summary,
            f"Relación con EPESF: {item.epesf_relationship}",
            f"Vigencia: {item.effective_date}", f"Fuente: {item.detail_url}",
        ])
        plain_parts.append("")
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
                        sender: str = "",
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
            message_id=str(message["Message-ID"]),
            source_ids=tuple(item.source_id for item in batch_items),
        ))
    return artifacts
