from __future__ import annotations

import csv
import html
import io
import json
import logging
import os
import threading
import time
import uuid
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
from .priority import publication_sort_key
from .summaries import PROMPT_VERSION, configured_summarizer, retryable_summary_error
from .web_ui import CSS, SCRIPT


STATUS_LABELS = {
    "direct_epesf": "Impacto directo",
    "potential_sector_impact": "Impacto potencial",
    "needs_review": "Sin clasificar",
    "not_relevant": "Descartada",
    "complete": "Completo",
    "partial": "Parcial",
    "failed": "Con error",
    "not_published": "No publicado",
}
LOGGER = logging.getLogger(__name__)


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
    category: str = ""
    text: str = ""
    history: bool = False
    selected_ids: tuple[int, ...] = ()
    email_status: str = ""
    email_items: int = 0
    email_files: int = 0
    email_error: str = ""
    email_names: tuple[str, ...] = ()
    end_day: str = ""
    view: str = "day"
    month: str = ""
    page: int = 1

    @classmethod
    def from_url(cls, query: str) -> "Query":
        values = parse_qs(query)
        day_value = values.get("date", [""])[0].strip()
        end_value = values.get("to", [""])[0].strip()
        item_value = values.get("items", ["0"])[0]
        file_value = values.get("files", ["0"])[0]
        selected_ids = tuple(
            int(value) for value in values.get("selected", []) if value.isdigit()
        )
        return cls(
            day=day_value,
            relevance=values.get("relevance", ["active"])[0].strip(),
            category=values.get("category", [""])[0].strip(),
            text=values.get("q", [""])[0].strip(),
            history=values.get("history", [""])[0] == "1",
            selected_ids=selected_ids,
            email_status=values.get("email", [""])[0].strip(),
            email_items=int(item_value) if item_value.isdigit() else 0,
            email_files=int(file_value) if file_value.isdigit() else 0,
            email_error=values.get("email_error", [""])[0].strip(),
            email_names=tuple(values.get("eml", [])),
            end_day="" if end_value == day_value else end_value,
            view=values.get("view", ["history" if values.get("history") == ["1"] else "day"])[0],
            month=values.get("month", [""])[0].strip(),
            page=max(1, int(values.get("page", ["1"])[0])) if values.get("page", ["1"])[0].isdigit() else 1,
        )


