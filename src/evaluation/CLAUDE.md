# src/evaluation/ — Métricas, splits y análisis

## Métricas por campo

| Métrica | Campos | Umbral mínimo |
|---------|--------|---------------|
| Exact match | numero_escritura, fecha_documento, numero_notaria, valor_catastral_bool | ≥ 0.85 |
| F1 token-level | nombre_notario, municipio, nombres de titulares/adquirientes | ≥ 0.80 |
| Validación Pydantic | % de outputs que pasan sin errores | ≥ 0.95 |

Estos umbrales son iniciales. Ajustar con datos reales en Fase 4.

## Confidence scoring por campo

**Diferido a Fase 6.** No se puede diseñar sin datos empíricos del modelo entrenado.

- **Plan A:** log-probabilities de vLLM agregados a nivel de campo
- **Plan B (fallback):** heurístico de source_text

| Condición | Confianza |
|-----------|-----------|
| source_text aparece como substring exacto en input | Alta |
| source_text con match fuzzy > 90% | Media |
| source_text no se encuentra en input | Baja (posible alucinación) |

## Clasificación de complejidad (para estratificación de splits)

Función: `classify_complexity(json_data) -> "simple" | "medio" | "complejo"`

| Nivel | Criterios |
|-------|-----------|
| Simple | 1 titular + 1 adquiriente, ambos FISICA, 0 representantes |
| Medio | 2+ partes en total, O al menos 1 MORAL, O al menos 1 representante |
| Complejo | 3+ partes, Y al menos 1 MORAL con representante, O fideicomisos |

El split estratificado garantiza proporción similar de simple/medio/complejo en train, validation y test.

## Interpretación de milestones

### Milestone 200 — solo plomería
- Confirma: pipeline funciona end-to-end, sin OOM, JSON válido, W&B loggea
- NO confirma: calidad del modelo (puede memorizar 160 ejemplos fácilmente)
- Métricas altas → continuar a 700, no celebrar
- Métricas bajas (F1 < 0.60) → investigar datos/preprocesamiento antes de continuar

### Milestone 700 — evaluación real
- Test set congelado (15% = ~105 documentos)
- Métricas sobre test set son la referencia para decisiones de producción
- Si se entrenaron Qwen3-4B y Qwen3-8B, comparar ambos aquí

## Comparación vs baseline (diferida)

La comparación formal contra el sistema actual (DeepSeek+Gemini) es diferible.
Se implementa bajo demanda si stakeholders lo solicitan.
Procedimiento: crear old_schema_to_v1.py → correr ambos sobre test set → comparar por campo.
