"""Read-only check of the cloud web's Turso queries and in-memory draft."""

from __future__ import annotations

import json
import os

from .cloud_db import TursoDatabase
from .cloud_web import CloudWeb, Filters


def main() -> int:
    if not os.environ.get("TURSO_DATABASE_URL") or not os.environ.get("TURSO_AUTH_TOKEN"):
        print(json.dumps({"status": "error", "message":
                          "Faltan variables Turso en esta sesión de PowerShell"},
                         ensure_ascii=False))
        return 1
    try:
        db = TursoDatabase.from_env()
        web = CloudWeb(db)
        latest = web._latest_date()
        total, rows = web._listing(Filters(latest))
        with db.connect() as connection:
            candidate = connection.execute("""
                SELECT p.id,p.publication_date FROM publications p
                JOIN summaries s ON s.publication_id=p.id AND s.status='complete'
                WHERE p.source='BORA' ORDER BY p.publication_date DESC,p.id DESC LIMIT 1
            """).fetchone()
        draft = "unavailable"
        if candidate:
            _, content = web._draft({"date": [str(candidate["publication_date"])],
                                     "selected": [str(candidate["id"])]})
            if b"X-Unsent: 1" not in content:
                raise ValueError("El borrador no se generó correctamente")
            draft = "ok"
        print(json.dumps({"status": "ok", "latest_date": latest,
                          "visible_count": total, "page_rows": len(rows),
                          "draft": draft}, ensure_ascii=False))
        return 0
    except Exception:
        print(json.dumps({"status": "error", "message":
                          "Falló la comprobación de sólo lectura de la web"},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
