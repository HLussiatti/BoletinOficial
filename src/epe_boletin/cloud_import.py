"""Review or import an allowlisted staging SQLite into Turso libSQL."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from .cloud_db import TursoDatabase
from .cloud_stage import STAGE_VERSION, _sha256_file


_STAGE_TABLES = frozenset({"stage_info", "publications", "coverage",
                           "notice_contents", "legacy_pdf_texts", "summaries"})
_DATA_TABLES = ("publications", "coverage", "notice_contents",
                "legacy_pdf_texts", "summaries")


class CloudImportError(ValueError):
    """A staging file or remote verification did not satisfy the import contract."""


def _open_stage(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise CloudImportError("No se encontró el archivo de etapa")
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        names = {row["name"] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if names != _STAGE_TABLES:
            raise CloudImportError("El archivo de etapa tiene tablas inesperadas")
        info = connection.execute("SELECT version FROM stage_info").fetchone()
        if info is None or info["version"] != STAGE_VERSION:
            raise CloudImportError("Versión de etapa no soportada")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CloudImportError("El archivo de etapa no superó la verificación SQLite")
        return connection
    except Exception:
        connection.close()
        raise


def inspect_stage(path: Path) -> dict[str, object]:
    connection = _open_stage(path)
    try:
        counts = {name: int(connection.execute(
            f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in _DATA_TABLES}
        return {"status": "ok", "stage_version": STAGE_VERSION,
                "counts": counts, "stage_sha256": _sha256_file(path)}
    finally:
        connection.close()


def _batches(rows: Iterable[sqlite3.Row], size: int) -> Iterator[list[sqlite3.Row]]:
    batch: list[sqlite3.Row] = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _write_batches(db: TursoDatabase, rows: Iterable[sqlite3.Row], sql: str,
                   convert: Callable[[sqlite3.Row], tuple[Any, ...]],
                   batch_size: int, name: str) -> None:
    values = re.search(r"\bVALUES\s*\(([^)]*)\)", sql, re.IGNORECASE)
    if values is None:
        raise CloudImportError("La sentencia de carga no contiene VALUES")
    row_sql = f"({values.group(1)})"
    total = 0
    for batch in _batches(rows, batch_size):
        parameters = [convert(row) for row in batch]
        if any(len(item) != row_sql.count("?") for item in parameters):
            raise CloudImportError("Los parámetros de carga no coinciden")
        batch_sql = (sql[:values.start()] + "VALUES " +
                     ",".join(row_sql for _ in parameters) + sql[values.end():])
        with db.connect() as connection:
            connection.execute(batch_sql, tuple(value for item in parameters
                                                for value in item))
        total += len(batch)
        if total % 500 < len(batch):
            print(f"{name}: {total} filas cargadas", file=sys.stderr, flush=True)
    print(f"{name}: {total} filas cargadas", file=sys.stderr, flush=True)


def _remote_publication_ids(db: TursoDatabase) -> dict[str, int]:
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT source_id,id FROM publications WHERE source='BORA'").fetchall()
    return {str(row["source_id"]): int(row["id"]) for row in rows}


def _verify(db: TursoDatabase, stage: sqlite3.Connection) -> dict[str, int]:
    checks = (
        ("publications", "SELECT * FROM publications",
         """SELECT source_id,publication_date,section,category,agency,title,
            reference,description,detail_url,has_annexes,relevance,
            relevance_reason,relevance_rules_version,classification_status,
            delivery_status,first_seen_at,last_seen_at FROM publications
            WHERE source='BORA'"""),
        ("coverage", "SELECT * FROM coverage",
         """SELECT publication_date,status,pages_fetched,publication_count,
            has_supplement,checked_at FROM coverage WHERE source='BORA'"""),
        ("notice_contents", "SELECT * FROM notice_contents",
         """SELECT p.source_id,n.text,n.sha256,n.notice_url,n.pdf_url,
            n.pdf_availability,n.annex_status,n.fetched_at FROM notice_contents n
            JOIN publications p ON p.id=n.publication_id WHERE p.source='BORA'"""),
        ("legacy_pdf_texts", "SELECT * FROM legacy_pdf_texts",
         """SELECT p.source_id,d.kind,d.sha256,d.extracted_text,d.page_count,
            d.extraction_status FROM legacy_pdf_texts d
            JOIN publications p ON p.id=d.publication_id WHERE p.source='BORA'"""),
        ("summaries", "SELECT * FROM summaries",
         """SELECT p.source_id,s.conceptual_summary,s.epesf_relationship,
            s.effective_date,s.needs_review,s.model,s.prompt_version,
            s.source_sha256,s.input_tokens,s.output_tokens,s.created_at
            FROM summaries s JOIN publications p ON p.id=s.publication_id
            WHERE p.source='BORA' AND s.status='complete'"""),
    )
    verified: dict[str, int] = {}
    for name, stage_sql, remote_sql in checks:
        print(f"Verificando {name}...", file=sys.stderr, flush=True)
        expected = {tuple(row) for row in stage.execute(stage_sql)}
        with db.connect() as connection:
            actual = {tuple(row.values()) for row in connection.execute(remote_sql)}
        if not expected.issubset(actual):
            raise CloudImportError(f"No coincide la verificación de {name}")
        verified[name] = len(expected)
    return verified


def import_stage(path: Path, db: TursoDatabase, expected_sha256: str,
                 batch_size: int = 50) -> dict[str, object]:
    if batch_size < 1 or batch_size > 50:
        raise CloudImportError("El tamaño de lote debe estar entre 1 y 50")
    if len(expected_sha256) != 64 or _sha256_file(path) != expected_sha256.lower():
        raise CloudImportError("El hash SHA-256 de la etapa no coincide")
    stage = _open_stage(path)
    try:
        print("Actualizando esquema remoto...", file=sys.stderr, flush=True)
        db.migrate()  # Upgrades the six-table pilot to the legacy-text schema.
        _write_batches(db, stage.execute("SELECT * FROM publications ORDER BY source_id"), """
            INSERT INTO publications(
                source,source_id,publication_date,section,category,agency,title,
                reference,description,detail_url,has_annexes,relevance,
                relevance_reason,relevance_rules_version,classification_status,
                delivery_status,first_seen_at,last_seen_at
            ) VALUES('BORA',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source,source_id) DO NOTHING
        """, lambda row: tuple(row), batch_size, "publications")
        print("Leyendo identificadores remotos...", file=sys.stderr, flush=True)
        ids = _remote_publication_ids(db)
        staged_ids = {str(row[0]) for row in stage.execute(
            "SELECT source_id FROM publications")}
        if not staged_ids.issubset(ids):
            raise CloudImportError("Faltan publicaciones después de la carga")

        _write_batches(db, stage.execute("SELECT * FROM coverage ORDER BY publication_date"), """
            INSERT INTO coverage(source,publication_date,status,pages_fetched,
                                 publication_count,has_supplement,checked_at)
            VALUES('BORA',?,?,?,?,?,?)
            ON CONFLICT(source,publication_date) DO NOTHING
        """, lambda row: tuple(row), batch_size, "coverage")

        _write_batches(db, stage.execute("SELECT * FROM notice_contents ORDER BY source_id"), """
            INSERT INTO notice_contents(publication_id,text,sha256,notice_url,
                pdf_url,pdf_availability,annex_status,fetched_at)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(publication_id) DO NOTHING
        """, lambda row: (ids[str(row["source_id"])], *tuple(row)[1:]),
                       batch_size, "notice_contents")

        _write_batches(db, stage.execute(
            "SELECT * FROM legacy_pdf_texts ORDER BY source_id,kind,sha256"), """
            INSERT INTO legacy_pdf_texts(publication_id,kind,sha256,
                extracted_text,page_count,extraction_status)
            VALUES(?,?,?,?,?,?) ON CONFLICT(publication_id,kind,sha256) DO NOTHING
        """, lambda row: (ids[str(row["source_id"])], *tuple(row)[1:]),
                       batch_size, "legacy_pdf_texts")

        _write_batches(db, stage.execute("SELECT * FROM summaries ORDER BY source_id"), """
            INSERT INTO summaries(publication_id,conceptual_summary,
                epesf_relationship,effective_date,needs_review,model,
                prompt_version,source_sha256,input_tokens,output_tokens,
                created_at,status,error)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,'complete',NULL)
            ON CONFLICT(publication_id,model,prompt_version,source_sha256)
                DO NOTHING
        """, lambda row: (ids[str(row["source_id"])], *tuple(row)[1:]),
                       batch_size, "summaries")
        print("Marcando resúmenes disponibles...", file=sys.stderr, flush=True)
        with db.connect() as connection:
            connection.execute("""
                UPDATE publications SET summary_status='ready'
                WHERE source='BORA' AND EXISTS (
                    SELECT 1 FROM summaries s WHERE s.publication_id=publications.id
                    AND s.status='complete')
            """)
        verified = _verify(db, stage)
        return {"status": "ok", "stage_sha256": expected_sha256.lower(),
                "verified": verified}
    finally:
        stage.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="Cargar datos depurados en Turso; requiere --expect-sha256")
    parser.add_argument("--expect-sha256", default="")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            result = import_stage(args.stage, TursoDatabase.from_env(),
                                  args.expect_sha256)
        else:
            result = inspect_stage(args.stage)
    except CloudImportError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({"status": "error", "message":
                          "Falló la operación; una carga parcial se puede reanudar"},
                         ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
