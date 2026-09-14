from __future__ import annotations

import csv
import html
import io
import json
import os
import threading
import webbrowser
from dataclasses import dataclass
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .db import Database
from .mail import EmailArtifact, build_email_batches


STATUS_LABELS = {
    "direct_epesf": "Impacto directo",
    "potential_sector_impact": "Impacto potencial",
    "needs_review": "Revisar",
    "not_relevant": "Descartada",
    "complete": "Completo",
    "partial": "Parcial",
    "failed": "Con error",
    "not_published": "No publicado",
}


def _label(value: str | None) -> str:
    return STATUS_LABELS.get(value or "", (value or "Sin datos").replace("_", " ").title())


def _h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _timestamp(value: object) -> str:
    if not value:
        return "Todavía no ejecutado"
    try:
        instant = datetime.fromisoformat(str(value)).astimezone()
        return instant.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)


@dataclass(frozen=True)
class Query:
    day: str = ""
    relevance: str = "active"
    text: str = ""
    history: bool = False
    selected_ids: tuple[int, ...] = ()
    email_status: str = ""
    email_items: int = 0
    email_files: int = 0
    email_error: str = ""

    @classmethod
    def from_url(cls, query: str) -> "Query":
        values = parse_qs(query)
        item_value = values.get("items", ["0"])[0]
        file_value = values.get("files", ["0"])[0]
        selected_ids = tuple(
            int(value) for value in values.get("selected", []) if value.isdigit()
        )
        return cls(
            day=values.get("date", [""])[0].strip(),
            relevance=values.get("relevance", ["active"])[0].strip(),
            text=values.get("q", [""])[0].strip(),
            history=values.get("history", [""])[0] == "1",
            selected_ids=selected_ids,
            email_status=values.get("email", [""])[0].strip(),
            email_items=int(item_value) if item_value.isdigit() else 0,
            email_files=int(file_value) if file_value.isdigit() else 0,
            email_error=values.get("email_error", [""])[0].strip(),
        )


class WebApplication:
    def __init__(self, database: Database, data_dir: Path,
                 email_opener: Callable[[Path], None] | None = None):
        self.database = database
        self.data_dir = data_dir.resolve()
        self.email_opener = email_opener or open_eml

    def publications(self, query: Query) -> list[dict[str, object]]:
        clauses: list[str] = []
        parameters: list[object] = []
        if query.day:
            clauses.append("p.publication_date=?")
            parameters.append(query.day)
        if query.relevance == "active":
            clauses.append("p.relevance!='not_relevant'")
        elif query.relevance and query.relevance != "all":
            clauses.append("p.relevance=?")
            parameters.append(query.relevance)
        if query.text:
            clauses.append("lower(p.category||' '||p.agency||' '||p.title||' '||p.reference||' '||p.description) LIKE ?")
            parameters.append(f"%{query.text.casefold()}%")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(f"""
                SELECT p.*,
                  (SELECT conceptual_summary FROM summaries s
                   WHERE s.publication_id=p.id AND s.status='complete'
                   ORDER BY s.id DESC LIMIT 1) conceptual_summary,
                  (SELECT epesf_relationship FROM summaries s
                   WHERE s.publication_id=p.id AND s.status='complete'
                   ORDER BY s.id DESC LIMIT 1) epesf_relationship
                FROM publications p {where}
                ORDER BY p.publication_date DESC, p.agency, p.title
            """, parameters).fetchall()
            result = [dict(row) for row in rows]
            for item in result:
                documents = connection.execute(
                    "SELECT id,kind,path,page_count FROM documents WHERE publication_id=? ORDER BY id",
                    (item["id"],),
                ).fetchall()
                item["documents"] = [dict(document) for document in documents]
            return result

    def latest_date(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT MAX(publication_date) value FROM publications").fetchone()
        return str(row["value"] or "")

    def date_stats(self, day: str = "") -> dict[str, int]:
        where = " WHERE publication_date=?" if day else ""
        parameters = (day,) if day else ()
        with self.database.connect() as connection:
            row = connection.execute(f"""
                SELECT COUNT(*) total,
                  COALESCE(SUM(relevance IN ('direct_epesf','potential_sector_impact')),0) relevant,
                  COALESCE(SUM(document_status='downloaded'),0) downloaded
                FROM publications{where}
            """, parameters).fetchone()
        return {key: int(row[key] or 0) for key in row.keys()}

    def operational_issues(self) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        with self.database.connect() as connection:
            for row in connection.execute("""
                SELECT publication_date,error FROM coverage
                WHERE status='failed' ORDER BY publication_date DESC
            """):
                issues.append({"kind": "Cobertura", "title": str(row["publication_date"]),
                               "detail": str(row["error"] or "Consulta fallida")})
            for row in connection.execute("""
                SELECT title,detail_url,document_status,summary_status,delivery_status
                FROM publications
                WHERE document_status='error' OR summary_status='error'
                   OR delivery_status IN ('error','uncertain')
                ORDER BY publication_date DESC,title
            """):
                states = []
                if row["document_status"] == "error": states.append("documento")
                if row["summary_status"] == "error": states.append("resumen")
                if row["delivery_status"] in ("error", "uncertain"): states.append("entrega")
                issues.append({"kind": "Publicación", "title": str(row["title"]),
                               "detail": "Revisar: " + ", ".join(states),
                               "url": str(row["detail_url"] or "")})
        return issues

    def document(self, document_id: int) -> tuple[Path, str] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT path,kind FROM documents WHERE id=?", (document_id,)
            ).fetchone()
        if not row:
            return None
        path = Path(row["path"])
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        if not path.is_relative_to(self.data_dir) or not path.is_file():
            return None
        return path, str(row["kind"])

    def email_items(self, query: Query):
        if not query.day or not query.selected_ids:
            return []
        visible_ids = {int(row["id"]) for row in self.publications(query)}
        selected_ids = tuple(
            publication_id for publication_id in query.selected_ids
            if publication_id in visible_ids
        )
        return self.database.bulletin_items(date.fromisoformat(query.day), selected_ids)

    def prepare_email(self, query: Query) -> list[EmailArtifact]:
        try:
            day = date.fromisoformat(query.day)
        except ValueError as exc:
            raise ValueError("Elegí una fecha válida para preparar el correo") from exc
        if not query.selected_ids:
            raise ValueError("Seleccioná al menos una publicación con resumen completo")
        items = self.email_items(query)
        if not items:
            raise ValueError("La selección no contiene publicaciones listas para el correo")
        output = self.data_dir / "outbox" / f"boletin_{day:%Y_%m_%d}.eml"
        artifacts = build_email_batches(items, day, output)
        for index, artifact in enumerate(artifacts, 1):
            self.database.record_prepared_delivery(
                day, artifact, (), index, len(artifacts)
            )
            self.email_opener(artifact.path.resolve())
        return artifacts


