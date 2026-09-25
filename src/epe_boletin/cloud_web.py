"""Stateless, authenticated WSGI web view backed by Turso libSQL."""

from __future__ import annotations

import csv
import html
import io
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .cloud_auth import CloudAuth, SESSION_SECONDS
from .cloud_db import TursoDatabase
from .mail import BulletinItem, _message


PAGE_SIZE = 50


class RequestError(ValueError):
    """Invalid browser input that may safely be shown to the user."""


RELEVANCE = {
    "active": "Relevantes y sin clasificar",
    "selected": "Relevantes",
    "direct_epesf": "Impacto directo",
    "potential_sector_impact": "Impacto potencial",
    "needs_review": "Sin clasificar",
    "not_relevant": "Descartadas",
    "all": "Todas",
}
STYLE = """
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#243443;background:#f2f5f4}
*{box-sizing:border-box}body{margin:0}a{color:#086d71}a:hover{text-decoration-thickness:2px}
.shell{max-width:1150px;margin:auto;padding:24px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px}
h1{font-size:1.5rem;margin:0}h2{font-size:1.15rem}.muted{color:#5a6c71}.pill{background:#e1f2ec;color:#135b46;padding:5px 10px;border-radius:20px}
form.filters,.card,.login{background:white;border:1px solid #d8e3e1;border-radius:12px;padding:18px;margin:18px 0}
.filters{display:flex;flex-wrap:wrap;gap:12px;align-items:end}.filters label{display:grid;gap:5px;font-size:.86rem;font-weight:600}
input,select,button{font:inherit;padding:9px 10px;border:1px solid #b5c7c4;border-radius:7px;background:white;color:inherit}
button{cursor:pointer;background:#066b60;color:white;border-color:#066b60}button:hover{background:#07574e}
.secondary{background:white;color:#066b60}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}
.list{list-style:none;padding:0}.item{background:white;border:1px solid #d8e3e1;border-radius:12px;padding:17px;margin:10px 0}
.item-head{display:flex;gap:12px;align-items:start}.item h2{margin:0 0 5px}.item p{margin:8px 0;line-height:1.45}
.meta{font-size:.84rem;color:#5a6c71}.badge{font-size:.8rem;background:#e4f0ee;padding:4px 8px;border-radius:6px;display:inline-block}
details{margin-top:10px}summary{cursor:pointer;font-weight:600}.actions{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}
.paging{display:flex;gap:12px;align-items:center;margin:20px 0}.login{max-width:420px;margin:10vh auto}.login label{display:grid;gap:5px;margin:12px 0}
.error{color:#a12d2d}.notice{background:#e7f4ee;border-left:4px solid #2d8b6a;padding:12px;margin:12px 0}
footer{margin:30px 0;color:#5a6c71;font-size:.84rem}@media(max-width:650px){.shell{padding:14px}.top{align-items:start}.filters>*{flex:1 1 150px}}
"""


def _h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _official_url(value: object) -> str:
    url = str(value or "")
    try:
        parsed = urlparse(url)
        valid = (parsed.scheme == "https" and parsed.hostname in
                 {"www.boletinoficial.gob.ar", "boletinoficial.gob.ar"}
                 and not parsed.username and not parsed.password
                 and parsed.port in (None, 443))
    except ValueError:
        return ""
    return url if valid else ""


def _csv_cell(value: object) -> str:
    result = str(value or "")
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


@dataclass(frozen=True)
class Filters:
    day: str
    relevance: str = "active"
    text: str = ""
    page: int = 1

    @classmethod
    def from_query(cls, query: dict[str, list[str]], latest: str) -> Filters:
        day = query.get("date", [latest])[0].strip()
        if day:
            try:
                if date.fromisoformat(day).isoformat() != day:
                    raise ValueError
            except ValueError as exc:
                raise RequestError("Fecha inválida") from exc
        relevance = query.get("relevance", ["active"])[0]
        if relevance not in RELEVANCE:
            raise RequestError("Filtro de relevancia inválido")
        text = query.get("q", [""])[0].strip()
        if len(text) > 100:
            raise RequestError("La búsqueda supera 100 caracteres")
        page_text = query.get("page", ["1"])[0]
        if not page_text.isdigit() or not 1 <= int(page_text) <= 1000:
            raise RequestError("Página inválida")
        return cls(day, relevance, text, int(page_text))

    def url(self, page: int | None = None) -> str:
        return "/?" + urlencode({"date": self.day, "relevance": self.relevance,
                                   "q": self.text, "page": self.page if page is None else page})


