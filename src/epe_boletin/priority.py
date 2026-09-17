from __future__ import annotations

from datetime import date
from typing import Mapping

from .relevance import normalize


def publication_sort_key(item: Mapping[str, object]) -> tuple[int, int, int, str, str, str]:
    """Prioritize review within each date without changing relevance classifications."""
    relevance_rank = {
        "direct_epesf": 0,
        "potential_sector_impact": 1,
        "needs_review": 2,
        "not_relevant": 3,
    }.get(str(item["relevance"]), 2)
    agency = normalize(str(item["agency"]))
    departments = {part.strip() for part in agency.split("-")}
    if "secretaria de energia" in departments:
        agency_rank = 0
    elif (
        "ente nacional regulador de la electricidad" in agency
        or "ente nacional regulador del gas y la electricidad" in agency
        or agency in {"enre", "enrge"}
    ):
        agency_rank = 2
    else:
        agency_rank = 1
    return (
        -date.fromisoformat(str(item["publication_date"])).toordinal(),
        relevance_rank,
        agency_rank,
        agency,
        normalize(str(item["title"])),
        str(item["source_id"]),
    )
