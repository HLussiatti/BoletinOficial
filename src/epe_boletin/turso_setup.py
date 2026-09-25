"""Initialize the empty Turso libSQL database for the cloud pilot."""

from __future__ import annotations

import argparse
import json

from .cloud_db import CLOUD_SCHEMA_VERSION, CloudSchemaError, TursoDatabase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", action="store_true",
                        help="Crear las tablas del piloto en la base Turso configurada")
    args = parser.parse_args(argv)
    if not args.init:
        parser.error("Indicá --init para crear las tablas del piloto")
    try:
        database = TursoDatabase.from_env()
        database.migrate()
        with database.connect() as connection:
            table_count = connection.execute("""
                SELECT COUNT(*) count FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """).fetchone()["count"]
    except (ValueError, CloudSchemaError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({"status": "error", "message": "No se pudo preparar Turso"},
                         ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "engine": "libsql",
                      "schema_version": CLOUD_SCHEMA_VERSION,
                      "table_count": table_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
