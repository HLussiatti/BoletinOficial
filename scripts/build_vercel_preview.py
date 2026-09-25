"""Create a minimal, data-free directory for a Vercel CLI preview deploy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SAFE_FILES = (
    Path(".vercelignore"),
    Path("vercel.json"),
    Path("pyproject.toml"),
    Path("requirements.txt"),
    Path("api/index.py"),
)


def build(output: Path) -> dict[str, object]:
    target = output.resolve()
    safe_root = (ROOT / "tmp").resolve()
    if not target.is_relative_to(safe_root) or target == safe_root:
        raise ValueError("El destino debe ser una carpeta nueva dentro de tmp/")
    if target.exists():
        raise ValueError("El destino ya existe; elegí una carpeta nueva")
    sources = (*SAFE_FILES, *sorted(
        path.relative_to(ROOT) for path in (ROOT / "src/epe_boletin").glob("*.py")))
    if not sources or any(not (ROOT / path).is_file() for path in sources):
        raise ValueError("Faltan archivos del paquete web")
    target.mkdir(parents=True)
    digest = hashlib.sha256()
    for relative in sources:
        content = (ROOT / relative).read_bytes()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        digest.update(relative.as_posix().encode("utf-8") + b"\0")
        digest.update(content)
    return {"status": "ok", "output": str(target),
            "file_count": len(sources), "source_sha256": digest.hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/vercel_preview")
    args = parser.parse_args()
    try:
        result = build(args.output)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
