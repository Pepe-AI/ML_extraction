"""Tests para src.annotation.schema_v1."""
import json
from pathlib import Path
from src.annotation import validate_annotation, AnnotationV1

GOLDEN_DIR = Path(__file__).parent / "golden"


def test_valid_fisica_simple():
    """El golden file fisica simple debe validar sin errores."""
    raw = (GOLDEN_DIR / "valid_fisica_simple.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    result = validate_annotation(data)

    assert isinstance(result, AnnotationV1)
    assert result.schema_version == "v1"
    assert result.doc_id == "ESC_001"
    assert result.titulares[0].nombre.value == "MARIA LOPEZ RUIZ"
    assert result.adquirientes[0].edad.value == 35
    assert result.fields.monto_operacion.value == 1500000.00
    assert result.fields.monto_operacion.currency.value == "MXN"
