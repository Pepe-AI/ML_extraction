"""Schema Pydantic v2 para anotaciones de escrituras de compra-venta (v1).

Excepción documentada: el campo `observaciones` en AnnotationV1 es el único
donde se permite string vacío (""), por ser nota libre del anotador.
"""

from enum import Enum
from typing import Literal


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
