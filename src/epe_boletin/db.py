from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import Publication

SCHEMA_VERSION = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL CHECK(mode IN ('daily','historical','simulation')),
                    date_from TEXT NOT NULL,
                    date_to TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL CHECK(status IN ('running','complete','partial','failed')),
                    publications_seen INTEGER NOT NULL DEFAULT 0,
                    publications_relevant INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS coverage (
                    source TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('complete','not_published','failed')),
                    pages_fetched INTEGER NOT NULL DEFAULT 0,
                    publication_count INTEGER NOT NULL DEFAULT 0,
                    has_supplement INTEGER NOT NULL DEFAULT 0,
                    checked_at TEXT NOT NULL,
                    error TEXT,
                    PRIMARY KEY(source, publication_date)
                );
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    section TEXT NOT NULL,
                    category TEXT NOT NULL,
                    agency TEXT NOT NULL,
                    title TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    description TEXT NOT NULL,
                    detail_url TEXT NOT NULL,
                    has_annexes INTEGER NOT NULL DEFAULT 0,
                    relevance TEXT NOT NULL,
                    relevance_reason TEXT NOT NULL,
                    document_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(document_status IN ('pending','downloaded','error','not_requested')),
                    classification_status TEXT NOT NULL DEFAULT 'metadata_only',
                    summary_status TEXT NOT NULL DEFAULT 'pending',
                    delivery_status TEXT NOT NULL DEFAULT 'pending',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    UNIQUE(source, source_id)
                );
                CREATE INDEX IF NOT EXISTS ix_publications_date
                    ON publications(publication_date);
                CREATE INDEX IF NOT EXISTS ix_publications_relevance
                    ON publications(relevance);
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    publication_id INTEGER NOT NULL REFERENCES publications(id),
                    kind TEXT NOT NULL DEFAULT 'main',
                    path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    byte_size INTEGER NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    extracted_text TEXT NOT NULL DEFAULT '',
                    page_count INTEGER,
                    extraction_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(extraction_status IN ('pending','complete','insufficient','error')),
                    extraction_error TEXT,
                    UNIQUE(publication_id, kind, sha256)
                );
            """)
            row = connection.execute("SELECT version FROM schema_info").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] == 1:
                columns = {
                    column["name"]
                    for column in connection.execute("PRAGMA table_info(documents)")
                }
                additions = {
                    "extracted_text": "TEXT NOT NULL DEFAULT ''",
                    "page_count": "INTEGER",
                    "extraction_status": "TEXT NOT NULL DEFAULT 'pending'",
                    "extraction_error": "TEXT",
                }
                for name, declaration in additions.items():
                    if name not in columns:
                        connection.execute(
                            f"ALTER TABLE documents ADD COLUMN {name} {declaration}"
                        )
                connection.execute("UPDATE schema_info SET version=?", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(f"Versión de base no soportada: {row['version']}")

    def start_run(self, mode: str, date_from: date, date_to: date) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runs(mode,date_from,date_to,started_at,status) VALUES (?,?,?,?, 'running')",
                (mode, date_from.isoformat(), date_to.isoformat(), utc_now()),
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, seen: int, relevant: int,
                   error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE runs SET finished_at=?, status=?, publications_seen=?, "
                "publications_relevant=?, error=? WHERE id=?",
                (utc_now(), status, seen, relevant, error, run_id),
            )

    def save_coverage(self, day: date, status: str, pages: int = 0,
                      count: int = 0, has_supplement: bool = False,
                      error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO coverage(source,publication_date,status,pages_fetched,
                                     publication_count,has_supplement,checked_at,error)
                VALUES('BORA',?,?,?,?,?,?,?)
                ON CONFLICT(source,publication_date) DO UPDATE SET
                    status=excluded.status, pages_fetched=excluded.pages_fetched,
                    publication_count=excluded.publication_count,
                    has_supplement=excluded.has_supplement,
                    checked_at=excluded.checked_at, error=excluded.error
            """, (day.isoformat(), status, pages, count, int(has_supplement), utc_now(), error))

    def upsert_publication(self, item: Publication, request_document: bool) -> int:
        return self.upsert_publications(((item, request_document),))[item.source_id]

    def upsert_publications(
        self, items: tuple[tuple[Publication, bool], ...]
    ) -> dict[str, int]:
        now = utc_now()
        with self.connect() as connection:
            for item, request_document in items:
                document_status = "pending" if request_document else "not_requested"
                connection.execute("""
                    INSERT INTO publications(
                        source,source_id,publication_date,section,category,agency,title,
                        reference,description,detail_url,has_annexes,relevance,
                        relevance_reason,document_status,first_seen_at,last_seen_at)
                    VALUES('BORA',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source,source_id) DO UPDATE SET
                        publication_date=excluded.publication_date,
                        section=excluded.section, category=excluded.category,
                        agency=excluded.agency, title=excluded.title,
                        reference=excluded.reference, description=excluded.description,
                        detail_url=excluded.detail_url, has_annexes=excluded.has_annexes,
                        relevance=excluded.relevance,
                        relevance_reason=excluded.relevance_reason,
                        document_status=CASE
                          WHEN publications.document_status='not_requested'
                               AND excluded.document_status='pending' THEN 'pending'
                          ELSE publications.document_status END,
                        last_seen_at=excluded.last_seen_at
                """, (item.source_id, item.publication_date.isoformat(), item.section,
                      item.category, item.agency, item.title, item.reference,
                      item.description, item.detail_url, int(item.has_annexes),
                      item.relevance, item.relevance_reason, document_status, now, now))
            source_ids = [item.source_id for item, _ in items]
            placeholders = ",".join("?" for _ in source_ids)
            rows = connection.execute(
                f"SELECT source_id,id FROM publications WHERE source='BORA' "
                f"AND source_id IN ({placeholders})", source_ids,
            ).fetchall()
            return {str(row["source_id"]): int(row["id"]) for row in rows}

    def save_document(self, publication_id: int, path: Path, sha256: str,
                      byte_size: int, source_url: str, extracted_text: str = "",
                      page_count: int | None = None,
                      extraction_status: str = "pending",
                      extraction_error: str | None = None,
                      kind: str = "main") -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO documents(publication_id,kind,path,sha256,
                    byte_size,downloaded_at,source_url,extracted_text,page_count,
                    extraction_status,extraction_error) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(publication_id,kind,sha256) DO UPDATE SET
                    path=excluded.path, byte_size=excluded.byte_size,
                    downloaded_at=excluded.downloaded_at,
                    extracted_text=excluded.extracted_text,
                    page_count=excluded.page_count,
                    extraction_status=excluded.extraction_status,
                    extraction_error=excluded.extraction_error
            """, (publication_id, kind, str(path), sha256, byte_size, utc_now(),
                  source_url, extracted_text, page_count, extraction_status,
                  extraction_error))
            connection.execute(
                "UPDATE publications SET document_status='downloaded' WHERE id=?",
                (publication_id,),
            )

    def document_text(self, publication_id: int, kind: str = "main") -> str | None:
        with self.connect() as connection:
            row = connection.execute("""
                SELECT extracted_text FROM documents
                WHERE publication_id=? AND kind=?
                  AND extraction_status IN ('complete','insufficient')
                ORDER BY id DESC LIMIT 1
            """, (publication_id, kind)).fetchone()
            return str(row["extracted_text"]) if row else None

    def update_classification(self, publication_id: int, relevance: str,
                              reason: str, status: str) -> None:
        with self.connect() as connection:
            connection.execute("""
                UPDATE publications SET relevance=?, relevance_reason=?,
                    classification_status=? WHERE id=?
            """, (relevance, reason, status, publication_id))

    def mark_document_error(self, publication_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE publications SET document_status='error' WHERE id=?",
                (publication_id,),
            )

    def status(self) -> dict[str, object]:
        with self.connect() as connection:
            last_run = connection.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
            counts = connection.execute("""
                SELECT COUNT(*) total,
                  SUM(relevance IN ('direct_epesf','potential_sector_impact')) relevant,
                  SUM(document_status='downloaded') downloaded,
                  SUM(document_status='error') document_errors
                FROM publications
            """).fetchone()
            pending = connection.execute(
                "SELECT COUNT(*) count FROM coverage WHERE status='failed'"
            ).fetchone()["count"]
            return {"last_run": dict(last_run) if last_run else None,
                    "publications": dict(counts), "failed_dates": pending}

    def export_csv(self, destination: Path) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT publication_date,category,agency,title,reference,relevance,
                       relevance_reason,document_status,summary_status,detail_url
                FROM publications ORDER BY publication_date,agency,title
            """).fetchall()
        fields = list(rows[0].keys()) if rows else [
            "publication_date", "category", "agency", "title", "reference",
            "relevance", "relevance_reason", "document_status", "summary_status",
            "detail_url",
        ]
        with destination.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)
        return len(rows)