class WebApplication:
    def __init__(self, database: Database, data_dir: Path,
                 email_opener: Callable[[Path], None] | None = None):
        self.database = database
        self.data_dir = data_dir.resolve()
        self.email_opener = email_opener or open_eml
        self.action_lock = threading.Lock()
        self.summary_lock = threading.Lock()
        self.auto_summary_guard = threading.Lock()
        self.auto_summary_thread: threading.Thread | None = None
        self.email_open_guard = threading.Lock()
        self.email_open_jobs: dict[str, dict[str, str]] = {}

    def publications(self, query: Query) -> list[dict[str, object]]:
        clauses: list[str] = []
        parameters: list[object] = []
        if query.day and query.end_day:
            clauses.append("p.publication_date BETWEEN ? AND ?")
            parameters.extend((query.day, query.end_day))
        elif query.day:
            clauses.append("p.publication_date=?")
            parameters.append(query.day)
        if query.relevance == "active":
            clauses.append("p.relevance!='not_relevant'")
        elif query.relevance == "selected":
            clauses.append("p.relevance IN ('direct_epesf','potential_sector_impact')")
        elif query.relevance and query.relevance != "all":
            clauses.append("p.relevance=?")
            parameters.append(query.relevance)
        if query.category:
            clauses.append("p.category=?")
            parameters.append(query.category)
        if query.text:
            clauses.append("lower(p.category||' '||p.agency||' '||p.title||' '||p.reference||' '||p.description) LIKE ?")
            parameters.append(f"%{query.text.casefold()}%")
        if query.view == "failures":
            clauses.append("(p.document_status='error' OR p.summary_status='error' OR p.delivery_status IN ('error','uncertain') OR EXISTS (SELECT 1 FROM coverage c WHERE c.publication_date=p.publication_date AND c.status='failed'))")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(f"""
                SELECT p.*,
                  (SELECT conceptual_summary FROM summaries s
                   WHERE s.publication_id=p.id AND s.status='complete'
                   ORDER BY s.id DESC LIMIT 1) conceptual_summary,
                  (SELECT epesf_relationship FROM summaries s
                   WHERE s.publication_id=p.id AND s.status='complete'
                   ORDER BY s.id DESC LIMIT 1) epesf_relationship,
                  (SELECT model FROM summaries s
                   WHERE s.publication_id=p.id AND s.status='complete'
                   ORDER BY s.id DESC LIMIT 1) summary_model
                FROM publications p {where}
            """, parameters).fetchall()
            result = sorted((dict(row) for row in rows), key=publication_sort_key)
            documents_by_publication: dict[int, list[dict[str, object]]] = {}
            for document in connection.execute("SELECT id,publication_id,kind,path,page_count FROM documents ORDER BY id"):
                documents_by_publication.setdefault(int(document["publication_id"]), []).append(dict(document))
            for item in result:
                item["documents"] = documents_by_publication.get(int(item["id"]), [])
            return result

    def latest_date(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT MAX(publication_date) value FROM (SELECT publication_date FROM publications UNION SELECT publication_date FROM coverage)").fetchone()
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
                SELECT id,publication_date,title,detail_url,document_status,summary_status,delivery_status
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
                               "id": str(row["id"]), "day": str(row["publication_date"]),
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
        if not query.day or query.end_day or not query.selected_ids:
            return []
        visible_ids = {int(row["id"]) for row in self.publications(query)}
        selected_ids = tuple(
            publication_id for publication_id in query.selected_ids
            if publication_id in visible_ids
        )
        return self.database.bulletin_items(date.fromisoformat(query.day), selected_ids)

    def email_file(self, name: str) -> Path | None:
        if not name or any(character in name for character in '/\\:') or not name.endswith('.eml'):
            return None
        path = (self.data_dir / 'outbox' / name).resolve()
        if not path.is_relative_to(self.data_dir / 'outbox') or not path.is_file():
            return None
        with self.database.connect() as connection:
            registered = connection.execute("SELECT path FROM deliveries WHERE status='prepared'").fetchall()
        return path if any(Path(row['path']).resolve() == path for row in registered) else None

    def prepare_email(self, query: Query, *, open_files: bool = True) -> list[EmailArtifact]:
        if query.end_day:
            raise ValueError("Elegí un solo día para preparar el correo")
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
        if open_files:
            for artifact in artifacts:
                self.email_opener(artifact.path.resolve())
        return artifacts

    def request_email_open(self, names: str | tuple[str, ...]) -> str:
        names = (names,) if isinstance(names, str) else tuple(dict.fromkeys(names))
        paths = [self.email_file(name) for name in names]
        if not paths or any(path is None for path in paths):
            raise ValueError('El borrador no está disponible. Generá nuevamente el correo.')
        with self.email_open_guard:
            if any(job['status'] == 'pending' for job in self.email_open_jobs.values()):
                raise ValueError('Hay una apertura de correo pendiente. Revisá tu aplicación de correo o descargá el .eml.')
            self.email_open_jobs.clear()
            token = uuid.uuid4().hex
            self.email_open_jobs[token] = {'status': 'pending'}

        def choose() -> None:
            try:
                errors = []
                for path in paths:
                    try:
                        self.email_opener(path)
                    except Exception as exc:
                        errors.append(str(exc) or 'No se pudo abrir la aplicación de correo.')
                result = {'status': 'error', 'error': ' '.join(dict.fromkeys(errors))} if errors else {'status': 'complete'}
            except Exception as exc:
                result = {'status': 'error', 'error': str(exc) or 'No se pudo abrir la aplicación. Descargá el .eml.'}
            with self.email_open_guard:
                self.email_open_jobs[token] = result

        threading.Thread(target=choose, daemon=True).start()
        return token

    def email_open_status(self, token: str) -> dict[str, str] | None:
        with self.email_open_guard:
            state = self.email_open_jobs.get(token)
            return dict(state) if state else None

    def consult_day(self, day_value: str) -> None:
        from .bora import BoraClient
        from .pipeline import run
        from .relevance import DEFAULT_RULES, load_rules

        day = date.fromisoformat(day_value)
        if day > date.today():
            raise ValueError("La fecha no puede ser futura")
        rules_path = Path("config/relevance_rules.json")
        rules = load_rules(rules_path) if rules_path.is_file() else DEFAULT_RULES
        result = run(self.database, BoraClient(rules=rules), self.data_dir,
                     "daily", day, day)
        if result.get("failed"):
            raise ValueError("La consulta no se completó. Revisá el detalle en Fallas y reintentá.")
        self.start_auto_summaries()

    def start_auto_summaries(self) -> bool:
        """Fill pending potential-impact summaries without blocking the web request."""
        if os.environ.get("EPE_AUTO_SUMMARIES", "1").strip().lower() not in ("1", "true", "yes"):
            return False
        with self.auto_summary_guard:
            if self.auto_summary_thread and self.auto_summary_thread.is_alive():
                return True
            try:
                model, summarizer = configured_summarizer(self.data_dir)
            except ValueError as exc:
                LOGGER.warning("Resúmenes automáticos no iniciados: %s", exc)
                return False
            worker = threading.Thread(
                target=self._run_auto_summaries,
                args=(model, summarizer),
                name="epe-auto-summaries",
                daemon=True,
            )
            self.auto_summary_thread = worker
            worker.start()
            return True

    def auto_summary_status(self) -> dict[str, int | bool]:
        with self.database.connect() as connection:
            counts = dict(connection.execute("""
                SELECT summary_status,COUNT(*) FROM publications
                WHERE relevance='potential_sector_impact'
                  AND document_status='downloaded'
                GROUP BY summary_status
            """).fetchall())
        return {
            "running": bool(self.auto_summary_thread and self.auto_summary_thread.is_alive()),
            "pending": counts.get("pending", 0),
            "ready": counts.get("ready", 0),
            "error": counts.get("error", 0),
        }

    def _run_auto_summaries(self, model: str, summarizer) -> None:
        consecutive_failures = 0
        retry_delay = 30
        while True:
            delay = 1
            with self.summary_lock:
                candidates = self.database.summary_candidates(
                    model, PROMPT_VERSION, limit=1,
                    relevance="potential_sector_impact", pending_only=True,
                )
                if not candidates:
                    return
                candidate = candidates[0]
                try:
                    summary = summarizer.summarize(candidate)
                    self.database.save_summary(candidate, summary, model, PROMPT_VERSION)
                    consecutive_failures = 0
                    retry_delay = 30
                except Exception as exc:
                    if retryable_summary_error(exc):
                        delay = retry_delay
                        retry_delay = min(retry_delay * 2, 300)
                        LOGGER.warning("Resumen automático pendiente tras falla temporal "
                                       "para publicación %s: %s", candidate.publication_id, exc)
                    else:
                        self.database.mark_summary_error(
                            candidate, model, PROMPT_VERSION,
                            "No se pudo generar el resumen automático. Reintentá manualmente.",
                        )
                        consecutive_failures += 1
                        delay = 5
                        LOGGER.error("Resumen automático falló para publicación %s: %s",
                                     candidate.publication_id, exc)
            if consecutive_failures >= 3:
                LOGGER.error("Resúmenes automáticos pausados tras tres fallas consecutivas")
                return
            time.sleep(delay)

    def generate_summary(self, publication_id: int) -> None:
        with self.summary_lock:
            model, summarizer = configured_summarizer(self.data_dir)
            with self.database.connect() as connection:
                row = connection.execute("SELECT publication_date FROM publications WHERE id=?", (publication_id,)).fetchone()
            if not row:
                raise ValueError("La publicación no está registrada")
            candidates = self.database.summary_candidates(model, PROMPT_VERSION,
                             include_completed=True, publication_date=date.fromisoformat(row["publication_date"]))
            candidate = next((item for item in candidates if item.publication_id == publication_id), None)
            if not candidate or not candidate.full_text.strip():
                raise ValueError("Hace falta un documento descargado con texto para generar el resumen. Consultá nuevamente la fecha.")
            try:
                summary = summarizer.summarize(candidate)
            except Exception:
                message = "El proveedor de IA no pudo generar el resumen. Reintentá o consultá el PDF original."
                self.database.mark_summary_error(candidate, model, PROMPT_VERSION, message)
                raise ValueError(message) from None
            self.database.save_summary(candidate, summary, model, PROMPT_VERSION)


def open_eml(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path.resolve()), 'open')  # type: ignore[attr-defined]
        return
    if not webbrowser.open(path.resolve().as_uri()):
        raise OSError('No se pudo abrir la aplicación de correo.')


