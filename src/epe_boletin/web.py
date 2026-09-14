from __future__ import annotations

import csv
import html
import io
import json
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from .db import Database


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

    @classmethod
    def from_url(cls, query: str) -> "Query":
        values = parse_qs(query)
        return cls(
            day=values.get("date", [""])[0].strip(),
            relevance=values.get("relevance", ["active"])[0].strip(),
            text=values.get("q", [""])[0].strip(),
        )


class WebApplication:
    def __init__(self, database: Database, data_dir: Path):
        self.database = database
        self.data_dir = data_dir.resolve()

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

    def date_stats(self, day: str) -> dict[str, int]:
        with self.database.connect() as connection:
            row = connection.execute("""
                SELECT COUNT(*) total,
                  COALESCE(SUM(relevance IN ('direct_epesf','potential_sector_impact')),0) relevant,
                  COALESCE(SUM(document_status='downloaded'),0) downloaded
                FROM publications WHERE publication_date=?
            """, (day,)).fetchone()
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


CSS = """
:root{--ink:#171715;--paper:#f5f2eb;--panel:#fffdf8;--muted:#66645f;--line:#d8d2c5;--gold:#b88a27;--focus:#624600;--ok:#27643a;--warn:#8b5a11;--bad:#9d2f2f;font-family:Segoe UI,Tahoma,Arial,sans-serif;color:var(--ink);background:var(--paper);scrollbar-color:var(--gold) var(--paper)}
*{box-sizing:border-box}::selection{background:#d8b763;color:var(--ink)}body{margin:0;overflow-wrap:anywhere}.shell{max-width:1480px;margin:auto;padding:28px 34px 64px}.mast{display:grid;grid-template-columns:1fr auto;gap:24px;border-top:5px solid var(--ink);border-bottom:2px solid var(--gold);padding:18px 0 20px}.mast>*{min-width:0}.context{font-size:.82rem;color:var(--muted);margin-top:7px}h1{font-family:Georgia,serif;font-size:clamp(2rem,4vw,4.2rem);line-height:.95;margin:.22em 0}.date{font-variant-numeric:tabular-nums;font-size:1.1rem}.run{align-self:center;padding:10px 0 0;min-width:240px}.run strong{display:block;font-size:1.15rem}.workflow{border-left:2px solid var(--gold);padding-left:16px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.metric{padding:18px 16px;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric b{display:block;font-family:Georgia,serif;font-size:2rem}.metric span{color:var(--muted);font-size:.82rem}.filters{display:grid;grid-template-columns:180px 210px minmax(220px,1fr) auto;gap:12px;padding:22px 0;align-items:end}label{display:grid;gap:6px;min-width:0;font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;color:var(--muted)}input,select,button{width:100%;max-width:100%;font:inherit;border:1px solid #aaa396;background:var(--panel);padding:10px 11px;color:var(--ink);caret-color:var(--focus);min-height:42px}button{cursor:pointer;background:var(--ink);color:white;border-color:var(--ink);font-weight:700}button:hover{background:#383832}a:hover{text-decoration-thickness:2px;color:#102f4e}input:hover,select:hover{border-color:#625e55}input:focus,select:focus,button:focus,a:focus,summary:focus{outline:3px solid var(--focus);outline-offset:2px}.result-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--ink);padding:9px 0;gap:12px}.result-head h2,.alerts h2{font-family:Georgia,serif;margin:0;font-size:1.45rem}.row{display:grid;grid-template-columns:120px minmax(280px,1.2fr) minmax(300px,2fr) 150px;gap:18px;padding:18px 0;border-bottom:1px solid var(--line);align-items:start}.row>*{min-width:0}.type{font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.title{font-family:Georgia,serif;font-size:1.15rem;margin:4px 0}.agency{font-size:.8rem;font-weight:700}.reason{color:var(--muted);line-height:1.5}.status{display:inline-block;padding:5px 8px;border:1px solid currentColor;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em}.status.direct_epesf,.status.potential_sector_impact{color:var(--ok)}.status.needs_review{color:var(--warn)}.status.not_relevant{color:var(--muted)}details{margin-top:10px}summary{cursor:pointer;font-weight:700;font-size:.82rem}.summary{border-top:2px solid var(--gold);padding-top:10px;line-height:1.55;margin:12px 0}.links{display:flex;flex-direction:column;gap:7px}a{color:#234d75;text-underline-offset:3px}.alerts{border:2px solid var(--bad);padding:16px;margin:22px 0}.alerts h2{color:var(--bad)}.alerts ul{margin-bottom:0}.empty{padding:48px 0;border-bottom:1px solid var(--line);font-family:Georgia,serif;font-size:1.3rem}.foot{margin-top:24px;color:var(--muted);font-size:.78rem}::-webkit-scrollbar{width:12px;height:12px}::-webkit-scrollbar-track{background:var(--paper)}::-webkit-scrollbar-thumb{background:var(--gold);border:3px solid var(--paper)}
@media(max-width:1050px){.shell{padding:18px}.mast{grid-template-columns:1fr}.run{border-left:0;border-top:3px solid var(--gold);padding:12px 0}.metrics{grid-template-columns:repeat(2,1fr)}.metric:nth-child(2){border-right:0}.filters{grid-template-columns:1fr 1fr}.filters label:last-of-type{grid-column:1/-1}.row{grid-template-columns:1fr}.links{flex-direction:row;flex-wrap:wrap}}
@media(max-width:520px){.filters{grid-template-columns:1fr}.filters label:last-of-type{grid-column:auto}.metrics{grid-template-columns:repeat(2,1fr)}.metric:nth-child(odd){border-right:1px solid var(--line)}.metric:nth-child(even){border-right:0}}
@media(max-width:360px){.metrics{grid-template-columns:1fr}.metric{border-right:0!important}}
"""


