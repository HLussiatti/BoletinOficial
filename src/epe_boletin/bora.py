from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Annex, Edition, Publication
from .relevance import DEFAULT_RULES, RelevanceRules, classify

BASE_URL = "https://www.boletinoficial.gob.ar"
DETAIL_RE = re.compile(r"/detalleAviso/(?P<section>[^/]+)/(?P<id>\d+)/(?P<date>\d{8})")
CALENDAR_RE = re.compile(r"diasHabilitadosPortadaSuplemento\s*=\s*JSON\.parse\('([^']+)'\)")
SELECTED_DATE_RE = re.compile(r"fechaSeleccionadaYMD\s*=\s*'(\d{8})'")
MORE_RE = re.compile(r"hayMasResultadosSeccion\s*=\s*(true|false)")
PAGE_RE = re.compile(r"var numeroPagina\s*=\s*(\d+)")
LAST_CATEGORY_RE = re.compile(r"var ultimoRubro\s*=\s*'([^']*)'")
COUNT_RE = re.compile(r"\((\d+)\)\s*$")
ANNEX_RE = re.compile(
    r"descargarPDFAnexo\(\s*['\"](?P<section>[^'\"]+)['\"]\s*,\s*"
    r"['\"](?P<number>[^'\"]+)['\"]\s*,\s*['\"](?P<id>[^'\"]+)['\"]\s*,\s*"
    r"['\"](?P<date>\d{8})['\"]\s*,\s*['\"](?P<endpoint>[^'\"]+)['\"]"
)


class BoraError(RuntimeError):
    pass


class EditionNotPublished(BoraError):
    pass


class BoraNetworkError(BoraError):
    pass


def _clean(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_publications(html: str, publication_date: date,
                       rules: RelevanceRules = DEFAULT_RULES) -> list[Publication]:
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
        relevance, reason = classify(item, rules=rules)
        results.append(replace(
            item, relevance=relevance, relevance_reason=reason,
            relevance_rules_version=rules.version,
        ))
    return results


def parse_expected_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    counts: list[int] = []
    for anchor in soup.select('a[onclick*="realizarBusquedaRubro"]'):
        match = COUNT_RE.search(_clean(anchor))
        if match:
            counts.append(int(match.group(1)))
    return sum(counts) if counts else None


def _safe_component(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("._")


def document_stem(publication: Publication) -> str:
    match = re.fullmatch(r"(?P<type>.+?)\s+(?P<number>\d+)(?:/\d{4})?", publication.title)
    if match:
        document_type = _safe_component(match.group("type"))
        number = match.group("number")
    else:
        document_type = _safe_component(publication.title) or "Documento"
        number = publication.source_id
    return f"{publication.publication_date:%Y_%m_%d}_{document_type}_{number}"


class BoraClient:
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, session: requests.Session | None = None, timeout: float = 30,
                 max_attempts: int = 3, backoff_seconds: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep,
                 rules: RelevanceRules = DEFAULT_RULES):
        if max_attempts < 1:
            raise ValueError("max_attempts debe ser al menos 1")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep
        self.rules = rules
        self.session.headers.update({
            "User-Agent": "EPESF-Boletin/0.1 (+seguimiento normativo institucional)",
        })

    def _request(self, method: str, url: str, **kwargs):
        last_error: BoraNetworkError | None = None
        for attempt in range(self.max_attempts):
            try:
                request = getattr(self.session, method.lower())
                response = request(url, timeout=self.timeout, **kwargs)
                status = getattr(response, "status_code", 200)
                if status not in self.RETRYABLE_STATUS:
                    response.raise_for_status()
                    return response
                last_error = BoraNetworkError(f"El BORA respondió HTTP {status}: {url}")
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = BoraNetworkError(f"No se pudo conectar con el BORA: {url}")
                last_error.__cause__ = exc
            except requests.RequestException as exc:
                raise BoraNetworkError(f"Falló la consulta al BORA: {url}") from exc
            if attempt + 1 < self.max_attempts:
                self.sleep(self.backoff_seconds * (2 ** attempt))
        assert last_error is not None
        raise last_error

    def _get_text(self, url: str) -> tuple[str, str]:
        response = self._request("get", url)
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
        publications = parse_publications(html, day, self.rules)
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
            response = self._request("get", endpoint)
            try:
                payload = response.json()
            except ValueError as exc:
                raise BoraError("El BORA respondió una página adicional inválida") from exc
            if not isinstance(payload, dict):
                raise BoraError("El BORA respondió una página adicional inesperada")
            extra = parse_publications(payload.get("html", ""), day, self.rules)
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
        response = self._request("post", endpoint, data={
            "nombreSeccion": publication.section,
            "idAviso": publication.source_id,
            "fechaPublicacion": publication.publication_date.strftime("%Y%m%d"),
        }, headers={"Referer": publication.detail_url,
                    "X-Requested-With": "XMLHttpRequest"})
        content = self._decode_pdf(response)
        output_dir.mkdir(parents=True, exist_ok=True)
        name = document_stem(publication) + ".pdf"
        return self._store_pdf(content, output_dir / name)

    def fetch_annexes(self, publication: Publication) -> tuple[Annex, ...]:
        html, _ = self._get_text(publication.detail_url + "?anexos=1")
        soup = BeautifulSoup(html, "html.parser")
        annexes: list[Annex] = []
        for node in soup.select('[onclick*="descargarPDFAnexo"]'):
            match = ANNEX_RE.search(node.get("onclick", ""))
            if not match:
                continue
            annexes.append(Annex(
                number=match.group("number"), source_id=match.group("id"),
                publication_date=publication.publication_date,
                section=match.group("section"), endpoint=match.group("endpoint"),
            ))
        if publication.has_annexes and not annexes:
            raise BoraError("El aviso indica anexos pero no se pudieron identificar")
        return tuple(annexes)

    def download_annex(self, publication: Publication, annex: Annex,
                       output_dir: Path) -> tuple[Path, str, int]:
        response = self._request("post", urljoin(BASE_URL, annex.endpoint), data={
            "seccion": annex.section,
            "nroAnexo": annex.number,
            "idAnexo": annex.source_id,
            "fechaPublicacion": annex.publication_date.strftime("%Y%m%d"),
        }, headers={"Referer": publication.detail_url,
                    "X-Requested-With": "XMLHttpRequest"})
        content = self._decode_pdf(response)
        output_dir.mkdir(parents=True, exist_ok=True)
        name = f"{document_stem(publication)}_Anexo_{_safe_component(annex.number)}.pdf"
        return self._store_pdf(content, output_dir / name)

    @staticmethod
    def _decode_pdf(response) -> bytes:
        try:
            payload = response.json()
        except ValueError as exc:
            raise BoraError("El BORA respondió un documento inválido") from exc
        if not isinstance(payload, dict):
            raise BoraError("El BORA respondió un documento inesperado")
        encoded = payload.get("pdfBase64")
        if not encoded:
            raise BoraError("El BORA respondió sin contenido PDF")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise BoraError("El BORA respondió un PDF Base64 inválido") from exc
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
            raise BoraError("El documento descargado no es un PDF íntegro")
        return content

    @staticmethod
    def _store_pdf(content: bytes, destination: Path) -> tuple[Path, str, int]:
        temporary = destination.with_suffix(".pdf.part")
        temporary.write_bytes(content)
        temporary.replace(destination)
        digest = hashlib.sha256(content).hexdigest()
        return destination, digest, len(content)
