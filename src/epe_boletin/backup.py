from __future__ import annotations

import hashlib
import json
import shutil
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


def restore_backup(archive_path: Path, destination: Path) -> dict[str, object]:
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(
            f"La carpeta de restauración debe estar vacía: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        try:
            manifest = json.loads(archive.read("manifest.json"))
            entries = manifest["files"]
            if not isinstance(entries, list) or not entries:
                raise ValueError("files")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("El respaldo no contiene un manifiesto válido") from exc
        declared = {str(item["path"]): item for item in entries}
        if len(declared) != len(entries) or "boletin.sqlite3" not in declared:
            raise ValueError("El manifiesto del respaldo está incompleto")
        available = set(archive.namelist())
        if not set(declared).issubset(available):
            raise ValueError("Faltan archivos declarados en el respaldo")

        staging = Path(tempfile.mkdtemp(prefix="epe-restore-", dir=destination.parent))
        try:
            for name, metadata in declared.items():
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Ruta insegura en el respaldo: {name}")
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                byte_count = 0
                with archive.open(name) as source, target.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        byte_count += len(chunk)
                        output.write(chunk)
                if byte_count != int(metadata["bytes"]):
                    raise ValueError(f"Tamaño inválido en el respaldo: {name}")
                if digest.hexdigest() != str(metadata["sha256"]):
                    raise ValueError(f"Huella inválida en el respaldo: {name}")

            database = sqlite3.connect(staging / "boletin.sqlite3")
            try:
                integrity = database.execute("PRAGMA integrity_check").fetchone()[0]
                foreign_keys = database.execute("PRAGMA foreign_key_check").fetchall()
            finally:
                database.close()
            if integrity != "ok" or foreign_keys:
                raise ValueError("La base restaurada no superó el control de integridad")
            if destination.exists():
                destination.rmdir()
            shutil.move(str(staging), str(destination))
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return {"path": str(destination), "files": len(declared)}
