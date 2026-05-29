"""Tests para src.annotation.schema_v1."""
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.annotation import validate_annotation, AnnotationV1


def _strip_json_strings(s: str) -> str:
    """Reemplaza el contenido de cada string JSON por "" para inspección estructural.

    Permite detectar ": " o ", " *fuera* de strings sin falsos positivos por
    contenidos como "RFC: ABC" o "Pérez García, Notario".
    """
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', s)

GOLDEN_DIR = Path(__file__).parent / "golden"

VALID_GOLDEN_FILES = sorted(GOLDEN_DIR.glob("valid_*.json"))
INVALID_GOLDEN_FILES = sorted(GOLDEN_DIR.glob("invalid_*.json"))


def _load(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


# ── Test funcional original ─────────────────────────────────────────────

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


# ── Parametrizados sobre golden files ────────────────────────────────────

@pytest.mark.parametrize(
    "golden_path",
    VALID_GOLDEN_FILES,
    ids=lambda p: p.stem,
)
def test_golden_valido_pasa(golden_path: Path):
    """Cada golden valid_*.json debe instanciar AnnotationV1 sin errores."""
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    result = validate_annotation(data)
    assert isinstance(result, AnnotationV1)


@pytest.mark.parametrize(
    "golden_path",
    INVALID_GOLDEN_FILES,
    ids=lambda p: p.stem,
)
def test_golden_invalido_falla(golden_path: Path):
    """Cada golden invalid_*.json debe disparar ValidationError o ValueError."""
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    with pytest.raises((ValidationError, ValueError)):
        validate_annotation(data)


# ── Tests específicos de normalizaciones ─────────────────────────────────

def _entity_dict(rfc_value: object = None, curp_value: object = None,
                 tipo_value: str = "FISICA", id_: str = "A1") -> dict:
    """Helper para construir un Entity como dict para tests de normalizacion."""
    ev = {"section_norm": "GENERALES", "page": 1, "lines": "1", "source_text": "x"}
    return {
        "id": id_,
        "nombre": {"value": "NAME", "evidence": [ev]},
        "tipo": {"value": tipo_value, "evidence": [ev]},
        "estado_civil": {"value": None, "evidence": []},
        "tipo_sociedad": {"value": None, "evidence": []},
        "edad": {"value": None, "evidence": []},
        "rfc": {"value": rfc_value, "evidence": [ev] if rfc_value is not None else []},
        "curp": {"value": curp_value, "evidence": [ev] if curp_value is not None else []},
        "representantes": [],
        "entity_flags": [],
    }


def _annotation_dict(**overrides) -> dict:
    """Construye un AnnotationV1 base como dict, aplicando overrides."""
    ev = {"section_norm": "PERSONALIDAD", "page": 1, "lines": "1", "source_text": "x"}
    base = {
        "schema_version": "v1",
        "preprocess_version": "preprocess@a3f8b21",
        "doc_id": "ESC_TEST",
        "file_name": "t.pdf",
        "annotator": "ana",
        "labeled_at": "2026-03-15",
        "observaciones": "",
        "qa_flags": [],
        "sections": [{
            "section_norm": "PERSONALIDAD", "raw_title": "X",
            "page_start": 1, "page_end": 1, "evidence": [ev],
        }],
        "fields": {
            "numero_escritura": {"value": "123", "evidence": [ev]},
            "fecha_documento": {"value": "2023-05-15", "evidence": [ev]},
            "valor_catastral_bool": {"value": True, "evidence": [ev]},
            "monto_operacion": {"value": 100.0, "currency": "MXN", "evidence": [ev]},
            "numero_notaria": {"value": "1", "evidence": [ev]},
            "nombre_notario": {"value": "X", "evidence": [ev]},
            "municipio": {"value": "X", "evidence": [ev]},
        },
        "titulares": [_entity_dict(id_="T1")],
        "adquirientes": [_entity_dict(id_="A1")],
    }
    base.update(overrides)
    return base


def test_rfc_normalizacion():
    """RFC con espacios y guiones se normaliza a UPPER sin separadores."""
    data = _annotation_dict()
    data["adquirientes"][0]["rfc"] = {
        "value": "abc 123-def45",
        "evidence": [{"section_norm": "GENERALES", "page": 1, "lines": "1", "source_text": "x"}],
    }
    result = validate_annotation(data)
    assert result.adquirientes[0].rfc.value == "ABC123DEF45"


def test_monto_redondeo():
    """monto_operacion.value se redondea a 2 decimales."""
    data = _annotation_dict()
    data["fields"]["monto_operacion"]["value"] = 8654
    result = validate_annotation(data)
    assert result.fields.monto_operacion.value == 8654.00

    data2 = _annotation_dict()
    data2["fields"]["monto_operacion"]["value"] = 8654.999
    result2 = validate_annotation(data2)
    assert result2.fields.monto_operacion.value == 8655.00


def test_tipo_normalizacion():
    """tipo en minúsculas con espacio se normaliza a FISICA/MORAL."""
    data = _annotation_dict()
    data["adquirientes"][0]["tipo"] = {
        "value": "fisica ",
        "evidence": [{"section_norm": "GENERALES", "page": 1, "lines": "1", "source_text": "x"}],
    }
    result = validate_annotation(data)
    assert result.adquirientes[0].tipo.value.value == "FISICA"


def test_fecha_espanol_rechazada():
    """Fecha en formato español es rechazada por el validador estricto."""
    data = _annotation_dict()
    data["fields"]["fecha_documento"] = {
        "value": "05 de mayo de 2023",
        "evidence": [{"section_norm": "PERSONALIDAD", "page": 1, "lines": "8", "source_text": "x"}],
    }
    with pytest.raises((ValidationError, ValueError)):
        validate_annotation(data)


def test_fecha_invalida_calendario():
    """Fecha con formato correcto pero día imposible (Feb 30) es rechazada."""
    data = _annotation_dict()
    data["fields"]["fecha_documento"] = {
        "value": "2023-02-30",
        "evidence": [{"section_norm": "PERSONALIDAD", "page": 1, "lines": "8", "source_text": "x"}],
    }
    with pytest.raises((ValidationError, ValueError)):
        validate_annotation(data)


def test_curp_normalizacion():
    """CURP en minúsculas o con espacios se normaliza a UPPER sin separadores."""
    # 1. Minúsculas → mayúsculas
    data = _annotation_dict()
    data["adquirientes"][0]["curp"] = {
        "value": "pesj850515hntrzn08",
        "evidence": [{"section_norm": "GENERALES", "page": 1, "lines": "1", "source_text": "x"}],
    }
    result = validate_annotation(data)
    assert result.adquirientes[0].curp.value == "PESJ850515HNTRZN08"

    # 2. Con espacios → sin espacios
    data2 = _annotation_dict()
    data2["adquirientes"][0]["curp"] = {
        "value": "PESJ 850515 HNTRZN08",
        "evidence": [{"section_norm": "GENERALES", "page": 1, "lines": "1", "source_text": "x"}],
    }
    result2 = validate_annotation(data2)
    assert result2.adquirientes[0].curp.value == "PESJ850515HNTRZN08"


# ── Tests de serialización y round-trip ──────────────────────────────────

def test_serializacion_compacta():
    """El formato compacto usado para training no escapa UTF-8 ni añade espacios."""
    data = json.loads(
        (GOLDEN_DIR / "valid_fisica_simple.json").read_text(encoding="utf-8")
    )
    # Mutamos para incluir caracteres unicode "duros" (Ñ, É, México)
    data["adquirientes"][0]["nombre"]["value"] = "JOSÉ MUÑOZ DE LA PEÑA"
    data["fields"]["municipio"]["value"] = "CIUDAD DE MÉXICO"

    result = validate_annotation(data)

    # 1. Pydantic model_dump_json: debe ser válido y no escapar UTF-8
    pyd_json = result.model_dump_json()
    assert isinstance(pyd_json, str)
    json.loads(pyd_json)  # debe re-parsear sin error
    assert "JOSÉ MUÑOZ DE LA PEÑA" in pyd_json
    assert "MÉXICO" in pyd_json
    assert "\\u" not in pyd_json  # no escapes unicode

    # 2. Formato compacto para training
    compact = json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # 2a. Caracteres UTF-8 literales, no escapados
    assert "JOSÉ MUÑOZ DE LA PEÑA" in compact
    assert "MÉXICO" in compact
    assert "Pérez" in compact   # acento del golden original
    assert "años" in compact     # ñ del golden original
    assert "\\u" not in compact

    # 2b. Estructuralmente compacto: sin espacios después de ":" ni ","
    #     (chequeado tras eliminar el contenido de los strings JSON).
    structural = _strip_json_strings(compact)
    assert ": " not in structural, "compact form tiene ': ' fuera de strings"
    assert ", " not in structural, "compact form tiene ', ' fuera de strings"

    # 2c. Versus la forma indentada: la compacta es estrictamente más corta
    indented = json.dumps(
        result.model_dump(mode="json"), ensure_ascii=False, indent=2
    )
    assert len(compact) < len(indented)


def test_round_trip():
    """Validar → dump → re-validar produce un objeto Pydantic equivalente."""
    data = json.loads(
        (GOLDEN_DIR / "valid_moral_con_representante.json").read_text(encoding="utf-8")
    )
    a = validate_annotation(data)
    dumped = a.model_dump(mode="json")
    b = validate_annotation(dumped)
    assert a == b
    # Y el round-trip es estable: dump(b) == dump(a)
    assert b.model_dump(mode="json") == dumped
