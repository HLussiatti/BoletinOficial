from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Edition, Publication
from .relevance import classify

BASE_URL = "https://www.boletinoficial.gob.ar"
DETAIL_RE = re.compile(r"/detalleAviso/(?P<section>[^/]+)/(?P<id>\d+)/(?P<date>\d{8})")
CALENDAR_RE = re.compile(r"diasHabilitadosPortadaSuplemento\s*=\s*JSON\.parse\('([^']+)'\)")
SELECTED_DATE_RE = re.compile(r"fechaSeleccionadaYMD\s*=\s*'(\d{8})'")
MORE_RE = re.compile(r"hayMasResultadosSeccion\s*=\s*(true|false)")
PAGE_RE = re.compile(r"var numeroPagina\s*=\s*(\d+)")
LAST_CATEGORY_RE = re.compile(r"var ultimoRubro\s*=\s*'([^']*)'")
COUNT_RE = re.compile(r"\((\d+)\)\s*$")


class BoraError(RuntimeError):
    pass


class EditionNotPublished(BoraError):
    pass


def _clean(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_publications(html: str, publication_date: date) -> list[Publication]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[Publication] = []
    current_category = ""
    for node in soup.select("h5.seccion-rubro, a[href] .linea-aviso"):
        if node.name == "h5":
            current_category = _clean(node)
            continue
        anchor = node.find_parent("a", href=True)
        if not anchor:
            continue
        match = DETAIL_RE.search(anchor["href"])
        if not match or match.group("date") != publication_date.strftime("%Y%m%d"):
            continue
        details = [_clean(value) for value in node.select(".item-detalle")]
        agency = _clean(node.select_one(".item"))
        title = details[0] if details else "Aviso sin identificación"
        description = " ".join(value for value in details[1:] if value)
        has_annexes = bool(soup.select_one(
            f'a[href*="/detalleAviso/{match.group("section")}/{match.group("id")}/"]'
            '[href*="anexos=1"]'
        ))
        item = Publication(
            source_id=match.group("id"), publication_date=publication_date,
            section=match.group("section"), category=current_category,
            agency=agency, title=title, reference=description.split(" - ", 1)[0],
            description=description, detail_url=urljoin(BASE_URL, anchor["href"]),
            has_annexes=has_annexes,
        )
        relevance, reason = classify(item)
        results.append(replace(item, relevance=relevance, relevance_reason=reason))
    return results


def parse_expected_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    counts: list[int] = []
    for anchor in soup.select('a[onclick*="realizarBusquedaRubro"]'):
        match = COUNT_RE.search(_clean(anchor))
        if match:
            counts.append(int(match.group(1)))
    return sum(counts) if counts else None


class BoraClient:
    def __init__(self, session: requests.Session | None = None, timeout: float = 30):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.update({
            "User-Agent": "EPESF-Boletin/0.1 (+seguimiento normativo institucional)",
        })

    def _get_text(self, url: str) -> tuple[str, str]:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text, response.url

    def fetch_edition(self, day: date, fixture: Path | None = None) -> Edition:
        ymd = day.strftime("%Y%m%d")
        if fixture:
            html = fixture.read_text(encoding="utf-8")
            final_url = f"{BASE_URL}/seccion/primera/{ymd}"
        else:
            html, final_url = self._get_text(f"{BASE_URL}/seccion/primera/{ymd}")
        selected = SELECTED_DATE_RE.search(html)
        if (selected and selected.group(1) != ymd) or ymd not in final_url:
            raise EditionNotPublished(f"El BORA no publicó la Primera Sección para {day.isoformat()}")
        publications = parse_publications(html, day)
        if not publications:
            raise BoraError("La edición respondió sin publicaciones reconocibles")
        expected_count = parse_expected_count(html)

        pages = 1
        more_match = MORE_RE.search(html)
        page_match = PAGE_RE.search(html)
        last_match = LAST_CATEGORY_RE.search(html)
        has_more = bool(more_match and more_match.group(1) == "true")
        next_page = int(page_match.group(1)) if page_match else 2
        last_category = last_match.group(1) if last_match else ""
        seen = {publication.source_id for publication in publications}
        while has_more and not fixture:
            endpoint = (f"{BASE_URL}/seccion/actualizar/primera?pag={next_page}"
                        f"&ult_rubro={quote(last_category)}")
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            extra = parse_publications(payload.get("html", ""), day)
            for publication in extra:
                if publication.source_id not in seen:
                    publications.append(publication)
                    seen.add(publication.source_id)
            pages += 1
            has_more = bool(payload.get("hay_mas_datos"))
            next_page = int(payload.get("sig_pag", next_page + 1))
            last_category = str(payload.get("ult_rubro", last_category))
            if pages > 100:
                raise BoraError("La paginación excedió el límite de seguridad")
        if expected_count is not None and len(publications) < expected_count:
            raise BoraError(
                f"Índice incompleto: se esperaban {expected_count} publicaciones "
                f"y se obtuvieron {len(publications)}"
            )

        calendar = CALENDAR_RE.search(html)
        supplements: set[str] = set()
        if calendar:
            try:
                supplements = set(json.loads(calendar.group(1))["fechas_con_suplemento"])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return Edition(day, tuple(publications), ymd in supplements, pages)

    def download_pdf(self, publication: Publication, output_dir: Path) -> tuple[Path, str, int]:
        match = DETAIL_RE.search(urlparse(publication.detail_url).path)
        if not match:
            raise BoraError(f"Enlace de aviso inválido: {publication.detail_url}")
        endpoint = f"{BASE_URL}/pdf/download_aviso"
        response = self.session.post(endpoint, data={
            "nombreSeccion": publication.section,
            "idAviso": publication.source_id,
            "fechaPublicacion": publication.publication_date.strftime("%Y%m%d"),
        }, headers={"Referer": publication.detail_url,
                    "X-Requested-With": "XMLHttpRequest"}, timeout=self.timeout)
        response.raise_for_status()
        encoded = response.json().get("pdfBase64")
        if not encoded:
            raise BoraError("El BORA respondió sin contenido PDF")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise BoraError("El BORA respondió un PDF Base64 inválido") from exc
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
            raise BoraError("El documento descargado no es un PDF íntegro")
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", publication.title).strip("_.")[:80]
        name = f"NACION_{safe_title or 'Aviso'}_BORA_{publication.source_id}_{match.group('date')}.pdf"
        destination = output_dir / name
        temporary = destination.with_suffix(".pdf.part")
        temporary.write_bytes(content)
        temporary.replace(destination)
        digest = hashlib.sha256(content).hexdigest()
        return destination, digest, len(content)
