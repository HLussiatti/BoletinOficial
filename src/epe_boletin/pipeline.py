from __future__ import annotations

import logging
import os
from dataclasses import replace
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from .bora import BoraClient, BoraError, EditionNotPublished
from .db import Database
from .documents import extract_pdf
from .relevance import DEFAULT_RULES, classify

RELEVANT = {"direct_epesf", "potential_sector_impact"}
REQUIRES_DOCUMENT = RELEVANT | {"needs_review"}
LOGGER = logging.getLogger(__name__)


@contextmanager
def execution_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Ya existe una ejecución en curso ({path})") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def days_between(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def run(db: Database, client: BoraClient, data_dir: Path, mode: str,
        date_from: date, date_to: date, download: bool = True,
        fixture_dir: Path | None = None) -> dict[str, int | str]:
    db.migrate()
    run_id = db.start_run(mode, date_from, date_to)
    seen = relevant = failed = not_published = downloaded = 0
    errors: list[str] = []
    LOGGER.info("Inicio de ejecución mode=%s from=%s to=%s download=%s",
                mode, date_from, date_to, download)
    try:
        with execution_lock(data_dir / "run.lock"):
            for day in days_between(date_from, date_to):
                fixture = None
                if fixture_dir:
                    candidate = fixture_dir / f"primera_{day:%Y%m%d}.html"
                    fixture = candidate if candidate.exists() else None
                    if fixture is None:
                        message = f"{day}: falta la muestra local {candidate}"
                        db.save_coverage(day, "failed", error=message)
                        LOGGER.error(message)
                        errors.append(message)
                        failed += 1
                        continue
                try:
                    edition = client.fetch_edition(day, fixture)
                    requests = tuple(
                        (item, item.relevance in REQUIRES_DOCUMENT)
                        for item in edition.publications
                    )
                    publication_ids = db.upsert_publications(requests)
                    for item in edition.publications:
                        request_document = item.relevance in REQUIRES_DOCUMENT
                        publication_id = publication_ids[item.source_id]
                        seen += 1
                        if request_document:
                            full_text = db.document_text(publication_id)
                            if download and not fixture_dir and full_text is None:
                                try:
                                    path, digest, size = client.download_pdf(
                                        item, data_dir / "documents" / f"{day:%Y}" / f"{day:%m}")
                                    extraction = extract_pdf(path)
                                    full_text = extraction.text
                                    db.save_document(
                                        publication_id, path, digest, size, item.detail_url,
                                        extraction.text, extraction.page_count,
                                        extraction.status, extraction.error,
                                        sections=extraction.sections,
                                    )
                                    downloaded += 1
                                except Exception as exc:
                                    db.mark_document_error(publication_id)
                                    message = f"{day}: PDF {item.source_id}: {exc}"
                                    errors.append(message)
                                    LOGGER.exception(message)
                                    failed += 1
                            annex_texts: list[str] = []
                            if download and not fixture_dir and item.has_annexes:
                                try:
                                    for annex in client.fetch_annexes(item):
                                        annex_text = db.document_text(publication_id, annex.kind)
                                        if annex_text is None:
                                            path, digest, size = client.download_annex(
                                                item, annex,
                                                data_dir / "documents" / f"{day:%Y}" / f"{day:%m}",
                                            )
                                            extraction = extract_pdf(path)
                                            annex_text = extraction.text
                                            db.save_document(
                                                publication_id, path, digest, size,
                                                item.detail_url + "?anexos=1",
                                                extraction.text, extraction.page_count,
                                                extraction.status, extraction.error,
                                                kind=annex.kind,
                                                sections=extraction.sections,
                                            )
                                            downloaded += 1
                                        annex_texts.append(annex_text)
                                except Exception as exc:
                                    message = f"{day}: anexos {item.source_id}: {exc}"
                                    errors.append(message)
                                    LOGGER.exception(message)
                                    failed += 1
                            if full_text is not None:
                                combined_text = "\n\n".join([full_text, *annex_texts])
                                rules = getattr(client, "rules", DEFAULT_RULES)
                                final_relevance, reason = classify(
                                    item, combined_text, rules
                                )
                                item = replace(
                                    item, relevance=final_relevance,
                                    relevance_reason=reason,
                                    relevance_rules_version=rules.version,
                                )
                                db.update_classification(
                                    publication_id, final_relevance, reason, "full_text",
                                    rules.version,
                                )
                        if item.relevance in RELEVANT:
                            relevant += 1
                    db.save_coverage(day, "complete", edition.pages_fetched,
                                     len(edition.publications), edition.has_supplement)
                except EditionNotPublished:
                    db.save_coverage(day, "not_published")
                    LOGGER.info("Sin edición publicada para %s", day)
                    not_published += 1
                except Exception as exc:
                    failed += 1
                    message = f"{day}: {exc}"
                    errors.append(message)
                    db.save_coverage(day, "failed", error=str(exc))
                    LOGGER.exception(message)
        status = "complete" if not failed else "partial"
        db.finish_run(run_id, status, seen, relevant, "\n".join(errors) or None)
    except Exception as exc:
        db.finish_run(run_id, "failed", seen, relevant, str(exc))
        LOGGER.exception("La ejecución %s finalizó con error", run_id)
        raise
    LOGGER.info("Fin de ejecución id=%s status=%s seen=%s relevant=%s downloaded=%s failed=%s",
                run_id, status, seen, relevant, downloaded, failed)
    return {"run_id": run_id, "status": status, "seen": seen,
            "relevant": relevant, "downloaded": downloaded,
            "not_published": not_published, "failed": failed}