def render_page(app: WebApplication, query: Query, raw_query: str = "") -> bytes:
    from .web_views import render
    return render(app, query, raw_query)


def create_handler(app: WebApplication):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/prepare-email", "/open-email", "/summary", "/consult"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            origin = self.headers.get("Origin", "")
            expected_origin = f"http://{self.headers.get('Host', '')}"
            if (urlparse(expected_origin).hostname not in ("127.0.0.1", "localhost")
                    or (origin and origin != expected_origin)
                    or self.headers.get("Sec-Fetch-Site") == "cross-site"):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            if length < 0 or length > 65536:
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            try:
                body = self.rfile.read(length).decode("utf-8")
            except UnicodeDecodeError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            query = Query.from_url(body)
            action_values = parse_qs(body)
            if parsed.path == '/open-email':
                try:
                    token = app.request_email_open(query.email_names)
                    self._send(json.dumps({'token': token, 'status': 'pending'}).encode(), 'application/json', status=HTTPStatus.ACCEPTED)
                except ValueError as exc:
                    self._send(json.dumps({'error': str(exc)}, ensure_ascii=False).encode(), 'application/json', status=HTTPStatus.BAD_REQUEST)
                return
            if parsed.path in ("/summary", "/consult"):
                if not app.action_lock.acquire(blocking=False):
                    self._send(json.dumps({"error": "Hay otra consulta o resumen en curso. Esperá a que termine y reintentá."}).encode(), "application/json", status=HTTPStatus.CONFLICT)
                    return
                try:
                    if parsed.path == "/consult":
                        app.consult_day(query.day)
                    else:
                        # Query.selected_ids is reserved for explicit email/CSV selection.
                        app.generate_summary(int(action_values.get("id", ["0"])[0]))
                    self._send(b'{"status":"complete"}', "application/json")
                except ValueError as exc:
                    self._send(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"), "application/json", status=HTTPStatus.BAD_REQUEST)
                except Exception:
                    self._send(json.dumps({"error": "No se pudo completar la acción. Revisá la configuración local, el PDF original y la vista Fallas."}).encode(), "application/json", status=HTTPStatus.BAD_REQUEST)
                finally:
                    app.action_lock.release()
                return
            parameters = {
                "date": query.day, "relevance": query.relevance, "category": query.category, "q": query.text,
                "to": query.end_day, "view": query.view,
            }
            if query.history:
                parameters["history"] = "1"
            result: dict[str, object] = {'generated': False}
            try:
                artifacts = app.prepare_email(query, open_files=False)
                parameters.update(email='prepared', items=str(sum(item.item_count for item in artifacts)), files=str(len(artifacts)), eml=[artifact.path.name for artifact in artifacts])
                result = {'generated': True, 'files': [{'name': artifact.path.name, 'url': '/email?' + urlencode({'name': artifact.path.name})} for artifact in artifacts]}
                try:
                    result['token'] = app.request_email_open(tuple(artifact.path.name for artifact in artifacts))
                except (OSError, ValueError) as exc:
                    result['error'] = str(exc)
                    parameters['email_error'] = str(exc)
            except (OSError, ValueError) as exc:
                parameters["email_error"] = str(exc)
                result['error'] = str(exc)
            redirect = '/?' + urlencode(parameters, doseq=True)
            if 'application/json' in self.headers.get('Accept', ''):
                self._send(json.dumps(result, ensure_ascii=False).encode(), 'application/json', status=HTTPStatus.OK if result['generated'] else HTTPStatus.BAD_REQUEST)
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", redirect)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(render_page(app, Query.from_url(parsed.query), parsed.query), "text/html; charset=utf-8")
                return
            if parsed.path == "/ui.js":
                self._send(SCRIPT.encode("utf-8"), "text/javascript; charset=utf-8")
                return
            if parsed.path == "/health":
                self._send(json.dumps({"status": "ok"}).encode(), "application/json")
                return
            if parsed.path == "/summary-status":
                self._send(json.dumps(app.auto_summary_status()).encode(), "application/json")
                return
            if parsed.path == '/email':
                name = parse_qs(parsed.query).get('name', [''])[0]
                path = app.email_file(name)
                if not path:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send(path.read_bytes(), 'message/rfc822', path.name)
                return
            if parsed.path == '/email-open-status':
                state = app.email_open_status(parse_qs(parsed.query).get('token', [''])[0])
                if state is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send(json.dumps(state, ensure_ascii=False).encode(), 'application/json')
                return
            if parsed.path == "/export.csv":
                query = Query.from_url(parsed.query)
                rows = app.publications(query)
                if query.selected_ids:
                    rows = [row for row in rows if int(row["id"]) in query.selected_ids]
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

        def _send(self, body: bytes, content_type: str, filename: str | None = None, inline: bool = False, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
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
    app.start_auto_summaries()
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
