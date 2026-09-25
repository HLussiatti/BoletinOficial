"""Run one authenticated cloud request on a GitHub-hosted runner."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from .bora import BoraClient
from .cloud_db import TursoDatabase
from .models import Publication
from .pipeline import run
from .relevance import DEFAULT_RULES, classify, load_rules
from .summaries import (DEFAULT_SUMMARY_MODEL, PROMPT_VERSION, GeminiSummarizer,
                        retryable_summary_error)


def execute(db: TursoDatabase, job_id: str, *, client: BoraClient | None = None,
            summarizer: GeminiSummarizer | None = None) -> dict[str, object]:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("Identificador de solicitud inválido")
    db.migrate()
    job = db.claim_job(job_id)
    if job is None:
        raise ValueError("La solicitud no está pendiente")
    rules_path = Path("config/relevance_rules.json")
    client = client or BoraClient(rules=load_rules(rules_path) if rules_path.is_file()
                                else DEFAULT_RULES)
    try:
        if job["kind"] == "consult":
            day = date.fromisoformat(str(job["target"]))
            outcome = run(db, client, Path(os.environ.get("RUNNER_TEMP", ".")),
                          "daily", day, day, download=False, source_mode="cloud")
            if outcome["status"] != "complete":
                raise RuntimeError("La consulta no se completó. Revisá Fallas.")
            result: dict[str, object] = {"kind": "consult", "date": day.isoformat(),
                                         "seen": outcome["seen"]}
        else:
            publication_id = int(job["target"])
            with db.connect() as connection:
                row = connection.execute("SELECT * FROM publications WHERE id=? AND source='BORA'",
                                         (publication_id,)).fetchone()
                existing = connection.execute("""
                    SELECT 1 FROM summaries WHERE publication_id=? AND status='complete' LIMIT 1
                """, (publication_id,)).fetchone()
            if row is None or row["relevance"] not in ("direct_epesf", "potential_sector_impact"):
                raise ValueError("La publicación no admite resumen")
            if existing:
                result = {"kind": "summary", "publication_id": publication_id,
                          "already_complete": True}
            else:
                if db.notice_text(publication_id) is None:
                    publication = Publication(
                        source_id=str(row["source_id"]),
                        publication_date=date.fromisoformat(str(row["publication_date"])),
                        section=str(row["section"]), category=str(row["category"]),
                        agency=str(row["agency"]), title=str(row["title"]),
                        reference=str(row["reference"]), description=str(row["description"]),
                        detail_url=str(row["detail_url"]),
                        has_annexes=bool(row["has_annexes"]), relevance=str(row["relevance"]),
                        relevance_reason=str(row["relevance_reason"]),
                    )
                    notice = client.fetch_notice(publication)
                    db.save_notice(publication_id, notice)
                    relevance, reason = classify(publication, notice.text, client.rules)
                    db.update_classification(publication_id, relevance, reason,
                                             "html_text", client.rules.version)
                    if relevance not in ("direct_epesf", "potential_sector_impact"):
                        raise ValueError("El texto del aviso no justifica generar un resumen")
                model = os.environ.get("EPE_SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL)
                candidates = db.summary_candidates(model, PROMPT_VERSION,
                                                   publication_id=publication_id, limit=1)
                if not candidates:
                    raise ValueError("No hay texto disponible para resumir")
                candidate = candidates[0]
                summarizer = summarizer or GeminiSummarizer(os.environ.get("GEMINI_API_KEY", ""), model)
                try:
                    summary = summarizer.summarize(candidate)
                    db.save_summary(candidate, summary, model, PROMPT_VERSION)
                except Exception as exc:
                    if not retryable_summary_error(exc):
                        db.mark_summary_error(candidate, model, PROMPT_VERSION,
                                              "No se pudo generar el resumen. Reintentá.")
                    raise
                result = {"kind": "summary", "publication_id": publication_id}
        db.finish_job(job_id, "complete")
        return result
    except Exception:
        db.finish_job(job_id, "failed", "La solicitud falló. Revisá el registro de ejecución y reintentá.")
        raise


def main() -> int:
    job_id = os.environ.get("EPE_CLOUD_JOB_ID", "")
    result = execute(TursoDatabase.from_env(), job_id)
    print(json.dumps({"status": "ok", **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