def render_page(app: WebApplication, query: Query) -> bytes:
    status = app.database.status()
    latest = app.latest_date()
    if not query.day and latest:
        query = Query(latest, query.relevance, query.text)
    rows = app.publications(query)
    issues = app.operational_issues()
    last = status.get("last_run") or {}
    counts = app.date_stats(query.day) if query.day else {"total": 0, "relevant": 0, "downloaded": 0}
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
        documents = row.pop("documents", [])
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
        rows_html.append(f"""
          <article class="row">
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
    params = urlencode({"date": query.day, "relevance": query.relevance, "q": query.text})
    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boletín EPESF</title><style>{CSS}</style></head>
    <body><main class="shell"><header class="mast"><div><h1>Boletín EPESF</h1><div class="date">Edición consultada: <strong>{_h(query.day or 'sin datos')}</strong></div><div class="context">Seguimiento normativo de la Primera Sección del BORA</div></div>
    <div class="run"><span class="context">Última ejecución</span><strong>{_h(_label(last.get('status')))}</strong><span>{_h(_timestamp(last.get('finished_at')))}</span></div></header><div class="workflow">
    <section class="metrics" aria-label="Estado general"><div class="metric"><b>{int(counts.get('total') or 0)}</b><span>publicaciones registradas</span></div><div class="metric"><b>{int(counts.get('relevant') or 0)}</b><span>relevantes</span></div><div class="metric"><b>{int(counts.get('downloaded') or 0)}</b><span>documentos descargados</span></div><div class="metric"><b>{int(status.get('failed_dates') or 0)}</b><span>fechas con fallas</span></div></section>
    {alerts}<form class="filters" method="get"><label>Fecha<input type="date" name="date" value="{_h(query.day)}"></label><label>Relevancia<select name="relevance">{option_html}</select></label><label>Buscar<input type="search" name="q" value="{_h(query.text)}" placeholder="Organismo, tipo, número o texto"></label><button type="submit">Aplicar filtros</button></form>
    <section><div class="result-head"><h2>Publicaciones</h2><a href="/export.csv?{params}">Exportar esta vista</a></div>{content}</section>
    </div><footer class="foot">Servicio local · Los datos y documentos permanecen en este equipo.</footer></main></body></html>"""
    return page.encode("utf-8")


def create_handler(app: WebApplication):
    class Handler(BaseHTTPRequestHandler):
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
