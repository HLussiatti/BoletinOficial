from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    text: str
    page_count: int
    status: str
    error: str | None = None


def extract_pdf(path: Path) -> ExtractedDocument:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            return ExtractedDocument("", len(reader.pages), "error", "PDF cifrado")
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text = "\n\n".join(page for page in pages if page)
        status = "complete" if len(text) >= 200 else "insufficient"
        return ExtractedDocument(text, len(reader.pages), status)
    except Exception as exc:
        return ExtractedDocument("", 0, "error", str(exc))
