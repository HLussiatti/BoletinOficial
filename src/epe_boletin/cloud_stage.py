"""Create a path-free SQLite staging copy for review before Turso import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .db import SCHEMA_VERSION, utc_now


STAGE_VERSION = 1
_LOCAL_PATH = re.compile(r"\b[A-Za-z]:[\\/](?:Users|Dev|Program Files|Windows)[\\/]", re.I)
_KEY_NAME = re.compile(r"(?:gemini_api_key|api_key)\.txt", re.I)

_SCHEMA = """
CREATE TABLE stage_info(version INTEGER NOT NULL, source_schema_version INTEGER NOT NULL,
                        generated_at TEXT NOT NULL);
CREATE TABLE publications(
    source_id TEXT PRIMARY KEY, publication_date TEXT NOT NULL, section TEXT NOT NULL,
    category TEXT NOT NULL, agency TEXT NOT NULL, title TEXT NOT NULL,
    reference TEXT NOT NULL, description TEXT NOT NULL, detail_url TEXT NOT NULL,
    has_annexes INTEGER NOT NULL, relevance TEXT NOT NULL,
    relevance_reason TEXT NOT NULL, relevance_rules_version TEXT NOT NULL,
    classification_status TEXT NOT NULL, delivery_status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
);
CREATE TABLE coverage(
    publication_date TEXT PRIMARY KEY, status TEXT NOT NULL,
    pages_fetched INTEGER NOT NULL, publication_count INTEGER NOT NULL,
    has_supplement INTEGER NOT NULL, checked_at TEXT NOT NULL
);
CREATE TABLE notice_contents(
    source_id TEXT PRIMARY KEY REFERENCES publications(source_id),
    text TEXT NOT NULL, sha256 TEXT NOT NULL, notice_url TEXT NOT NULL,
    pdf_url TEXT NOT NULL, pdf_availability TEXT NOT NULL,
    annex_status TEXT NOT NULL, fetched_at TEXT NOT NULL
);
CREATE TABLE legacy_pdf_texts(
    source_id TEXT NOT NULL REFERENCES publications(source_id),
    kind TEXT NOT NULL, sha256 TEXT NOT NULL, extracted_text TEXT NOT NULL,
    page_count INTEGER, extraction_status TEXT NOT NULL,
    PRIMARY KEY(source_id,kind,sha256)
);
CREATE TABLE summaries(
    source_id TEXT NOT NULL REFERENCES publications(source_id),
    conceptual_summary TEXT NOT NULL, epesf_relationship TEXT NOT NULL,
    effective_date TEXT NOT NULL, needs_review INTEGER NOT NULL,
    model TEXT NOT NULL, prompt_version TEXT NOT NULL,
    source_sha256 TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
    created_at TEXT NOT NULL,
    PRIMARY KEY(source_id,model,prompt_version,source_sha256)
);
"""


class StageError(ValueError):
    """The source contains data that cannot be safely staged as public content."""


def _official_url(value: str, prefix: str) -> bool:
    parsed = urlparse(value)
    accepted_query = (not parsed.query or
                      (prefix == "/detalleAviso/" and parsed.query == "suplemento=1"))
    return (parsed.scheme == "https"
            and parsed.hostname == "www.boletinoficial.gob.ar"
            and parsed.path.startswith(prefix)
            and not parsed.username and not parsed.password
            and accepted_query and not parsed.fragment)


def _check_text(*values: object) -> None:
    if any(_LOCAL_PATH.search(str(value or "")) or _KEY_NAME.search(str(value or ""))
           for value in values):
        raise StageError("La copia contiene una posible ruta local o nombre de clave")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_snapshot(source: Path) -> sqlite3.Connection:
    if not source.is_file():
        raise StageError("No se encontró la base SQLite de origen")
    original: sqlite3.Connection | None = None
    immutable = False
    before = source.stat()
    sidecars = (Path(str(source) + "-wal"), Path(str(source) + "-shm"))
    try:
        original = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
        original.execute("PRAGMA schema_version").fetchone()
    except sqlite3.OperationalError:
        if original is not None:
            original.close()
        if any(path.exists() for path in sidecars):
            raise StageError("La base usa WAL activo; se necesita una copia consistente")
        original = sqlite3.connect(
            f"{source.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
        immutable = True
    try:
        original.execute("PRAGMA query_only=ON")
        snapshot = sqlite3.connect(":memory:")
        try:
            original.backup(snapshot)
            if immutable:
                after = source.stat()
                if (before.st_size != after.st_size
                        or before.st_mtime_ns != after.st_mtime_ns
                        or any(path.exists() for path in sidecars)):
                    raise StageError("La base cambió durante el snapshot; reintentar más tarde")
                if snapshot.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise StageError("El snapshot SQLite no superó la verificación")
        except Exception:
            snapshot.close()
            raise
        snapshot.row_factory = sqlite3.Row
        return snapshot
    finally:
        original.close()


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _copy_rows(source: sqlite3.Connection, stage: sqlite3.Connection) -> dict[str, int]:
    tables = {row["name"] for row in source.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"schema_info", "publications", "coverage", "summaries"}.issubset(tables):
        raise StageError("La base de origen no tiene el esquema local esperado")
    info = source.execute("SELECT version FROM schema_info").fetchone()
    if info is None or not 1 <= int(info["version"]) <= SCHEMA_VERSION:
        raise StageError("Versión de esquema local no soportada")
    publication_columns = _columns(source, "publications")
    required = {"source", "source_id", "publication_date", "section", "category",
                "agency", "title", "reference", "description", "detail_url",
                "has_annexes", "relevance", "relevance_reason", "first_seen_at",
                "last_seen_at"}
    if not required.issubset(publication_columns):
        raise StageError("Faltan columnas de publicaciones en la base de origen")
    stage.execute("INSERT INTO stage_info VALUES (?,?,?)",
                  (STAGE_VERSION, int(info["version"]), utc_now()))

    publication_ids: dict[int, str] = {}
    for row in source.execute("SELECT * FROM publications WHERE source='BORA' ORDER BY id"):
        if not _official_url(str(row["detail_url"]), "/detalleAviso/"):
            raise StageError("Hay publicaciones con URL no oficial; revisar la copia")
        fields = ("source_id", "publication_date", "section", "category", "agency",
                  "title", "reference", "description", "detail_url",
                  "relevance", "relevance_reason")
        _check_text(*(row[name] for name in fields))
        source_id = str(row["source_id"])
        publication_ids[int(row["id"])] = source_id
        stage.execute("""
            INSERT INTO publications VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (source_id, row["publication_date"], row["section"], row["category"],
              row["agency"], row["title"], row["reference"], row["description"],
              row["detail_url"], row["has_annexes"], row["relevance"],
              row["relevance_reason"],
              row["relevance_rules_version"] if "relevance_rules_version" in publication_columns
              else "builtin-2026-09-11.1",
              row["classification_status"] if "classification_status" in publication_columns
              else "metadata_only",
              row["delivery_status"] if "delivery_status" in publication_columns
              else "pending",
              row["first_seen_at"], row["last_seen_at"]))

    for row in source.execute("""
        SELECT publication_date,status,pages_fetched,publication_count,
               has_supplement,checked_at FROM coverage WHERE source='BORA'
        ORDER BY publication_date
    """):
        stage.execute("INSERT INTO coverage VALUES (?,?,?,?,?,?)", tuple(row))

    if "notice_contents" in tables:
        for row in source.execute("""
            SELECT publication_id,text,sha256,notice_url,pdf_url,
                   pdf_availability,annex_status,fetched_at
            FROM notice_contents ORDER BY publication_id
        """):
            source_id = publication_ids.get(int(row["publication_id"]))
            if source_id is None:
                continue
            if not _official_url(str(row["notice_url"]), "/detalleAviso/"):
                raise StageError("Hay avisos HTML con URL no oficial; revisar la copia")
            if not _official_url(str(row["pdf_url"]), "/pdf/aviso/"):
                raise StageError("Hay enlaces PDF no oficiales; revisar la copia")
            _check_text(row["text"])
            stage.execute("INSERT INTO notice_contents VALUES (?,?,?,?,?,?,?,?)",
                          (source_id, row["text"], row["sha256"], row["notice_url"],
                           row["pdf_url"], row["pdf_availability"],
                           row["annex_status"], row["fetched_at"]))

    if "documents" in tables and "extracted_text" in _columns(source, "documents"):
        for row in source.execute("""
            SELECT publication_id,kind,sha256,extracted_text,page_count,
                   extraction_status FROM documents
            WHERE extracted_text IS NOT NULL AND extracted_text != ''
              AND extraction_status IN ('complete','insufficient')
            ORDER BY publication_id,kind,id
        """):
            source_id = publication_ids.get(int(row["publication_id"]))
            if source_id is None:
                continue
            _check_text(row["extracted_text"])
            stage.execute("INSERT OR IGNORE INTO legacy_pdf_texts VALUES (?,?,?,?,?,?)",
                          (source_id, row["kind"], row["sha256"],
                           row["extracted_text"], row["page_count"],
                           row["extraction_status"]))

    for row in source.execute("""
        SELECT publication_id,conceptual_summary,epesf_relationship,
               effective_date,needs_review,model,prompt_version,source_sha256,
               input_tokens,output_tokens,created_at FROM summaries
        WHERE status='complete' ORDER BY publication_id,id
    """):
        source_id = publication_ids.get(int(row["publication_id"]))
        if source_id is None:
            continue
        _check_text(row["conceptual_summary"], row["epesf_relationship"],
                    row["effective_date"])
        stage.execute("""
            INSERT OR REPLACE INTO summaries VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (source_id, row["conceptual_summary"], row["epesf_relationship"],
              row["effective_date"], row["needs_review"], row["model"],
              row["prompt_version"], row["source_sha256"],
              row["input_tokens"], row["output_tokens"], row["created_at"]))

    return {table: int(stage.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("publications", "coverage", "notice_contents",
                          "legacy_pdf_texts", "summaries")}


def create_stage(source: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise StageError("El archivo de etapa ya existe; elegí otro nombre")
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = _source_snapshot(source)
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".epe-stage-", suffix=".sqlite3", dir=output.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        stage = sqlite3.connect(temporary)
        try:
            stage.execute("PRAGMA foreign_keys=ON")
            stage.executescript(_SCHEMA)
            counts = _copy_rows(snapshot, stage)
            stage.commit()
        finally:
            stage.close()
        digest = _sha256_file(temporary)
        created_output = False
        try:
            with temporary.open("rb") as source_stream:
                with output.open("xb") as output_stream:
                    created_output = True
                    shutil.copyfileobj(source_stream, output_stream)
            if _sha256_file(output) != digest:
                raise StageError("La copia depurada no superó la verificación de integridad")
        except Exception:
            if created_output:
                output.unlink(missing_ok=True)
            raise
        return {"status": "ok", "stage_version": STAGE_VERSION,
                "counts": counts, "stage_sha256": digest}
    finally:
        snapshot.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="Base SQLite de origen; se abre sólo para lectura")
    parser.add_argument("--output", required=True, type=Path,
                        help="Archivo nuevo de etapa, preferentemente dentro de tmp/")
    args = parser.parse_args(argv)
    try:
        result = create_stage(args.source, args.output)
    except (StageError, sqlite3.Error, OSError) as exc:
        # Paths and database payloads must not appear in CLI output.
        message = str(exc) if isinstance(exc, StageError) else "No se pudo crear la copia depurada"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