def open_eml(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path), "open")  # type: ignore[attr-defined]
        return
    webbrowser.open(path.as_uri())


CSS = """
:root{--ink:#171715;--paper:#f5f2eb;--panel:#fffdf8;--muted:#66645f;--line:#d8d2c5;--gold:#b88a27;--focus:#624600;--ok:#27643a;--warn:#8b5a11;--bad:#9d2f2f;font-family:Segoe UI,Tahoma,Arial,sans-serif;color:var(--ink);background:var(--paper);scrollbar-color:var(--gold) var(--paper)}
*{box-sizing:border-box}::selection{background:#d8b763;color:var(--ink)}body{margin:0;overflow-wrap:anywhere}.shell{max-width:1480px;margin:auto;padding:28px 34px 64px}.mast{display:grid;grid-template-columns:1fr auto;gap:24px;border-top:5px solid var(--ink);border-bottom:2px solid var(--gold);padding:18px 0 20px}.mast>*{min-width:0}.context{font-size:.82rem;color:var(--muted);margin-top:7px}h1{font-family:Georgia,serif;font-size:clamp(2rem,4vw,4.2rem);line-height:.95;margin:.22em 0}.date{font-variant-numeric:tabular-nums;font-size:1.1rem}.run{align-self:center;padding:10px 0 0;min-width:240px}.run strong{display:block;font-size:1.15rem}.workflow{border-left:2px solid var(--gold);padding-left:16px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.metric{padding:18px 16px;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric b{display:block;font-family:Georgia,serif;font-size:2rem}.metric span{color:var(--muted);font-size:.82rem}.filters{display:grid;grid-template-columns:180px 210px minmax(220px,1fr) auto;gap:12px;padding:22px 0;align-items:end}label{display:grid;gap:6px;min-width:0;font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;color:var(--muted)}input,select,button{width:100%;max-width:100%;font:inherit;border:1px solid #aaa396;background:var(--panel);padding:10px 11px;color:var(--ink);caret-color:var(--focus);min-height:42px}button{cursor:pointer;background:var(--ink);color:white;border-color:var(--ink);font-weight:700}button:hover{background:#383832}a:hover{text-decoration-thickness:2px;color:#102f4e}input:hover,select:hover{border-color:#625e55}input:focus,select:focus,button:focus,a:focus,summary:focus{outline:3px solid var(--focus);outline-offset:2px}.result-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--ink);padding:9px 0;gap:12px}.result-head h2,.alerts h2{font-family:Georgia,serif;margin:0;font-size:1.45rem}.row{display:grid;grid-template-columns:72px 120px minmax(280px,1.2fr) minmax(300px,2fr) 150px;gap:18px;padding:18px 0;border-bottom:1px solid var(--line);align-items:start}.row>*{min-width:0}.type{font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.title{font-family:Georgia,serif;font-size:1.15rem;margin:4px 0}.agency{font-size:.8rem;font-weight:700}.reason{color:var(--muted);line-height:1.5}.status{display:inline-block;padding:5px 8px;border:1px solid currentColor;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em}.status.direct_epesf,.status.potential_sector_impact{color:var(--ok)}.status.needs_review{color:var(--warn)}.status.not_relevant{color:var(--muted)}details{margin-top:10px}summary{cursor:pointer;font-weight:700;font-size:.82rem}.summary{border-top:2px solid var(--gold);padding-top:10px;line-height:1.55;margin:12px 0}.links{display:flex;flex-direction:column;gap:7px}a{color:#234d75;text-underline-offset:3px}.alerts{border:2px solid var(--bad);padding:16px;margin:22px 0}.alerts h2{color:var(--bad)}.alerts ul{margin-bottom:0}.empty{padding:48px 0;border-bottom:1px solid var(--line);font-family:Georgia,serif;font-size:1.3rem}.foot{margin-top:24px;color:var(--muted);font-size:.78rem}::-webkit-scrollbar{width:12px;height:12px}::-webkit-scrollbar-track{background:var(--paper)}::-webkit-scrollbar-thumb{background:var(--gold);border:3px solid var(--paper)}
.actions{display:flex;align-items:center;gap:16px}.selection-form{margin:0}.selection-form button{width:auto}.selection-form button:disabled{cursor:not-allowed;background:#77736a;border-color:#77736a}.pick{display:flex;justify-content:center;padding-top:2px}.pick label{display:flex;align-items:center;gap:7px;text-transform:none;letter-spacing:0;font-size:.78rem;cursor:pointer}.pick input{width:20px;height:20px;min-height:0;margin:0;accent-color:var(--ink)}.pick input:disabled{cursor:not-allowed}.period-nav{display:flex;gap:14px;align-items:center;margin:-8px 0 12px;font-size:.82rem}.notice{padding:13px 15px;margin:18px 0;border-top:2px solid var(--ok);background:#edf5ed}.notice.error{border-color:var(--bad);background:#f8eaea}
@media(max-width:1050px){.shell{padding:18px}.mast{grid-template-columns:1fr}.run{border-left:0;border-top:3px solid var(--gold);padding:12px 0}.metrics{grid-template-columns:repeat(2,1fr)}.metric:nth-child(2){border-right:0}.filters{grid-template-columns:1fr 1fr}.filters label:last-of-type{grid-column:1/-1}.row{grid-template-columns:1fr}.links{flex-direction:row;flex-wrap:wrap}}
@media(max-width:520px){.filters{grid-template-columns:1fr}.filters label:last-of-type{grid-column:auto}.metrics{grid-template-columns:repeat(2,1fr)}.metric:nth-child(odd){border-right:1px solid var(--line)}.metric:nth-child(even){border-right:0}.result-head{align-items:flex-start;flex-direction:column}.actions{width:100%;justify-content:space-between;flex-wrap:wrap}}
@media(max-width:360px){.metrics{grid-template-columns:1fr}.metric{border-right:0!important}}
"""


