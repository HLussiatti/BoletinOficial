from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Publication:
    source_id: str
    publication_date: date
    section: str
    category: str
    agency: str
    title: str
    reference: str
    description: str
    detail_url: str
    has_annexes: bool = False
    relevance: str = "pending"
    relevance_reason: str = ""


@dataclass(frozen=True, slots=True)
class Edition:
    publication_date: date
    publications: tuple[Publication, ...]
    has_supplement: bool
    pages_fetched: int


@dataclass(frozen=True, slots=True)
class Annex:
    number: str
    source_id: str
    publication_date: date
    section: str
    endpoint: str

    @property
    def kind(self) -> str:
        return f"annex:{self.number}:{self.source_id}"
