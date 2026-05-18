"""Schema Pydantic v2 para anotaciones de escrituras de compra-venta (v1).

Excepción documentada: el campo `observaciones` en AnnotationV1 es el único
donde se permite string vacío (""), por ser nota libre del anotador.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────

class SectionEnum(str, Enum):
    """Secciones normalizadas de una escritura notarial."""
    DECLARACIONES = "DECLARACIONES"
    CLAUSULAS = "CLAUSULAS"
    PERSONALIDAD = "PERSONALIDAD"
    GENERALES = "GENERALES"
    AUTORIZO = "AUTORIZO"
    UNKNOWN = "UNKNOWN"


class TipoEnum(str, Enum):
    """Tipo de persona: física o moral."""
    FISICA = "FISICA"
    MORAL = "MORAL"


class CurrencyEnum(str, Enum):
    """Monedas aceptadas para montos de operación."""
    MXN = "MXN"
    USD = "USD"


# ── Type aliases ─────────────────────────────────────────────────────────

StrOrNA = str | Literal["NA"]


# ── Modelos base ─────────────────────────────────────────────────────────

class Evidence(BaseModel):
    """Evidencia textual que respalda un campo extraído."""
    section_norm: SectionEnum
    page: int = Field(ge=1)
    lines: str = Field(pattern=r"^\d+(-\d+)?$")
    source_text: str = Field(min_length=1, max_length=160)

    @field_validator("source_text")
    @classmethod
    def source_text_not_blank(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("source_text no puede ser vacío después de strip()")
        return v
