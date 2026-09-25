"""Stateless, authenticated WSGI web view backed by Turso libSQL."""

from __future__ import annotations

import csv
import html
import io
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .cloud_auth import CloudAuth, SESSION_SECONDS
from .cloud_db import TursoDatabase
from .mail import BulletinItem, _message
from .web_ui import CSS


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
STYLE = CSS + """
.login{width:min(420px,100%);margin:10vh auto;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:var(--s5)}
.login h1{font-size:var(--fs-display);margin-bottom:var(--s3)}.login p{margin:var(--s2) 0;line-height:1.5}
.login label{display:grid;gap:var(--s1);margin:var(--s4) 0;font-weight:600}
.login button{margin-top:var(--s2)}.login .error{color:var(--sig-alta)}
@media(max-width:650px){.login{margin-top:7vh}}
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


def _official_pdf_url(detail_url: object) -> str:
    official = _official_url(detail_url)
    if not official:
        return ""
    match = re.fullmatch(r"/detalleAviso/primera/(\d+)/(\d{8})/?",
                         urlparse(official).path)
    if not match:
        return ""
    return f"https://www.boletinoficial.gob.ar/pdf/aviso/primera/{match[1]}/{match[2]}"


def _csv_cell(value: object) -> str:
    result = str(value or "")
    return "'" + result if result.lstrip().startswith(("=", "+", "-", "@")) else result


@dataclass(frozen=True)
class Filters:
    day: str
    end_day: str = ""
    relevance: str = "active"
    category: str = ""
    text: str = ""
    view: str = "day"
    month: str = ""
    page: int = 1

    @classmethod
    def from_query(cls, query: dict[str, list[str]], latest: str) -> Filters:
        view = query.get("view", ["day"])[0]
        if view not in ("day", "history", "failures"):
            raise RequestError("Vista inválida")
        day = query.get("date", [latest if view == "day" else ""])[0].strip()
        end_day = query.get("to", [""])[0].strip()
        for value in (day, end_day):
            if not value:
                continue
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError as exc:
                raise RequestError("Fecha inválida") from exc
        if end_day and (not day or end_day < day):
            raise RequestError("El período seleccionado es inválido")
        if end_day == day:
            end_day = ""
        relevance = query.get("relevance", ["active"])[0]
        if relevance not in RELEVANCE:
            raise RequestError("Filtro de relevancia inválido")
        category = query.get("category", [""])[0].strip()
        if len(category) > 100:
            raise RequestError("El tipo de publicación es demasiado largo")
        text = query.get("q", [""])[0].strip()
        if len(text) > 100:
            raise RequestError("La búsqueda supera 100 caracteres")
        month = query.get("month", [""])[0]
        if month:
            try:
                if date.fromisoformat(month + "-01").strftime("%Y-%m") != month:
                    raise ValueError
            except ValueError as exc:
                raise RequestError("Mes inválido") from exc
        page_text = query.get("page", ["1"])[0]
        if not page_text.isdigit() or not 1 <= int(page_text) <= 1000:
            raise RequestError("Página inválida")
        return cls(day, end_day, relevance, category, text, view, month, int(page_text))

    def url(self, **updates: object) -> str:
        values = {"date": self.day, "to": self.end_day, "relevance": self.relevance,
                  "category": self.category, "q": self.text, "view": self.view,
                  "month": self.month, "page": self.page}
        values.update(updates)
        return "/?" + urlencode({key: value for key, value in values.items() if value})


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
            if filters.end_day:
                where.append("p.publication_date BETWEEN ? AND ?")
                args.extend((filters.day, filters.end_day))
            else:
                where.append("p.publication_date=?")
                args.append(filters.day)
        if filters.category:
            where.append("p.category=?")
            args.append(filters.category)
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
                       p.relevance_reason,p.has_annexes,p.first_seen_at,
                       p.summary_status,p.document_status,
                       s.conceptual_summary,s.epesf_relationship,s.effective_date,
                       s.model summary_model,
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

    def _overview(self, filters: Filters) -> dict[str, object]:
        where = ["source='BORA'"]
        args: list[str] = []
        if filters.day:
            if filters.end_day:
                where.append("publication_date BETWEEN ? AND ?")
                args.extend((filters.day, filters.end_day))
            else:
                where.append("publication_date=?")
                args.append(filters.day)
        with self._database().connect() as connection:
            groups = connection.execute(
                f"SELECT category,relevance,COUNT(*) count FROM publications WHERE {' AND '.join(where)} "
                "GROUP BY category,relevance", tuple(args)).fetchall()
            failed = int(connection.execute(
                "SELECT COUNT(*) count FROM coverage WHERE source='BORA' AND status='failed'"
            ).fetchone()["count"])
            last = connection.execute(
                "SELECT status,finished_at FROM runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            coverage = (connection.execute(
                "SELECT status,error FROM coverage WHERE source='BORA' AND publication_date=?",
                (filters.day,)).fetchone() if filters.day and not filters.end_day else None)
        categories = sorted({str(row["category"]) for row in groups if row["category"]},
                            key=str.casefold)
        scoped = [row for row in groups if not filters.category or row["category"] == filters.category]
        counts = {key: 0 for key in RELEVANCE}
        for row in scoped:
            value = int(row["count"])
            relevance = str(row["relevance"])
            counts["all"] += value
            if relevance != "not_relevant":
                counts["active"] += value
            if relevance in ("direct_epesf", "potential_sector_impact"):
                counts["selected"] += value
            if relevance in counts:
                counts[relevance] += value
        return {"categories": categories, "counts": counts, "failed": failed,
                "last": last, "coverage": coverage}

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

    def _csv(self, filters: Filters, selected: list[str] | None = None) -> bytes:
        _, rows = self._listing(filters)
        if selected:
            if len(selected) > PAGE_SIZE or any(not item.isdigit() for item in selected):
                raise RequestError("Selección de CSV inválida")
            ids = {int(item) for item in selected}
            rows = [row for row in rows if int(row["id"]) in ids]
            if len(rows) != len(ids):
                raise RequestError("La selección no pertenece a esta página")
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

    def _page(self, filters: Filters, csrf: str, user: str, job_id: str = "") -> bytes:
        from .cloud_web_views import render
        return render(self, filters, csrf, user, job_id)

    def _queue(self, action: str, body: dict[str, list[str]], user: str) -> str:
        from .cloud_dispatch import configured, dispatch
        if not configured():
            raise RequestError("La ejecución todavía no está configurada")
        if action == "consult":
            target = body.get("date", [""])[0]
            try:
                day = date.fromisoformat(target)
                if day.isoformat() != target or day > datetime.now(
                        timezone(timedelta(hours=-3))).date():
                    raise ValueError
            except ValueError as exc:
                raise RequestError("Elegí una fecha válida para consultar") from exc
        else:
            target = body.get("id", [""])[0]
            if not target.isdigit() or not 0 < int(target) < 2**63:
                raise RequestError("Publicación inválida")
            with self._database().connect() as connection:
                row = connection.execute("""
                    SELECT p.id FROM publications p WHERE p.id=? AND p.source='BORA'
                      AND p.relevance IN ('direct_epesf','potential_sector_impact')
                      AND NOT EXISTS (SELECT 1 FROM summaries s
                          WHERE s.publication_id=p.id AND s.status='complete')
                """, (int(target),)).fetchone()
            if row is None:
                raise RequestError("Esta publicación no tiene un resumen pendiente")
        db = self._database()
        db.migrate()
        job_id, created = db.enqueue_job(action, target, user)
        if created:
            try:
                dispatch(job_id)
            except Exception:
                db.finish_job(job_id, "failed", "No se pudo iniciar el ejecutor. Reintentá.")
        return job_id

    def _login_page(self, csrf: str, error: str = "") -> bytes:
        message = f'<p class="error" role="alert">{_h(error)}</p>' if error else ""
        return (f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Acceso · Boletín Oficial EPESF</title><style>{STYLE}</style></head><body><main class="shell"><div class="login">
            <h1>Boletín Oficial EPESF</h1><p>Ingresá para consultar las publicaciones.</p>{message}
            <form method="post" action="/?action=login"><input type="hidden" name="login_csrf" value="{_h(csrf)}">
            <label>Usuario<input name="user" autocomplete="username" required></label>
            <label>Contraseña<input name="password" type="password" autocomplete="current-password" required></label>
            <button class="primary" type="submit">Ingresar</button></form></div></main></body></html>''').encode("utf-8")

    def _login_response(self, start_response: Callable, auth: CloudAuth,
                        status: int = 200, error: str = ""):
        nonce = auth.new_login_nonce()
        cookie = f"epe_login_nonce={nonce}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=600"
        return self._respond(start_response, status,
                             self._login_page(auth.login_csrf_token(nonce), error),
                             [("Set-Cookie", cookie)])

    def __call__(self, environ: dict, start_response: Callable):
        try:
            auth = self._auth()
            user, ticket = auth.request_user(environ.get("HTTP_COOKIE", ""))
            method = environ.get("REQUEST_METHOD", "GET").upper()
            query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
            action = query.get("action", [""])[0]
            body: dict[str, list[str]] = {}
            if method == "POST":
                length = int(environ.get("CONTENT_LENGTH", "0") or "0")
                if length < 0 or length > 8192:
                    return self._respond(start_response, 413, b"Formulario demasiado grande")
                raw = environ["wsgi.input"].read(length)
                body = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
            if action == "login" and method == "POST":
                if not auth.valid_login_csrf(environ.get("HTTP_COOKIE", ""),
                                             body.get("login_csrf", [""])[0]):
                    return self._respond(start_response, 403, b"Solicitud rechazada")
                name = body.get("user", [""])[0]
                password = body.get("password", [""])[0]
                if not auth.verify_password(name, password):
                    return self._login_response(start_response, auth, 401,
                                                "Usuario o contraseña incorrectos")
                ticket = auth.new_ticket(name)
                return self._respond(start_response, 303, b"", [
                    ("Location", "/"), ("Set-Cookie", f"epe_session={ticket}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={SESSION_SECONDS}")])
            if not user:
                return self._login_response(start_response, auth)
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
            if action in ("consult", "summary") and method == "POST":
                job_id = self._queue(action, body, user)
                day = body.get("date", [""])[0]
                if action == "summary":
                    with self._database().connect() as connection:
                        row = connection.execute("SELECT publication_date FROM publications WHERE id=?",
                                                 (int(body["id"][0]),)).fetchone()
                    day = str(row["publication_date"]) if row else ""
                location = "/?" + urlencode({"date": day, "job": job_id})
                return self._respond(start_response, 303, b"", [("Location", location)])
            if action == "ui" and method == "GET":
                from .cloud_web_views import CLOUD_SCRIPT
                return self._respond(start_response, 200, CLOUD_SCRIPT.encode("utf-8"), [
                    ("Content-Type", "text/javascript; charset=utf-8")])
            if method != "GET" or action:
                if method == "GET" and action == "export":
                    filters = Filters.from_query(query, self._latest_date())
                    return self._respond(start_response, 200,
                                         self._csv(filters, query.get("selected")), [
                        ("Content-Type", "text/csv; charset=utf-8"),
                        ("Content-Disposition", 'attachment; filename="publicaciones.csv"')])
                return self._respond(start_response, 404, b"No encontrado")
            filters = Filters.from_query(query, self._latest_date())
            job_id = query.get("job", [""])[0]
            if job_id and not re.fullmatch(r"[0-9a-f]{32}", job_id):
                raise RequestError("Solicitud inválida")
            return self._respond(start_response, 200,
                                 self._page(filters, auth.csrf_token(ticket), user,
                                            job_id))
        except RequestError as exc:
            return self._respond(start_response, 400, _h(exc).encode("utf-8"))
        except Exception as exc:
            detail = str(exc)
            for key in ("TURSO_AUTH_TOKEN", "EPE_WEB_SESSION_SECRET", "EPE_WEB_USERS",
                        "TURSO_DATABASE_URL", "EPE_GITHUB_ACTIONS_TOKEN"):
                value = os.environ.get(key, "")
                if value:
                    detail = detail.replace(value, "[redacted]")
            logging.error("Cloud web request failed (%s): %s", type(exc).__name__,
                          detail[:300])
            return self._respond(start_response, 503, b"Servicio temporalmente no disponible")

    @staticmethod
    def _respond(start_response: Callable, status: int, body: bytes,
                 extra: list[tuple[str, str]] | None = None):
        headers = [("Content-Type", "text/html; charset=utf-8"),
                   ("Content-Length", str(len(body))),
                   ("Cache-Control", "no-store"),
                   ("X-Content-Type-Options", "nosniff"),
                   ("Referrer-Policy", "no-referrer"),
                   ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")]
        for key, value in extra or []:
            headers = [(name, current) for name, current in headers
                       if name.lower() != key.lower()]
            headers.append((key, value))
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [body]
