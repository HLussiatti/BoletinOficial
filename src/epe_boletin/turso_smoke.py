"""Exercise Turso writes with a synthetic record and remove it afterward."""

from __future__ import annotations

import hashlib
import json

from .bora import NoticeContent
from .cloud_db import CLOUD_SCHEMA_VERSION, CloudSchemaError, TursoDatabase
from .db import utc_now
from .summaries import ConceptualSummary, SummaryCandidate


_SOURCE = "PILOT_SMOKE"
_SOURCE_ID = "adapter-v1"
_TEXT = "Aviso sintético para probar la conexión. No es una publicación oficial."


def _smoke_id(db: TursoDatabase) -> int | None:
    with db.connect() as connection:
        row = connection.execute(
            "SELECT id FROM publications WHERE source=? AND source_id=?",
            (_SOURCE, _SOURCE_ID),
        ).fetchone()
    return int(row["id"]) if row else None


def _cleanup(db: TursoDatabase) -> None:
    publication_id = _smoke_id(db)
    if publication_id is None:
        return
    with db.connect() as connection:
        connection.execute("DELETE FROM summaries WHERE publication_id=?",
                           (publication_id,))
        connection.execute("DELETE FROM notice_contents WHERE publication_id=?",
                           (publication_id,))
        connection.execute("DELETE FROM publications WHERE id=? AND source=?",
                           (publication_id, _SOURCE))


def smoke_turso(db: TursoDatabase) -> dict[str, object]:
    with db.connect() as connection:
        schema = connection.execute(
            "SELECT version,kind FROM cloud_schema_info").fetchone()
    if schema != {"version": CLOUD_SCHEMA_VERSION, "kind": "epe-html-pilot"}:
        raise CloudSchemaError("La base no tiene el esquema del piloto")

    _cleanup(db)  # Retira un registro sintético que haya quedado de un intento anterior.
    try:
        now = utc_now()
        with db.connect() as connection:
            for _ in range(2):
                connection.execute("""
                    INSERT INTO publications(
                        source,source_id,publication_date,section,category,agency,
                        title,reference,description,detail_url,relevance,
                        relevance_reason,first_seen_at,last_seen_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source,source_id) DO UPDATE SET
                        title=excluded.title,last_seen_at=excluded.last_seen_at
                """, (_SOURCE, _SOURCE_ID, "2026-09-24", "primera",
                      "PRUEBA", "Prueba del piloto", "Aviso sintético",
                      "PRUEBA", "No es un aviso de BORA", "https://example.invalid/smoke",
                      "potential_sector_impact", "Prueba del adaptador", now, now))
        publication_id = _smoke_id(db)
        if publication_id is None:
            raise CloudSchemaError("No se pudo leer el registro sintético")
        db.save_notice(publication_id, NoticeContent(
            text=_TEXT, notice_url="https://example.invalid/smoke",
            pdf_url="https://example.invalid/smoke.pdf",
            pdf_availability="unknown", annex_status="none",
        ))
        digest = hashlib.sha256(_TEXT.encode("utf-8")).hexdigest()
        candidate = SummaryCandidate(
            publication_id=publication_id, source_id=_SOURCE_ID,
            title="Aviso sintético", agency="Prueba del piloto",
            publication_date="2026-09-24", relevance="potential_sector_impact",
            relevance_reason="Prueba del adaptador",
            detail_url="https://example.invalid/smoke", full_text=_TEXT,
            source_sha256=digest,
        )
        db.save_summary(candidate, ConceptualSummary(
            "Resumen sintético", "Sin efecto real", "No aplica", True,
        ), "smoke-model", "smoke-prompt")
        with db.connect() as connection:
            row = connection.execute("""
                SELECT p.source_id,p.summary_status,n.sha256,s.status
                FROM publications p
                JOIN notice_contents n ON n.publication_id=p.id
                JOIN summaries s ON s.publication_id=p.id
                WHERE p.id=? AND p.source=?
            """, (publication_id, _SOURCE)).fetchone()
        if row != {"source_id": _SOURCE_ID, "summary_status": "ready",
                   "sha256": digest, "status": "complete"}:
            raise CloudSchemaError("La lectura del registro sintético no coincide")
    finally:
        _cleanup(db)
    if _smoke_id(db) is not None:
        raise CloudSchemaError("No se pudo eliminar el registro sintético")
    return {"status": "ok", "engine": "libsql", "write_read": "ok",
            "upsert": "ok", "cleanup": "ok"}


def main() -> int:
    try:
        result = smoke_turso(TursoDatabase.from_env())
    except (ValueError, CloudSchemaError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({"status": "error", "message":
                          "Falló la prueba remota; repetila para limpiar el registro sintético"},
                         ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
