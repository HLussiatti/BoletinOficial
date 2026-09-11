from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(data_dir: Path, destination: Path,
                  rules_path: Path | None = None) -> dict[str, object]:
    database_path = data_dir / "boletin.sqlite3"
    if not database_path.is_file():
        raise FileNotFoundError(f"No se encontró la base: {database_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        snapshot = Path(folder) / "boletin.sqlite3"
        source = sqlite3.connect(database_path)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        files: list[tuple[Path, str]] = [(snapshot, "boletin.sqlite3")]
        documents = data_dir / "documents"
        if documents.is_dir():
            files.extend(
                (path, path.relative_to(data_dir).as_posix())
                for path in sorted(documents.rglob("*")) if path.is_file()
            )
        if rules_path and rules_path.is_file():
            files.append((rules_path, "config/relevance_rules.json"))
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": [
                {"path": archive_name, "bytes": path.stat().st_size,
                 "sha256": _sha256(path)}
                for path, archive_name in files
            ],
        }
        temporary = destination.with_suffix(destination.suffix + ".part")
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, archive_name in files:
                archive.write(path, archive_name)
            archive.writestr(
                "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
            )
        temporary.replace(destination)
    return {"path": str(destination), "files": len(files),
            "bytes": destination.stat().st_size}
