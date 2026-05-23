"""Schema Pydantic v2 para anotaciones de escrituras de compra-venta (v1).

Excepción documentada: el campo `observaciones` en AnnotationV1 es el único
donde se permite string vacío (""), por ser nota libre del anotador.
"""

from enum import Enum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator


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

T = TypeVar("T")


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


class Section(BaseModel):
    """Sección identificada dentro de la escritura notarial."""
    section_norm: SectionEnum
    raw_title: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    evidence: list[Evidence] = Field(min_length=1)

    @model_validator(mode="after")
    def page_end_gte_page_start(self) -> "Section":
        if self.page_end < self.page_start:
            raise ValueError(
                f"page_end ({self.page_end}) debe ser >= page_start ({self.page_start})"
            )
        return self


class FieldWithEvidence(BaseModel, Generic[T]):
    """Campo de datos con su evidencia textual de respaldo."""
    value: T
    evidence: list[Evidence]

    @field_validator("value", mode="before")
    @classmethod
    def reject_empty_string(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            raise ValueError(
                "value no puede ser string vacío. Usa 'NA' o null."
            )
        return v

    @model_validator(mode="after")
    def value_evidence_coherence(self) -> "FieldWithEvidence[T]":
        if self.value is None and self.evidence:
            raise ValueError(
                "evidence debe ser [] cuando value es null"
            )
        if self.value is not None and not self.evidence:
            raise ValueError(
                "evidence no puede ser [] cuando value tiene un valor"
            )
        return self