def render_page(app: WebApplication, query: Query) -> bytes:
    status = app.database.status()
    latest = app.latest_date()
    if not query.day and latest and not query.history:
        query = Query(
            day=latest, relevance=query.relevance, text=query.text,
            email_status=query.email_status, email_items=query.email_items,
            email_files=query.email_files, email_error=query.email_error,
        )
    rows = app.publications(query)
    ready_ids = {int(row["id"]) for row in rows if row.get("conceptual_summary")}
    ready_count = len(ready_ids)
    issues = app.operational_issues()
    last = status.get("last_run") or {}
    counts = app.date_stats(query.day)
    options = [
        ("active", "Seleccionadas y pendientes"), ("all", "Todas"),
        ("direct_epesf", "Impacto directo"),
        ("potential_sector_impact", "Impacto potencial"),
        ("needs_review", "Revisar"), ("not_relevant", "Descartadas"),
    ]
    option_html = "".join(
        f'<option value="{_h(value)}"{" selected" if query.relevance == value else ""}>{_h(label)}</option>'
        for value, label in options
    )
    rows_html = []
    for row in rows:
        documents = row.get("documents", [])
        doc_links = "".join(
            f'<a href="/document/{doc["id"]}" target="_blank">'
            f'{"PDF principal" if doc["kind"] == "main" else "Anexo"} · {doc["page_count"] or "?"} pág.</a>'
            for doc in documents
        )
        summary = row.get("conceptual_summary")
        details = ""
        if summary or row.get("description"):
            details = '<details><summary>Ver detalle</summary>'
            if summary:
                details += f'<div class="summary"><strong>Resumen conceptual</strong><br>{_h(summary)}'
                if row.get("epesf_relationship"):
                    details += f'<br><strong>Relación con EPESF:</strong> {_h(row["epesf_relationship"])}'
                details += "</div>"
            if row.get("description"):
                details += f'<p class="reason">{_h(row["description"])}</p>'
            details += "</details>"
        publication_id = int(row["id"])
        if query.day and publication_id in ready_ids:
            picker = (
                f'<label><input type="checkbox" name="selected" '
                f'value="{publication_id}"> Incluir</label>'
            )
        else:
            reason = "Elegí una fecha" if not query.day else "Sin resumen"
            picker = f'<label title="{reason}"><input type="checkbox" disabled> {reason}</label>'
        rows_html.append(f"""
          <article class="row">
            <div class="pick">{picker}</div>
            <div><div class="type">{_h(row['category'])}</div><div class="date">{_h(row['publication_date'])}</div></div>
            <div><div class="agency">{_h(row['agency'])}</div><div class="title">{_h(row['title'])}</div><div>{_h(row['reference'])}</div></div>
            <div><span class="status {_h(row['relevance'])}">{_h(_label(str(row['relevance'])))}</span><p class="reason">{_h(row['relevance_reason'])}</p>{details}</div>
            <div class="links"><a href="{_h(row['detail_url'])}" target="_blank" rel="noreferrer">Aviso en BORA</a>{doc_links}</div>
          </article>""")
    content = "".join(rows_html) or '<div class="empty">No hay publicaciones para estos filtros.</div>'
    alerts = ""
    if issues:
        alert_items = []
        for issue in issues:
            link = ""
            if issue.get("url"):
                link = f' · <a href="{_h(issue["url"])}" target="_blank" rel="noreferrer">Abrir aviso</a>'
            alert_items.append(
                f'<li><strong>{_h(issue["kind"])} · {_h(issue["title"])}</strong>: '
                f'{_h(issue["detail"])}{link}</li>'
            )
        alert_rows = "".join(alert_items)
        alerts = f'<section class="alerts"><h2>Requiere atención</h2><ul>{alert_rows}</ul></section>'
    view_parameters = {
        "date": query.day, "relevance": query.relevance, "q": query.text,
    }
    if query.history:
        view_parameters["history"] = "1"
    params = urlencode(view_parameters)
    notice = ""
    if query.email_status == "prepared":
        item_label = "publicación" if query.email_items == 1 else "publicaciones"
        file_label = "archivo" if query.email_files == 1 else "archivos"
        prepared_verb = "Se preparó" if query.email_items == 1 else "Se prepararon"
        notice = (
            f'<div class="notice" role="status">{prepared_verb} {_h(query.email_items)} '
            f'{item_label} en {_h(query.email_files)} {file_label} .eml y se abrió el correo '
            "predeterminado. Completá remitente y destinatarios antes de enviar.</div>"
        )
    elif query.email_error:
        notice = f'<div class="notice error" role="alert">{_h(query.email_error)}</div>'
    hidden = (
        f'<input type="hidden" name="date" value="{_h(query.day)}">'
        f'<input type="hidden" name="relevance" value="{_h(query.relevance)}">'
        f'<input type="hidden" name="q" value="{_h(query.text)}">'
        + ('<input type="hidden" name="history" value="1">' if query.history else '')
    )
    if not query.day:
        disabled = ' disabled title="Elegí una fecha para preparar el correo"'
    elif not ready_count:
        disabled = ' disabled title="No hay publicaciones filtradas con resumen completo"'
    else:
        disabled = ""
    period_label = query.day or "Histórico desde noviembre de 2025"
    period_nav = (
        '<div class="period-nav"><a href="/?history=1&relevance=active">Ver todo el histórico</a></div>'
        if query.day else
        f'<div class="period-nav"><a href="/?date={_h(latest)}&relevance=active">Volver a la última edición</a></div>'
    )
    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boletín EPESF</title><style>{CSS}</style></head>
    <body><main class="shell"><header class="mast"><div><h1>Boletín EPESF</h1><div class="date">Período consultado: <strong>{_h(period_label)}</strong></div><div class="context">Seguimiento normativo de la Primera Sección del BORA</div></div>
    <div class="run"><span class="context">Última ejecución</span><strong>{_h(_label(last.get('status')))}</strong><span>{_h(_timestamp(last.get('finished_at')))}</span></div></header><div class="workflow">
    <section class="metrics" aria-label="Estado general"><div class="metric"><b>{int(counts.get('total') or 0)}</b><span>publicaciones registradas</span></div><div class="metric"><b>{int(counts.get('relevant') or 0)}</b><span>relevantes</span></div><div class="metric"><b>{int(counts.get('downloaded') or 0)}</b><span>documentos descargados</span></div><div class="metric"><b>{int(status.get('failed_dates') or 0)}</b><span>fechas con fallas</span></div></section>
    {alerts}{notice}<form class="filters" method="get"><label>Fecha<input type="date" name="date" value="{_h(query.day)}"></label><label>Relevancia<select name="relevance">{option_html}</select></label><label>Buscar<input type="search" name="q" value="{_h(query.text)}" placeholder="Organismo, tipo, número o texto"></label><button type="submit">Aplicar filtros</button></form>{period_nav}
    <section><form class="selection-form" action="/prepare-email" method="post">{hidden}<div class="result-head"><h2>Publicaciones</h2><div class="actions"><a href="/export.csv?{params}">Exportar esta vista</a><button type="submit"{disabled}>Generar correo con seleccionadas</button></div></div>{content}</form></section>
    </div><footer class="foot">Servicio local · Los datos y documentos permanecen en este equipo.</footer></main></body></html>"""
    return page.encode("utf-8")


def create_handler(app: WebApplication):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/prepare-email":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            origin = self.headers.get("Origin", "")
            expected_origin = f"http://{self.headers.get('Host', '')}"
            if origin and origin != expected_origin:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            if length > 8192:
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            query = Query.from_url(self.rfile.read(length).decode("utf-8"))
            parameters = {
                "date": query.day, "relevance": query.relevance, "q": query.text,
            }
            if query.history:
                parameters["history"] = "1"
            try:
                artifacts = app.prepare_email(query)
                parameters.update({
                    "email": "prepared",
                    "items": str(sum(item.item_count for item in artifacts)),
                    "files": str(len(artifacts)),
                })
            except (OSError, ValueError) as exc:
                parameters["email_error"] = str(exc)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/?" + urlencode(parameters))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(render_page(app, Query.from_url(parsed.query)), "text/html; charset=utf-8")
                return
            if parsed.path == "/health":
                self._send(json.dumps({"status": "ok"}).encode(), "application/json")
                return
            if parsed.path == "/export.csv":
                query = Query.from_url(parsed.query)
                rows = app.publications(query)
                stream = io.StringIO(newline="")
                fields = ["publication_date", "category", "agency", "title", "reference", "relevance", "relevance_reason", "detail_url"]
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
                writer.writeheader(); writer.writerows(rows)
                self._send(stream.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "publicaciones_filtradas.csv")
                return
            if parsed.path.startswith("/document/"):
                try:
                    document_id = int(parsed.path.rsplit("/", 1)[1])
                except ValueError:
                    self.send_error(HTTPStatus.NOT_FOUND); return
                document = app.document(document_id)
                if not document:
                    self.send_error(HTTPStatus.NOT_FOUND); return
                path, _ = document
                self._send(path.read_bytes(), "application/pdf", path.name, inline=True)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _send(self, body: bytes, content_type: str, filename: str | None = None, inline: bool = False) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'; form-action 'self'")
            if filename:
                disposition = "inline" if inline else "attachment"
                self.send_header("Content-Disposition", f'{disposition}; filename="{filename.encode("ascii", "ignore").decode()}"')
            self.end_headers(); self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def serve(database: Database, data_dir: Path, port: int = 8765, open_browser: bool = True) -> None:
    database.migrate()
    app = WebApplication(database, data_dir)
    server = ThreadingHTTPServer(("127.0.0.1", port), create_handler(app))
    url = f"http://127.0.0.1:{server.server_port}/"
    if open_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    print(f"Interfaz disponible en {url} (Ctrl+C para cerrar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
