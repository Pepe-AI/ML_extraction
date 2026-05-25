"""Validador de JSONs anotados con registry de schemas y CLI."""
from __future__ import annotations

import argparse
import glob as glob_module
import json
import subprocess
import sys
from pathlib import Path
from typing import Type

from pydantic import BaseModel, ValidationError

from .schema_v1 import AnnotationV1


SCHEMA_REGISTRY: dict[str, Type[BaseModel]] = {
    "v1": AnnotationV1,
}


def get_preprocess_version() -> str:
    """SHA corto del último commit que tocó preprocess_ocr.py.

    Si el archivo aún no se ha committeado, o no hay repo, retorna
    'preprocess@uncommitted' sin crashear.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--",
             "src/preprocessing/preprocess_ocr.py"],
            capture_output=True, text=True, check=False,
        )
    except (FileNotFoundError, OSError):
        return "preprocess@uncommitted"
    sha = result.stdout.strip()
    if not sha:
        return "preprocess@uncommitted"
    return f"preprocess@{sha}"


def validate_annotation(data: dict) -> BaseModel:
    """Punto único de validación. Selecciona modelo Pydantic por schema_version."""
    version = data.get("schema_version")
    if version is None:
        raise ValueError("JSON sin campo 'schema_version' obligatorio")

    model_class = SCHEMA_REGISTRY.get(version)
    if model_class is None:
        supported = sorted(SCHEMA_REGISTRY.keys())
        raise ValueError(
            f"schema_version='{version}' no soportada. Disponibles: {supported}"
        )

    return model_class.model_validate(data)


def validate_file(path: Path) -> tuple[bool, str]:
    """Valida un archivo JSON. Retorna (ok, mensaje)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"JSON malformado: {e}"
    except OSError as e:
        return False, f"No se pudo leer el archivo: {e}"

    try:
        validate_annotation(data)
        return True, "OK"
    except (ValidationError, ValueError) as e:
        return False, str(e)


def main(argv: list[str] | None = None) -> int:
    # En Windows la consola usa cp1252 por defecto, que no codifica emojis.
    # Reconfigurar solo cuando se ejecuta el CLI, no en uso programático.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="python -m src.annotation.validate",
        description="Valida JSONs anotados contra el schema v1.",
    )
    parser.add_argument("paths", nargs="+", help="Archivos JSON (acepta globs)")
    parser.add_argument(
        "--check-preprocess",
        action="store_true",
        help="Warning si preprocess_version difiere del actual",
    )
    args = parser.parse_args(argv)

    files: list[Path] = []
    for p in args.paths:
        if "*" in p or "?" in p:
            # glob.glob soporta paths absolutos y relativos (Path().glob no).
            files.extend(Path(match) for match in glob_module.glob(p))
        else:
            files.append(Path(p))

    if not files:
        print("No se encontraron archivos.", file=sys.stderr)
        return 2

    current_pp = get_preprocess_version() if args.check_preprocess else None

    ok_count, fail_count = 0, 0
    for f in files:
        ok, msg = validate_file(f)
        if ok:
            ok_count += 1
            print(f"✅ {f}")
            if current_pp is not None:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    file_pp = data.get("preprocess_version")
                    if file_pp != current_pp:
                        print(
                            f"   ⚠️  preprocess_version difiere "
                            f"({file_pp} vs {current_pp})"
                        )
                except (OSError, json.JSONDecodeError):
                    pass
        else:
            fail_count += 1
            print(f"❌ {f}\n   {msg}")

    print(
        f"\nTotal: {len(files)} archivos, "
        f"{ok_count} válidos, {fail_count} con errores"
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
