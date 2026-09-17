from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from .documents import DocumentSection
from .mail import BulletinItem, EmailArtifact
from .models import Publication
from .priority import publication_sort_key
from .summaries import ConceptualSummary, SummaryCandidate, source_digest

SCHEMA_VERSION = 6


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
                    relevance_rules_version TEXT NOT NULL DEFAULT 'builtin-2026-09-11.1',
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
                    structure_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(structure_status IN ('pending','complete','not_applicable','error')),
                    structure_error TEXT,
                    UNIQUE(publication_id, kind, sha256)
                );
                CREATE TABLE IF NOT EXISTS document_sections (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    section_type TEXT NOT NULL
                        CHECK(section_type IN ('considerations','dispositive','article')),
                    ordinal INTEGER NOT NULL,
                    heading TEXT NOT NULL,
                    text TEXT NOT NULL,
                    page_from INTEGER NOT NULL,
                    page_to INTEGER NOT NULL,
                    UNIQUE(document_id, section_type, ordinal)
                );
                CREATE INDEX IF NOT EXISTS ix_document_sections_document
                    ON document_sections(document_id, section_type, ordinal);
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY,
                    publication_id INTEGER NOT NULL REFERENCES publications(id),
                    conceptual_summary TEXT NOT NULL,
                    epesf_relationship TEXT NOT NULL,
                    effective_date TEXT NOT NULL,
                    needs_review INTEGER NOT NULL DEFAULT 0,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('complete','error')),
                    error TEXT,
                    UNIQUE(publication_id, model, prompt_version, source_sha256)
                );
                CREATE INDEX IF NOT EXISTS ix_summaries_publication
                    ON summaries(publication_id,created_at);
                CREATE TABLE IF NOT EXISTS deliveries (
                    id INTEGER PRIMARY KEY,
                    message_id TEXT NOT NULL UNIQUE,
                    publication_date TEXT NOT NULL,
                    batch_number INTEGER NOT NULL,
                    total_batches INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    recipients_json TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('prepared','sent','error','uncertain')),
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS delivery_publications (
                    delivery_id INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
                    publication_id INTEGER NOT NULL REFERENCES publications(id),
                    PRIMARY KEY(delivery_id,publication_id)
                );
            """)
            row = connection.execute("SELECT version FROM schema_info").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
                return
            current_version = int(row["version"])
            if current_version < 1 or current_version > SCHEMA_VERSION:
                raise RuntimeError(f"Versión de base no soportada: {current_version}")
            if current_version == 1:
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
                connection.execute("UPDATE schema_info SET version=2")
                current_version = 2
            if current_version == 2:
                columns = {
                    column["name"]
                    for column in connection.execute("PRAGMA table_info(documents)")
                }
                additions = {
                    "structure_status": "TEXT NOT NULL DEFAULT 'pending'",
                    "structure_error": "TEXT",
                }
                for name, declaration in additions.items():
                    if name not in columns:
                        connection.execute(
                            f"ALTER TABLE documents ADD COLUMN {name} {declaration}"
                        )
                connection.execute("UPDATE schema_info SET version=3")
                current_version = 3
            if current_version == 3:
                columns = {
                    column["name"]
                    for column in connection.execute("PRAGMA table_info(publications)")
                }
                if "relevance_rules_version" not in columns:
                    connection.execute("""
                        ALTER TABLE publications ADD COLUMN relevance_rules_version
                        TEXT NOT NULL DEFAULT 'builtin-2026-09-11.1'
                    """)
                connection.execute("UPDATE schema_info SET version=4")
                current_version = 4
            if current_version == 4:
                connection.execute("UPDATE schema_info SET version=5")
                current_version = 5
            if current_version == 5:
                connection.execute("UPDATE schema_info SET version=?", (SCHEMA_VERSION,))

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

    def last_complete_date(self) -> date | None:
        with self.connect() as connection:
            row = connection.execute("""
                SELECT MAX(publication_date) value FROM coverage
                WHERE source='BORA' AND status='complete'
            """).fetchone()
            return date.fromisoformat(row["value"]) if row and row["value"] else None

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
                        relevance_reason,relevance_rules_version,document_status,
                        first_seen_at,last_seen_at)
                    VALUES('BORA',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source,source_id) DO UPDATE SET
                        publication_date=excluded.publication_date,
                        section=excluded.section, category=excluded.category,
                        agency=excluded.agency, title=excluded.title,
                        reference=excluded.reference, description=excluded.description,
                        detail_url=excluded.detail_url, has_annexes=excluded.has_annexes,
                        relevance=excluded.relevance,
                        relevance_reason=excluded.relevance_reason,
                        relevance_rules_version=excluded.relevance_rules_version,
                        document_status=CASE
                          WHEN publications.document_status='not_requested'
                               AND excluded.document_status='pending' THEN 'pending'
                          ELSE publications.document_status END,
                        last_seen_at=excluded.last_seen_at
                """, (item.source_id, item.publication_date.isoformat(), item.section,
                      item.category, item.agency, item.title, item.reference,
                      item.description, item.detail_url, int(item.has_annexes),
                      item.relevance, item.relevance_reason,
                      item.relevance_rules_version, document_status, now, now))
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
                      kind: str = "main",
                      sections: tuple[DocumentSection, ...] = ()) -> int:
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
            document_id = int(connection.execute("""
                SELECT id FROM documents
                WHERE publication_id=? AND kind=? AND sha256=?
            """, (publication_id, kind, sha256)).fetchone()["id"])
            self._replace_sections(connection, document_id, sections)
            if extraction_status == "error":
                structure_status = "error"
                structure_error = extraction_error
            else:
                structure_status = "complete" if sections else "not_applicable"
                structure_error = None
            connection.execute("""
                UPDATE documents SET structure_status=?,structure_error=? WHERE id=?
            """, (structure_status, structure_error, document_id))
            return document_id

    @staticmethod
    def _replace_sections(connection: sqlite3.Connection, document_id: int,
                          sections: tuple[DocumentSection, ...]) -> None:
        connection.execute(
            "DELETE FROM document_sections WHERE document_id=?", (document_id,)
        )
        connection.executemany("""
            INSERT INTO document_sections(
                document_id,section_type,ordinal,heading,text,page_from,page_to
            ) VALUES(?,?,?,?,?,?,?)
        """, (
            (document_id, section.section_type, section.ordinal, section.heading,
             section.text, section.page_from, section.page_to)
            for section in sections
        ))

    def documents_without_sections(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute("""
                SELECT d.id,d.path,d.kind,p.title,p.source_id
                FROM documents d
                JOIN publications p ON p.id=d.publication_id
                WHERE d.extraction_status IN ('complete','insufficient')
                  AND d.structure_status='pending'
                ORDER BY p.publication_date,p.id,d.kind
            """).fetchall()

    def save_document_sections(self, document_id: int,
                               sections: tuple[DocumentSection, ...]) -> None:
        with self.connect() as connection:
            self._replace_sections(connection, document_id, sections)
            structure_status = "complete" if sections else "not_applicable"
            connection.execute("""
                UPDATE documents SET structure_status=?,structure_error=NULL WHERE id=?
            """, (structure_status, document_id))

    def mark_document_structure_error(self, document_id: int, error: str) -> None:
        with self.connect() as connection:
            connection.execute("""
                UPDATE documents SET structure_status='error',structure_error=? WHERE id=?
            """, (error, document_id))

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
                              reason: str, status: str, rules_version: str) -> None:
        with self.connect() as connection:
            connection.execute("""
                UPDATE publications SET relevance=?, relevance_reason=?,
                    classification_status=?,relevance_rules_version=? WHERE id=?
            """, (relevance, reason, status, rules_version, publication_id))

    def update_classifications(
        self, updates: list[tuple[str, str, str, str, int]]
    ) -> None:
        if not updates:
            return
        with self.connect() as connection:
            connection.executemany("""
                UPDATE publications SET relevance=?, relevance_reason=?,
                    classification_status=?,relevance_rules_version=? WHERE id=?
            """, updates)

    def publications_for_reclassification(
        self,
    ) -> list[tuple[int, Publication, str]]:
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT p.*,COALESCE(GROUP_CONCAT(d.extracted_text, '\n\n'), '') full_text
                FROM publications p
                LEFT JOIN documents d ON d.publication_id=p.id
                  AND d.extraction_status IN ('complete','insufficient')
                GROUP BY p.id
                ORDER BY p.publication_date,p.id
            """).fetchall()
        results: list[tuple[int, Publication, str]] = []
        for row in rows:
            publication = Publication(
                source_id=str(row["source_id"]),
                publication_date=date.fromisoformat(row["publication_date"]),
                section=str(row["section"]), category=str(row["category"]),
                agency=str(row["agency"]), title=str(row["title"]),
                reference=str(row["reference"]), description=str(row["description"]),
                detail_url=str(row["detail_url"]), has_annexes=bool(row["has_annexes"]),
                relevance=str(row["relevance"]),
                relevance_reason=str(row["relevance_reason"]),
                relevance_rules_version=str(row["relevance_rules_version"]),
            )
            results.append((int(row["id"]), publication, str(row["full_text"])))
        return results

    def mark_document_error(self, publication_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE publications SET document_status='error' WHERE id=?",
                (publication_id,),
            )

    def summary_candidates(self, model: str, prompt_version: str,
                           limit: int | None = None,
                           include_completed: bool = False,
                           publication_date: date | None = None) -> list[SummaryCandidate]:
        with self.connect() as connection:
            date_clause = " AND publication_date=?" if publication_date else ""
            parameters = (publication_date.isoformat(),) if publication_date else ()
            publications = connection.execute(f"""
                SELECT * FROM publications
                WHERE relevance IN ('direct_epesf','potential_sector_impact')
                  AND document_status='downloaded'
                  {date_clause}
                ORDER BY publication_date,id
            """, parameters).fetchall()
            results: list[SummaryCandidate] = []
            for publication in publications:
                documents = connection.execute("""
                    SELECT kind,sha256,extracted_text FROM documents
                    WHERE publication_id=?
                      AND extraction_status IN ('complete','insufficient')
                    ORDER BY kind,id
                """, (publication["id"],)).fetchall()
                if not documents:
                    continue
                digest, full_text = source_digest([
                    (str(row["kind"]), str(row["sha256"]), str(row["extracted_text"]))
                    for row in documents
                ])
                exists = connection.execute("""
                    SELECT 1 FROM summaries
                    WHERE publication_id=? AND model=? AND prompt_version=?
                      AND source_sha256=? AND status='complete'
                """, (publication["id"], model, prompt_version, digest)).fetchone()
                if exists and not include_completed:
                    continue
                results.append(SummaryCandidate(
                    publication_id=int(publication["id"]),
                    source_id=str(publication["source_id"]),
                    title=str(publication["title"]), agency=str(publication["agency"]),
                    publication_date=str(publication["publication_date"]),
                    relevance=str(publication["relevance"]),
                    relevance_reason=str(publication["relevance_reason"]),
                    detail_url=str(publication["detail_url"]), full_text=full_text,
                    source_sha256=digest,
                ))
                if limit is not None and len(results) >= limit:
                    break
            return results

    def save_summary(self, candidate: SummaryCandidate, summary: ConceptualSummary,
                     model: str, prompt_version: str) -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO summaries(
                    publication_id,conceptual_summary,epesf_relationship,
                    effective_date,needs_review,model,prompt_version,source_sha256,
                    input_tokens,output_tokens,created_at,status,error
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'complete',NULL)
                ON CONFLICT(publication_id,model,prompt_version,source_sha256)
                DO UPDATE SET conceptual_summary=excluded.conceptual_summary,
                    epesf_relationship=excluded.epesf_relationship,
                    effective_date=excluded.effective_date,
                    needs_review=excluded.needs_review,
                    input_tokens=excluded.input_tokens,
                    output_tokens=excluded.output_tokens,
                    created_at=excluded.created_at,status='complete',error=NULL
            """, (
                candidate.publication_id, summary.conceptual_summary,
                summary.epesf_relationship, summary.effective_date,
                int(summary.needs_review), model, prompt_version,
                candidate.source_sha256, summary.input_tokens,
                summary.output_tokens, utc_now(),
            ))
            connection.execute(
                "UPDATE publications SET summary_status='ready' WHERE id=?",
                (candidate.publication_id,),
            )

    def mark_summary_error(self, candidate: SummaryCandidate, model: str,
                           prompt_version: str, error: str) -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO summaries(
                    publication_id,conceptual_summary,epesf_relationship,
                    effective_date,needs_review,model,prompt_version,source_sha256,
                    created_at,status,error
                ) VALUES(?,'','','',1,?,?,?,?,'error',?)
                ON CONFLICT(publication_id,model,prompt_version,source_sha256)
                DO UPDATE SET created_at=excluded.created_at,status='error',
                    error=excluded.error
            """, (candidate.publication_id, model, prompt_version,
                  candidate.source_sha256, utc_now(), error))
            connection.execute(
                "UPDATE publications SET summary_status='error' WHERE id=?",
                (candidate.publication_id,),
            )

    def bulletin_items(self, day: date,
                       publication_ids: tuple[int, ...] | None = None) -> list[BulletinItem]:
        if publication_ids == ():
            return []
        id_clause = ""
        parameters: list[object] = [day.isoformat()]
        if publication_ids is not None:
            placeholders = ",".join("?" for _ in publication_ids)
            id_clause = f" AND p.id IN ({placeholders})"
            parameters.extend(publication_ids)
        with self.connect() as connection:
            rows = connection.execute(f"""
                SELECT p.id,p.source_id,p.title,p.agency,p.publication_date,p.detail_url,p.relevance,
                       s.conceptual_summary,s.epesf_relationship,s.effective_date
                FROM publications p
                JOIN summaries s ON s.id=(
                    SELECT s2.id FROM summaries s2
                    WHERE s2.publication_id=p.id AND s2.status='complete'
                    ORDER BY s2.id DESC LIMIT 1
                )
                WHERE p.publication_date=?
                  AND p.relevance IN ('direct_epesf','potential_sector_impact')
                  {id_clause}
            """, parameters).fetchall()
            results: list[BulletinItem] = []
            for row in sorted((dict(row) for row in rows), key=publication_sort_key):
                documents = connection.execute("""
                    SELECT path FROM documents WHERE publication_id=?
                    ORDER BY CASE kind WHEN 'main' THEN 0 ELSE 1 END,kind,id
                """, (row["id"],)).fetchall()
                results.append(BulletinItem(
                    source_id=str(row["source_id"]), title=str(row["title"]),
                    agency=str(row["agency"]),
                    publication_date=str(row["publication_date"]),
                    conceptual_summary=str(row["conceptual_summary"]),
                    epesf_relationship=str(row["epesf_relationship"]),
                    effective_date=str(row["effective_date"]),
                    detail_url=str(row["detail_url"]),
                    documents=tuple(Path(item["path"]) for item in documents),
                ))
            return results

    def record_prepared_delivery(self, day: date, artifact: EmailArtifact,
                                 recipients: tuple[str, ...], batch_number: int,
                                 total_batches: int) -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO deliveries(
                    message_id,publication_date,batch_number,total_batches,path,
                    recipients_json,status,created_at,sent_at,error
                ) VALUES(?,?,?,?,?,?,'prepared',?,NULL,NULL)
                ON CONFLICT(message_id) DO UPDATE SET path=excluded.path,
                    recipients_json=excluded.recipients_json,status='prepared',
                    created_at=excluded.created_at,sent_at=NULL,error=NULL
            """, (
                artifact.message_id, day.isoformat(), batch_number, total_batches,
                str(artifact.path), json.dumps(recipients), utc_now(),
            ))
            delivery_id = int(connection.execute(
                "SELECT id FROM deliveries WHERE message_id=?",
                (artifact.message_id,),
            ).fetchone()["id"])
            connection.execute(
                "DELETE FROM delivery_publications WHERE delivery_id=?",
                (delivery_id,),
            )
            for source_id in artifact.source_ids:
                publication = connection.execute("""
                    SELECT id FROM publications WHERE source='BORA' AND source_id=?
                """, (source_id,)).fetchone()
                if publication:
                    connection.execute("""
                        INSERT INTO delivery_publications(delivery_id,publication_id)
                        VALUES(?,?)
                    """, (delivery_id, publication["id"]))

    def update_delivery(self, message_id: str, status: str,
                        error: str | None = None) -> None:
        sent_at = utc_now() if status == "sent" else None
        with self.connect() as connection:
            cursor = connection.execute("""
                UPDATE deliveries SET status=?,sent_at=?,error=? WHERE message_id=?
            """, (status, sent_at, error, message_id))
            if cursor.rowcount != 1:
                raise ValueError(f"No existe la entrega {message_id}")
            if status == "sent":
                connection.execute("""
                    UPDATE publications SET delivery_status='sent'
                    WHERE id IN (
                        SELECT publication_id FROM delivery_publications
                        WHERE delivery_id=(SELECT id FROM deliveries WHERE message_id=?)
                    )
                """, (message_id,))

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
            document_counts = connection.execute("""
                SELECT SUM(structure_status='complete') structured,
                       SUM(structure_status='pending') structure_pending,
                       SUM(structure_status='error') structure_errors
                FROM documents
            """).fetchone()
            summary_counts = connection.execute("""
                SELECT SUM(status='complete') ready,SUM(status='error') errors
                FROM summaries
            """).fetchone()
            delivery_counts = connection.execute("""
                SELECT SUM(status='prepared') prepared,SUM(status='sent') sent,
                       SUM(status='error') errors,SUM(status='uncertain') uncertain
                FROM deliveries
            """).fetchone()
            pending = connection.execute(
                "SELECT COUNT(*) count FROM coverage WHERE status='failed'"
            ).fetchone()["count"]
            return {"last_run": dict(last_run) if last_run else None,
                    "publications": dict(counts),
                    "documents": dict(document_counts),
                    "summaries": dict(summary_counts),
                    "deliveries": dict(delivery_counts), "failed_dates": pending}

    def export_csv(self, destination: Path, include_all: bool = False) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            where = "" if include_all else "WHERE relevance != 'not_relevant'"
            rows = connection.execute(f"""
                SELECT publication_date,category,agency,title,reference,relevance,
                       relevance_reason,relevance_rules_version,document_status,
                       summary_status,detail_url
                FROM publications {where} ORDER BY publication_date,agency,title
            """).fetchall()
        fields = list(rows[0].keys()) if rows else [
            "publication_date", "category", "agency", "title", "reference",
            "relevance", "relevance_reason", "relevance_rules_version",
            "document_status", "summary_status", "detail_url",
        ]
        with destination.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)
        return len(rows)
