"""Read-only inventory of a SQLite copy before planning a Turso import."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .cloud_stage import _source_snapshot


def inventory(source: Path) -> dict[str, object]:
    connection = _source_snapshot(source)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        tables = {row["name"] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"schema_info", "publications", "coverage", "summaries"}
        if not required.issubset(tables):
            raise ValueError("La copia no tiene el esquema local esperado")
        version = connection.execute("SELECT version FROM schema_info").fetchone()
        if version is None:
            raise ValueError("La copia no tiene versión de esquema")
        publications = connection.execute("""
            SELECT COUNT(*) total,
                   COALESCE(SUM(relevance IN
                       ('direct_epesf','potential_sector_impact')),0) relevant
            FROM publications
        """).fetchone()
        summaries = connection.execute("""
            SELECT COUNT(*) total,
                   COALESCE(SUM(status='complete'),0) complete
            FROM summaries
        """).fetchone()
        coverage = connection.execute("SELECT COUNT(*) count FROM coverage").fetchone()
        html_count = (connection.execute(
            "SELECT COUNT(*) count FROM notice_contents").fetchone()["count"]
            if "notice_contents" in tables else 0)
        legacy_count = 0
        if "documents" in tables:
            columns = {row["name"] for row in connection.execute(
                "PRAGMA table_info(documents)")}
            if "extracted_text" in columns:
                legacy_count = connection.execute("""
                    SELECT COUNT(DISTINCT publication_id) count FROM documents
                    WHERE extracted_text IS NOT NULL AND extracted_text != ''
                """).fetchone()["count"]
        return {"status": "ok", "source_schema_version": int(version["version"]),
                "publications": int(publications["total"]),
                "relevant_publications": int(publications["relevant"]),
                "html_notices": int(html_count),
                "legacy_pdf_text_publications": int(legacy_count),
                "summaries": int(summaries["total"]),
                "complete_summaries": int(summaries["complete"]),
                "coverage_dates": int(coverage["count"])}
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="Ruta a una copia SQLite, no a la base operativa")
    args = parser.parse_args(argv)
    try:
        result = inventory(args.source)
    except (ValueError, sqlite3.Error):
        print(json.dumps({"status": "error", "message":
                          "No se pudo leer la copia SQLite con el esquema esperado"},
                         ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
