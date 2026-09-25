"""Turso libSQL storage for the HTML-only cloud pilot.

The local Database and its file-backed tables remain untouched. This backend
reuses its SQL methods where the remote schema has the same shape.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .db import Database
from .models import Publication
from .summaries import SummaryCandidate, source_digest
from .turso_preflight import validate_turso_url


CLOUD_SCHEMA_VERSION = 3

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS cloud_schema_info (
        version INTEGER NOT NULL, kind TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY,
        mode TEXT NOT NULL CHECK(mode IN ('daily','historical','simulation')),
        date_from TEXT NOT NULL, date_to TEXT NOT NULL,
        started_at TEXT NOT NULL, finished_at TEXT,
        status TEXT NOT NULL CHECK(status IN ('running','complete','partial','failed')),
        publications_seen INTEGER NOT NULL DEFAULT 0,
        publications_relevant INTEGER NOT NULL DEFAULT 0, error TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS coverage (
        source TEXT NOT NULL, publication_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('complete','not_published','failed')),
        pages_fetched INTEGER NOT NULL DEFAULT 0,
        publication_count INTEGER NOT NULL DEFAULT 0,
        has_supplement INTEGER NOT NULL DEFAULT 0,
        checked_at TEXT NOT NULL, error TEXT,
        PRIMARY KEY(source, publication_date)
    )""",
    """CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL,
        publication_date TEXT NOT NULL, section TEXT NOT NULL,
        category TEXT NOT NULL, agency TEXT NOT NULL, title TEXT NOT NULL,
        reference TEXT NOT NULL, description TEXT NOT NULL,
        detail_url TEXT NOT NULL, has_annexes INTEGER NOT NULL DEFAULT 0,
        relevance TEXT NOT NULL, relevance_reason TEXT NOT NULL,
        relevance_rules_version TEXT NOT NULL DEFAULT 'builtin-2026-09-11.1',
        document_status TEXT NOT NULL DEFAULT 'not_requested'
            CHECK(document_status IN ('pending','downloaded','error','not_requested')),
        classification_status TEXT NOT NULL DEFAULT 'metadata_only',
        summary_status TEXT NOT NULL DEFAULT 'pending',
        delivery_status TEXT NOT NULL DEFAULT 'pending',
        first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
        UNIQUE(source, source_id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_cloud_publications_date ON publications(publication_date)",
    "CREATE INDEX IF NOT EXISTS ix_cloud_publications_relevance ON publications(relevance)",
    """CREATE TABLE IF NOT EXISTS notice_contents (
        publication_id INTEGER PRIMARY KEY REFERENCES publications(id) ON DELETE CASCADE,
        text TEXT NOT NULL, sha256 TEXT NOT NULL,
        notice_url TEXT NOT NULL, pdf_url TEXT NOT NULL,
        pdf_availability TEXT NOT NULL
            CHECK(pdf_availability IN ('available','missing','unknown')),
        annex_status TEXT NOT NULL CHECK(annex_status IN ('none','unread')),
        fetched_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS legacy_pdf_texts (
        publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
        kind TEXT NOT NULL, sha256 TEXT NOT NULL, extracted_text TEXT NOT NULL,
        page_count INTEGER,
        extraction_status TEXT NOT NULL
            CHECK(extraction_status IN ('complete','insufficient')),
        PRIMARY KEY(publication_id,kind,sha256)
    )""",
    """CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY,
        publication_id INTEGER NOT NULL REFERENCES publications(id),
        conceptual_summary TEXT NOT NULL, epesf_relationship TEXT NOT NULL,
        effective_date TEXT NOT NULL, needs_review INTEGER NOT NULL DEFAULT 0,
        model TEXT NOT NULL, prompt_version TEXT NOT NULL,
        source_sha256 TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
        created_at TEXT NOT NULL, status TEXT NOT NULL
            CHECK(status IN ('complete','error')),
        error TEXT,
        UNIQUE(publication_id, model, prompt_version, source_sha256)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_cloud_summaries_publication ON summaries(publication_id,created_at)",
    """CREATE TABLE IF NOT EXISTS cloud_jobs (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('consult','summary')),
        target TEXT NOT NULL, requested_by TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','running','complete','failed')),
        created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, error TEXT
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_cloud_jobs_active ON cloud_jobs(kind,target) WHERE status IN ('pending','running')",
    "CREATE INDEX IF NOT EXISTS ix_cloud_jobs_created ON cloud_jobs(created_at)",
)

_TABLES = frozenset({"cloud_schema_info", "runs", "coverage", "publications",
                     "notice_contents", "legacy_pdf_texts", "summaries", "cloud_jobs"})


class CloudSchemaError(RuntimeError):
    """The selected remote database is not the expected cloud pilot."""


class _Cursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    def _record(self, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(zip((column[0] for column in self._cursor.description), row))

    def fetchone(self) -> dict[str, Any] | None:
        return self._record(self._cursor.fetchone())

    def fetchall(self) -> list[dict[str, Any]]:
        return [self._record(row) for row in self._cursor.fetchall()]

    def __iter__(self) -> Iterator[dict[str, Any]]:
        while (row := self._cursor.fetchone()) is not None:
            yield self._record(row)

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class _Connection:
    def __init__(self, connection: Any):
        self._connection = connection

    def execute(self, sql: str, parameters: Any = ()) -> _Cursor:
        return _Cursor(self._connection.execute(sql, parameters))

    def executemany(self, sql: str, parameters: Any) -> _Cursor:
        return _Cursor(self._connection.executemany(sql, parameters))

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


class TursoDatabase(Database):
    """Remote backend for cloud ingestion and summaries; no local file paths."""

    def __init__(self, url: str, token: str,
                 connector: Callable[..., Any] | None = None):
        validate_turso_url(url)
        if not token.strip():
            raise ValueError("Falta TURSO_AUTH_TOKEN")
        self.url = url
        self.token = token
        self._connector = connector

    @classmethod
    def from_env(cls) -> TursoDatabase:
        return cls(os.environ.get("TURSO_DATABASE_URL", ""),
                   os.environ.get("TURSO_AUTH_TOKEN", ""))

    @contextmanager
    def connect(self) -> Iterator[_Connection]:
        connector = self._connector
        if connector is None:
            import libsql
            connector = libsql.connect
        connection = _Connection(connector(database=self.url, auth_token=self.token))
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            existing = {row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'").fetchall()}
            if existing - _TABLES:
                raise CloudSchemaError("La base Turso contiene tablas ajenas al piloto")
            if "cloud_schema_info" in existing:
                row = connection.execute(
                    "SELECT version,kind FROM cloud_schema_info").fetchone()
                if row and (row["version"] not in (1, 2, CLOUD_SCHEMA_VERSION)
                            or row["kind"] != "epe-html-pilot"):
                    raise CloudSchemaError("Versión de esquema Turso no soportada")
            for statement in _SCHEMA:
                connection.execute(statement)
            row = connection.execute(
                "SELECT version,kind FROM cloud_schema_info").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO cloud_schema_info(version,kind) VALUES (?,?)",
                    (CLOUD_SCHEMA_VERSION, "epe-html-pilot"))
            elif row["version"] in (1, 2):
                connection.execute("UPDATE cloud_schema_info SET version=?",
                                   (CLOUD_SCHEMA_VERSION,))

    def enqueue_job(self, kind: str, target: str, user: str) -> tuple[str, bool]:
        if kind not in ("consult", "summary") or not target or not user:
            raise ValueError("Solicitud inválida")
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        stale = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        with self.connect() as connection:
            connection.execute("""
                UPDATE cloud_jobs SET status='failed',finished_at=?,
                  error='La ejecución no comenzó o excedió el tiempo esperado. Reintentá.'
                WHERE kind=? AND target=? AND status IN ('pending','running')
                  AND COALESCE(started_at,created_at) < ?
            """, (now, kind, target, stale))
            result = connection.execute("""
                INSERT OR IGNORE INTO cloud_jobs(id,kind,target,requested_by,status,created_at)
                VALUES(?,?,?,?,'pending',?)
            """, (job_id, kind, target, user, now))
            if result.rowcount:
                return job_id, True
            current = connection.execute("""
                SELECT id FROM cloud_jobs WHERE kind=? AND target=?
                  AND status IN ('pending','running') ORDER BY created_at DESC LIMIT 1
            """, (kind, target)).fetchone()
            if current is None:
                raise RuntimeError("No se pudo registrar la solicitud")
            return str(current["id"]), False

    def job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM cloud_jobs WHERE id=?", (job_id,)).fetchone()
        if (row and row["status"] in ("pending", "running")
                and datetime.fromisoformat(row["started_at"] or row["created_at"])
                    < datetime.now(timezone.utc) - timedelta(minutes=30)):
            self.finish_job(job_id, "failed",
                            "La ejecución no comenzó o excedió el tiempo esperado. Reintentá.")
            with self.connect() as connection:
                row = connection.execute("SELECT * FROM cloud_jobs WHERE id=?", (job_id,)).fetchone()
        return row

    def claim_job(self, job_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            claimed = connection.execute("""
                UPDATE cloud_jobs SET status='running',started_at=?
                WHERE id=? AND status='pending'
            """, (now, job_id))
            if not claimed.rowcount:
                return None
            return connection.execute("SELECT * FROM cloud_jobs WHERE id=?", (job_id,)).fetchone()

    def finish_job(self, job_id: str, status: str, error: str = "") -> None:
        if status not in ("complete", "failed"):
            raise ValueError("Estado inválido")
        with self.connect() as connection:
            connection.execute("""
                UPDATE cloud_jobs SET status=?,finished_at=?,error=?
                WHERE id=? AND status IN ('pending','running')
            """, (status, datetime.now(timezone.utc).isoformat(), error[:500], job_id))

    def upsert_publications(
        self, items: tuple[tuple[Publication, bool], ...]
    ) -> dict[str, int]:
        # HTML is fetched independently; this backend never downloads documents.
        return super().upsert_publications(tuple((item, False) for item, _ in items))

    def summary_candidates(self, model: str, prompt_version: str,
                           limit: int | None = None,
                           include_completed: bool = False,
                           publication_date: date | None = None,
                           relevance: str | None = None,
                           pending_only: bool = False,
                           publication_id: int | None = None) -> list[SummaryCandidate]:
        if relevance and relevance not in ("direct_epesf", "potential_sector_impact"):
            raise ValueError("Clasificación de resumen inválida")
        filters = ["p.relevance IN ('direct_epesf','potential_sector_impact')"]
        parameters: list[str] = []
        if publication_date:
            filters.append("p.publication_date=?")
            parameters.append(publication_date.isoformat())
        if publication_id is not None:
            filters.append("p.id=?")
            parameters.append(str(publication_id))
        if relevance:
            filters.append("p.relevance=?")
            parameters.append(relevance)
        if pending_only:
            filters.append("p.summary_status='pending'")
        with self.connect() as connection:
            rows = connection.execute(f"""
                SELECT p.*,n.text notice_text,n.sha256 notice_sha256,
                       n.annex_status notice_annex_status
                FROM publications p
                LEFT JOIN notice_contents n ON n.publication_id=p.id
                WHERE {' AND '.join(filters)}
                  AND (n.publication_id IS NOT NULL OR EXISTS (
                      SELECT 1 FROM legacy_pdf_texts d WHERE d.publication_id=p.id))
                ORDER BY p.publication_date,p.id
            """, parameters).fetchall()
            candidates = []
            for row in rows:
                if row["notice_text"] is not None:
                    digest = str(row["notice_sha256"])
                    full_text = str(row["notice_text"])
                    limitations = (
                        "El aviso tiene anexos no analizados; el texto HTML no incluye su contenido."
                        if row["notice_annex_status"] == "unread" else "")
                else:
                    documents = connection.execute("""
                        SELECT kind,sha256,extracted_text FROM legacy_pdf_texts
                        WHERE publication_id=? ORDER BY kind,sha256
                    """, (row["id"],)).fetchall()
                    digest, full_text = source_digest([
                        (str(item["kind"]), str(item["sha256"]),
                         str(item["extracted_text"])) for item in documents])
                    limitations = "Texto extraído históricamente de PDF; verificar contra BORA."
                exists = connection.execute("""
                    SELECT 1 FROM summaries
                    WHERE publication_id=? AND model=? AND prompt_version=?
                      AND source_sha256=? AND status='complete'
                """, (row["id"], model, prompt_version,
                      digest)).fetchone()
                if exists and not include_completed:
                    continue
                candidates.append(SummaryCandidate(
                    publication_id=int(row["id"]), source_id=str(row["source_id"]),
                    title=str(row["title"]), agency=str(row["agency"]),
                    publication_date=str(row["publication_date"]),
                    relevance=str(row["relevance"]),
                    relevance_reason=str(row["relevance_reason"]),
                    detail_url=str(row["detail_url"]),
                    full_text=full_text, source_sha256=digest,
                    source_limitations=limitations,
                ))
                if limit is not None and len(candidates) >= limit:
                    break
            return candidates

    def status(self) -> dict[str, object]:
        with self.connect() as connection:
            last_run = connection.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
            publications = connection.execute("""
                SELECT COUNT(*) total,
                    SUM(relevance IN ('direct_epesf','potential_sector_impact')) relevant
                FROM publications
            """).fetchone()
            summaries = connection.execute("""
                SELECT SUM(status='complete') ready,SUM(status='error') errors
                FROM summaries
            """).fetchone()
            failed_dates = connection.execute(
                "SELECT COUNT(*) count FROM coverage WHERE status='failed'").fetchone()["count"]
            return {"last_run": last_run, "publications": publications,
                    "summaries": summaries, "failed_dates": failed_dates}
