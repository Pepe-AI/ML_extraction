"""Tests del dispatcher validate_annotation, validate_file y CLI."""
import json
import re
from pathlib import Path

import pytest

from src.annotation import (
    AnnotationV1,
    get_preprocess_version,
    validate_annotation,
    validate_file,
)

GOLDEN_DIR = Path(__file__).parent / "golden"


def _load_valid_dict() -> dict:
    """Carga un golden válido y retorna el dict."""
    return json.loads(
        (GOLDEN_DIR / "valid_fisica_simple.json").read_text(encoding="utf-8")
    )


def test_validate_annotation_valida_v1():
    """Un dict válido pasa por validate_annotation y retorna AnnotationV1."""
    data = _load_valid_dict()
    result = validate_annotation(data)
    assert isinstance(result, AnnotationV1)
    assert result.schema_version == "v1"


def test_validate_annotation_sin_schema_version():
    """Un dict sin schema_version lanza ValueError explícito."""
    with pytest.raises(ValueError, match="schema_version"):
        validate_annotation({})


def test_validate_annotation_schema_desconocido():
    """schema_version no registrada lanza ValueError listando disponibles."""
    with pytest.raises(ValueError) as exc_info:
        validate_annotation({"schema_version": "v99"})
    msg = str(exc_info.value)
    assert "v99" in msg
    assert "v1" in msg  # debe listar las disponibles


def test_validate_file_json_malformado(tmp_path: Path):
    """validate_file con JSON malformado retorna (False, mensaje JSON malformado)."""
    bad = tmp_path / "bad.json"
    bad.write_text("{esto no es JSON", encoding="utf-8")
    ok, msg = validate_file(bad)
    assert ok is False
    assert "JSON malformado" in msg


def test_get_preprocess_version_formato():
    """get_preprocess_version retorna string que cumple regex 'preprocess@...'."""
    pp = get_preprocess_version()
    assert re.match(r"^preprocess@.+$", pp)
