from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from .bora import BoraClient
from .db import Database
from .pipeline import run


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


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="epe-boletin")
    result.add_argument("--data-dir", type=Path, default=Path("var"),
                        help="Carpeta para la base, documentos y estado (por defecto: var)")
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
    commands.add_parser("status", help="Mostrar el último estado operativo")
    export = commands.add_parser("export-csv", help="Exportar publicaciones para consulta")
    export.add_argument("destination", type=Path)
    export.add_argument("--all", action="store_true",
                        help="Incluir también las publicaciones descartadas")
    return result


def main(argv: list[str] | None = None) -> int:
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

    today = date.today()
    date_from = args.date_from or today
    date_to = args.date_to or date_from
    if date_to < date_from:
        parser().error("--to no puede ser anterior a --from")
    configure_logging(args.data_dir)
    try:
        client = BoraClient(timeout=args.timeout, max_attempts=args.max_attempts)
        result = run(database, client, args.data_dir, args.mode,
                     date_from, date_to, not args.no_download, args.fixture_dir)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 2
