from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .models import Publication

@dataclass(frozen=True, slots=True)
class RelevanceRules:
    version: str
    direct_terms: tuple[str, ...]
    strong_sector_terms: tuple[str, ...]
    electric_terms: tuple[str, ...]
    activity_terms: tuple[str, ...]
    local_terms: tuple[str, ...]
    discard_nonlocal_official_notices: bool = True


DEFAULT_RULES = RelevanceRules(
    version="builtin-2026-09-14.1",
    direct_terms=(
        "epesf", "e.p.e.", "empresa provincial de la energia de santa fe",
    ),
    strong_sector_terms=(
        "energia electrica", "mercado electrico mayorista", "cammesa",
        "ente nacional regulador de la electricidad", "generacion distribuida",
        "subsecretaria de energia electrica",
        "subsidios energeticos focalizados",
        "subsecretaria de transicion y planeamiento energetico",
        "emergencia del sector energetico nacional",
    ),
    electric_terms=("electricidad", "electrica", "electrico"),
    activity_terms=(
        "distribucion", "transporte", "generacion", "tarifa", "subsidio",
        "usuario", "potencia",
    ),
    local_terms=("santa fe", "epesf", "e.p.e."),
)


def load_rules(path: Path) -> RelevanceRules:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer la configuración de reglas: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("La configuración de reglas debe ser un objeto JSON")

    def terms(name: str) -> tuple[str, ...]:
        value = payload.get(name)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(f"La regla {name} debe ser una lista de textos")
        return tuple(item.strip() for item in value)

    version = payload.get("version")
    discard = payload.get("discard_nonlocal_official_notices", True)
    if not isinstance(version, str) or not version.strip():
        raise ValueError("La configuración debe declarar una versión")
    if not isinstance(discard, bool):
        raise ValueError("discard_nonlocal_official_notices debe ser verdadero o falso")
    return RelevanceRules(
        version=version.strip(), direct_terms=terms("direct_terms"),
        strong_sector_terms=terms("strong_sector_terms"),
        electric_terms=terms("electric_terms"),
        activity_terms=terms("activity_terms"), local_terms=terms("local_terms"),
        discard_nonlocal_official_notices=discard,
    )


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip()


def classify(publication: Publication, full_text: str = "",
             rules: RelevanceRules = DEFAULT_RULES) -> tuple[str, str]:
    text = normalize(" ".join((publication.agency, publication.title,
                               publication.reference, publication.description,
                               full_text)))
    direct = [term for term in map(normalize, rules.direct_terms) if term in text]
    if direct:
        return "direct_epesf", f"Mención directa: {', '.join(direct)}"

    category = normalize(publication.category)
    local = [term for term in map(normalize, rules.local_terms) if term in text]
    if (full_text and rules.discard_nonlocal_official_notices
            and category.startswith("avisos oficiales") and not local):
        return (
            "not_relevant",
            "Aviso sobre un caso particular sin vínculo identificado con EPESF o Santa Fe",
        )

    strong = [term for term in map(normalize, rules.strong_sector_terms) if term in text]
    electric = [term for term in map(normalize, rules.electric_terms) if term in text]
    activity = [term for term in map(normalize, rules.activity_terms) if term in text]
    if strong or (electric and activity):
        matches = strong or electric + activity
        return "potential_sector_impact", f"Indicios sectoriales: {', '.join(matches[:4])}"
    if "energia" in text or electric:
        return "needs_review", "Coincidencia relacionada que requiere revisar el texto completo"
    return "not_relevant", "Sin indicios eléctricos en los metadatos del índice"
