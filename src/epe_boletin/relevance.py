from __future__ import annotations

import re
import unicodedata

from .models import Publication

DIRECT_TERMS = (
    "epesf",
    "e.p.e.",
    "empresa provincial de la energia",
)

STRONG_SECTOR_TERMS = (
    "energia electrica",
    "mercado electrico mayorista",
    "cammesa",
    "ente nacional regulador de la electricidad",
    "generacion distribuida",
    "subsecretaria de energia electrica",
)

ELECTRIC_TERMS = ("electricidad", "electrica", "electrico")
ACTIVITY_TERMS = (
    "distribucion",
    "transporte",
    "generacion",
    "tarifa",
    "subsidio",
    "usuario",
    "potencia",
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip()


def classify(publication: Publication, full_text: str = "") -> tuple[str, str]:
    text = normalize(" ".join((publication.agency, publication.title,
                               publication.reference, publication.description,
                               full_text)))
    direct = [term for term in DIRECT_TERMS if term in text]
    if direct:
        return "direct_epesf", f"Mención directa: {', '.join(direct)}"

    strong = [term for term in STRONG_SECTOR_TERMS if term in text]
    electric = [term for term in ELECTRIC_TERMS if term in text]
    activity = [term for term in ACTIVITY_TERMS if term in text]
    if strong or (electric and activity):
        matches = strong or electric + activity
        return "potential_sector_impact", f"Indicios sectoriales: {', '.join(matches[:4])}"
    if "energia" in text or electric:
        return "needs_review", "Coincidencia relacionada que requiere revisar el texto completo"
    return "not_relevant", "Sin indicios eléctricos en los metadatos del índice"
