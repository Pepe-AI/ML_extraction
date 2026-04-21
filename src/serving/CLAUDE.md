# src/serving/ — vLLM + FastAPI gateway

## Pipeline de producción

```
PDF → Azure OCR → preprocess_ocr.py → modelo (JSON compacto) → json.loads → json.dumps(indent=2) → validación Pydantic → respuesta
```

**CRÍTICO:** El preprocesamiento en producción DEBE ser idéntico al usado en training (mismo script preprocess_ocr.py). Si el modelo se entrenó con texto preprocesado pero en producción recibe texto crudo, el rendimiento se degrada.

## vLLM server (Fase 6.2)

- Modelo: Qwen3-4B merged (LoRA + base) + cuantización AWQ
- VRAM inferencia AWQ 4-bit: ~3-4 GB (4B) o ~5-6 GB (8B)
- Guided decoding: JSON schema de compra-venta para garantizar output válido
- PagedAttention para throughput óptimo
- API compatible con OpenAI
- Non-thinking mode: `enable_thinking=False`

## Merge y cuantización (Fase 6.1)

1. Script para merge LoRA adapters con modelo base Qwen3-4B
2. Cuantización AWQ para inferencia
3. Verificar que el modelo merged genera output equivalente al LoRA

## FastAPI gateway (Fase 6.3)

- Endpoint: `POST /extract` — recibe PDF de compra-venta
- Pipeline interno: OCR → preprocess → modelo → reformat → validate → response
- El modelo genera JSON compacto (así fue entrenado)
- El gateway reformatea: `json.loads(model_output)` → `json.dumps(parsed, indent=2)`
- Validación Pydantic antes de responder
- Respuesta incluye JSON + confidence scores por campo (cuando se implemente)

## Docker (Fase 6.4)

- Dockerfile con NVIDIA Container Toolkit
- docker-compose.yml con servicios: vllm-server, fastapi-gateway
- El gateway depende de que vllm-server esté healthy antes de aceptar requests

## Confidence scoring (diferido)

No implementar hasta tener modelo entrenado y datos empíricos.

- **Plan A:** log-probabilities de vLLM agregados a nivel de campo
  - Requiere evaluar si el modelo es sobreconfiado (fine-tuning con pocos datos puede causar esto)
  - Diseño exacto (media, mínimo, percentil) se decide con datos reales

- **Plan B (fallback):** verificar si source_text generado aparece en el input
  - Determinístico, sin calibración
  - Puede complementar Plan A incluso si log-probs funcionan

## Monitoreo (Fase 7.1)

- Logging de confidence scores por campo para detectar drift
- Alertas cuando confidence promedio baja de umbral
- Dashboard básico de métricas de uso
