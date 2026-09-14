from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from .bora import BoraClient
from .backup import create_backup, restore_backup
from .db import Database
from .documents import extract_pdf
from .mail import build_email_batches
from .pipeline import run
from .relevance import DEFAULT_RULES, classify, load_rules
from .summaries import (
    DEFAULT_SUMMARY_MODEL,
    PROMPT_VERSION,
    ConceptualSummary,
    OpenAISummarizer,
)
from .settings import load_operation_settings, readiness_issues
from .web import serve


def configure_logging(data_dir: Path) -> Path:
    log_path = data_dir / "logs" / "epe-boletin.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )
    return log_path


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use una fecha AAAA-MM-DD") from exc


def daily_start(last_complete: date | None, today: date, overlap_days: int) -> date:
    if overlap_days < 1:
        raise ValueError("overlap_days debe ser al menos 1")
    if last_complete is None:
        return today
    return min(last_complete, today) - timedelta(days=overlap_days - 1)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="epe-boletin")
    result.add_argument("--data-dir", type=Path, default=Path("var"),
                        help="Carpeta para la base, documentos y estado (por defecto: var)")
    result.add_argument("--rules", type=Path,
                        help="Archivo JSON con reglas de relevancia versionadas")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Crear o actualizar la base local")
    execute = commands.add_parser("run", help="Recolectar un período del BORA")
    execute.add_argument("--mode", choices=("daily", "historical", "simulation"),
                         default="simulation")
    execute.add_argument("--from", dest="date_from", type=parse_date)
    execute.add_argument("--to", dest="date_to", type=parse_date)
    execute.add_argument("--no-download", action="store_true")
    execute.add_argument("--fixture-dir", type=Path,
                         help="Ejecutar con índices HTML locales, sin acceder a Internet")
    execute.add_argument("--timeout", type=float, default=30,
                         help="Tiempo máximo por intento HTTP, en segundos")
    execute.add_argument("--max-attempts", type=int, default=3,
                         help="Cantidad máxima de intentos HTTP")
    execute.add_argument("--overlap-days", type=int, default=7,
                         help="Días a revisar nuevamente en el modo diario")
    commands.add_parser("status", help="Mostrar el último estado operativo")
    commands.add_parser(
        "structure-documents",
        help="Identificar considerandos, parte dispositiva y artículos pendientes",
    )
    commands.add_parser(
        "reclassify", help="Aplicar las reglas vigentes a los registros existentes"
    )
    summarize = commands.add_parser(
        "summarize", help="Generar resúmenes conceptuales pendientes mediante API"
    )
    summarize.add_argument("--model", help="Modelo configurado para los resúmenes")
    summarize.add_argument("--max-items", type=int)
    summarize.add_argument("--api-key-env", default="OPENAI_API_KEY",
                           help="Variable de entorno que contiene la credencial")
    import_summaries = commands.add_parser(
        "import-summaries", help="Importar resúmenes revisados desde un JSON"
    )
    import_summaries.add_argument("source", type=Path)
    email = commands.add_parser(
        "build-email", help="Crear uno o más correos .eml sin enviarlos"
    )
    email.add_argument("--date", required=True, type=parse_date)
    email.add_argument("--output", required=True, type=Path)
    email.add_argument("--from", dest="sender", default="")
    email.add_argument("--to", dest="recipients", action="append", default=[])
    email.add_argument("--max-mb", type=float, default=20)
    backup = commands.add_parser(
        "backup", help="Respaldar la base, documentos y reglas en un ZIP"
    )
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser(
        "restore", help="Restaurar un respaldo verificado en una carpeta vacía"
    )
    restore.add_argument("archive", type=Path)
    restore.add_argument("destination", type=Path)
    check = commands.add_parser(
        "check-config", help="Comprobar si la configuración operativa está completa"
    )
    check.add_argument("source", type=Path)
    export = commands.add_parser("export-csv", help="Exportar publicaciones para consulta")
    export.add_argument("destination", type=Path)
    export.add_argument("--all", action="store_true",
                        help="Incluir también las publicaciones descartadas")
    web = commands.add_parser("serve", help="Abrir la interfaz local en el navegador")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--no-open", action="store_true",
                     help="Iniciar el servicio sin abrir el navegador")
    return result


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    database = Database(args.data_dir / "boletin.sqlite3")
    if args.command == "init":
        database.migrate()
        print(f"Base preparada: {database.path}")
        return 0
    if args.command == "status":
        database.migrate()
        print(json.dumps(database.status(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "export-csv":
        database.migrate()
        count = database.export_csv(args.destination, include_all=args.all)
        print(f"Exportados {count} registros a {args.destination}")
        return 0
    if args.command == "serve":
        serve(database, args.data_dir, args.port, open_browser=not args.no_open)
        return 0
    if args.command == "structure-documents":
        database.migrate()
        processed = structured = failed = 0
        for row in database.documents_without_sections():
            processed += 1
            path = Path(row["path"])
            if not path.is_file():
                database.mark_document_structure_error(
                    int(row["id"]), f"No se encontró el archivo: {path}"
                )
                failed += 1
                continue
            extraction = extract_pdf(path)
            if extraction.status == "error":
                database.mark_document_structure_error(
                    int(row["id"]), extraction.error or "Falló la extracción"
                )
                failed += 1
                continue
            database.save_document_sections(int(row["id"]), extraction.sections)
            structured += int(bool(extraction.sections))
        print(json.dumps({"processed": processed, "structured": structured,
                          "failed": failed}, ensure_ascii=False, indent=2))
        return 0 if not failed else 2
    if args.command == "reclassify":
        database.migrate()
        rules = load_rules(args.rules) if args.rules else DEFAULT_RULES
        counts: dict[str, int] = {}
        processed = 0
        for publication_id, publication, full_text in (
            database.publications_for_reclassification()
        ):
            relevance, reason = classify(publication, full_text, rules)
            status = "full_text" if full_text else "metadata_only"
            database.update_classification(
                publication_id, relevance, reason, status, rules.version
            )
            counts[relevance] = counts.get(relevance, 0) + 1
            processed += 1
        print(json.dumps({"processed": processed, "rules_version": rules.version,
                          "results": counts}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "summarize":
        database.migrate()
        model = args.model or os.environ.get("EPE_OPENAI_MODEL", DEFAULT_SUMMARY_MODEL)
        api_key = os.environ.get(args.api_key_env, "")
        try:
            summarizer = OpenAISummarizer(api_key, model)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        completed = failed = 0
        for candidate in database.summary_candidates(
            model, PROMPT_VERSION, args.max_items
        ):
            try:
                summary = summarizer.summarize(candidate)
                database.save_summary(candidate, summary, model, PROMPT_VERSION)
                completed += 1
            except Exception as exc:
                database.mark_summary_error(
                    candidate, model, PROMPT_VERSION, str(exc)
                )
                failed += 1
        print(json.dumps({"completed": completed, "failed": failed,
                          "model": model, "prompt_version": PROMPT_VERSION},
                         ensure_ascii=False, indent=2))
        return 0 if not failed else 2
    if args.command == "import-summaries":
        database.migrate()
        try:
            payload = json.loads(args.source.read_text(encoding="utf-8"))
            prompt_version = str(payload["prompt_version"])
            entries = payload["summaries"]
            if not isinstance(entries, list):
                raise TypeError("summaries")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"Error: archivo de resúmenes inválido: {exc}", file=sys.stderr)
            return 1
        candidates = {
            candidate.source_id: candidate
            for candidate in database.summary_candidates(
                "human-reviewed", prompt_version, include_completed=True
            )
        }
        imported = missing = 0
        for entry in entries:
            if not isinstance(entry, dict):
                print("Error: cada resumen debe ser un objeto", file=sys.stderr)
                return 1
            candidate = candidates.get(str(entry.get("source_id", "")))
            if candidate is None:
                missing += 1
                continue
            try:
                needs_review = entry.get("needs_review", False)
                if not isinstance(needs_review, bool):
                    raise TypeError("needs_review")
                summary = ConceptualSummary(
                    conceptual_summary=str(entry["conceptual_summary"]).strip(),
                    epesf_relationship=str(entry["epesf_relationship"]).strip(),
                    effective_date=str(entry["effective_date"]).strip(),
                    needs_review=needs_review,
                )
            except (KeyError, TypeError) as exc:
                print(f"Error: resumen inválido: {exc}", file=sys.stderr)
                return 1
            database.save_summary(
                candidate, summary, "human-reviewed", prompt_version
            )
            imported += 1
        print(json.dumps({"imported": imported, "missing": missing,
                          "prompt_version": prompt_version},
                         ensure_ascii=False, indent=2))
        return 0 if not missing else 2
    if args.command == "build-email":
        database.migrate()
        try:
            artifacts = build_email_batches(
                database.bulletin_items(args.date), args.date, args.output,
                args.sender, tuple(args.recipients), int(args.max_mb * 1024 * 1024),
            )
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        for index, artifact in enumerate(artifacts, 1):
            database.record_prepared_delivery(
                args.date, artifact, tuple(args.recipients), index, len(artifacts)
            )
        print(json.dumps({"emails": [
            {"path": str(item.path), "publications": item.item_count,
             "attachments": item.attachment_count, "bytes": item.byte_size,
             "message_id": item.message_id}
            for item in artifacts
        ]}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "backup":
        database.migrate()
        try:
            result = create_backup(args.data_dir, args.destination, args.rules)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "restore":
        try:
            result = restore_backup(args.archive, args.destination)
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "check-config":
        try:
            settings = load_operation_settings(args.source)
            issues = readiness_issues(settings, os.environ)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"ready": not issues, "issues": issues},
                         ensure_ascii=False, indent=2))
        return 0 if not issues else 2

    today = date.today()
    if args.overlap_days < 1:
        parser().error("--overlap-days debe ser al menos 1")
    if args.mode == "daily" and args.date_from is None:
        database.migrate()
        last_complete = database.last_complete_date()
        date_from = daily_start(last_complete, today, args.overlap_days)
        date_to = args.date_to or today
    else:
        date_from = args.date_from or today
        date_to = args.date_to or date_from
    if date_to < date_from:
        parser().error("--to no puede ser anterior a --from")
    configure_logging(args.data_dir)
    try:
        rules = load_rules(args.rules) if args.rules else DEFAULT_RULES
        client = BoraClient(timeout=args.timeout, max_attempts=args.max_attempts,
                            rules=rules)
        result = run(database, client, args.data_dir, args.mode,
                     date_from, date_to, not args.no_download, args.fixture_dir)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 2
