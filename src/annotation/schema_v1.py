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


class Representative(BaseModel):
    """Representante legal de una entidad (titular o adquiriente)."""
    id: str = Field(pattern=r"^(T|A)\d+_R\d+$")
    nombre: FieldWithEvidence[StrOrNA]
    actua_por: FieldWithEvidence[StrOrNA]
    en_calidad: FieldWithEvidence[StrOrNA]
    poder_escritura: FieldWithEvidence[StrOrNA]
    fecha_poder: FieldWithEvidence[StrOrNA]


class Entity(BaseModel):
    """Persona física o moral que participa en la operación (titular o adquiriente)."""
    id: str = Field(pattern=r"^(T|A)\d+$")
    nombre: FieldWithEvidence[StrOrNA]
    tipo: FieldWithEvidence[TipoEnum]
    estado_civil: FieldWithEvidence[str | None]
    tipo_sociedad: FieldWithEvidence[str | None]
    edad: FieldWithEvidence[int | None]
    rfc: FieldWithEvidence[str | None]
    curp: FieldWithEvidence[str | None]
    representantes: list[Representative]
    entity_flags: list[str]

    @field_validator("edad", mode="after")
    @classmethod
    def edad_no_negativa(
        cls, v: "FieldWithEvidence[int | None]"
    ) -> "FieldWithEvidence[int | None]":
        if v.value is not None and v.value < 0:
            raise ValueError(f"edad debe ser >= 0, se recibió {v.value}")
        return v

    @model_validator(mode="after")
    def moral_requiere_representante_o_flag(self) -> "Entity":
        if self.tipo.value == "MORAL":
            tiene_rep = len(self.representantes) >= 1
            tiene_flag = "MORAL_SIN_REPRESENTANTE_ENCONTRADO" in self.entity_flags
            if not (tiene_rep or tiene_flag):
                raise ValueError(
                    f"Entity '{self.id}' con tipo=MORAL requiere al menos un "
                    f"representante o el flag 'MORAL_SIN_REPRESENTANTE_ENCONTRADO' "
                    f"en entity_flags"
                )
        return self


class MontoOperacion(BaseModel):
    """Monto monetario de la operación con su moneda y evidencia."""
    value: float | Literal["NA"]
    currency: CurrencyEnum
    evidence: list[Evidence] = Field(min_length=1)

    @field_validator("value", mode="after")
    @classmethod
    def value_no_negativo(cls, v: float | Literal["NA"]) -> float | Literal["NA"]:
        if isinstance(v, float) and v < 0:
            raise ValueError(f"monto_operacion.value debe ser >= 0, se recibió {v}")
        return v


class DocumentFields(BaseModel):
    """Campos extraídos del documento (escritura)."""
    numero_escritura: FieldWithEvidence[StrOrNA]
    fecha_documento: FieldWithEvidence[StrOrNA]
    valor_catastral_bool: FieldWithEvidence[bool]
    monto_operacion: MontoOperacion | None
    numero_notaria: FieldWithEvidence[StrOrNA]
    nombre_notario: FieldWithEvidence[StrOrNA]
    municipio: FieldWithEvidence[StrOrNA]

    @model_validator(mode="after")
    def coherencia_valor_catastral_monto(self) -> "DocumentFields":
        if self.valor_catastral_bool.value is False:
            if self.monto_operacion is not None:
                raise ValueError(
                    "Si valor_catastral_bool=False, monto_operacion debe ser null."
                )
        if self.valor_catastral_bool.value is True:
            if self.monto_operacion is None:
                raise ValueError(
                    "Si valor_catastral_bool=True, monto_operacion no puede ser null. "
                    "Usa value='NA' si no se encontró."
                )
        return self


# Campos obligatorios del documento (admiten "NA" + qa_flag, no admiten null).
_CAMPOS_OBLIGATORIOS_DOC: tuple[str, ...] = (
    "numero_escritura",
    "fecha_documento",
    "numero_notaria",
    "nombre_notario",
    "municipio",
)


class AnnotationV1(BaseModel):
    """Anotación completa de una escritura de compra-venta (raíz del schema v1).

    Nota: `observaciones` es el único campo del schema donde se permite
    string vacío (""), por ser nota libre del anotador (no es campo de datos).
    """
    schema_version: Literal["v1"]
    preprocess_version: str = Field(
        pattern=r"^preprocess@([a-f0-9]{7,40}|uncommitted)$"
    )
    doc_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    annotator: str = Field(min_length=1)
    labeled_at: str
    observaciones: str
    qa_flags: list[str]
    sections: list[Section] = Field(min_length=1)
    fields: DocumentFields
    titulares: list[Entity] = Field(min_length=1)
    adquirientes: list[Entity] = Field(min_length=1)

    @model_validator(mode="after")
    def qa_flag_monto_operacion(self) -> "AnnotationV1":
        monto = self.fields.monto_operacion
        if monto is not None and monto.value == "NA":
            if "NA:monto_operacion" not in self.qa_flags:
                raise ValueError(
                    "monto_operacion.value='NA' requiere 'NA:monto_operacion' "
                    "en qa_flags"
                )
        return self

    @model_validator(mode="after")
    def qa_flags_campos_obligatorios(self) -> "AnnotationV1":
        faltantes: list[str] = []
        for campo in _CAMPOS_OBLIGATORIOS_DOC:
            field_obj = getattr(self.fields, campo)
            if field_obj.value == "NA" and f"NA:{campo}" not in self.qa_flags:
                faltantes.append(f"NA:{campo}")
        if faltantes:
            raise ValueError(
                f"Faltan qa_flags para campos en 'NA': {faltantes}"
            )
        return self