class CloudWeb:
    def __init__(self, database: TursoDatabase | None = None,
                 auth: CloudAuth | None = None):
        self.database = database
        self.auth = auth

    def _database(self) -> TursoDatabase:
        return self.database or TursoDatabase.from_env()

    def _auth(self) -> CloudAuth:
        return self.auth or CloudAuth.from_env()

    def _latest_date(self) -> str:
        with self._database().connect() as connection:
            row = connection.execute("""SELECT MAX(publication_date) latest FROM (
                SELECT publication_date FROM publications WHERE source='BORA'
                UNION SELECT publication_date FROM coverage WHERE source='BORA')""").fetchone()
        return str(row["latest"] or "")

    def _listing(self, filters: Filters) -> tuple[int, list[dict[str, object]]]:
        where = ["p.source='BORA'"]
        args: list[object] = []
        if filters.day:
            where.append("p.publication_date=?")
            args.append(filters.day)
        if filters.relevance == "active":
            where.append("p.relevance!='not_relevant'")
        elif filters.relevance == "selected":
            where.append("p.relevance IN ('direct_epesf','potential_sector_impact')")
        elif filters.relevance != "all":
            where.append("p.relevance=?")
            args.append(filters.relevance)
        if filters.text:
            where.append("LOWER(p.title||' '||p.agency||' '||p.reference||' '||p.description) LIKE ?")
            args.append("%" + filters.text.lower() + "%")
        condition = " AND ".join(where)
        with self._database().connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) count FROM publications p WHERE {condition}",
                tuple(args)).fetchone()["count"])
            rows = connection.execute(f"""
                SELECT p.id,p.source_id,p.publication_date,p.category,p.agency,
                       p.title,p.reference,p.description,p.detail_url,p.relevance,
                       p.relevance_reason,p.has_annexes,
                       s.conceptual_summary,s.epesf_relationship,s.effective_date,
                       n.pdf_url,n.pdf_availability,n.annex_status
                FROM publications p
                LEFT JOIN summaries s ON s.id=(
                    SELECT id FROM summaries WHERE publication_id=p.id
                    AND status='complete' ORDER BY id DESC LIMIT 1)
                LEFT JOIN notice_contents n ON n.publication_id=p.id
                WHERE {condition}
                ORDER BY p.publication_date DESC,
                    CASE p.relevance WHEN 'direct_epesf' THEN 0
                        WHEN 'potential_sector_impact' THEN 1 ELSE 2 END,
                    p.title,p.id
                LIMIT ? OFFSET ?
            """, (*args, PAGE_SIZE, (filters.page - 1) * PAGE_SIZE)).fetchall()
        return total, rows

    def _draft(self, body: dict[str, list[str]]) -> tuple[str, bytes]:
        day_text = body.get("date", [""])[0]
        try:
            day = date.fromisoformat(day_text)
            if day.isoformat() != day_text:
                raise ValueError
        except ValueError as exc:
            raise RequestError("Elegí una fecha válida") from exc
        ids_text = body.get("selected", [])
        if (not ids_text or len(ids_text) > 25 or
                any(not value.isdigit() or int(value) <= 0 for value in ids_text)):
            raise RequestError("Seleccioná entre 1 y 25 publicaciones")
        ids = tuple(dict.fromkeys(int(value) for value in ids_text))
        if len(ids) != len(ids_text):
            raise RequestError("La selección contiene duplicados")
        marks = ",".join("?" for _ in ids)
        with self._database().connect() as connection:
            rows = connection.execute(f"""
                SELECT p.id,p.source_id,p.title,p.agency,p.publication_date,
                       p.detail_url,s.conceptual_summary,s.epesf_relationship,
                       s.effective_date
                FROM publications p JOIN summaries s ON s.id=(
                    SELECT id FROM summaries WHERE publication_id=p.id
                    AND status='complete' ORDER BY id DESC LIMIT 1)
                WHERE p.source='BORA' AND p.publication_date=?
                  AND p.id IN ({marks})
            """, (day_text, *ids)).fetchall()
        by_id = {int(row["id"]): row for row in rows}
        if len(by_id) != len(ids) or any(not _official_url(by_id[item]["detail_url"])
                                         for item in ids if item in by_id):
            raise RequestError("La selección contiene publicaciones no disponibles")
        items = [BulletinItem(
            source_id=str(by_id[item]["source_id"]),
            title=str(by_id[item]["title"]), agency=str(by_id[item]["agency"]),
            publication_date=str(by_id[item]["publication_date"]),
            conceptual_summary=str(by_id[item]["conceptual_summary"]),
            epesf_relationship=str(by_id[item]["epesf_relationship"]),
            effective_date=str(by_id[item]["effective_date"]),
            detail_url=str(by_id[item]["detail_url"]), documents=(),
        ) for item in ids]
        content = _message(items, day, "", (), 1, 1).as_bytes()
        if len(content) > 10 * 1024 * 1024:
            raise RequestError("El borrador supera 10 MB; seleccioná menos publicaciones")
        return f"boletin_{day:%Y_%m_%d}.eml", content

    def _csv(self, filters: Filters) -> bytes:
        _, rows = self._listing(filters)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(("fecha", "organismo", "tipo", "titulo", "referencia",
                         "relevancia", "resumen", "relacion_epesf", "vigencia", "url_oficial"))
        for row in rows:
            writer.writerow(tuple(_csv_cell(value) for value in (
                             row["publication_date"], row["agency"], row["category"],
                             row["title"], row["reference"], row["relevance"],
                             row["conceptual_summary"] or "", row["epesf_relationship"] or "",
                             row["effective_date"] or "", _official_url(row["detail_url"]))))
        return output.getvalue().encode("utf-8-sig")

    def _page(self, filters: Filters, csrf: str, user: str) -> bytes:
        total, rows = self._listing(filters)
        chosen = f"{_h(filters.day)}" if filters.day else "Todo el histórico"
        options = "".join(f'<option value="{_h(key)}"{" selected" if key == filters.relevance else ""}>{_h(value)}</option>'
                          for key, value in RELEVANCE.items())
        items = []
        for row in rows:
            official = _official_url(row["detail_url"])
            pdf = _official_url(row["pdf_url"])
            has_summary = bool(row["conceptual_summary"])
            select = (f'<input type="checkbox" name="selected" value="{int(row["id"])}" '
                      f'aria-label="Incluir {_h(row["title"])}" >') if has_summary and filters.day else ""
            summary = (f'<p><strong>Resumen:</strong> {_h(row["conceptual_summary"])}</p>'
                       f'<p><strong>Relación con EPESF:</strong> {_h(row["epesf_relationship"])}</p>'
                       f'<p><strong>Vigencia:</strong> {_h(row["effective_date"])}</p>') if has_summary else '<p class="muted">Sin resumen completo.</p>'
            annex = '<p class="muted">Tiene anexo no analizado.</p>' if row["has_annexes"] or row["annex_status"] == "unread" else ""
            links = (f'<a href="{_h(official)}" target="_blank" rel="noopener noreferrer">Aviso oficial</a>' if official else "")
            if pdf:
                links += f' <a href="{_h(pdf)}" target="_blank" rel="noopener noreferrer">PDF oficial</a>'
            items.append(f'''<li class="item"><div class="item-head">{select}<div>
                <div class="meta">{_h(row["publication_date"])} · {_h(row["category"])} · {_h(row["agency"])}</div>
                <h2>{_h(row["title"])}</h2><span class="badge">{_h(RELEVANCE.get(str(row["relevance"]), str(row["relevance"])))}</span>
                <span class="meta">{_h(row["reference"])}</span></div></div>
                <details><summary>Ver análisis y fuente</summary>{summary}{annex}
                <p>{_h(row["description"])}</p><p class="meta">{_h(row["relevance_reason"])}</p>
                <div class="actions">{links}</div></details></li>''')
        previous = f'<a href="{_h(filters.url(filters.page - 1))}">Anterior</a>' if filters.page > 1 else ""
        following = f'<a href="{_h(filters.url(filters.page + 1))}">Siguiente</a>' if filters.page * PAGE_SIZE < total else ""
        draft = (f'<input type="hidden" name="date" value="{_h(filters.day)}">'
                 f'<input type="hidden" name="csrf" value="{_h(csrf)}">'
                 '<button type="submit">Descargar correo de las seleccionadas</button>'
                 '<p class="muted">El borrador no incluye adjuntos. Los enlaces llevan al BORA.</p>') if filters.day else '<p class="muted">Elegí un solo día para preparar un correo.</p>'
        content = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Boletín Oficial EPESF</title><style>{STYLE}</style></head><body><main class="shell">
            <header class="top"><div><h1>Boletín Oficial EPESF</h1><span class="muted">Publicaciones nacionales relevantes para EPESF</span></div>
            <form action="/?action=logout" method="post"><input type="hidden" name="csrf" value="{_h(csrf)}"><button class="secondary">Salir ({_h(user)})</button></form></header>
            <form class="filters" method="get" action="/"><label>Fecha (vacía: histórico)<input name="date" type="date" value="{_h(filters.day)}"></label>
            <label>Relevancia<select name="relevance">{options}</select></label>
            <label>Buscar<input name="q" maxlength="100" value="{_h(filters.text)}"></label><button>Filtrar</button></form>
            <div class="toolbar"><div><strong>{total} publicaciones</strong> · {chosen}</div>
            <div class="actions"><a href="/?date=&amp;relevance=active">Ver histórico</a>
            <a href="{_h(filters.url())}&amp;action=export">Exportar esta página a CSV</a></div></div>
            <form method="post" action="/?action=draft"><ul class="list">{''.join(items) if items else '<li class="card">No hay publicaciones para este filtro.</li>'}</ul>
            {draft}</form><nav class="paging" aria-label="Páginas">{previous}<span>Página {filters.page}</span>{following}</nav>
            <footer>Datos en Turso · Fuentes oficiales en BORA · El correo se genera en memoria.</footer>
            </main></body></html>'''
        return content.encode("utf-8")

    def _login_page(self, error: str = "") -> bytes:
        message = f'<p class="error" role="alert">{_h(error)}</p>' if error else ""
        return (f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Acceso · Boletín Oficial EPESF</title><style>{STYLE}</style></head><body><main class="shell"><div class="login">
            <h1>Boletín Oficial EPESF</h1><p>Ingresá para consultar las publicaciones.</p>{message}
            <form method="post" action="/?action=login"><label>Usuario<input name="user" autocomplete="username" required></label>
            <label>Contraseña<input name="password" type="password" autocomplete="current-password" required></label>
            <button type="submit">Ingresar</button></form></div></main></body></html>''').encode("utf-8")

    def __call__(self, environ: dict, start_response: Callable):
        try:
            auth = self._auth()
            user, ticket = auth.request_user(environ.get("HTTP_COOKIE", ""))
            method = environ.get("REQUEST_METHOD", "GET").upper()
            query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
            action = query.get("action", [""])[0]
            body: dict[str, list[str]] = {}
            if method == "POST":
                host = environ.get("HTTP_HOST", "")
                origin = urlparse(environ.get("HTTP_ORIGIN", ""))
                if (not host or origin.netloc != host or origin.scheme not in ("http", "https")):
                    return self._respond(start_response, 403, b"Solicitud rechazada")
                length = int(environ.get("CONTENT_LENGTH", "0") or "0")
                if length < 0 or length > 8192:
                    return self._respond(start_response, 413, b"Formulario demasiado grande")
                raw = environ["wsgi.input"].read(length)
                body = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
            if action == "login" and method == "POST":
                name = body.get("user", [""])[0]
                password = body.get("password", [""])[0]
                if not auth.verify_password(name, password):
                    return self._respond(start_response, 401,
                                         self._login_page("Usuario o contraseña incorrectos"))
                ticket = auth.new_ticket(name)
                return self._respond(start_response, 303, b"", [
                    ("Location", "/"), ("Set-Cookie", f"epe_session={ticket}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={SESSION_SECONDS}")])
            if not user:
                return self._respond(start_response, 200, self._login_page())
            if method == "POST" and not auth.valid_csrf(ticket, body.get("csrf", [""])[0]):
                return self._respond(start_response, 403, b"Solicitud rechazada")
            if action == "logout" and method == "POST":
                return self._respond(start_response, 303, b"", [
                    ("Location", "/"), ("Set-Cookie", "epe_session=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0")])
            if action == "draft" and method == "POST":
                filename, content = self._draft(body)
                return self._respond(start_response, 200, content, [
                    ("Content-Type", "message/rfc822"),
                    ("Content-Disposition", f'attachment; filename="{filename}"')])
            if method != "GET" or action:
                if method == "GET" and action == "export":
                    filters = Filters.from_query(query, self._latest_date())
                    return self._respond(start_response, 200, self._csv(filters), [
                        ("Content-Type", "text/csv; charset=utf-8"),
                        ("Content-Disposition", 'attachment; filename="publicaciones.csv"')])
                return self._respond(start_response, 404, b"No encontrado")
            filters = Filters.from_query(query, self._latest_date())
            return self._respond(start_response, 200,
                                 self._page(filters, auth.csrf_token(ticket), user))
        except RequestError as exc:
            return self._respond(start_response, 400, _h(exc).encode("utf-8"))
        except Exception:
            return self._respond(start_response, 503, b"Servicio temporalmente no disponible")

    @staticmethod
    def _respond(start_response: Callable, status: int, body: bytes,
                 extra: list[tuple[str, str]] | None = None):
        headers = [("Content-Type", "text/html; charset=utf-8"),
                   ("Content-Length", str(len(body))),
                   ("Cache-Control", "no-store"),
                   ("X-Content-Type-Options", "nosniff"),
                   ("Referrer-Policy", "no-referrer"),
                   ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")]
        for key, value in extra or []:
            headers = [(name, current) for name, current in headers
                       if name.lower() != key.lower()]
            headers.append((key, value))
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [body]
