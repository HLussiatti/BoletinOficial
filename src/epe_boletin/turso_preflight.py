"""Read-only connectivity check for a Turso Cloud libSQL database."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from urllib.parse import urlparse


def validate_turso_url(url: str) -> None:
    if not url.strip():
        raise ValueError("Falta TURSO_DATABASE_URL en esta sesión de PowerShell")
    if url != url.strip():
        raise ValueError("TURSO_DATABASE_URL tiene espacios al principio o al final")
    parsed = urlparse(url)
    if parsed.scheme == "turso":
        raise ValueError("La URL usa el motor Turso; este piloto requiere una base libSQL")
    if parsed.scheme not in ("libsql", "https"):
        raise ValueError("TURSO_DATABASE_URL debe comenzar con libsql:// o https://")
    if not parsed.hostname or not parsed.hostname.endswith(".turso.io"):
        raise ValueError("TURSO_DATABASE_URL debe apuntar a un host *.turso.io")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("TURSO_DATABASE_URL debe contener sólo la URL, sin credenciales")


def check_turso(url: str, token: str,
                connect: Callable[..., object] | None = None) -> dict[str, object]:
    validate_turso_url(url)
    if not token.strip():
        raise ValueError("Falta TURSO_AUTH_TOKEN")
    if connect is None:
        try:
            import libsql
        except ImportError as exc:
            raise RuntimeError("Falta el paquete Python libsql (pip install libsql)") from exc
        connect = libsql.connect

    connection = connect(database=url, auth_token=token)
    try:
        version = connection.execute("SELECT sqlite_version()").fetchone()[0]
        tables = connection.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()
    finally:
        connection.close()
    return {"status": "ok", "engine": "libsql", "sqlite_version": str(version),
            "table_count": len(tables)}


def main() -> int:
    try:
        result = check_turso(os.environ.get("TURSO_DATABASE_URL", ""),
                             os.environ.get("TURSO_AUTH_TOKEN", ""))
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({"status": "error", "message": "No se pudo conectar a Turso"},
                         ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
