"""Módulo de anotación: schema Pydantic v1 y validación de JSONs anotados.

Punto de entrada público del paquete. Re-exporta los símbolos que los
consumidores externos deben usar (la clase raíz y las funciones de
validación). Si necesitas tipos internos (Evidence, Section, Entity, etc.)
impórtalos directamente desde `src.annotation.schema_v1`.
"""

from .schema_v1 import AnnotationV1
from .validate import (
    SCHEMA_REGISTRY,
    get_preprocess_version,
    validate_annotation,
    validate_file,
)

__all__ = [
    "AnnotationV1",
    "SCHEMA_REGISTRY",
    "get_preprocess_version",
    "validate_annotation",
    "validate_file",
]
