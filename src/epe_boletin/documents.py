from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class DocumentSection:
    section_type: str
    ordinal: int
    heading: str
    text: str
    page_from: int
    page_to: int


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    text: str
    page_count: int
    status: str
    error: str | None = None
    sections: tuple[DocumentSection, ...] = ()


CONSIDERATIONS_RE = re.compile(r"(?im)^\s*CONSIDERANDO\s*:\s*$")
DISPOSITIVE_RE = re.compile(
    r"(?im)^\s*(?P<heading>RESUELVE|DECRETA|DISPONE|DECIDE)\s*:\s*$"
)
ARTICLE_RE = re.compile(
    r"(?im)^\s*(?P<heading>ART[IÍ]CULO\s+"
    r"(?P<number>\d+|[IVXLCDM]+|[ÚU]NICO)[º°°]?)\s*[.\-–—]*\s*"
)


def structure_pages(pages: tuple[str, ...]) -> tuple[DocumentSection, ...]:
    if not pages:
        return ()
    page_starts: list[int] = []
    parts: list[str] = []
    offset = 0
    for page in pages:
        if parts:
            parts.append("\n\n")
            offset += 2
        page_starts.append(offset)
        parts.append(page)
        offset += len(page)
    text = "".join(parts)

    def page_for(position: int) -> int:
        return bisect.bisect_right(page_starts, max(position, 0))

    def build(section_type: str, ordinal: int, heading: str,
              start: int, end: int) -> DocumentSection | None:
        content = text[start:end].strip()
        if not content:
            return None
        content_start = text.find(content, start, end)
        content_end = content_start + len(content) - 1
        return DocumentSection(
            section_type, ordinal, heading, content,
            page_for(content_start), page_for(content_end),
        )

    sections: list[DocumentSection] = []
    considerations = CONSIDERATIONS_RE.search(text)
    dispositive = DISPOSITIVE_RE.search(text)
    if considerations and dispositive and considerations.end() < dispositive.start():
        section = build(
            "considerations", 1, "CONSIDERANDO",
            considerations.end(), dispositive.start(),
        )
        if section:
            sections.append(section)
    if dispositive:
        section = build(
            "dispositive", 1, dispositive.group("heading").upper(),
            dispositive.start(), len(text),
        )
        if section:
            sections.append(section)
        matches = list(ARTICLE_RE.finditer(text, dispositive.end()))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = build(
                "article", index + 1, match.group("heading").upper(),
                match.start(), end,
            )
            if section:
                sections.append(section)
    return tuple(sections)


def extract_pdf(path: Path) -> ExtractedDocument:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            return ExtractedDocument("", len(reader.pages), "error", "PDF cifrado")
        pages = tuple((page.extract_text() or "").strip() for page in reader.pages)
        text = "\n\n".join(page for page in pages if page)
        status = "complete" if len(text) >= 200 else "insufficient"
        return ExtractedDocument(
            text, len(reader.pages), status, sections=structure_pages(pages)
        )
    except Exception as exc:
        return ExtractedDocument("", 0, "error", str(exc))
