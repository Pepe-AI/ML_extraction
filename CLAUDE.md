# Proyecto: ML Extraction — Escrituras de Compra-Venta

Modelo fine-tuned para extraer datos estructurados de escrituras notariales mexicanas.
Entrada: texto OCR de prosa legal corrida. Salida: JSON jerárquico con valores normalizados y source_text.

## Infraestructura

- Servidor: Ubuntu 24.04, RTX 5090 32GB, CUDA 12.6
- PostgreSQL: 192.168.200.156 → BD `erpp` (datos fuente), `labelstudio`, `ml_extraction` (user: ml_user)
- Label Studio: http://192.168.200.11:8080
- Python 3.11+ con venv, Pydantic v2

## Stack por fase

| Fase | Herramientas |
|------|-------------|
| Anotación (1) | Label Studio, DVC, Pydantic v2, psycopg2-binary |
| Preprocesamiento (2) | Script determinístico (sin LLM) |
| Training (3,5) | PEFT, TRL, bitsandbytes, Qwen3-4B, W&B |
| Evaluación (4) | scikit-learn, Optuna |
| Serving (6,7) | vLLM, FastAPI, Docker, NVIDIA Container Toolkit |
| OCR externo | Azure Document Intelligence |

## Convenciones globales (OBLIGATORIO en todo el código)

### Campos ausentes
- `null` = el campo NO APLICA al documento (ej: tipo_sociedad para persona FISICA)
- `"NA"` + qa_flag = el campo APLICA pero no se encontró en el texto
- `""` = **NUNCA USAR.** Rechazar siempre strings vacíos

### Normalización de valores
- Fechas: `YYYY-MM-DD`
- Montos: `float` con 2 decimales (ej: `8654.00`)
- RFC/CURP: mayúsculas, sin espacios (ej: `GARC850101H01`)
- Tipo persona: solo `FISICA` o `MORAL`
- valor_catastral_bool: solo `true` o `false`

### JSON para training vs producción
- Training: `json.dumps(data, ensure_ascii=False, separators=(",",":"))`  ← compacto, sin indent
- Producción (post-inferencia): `json.dumps(data, ensure_ascii=False, indent=2)` ← formateado

### Metadatos obligatorios en cada JSON anotado
- `schema_version`: `"v1"`
- `preprocess_version`: versión del script preprocess_ocr.py usado (ej: `"v1.0"`)

## Estructura del proyecto

```
ml-extraction/
├── data/
│   ├── raw/              # PDFs y archivos OCR originales
│   ├── annotated/        # JSONs etiquetados (DVC tracked)
│   └── processed/        # Dataset procesado para training
├── src/
│   ├── annotation/       # Schema Pydantic, validación, pre-anotación
│   ├── preprocessing/    # Limpieza OCR (Lista 1 + corte antecedentes)
│   ├── training/         # QLoRA fine-tuning
│   ├── evaluation/       # Métricas por campo, splits
│   ├── serving/          # vLLM + FastAPI gateway
│   └── utils/            # Funciones compartidas
├── configs/              # YAML de configuración (hiperparámetros, etc.)
├── docker/               # Dockerfiles y docker-compose
├── tests/                # Tests unitarios por módulo
└── pyproject.toml
```

## Decisiones ya tomadas (NO re-discutir)

- **Modelo primario:** Qwen3-4B + QLoRA. Alternativa: Qwen3-8B (comparar en Fase 4)
- **seq_len:** 16,384 tokens. Budget real para input: ~14,879 tokens (caso complejo)
- **Non-thinking mode:** `enable_thinking=False` para extracción
- **Test set:** se congela en milestone 700. Nuevos datos (700→1500) solo van a train/validation
- **DVC remote:** obligatorio desde Fase 0
- **Alcance:** solo escrituras de compra-venta. Otros tipos en versión futura
- **Anotadores:** trabajan con texto preprocesado, no OCR crudo. PDF solo como referencia

## NO hacer (anti-patterns)

- No usar `indent` en JSON de training
- No agregar campos que no existan en schema v1
- No usar strings vacíos `""` — solo `null` o `"NA"`
- No mezclar patrones del sistema viejo (`false`, `"NO SE ENCONTRÓ DATO"`)
- No usar LLM en el preprocesamiento — es determinístico
- No confiar en métricas del milestone 200 como indicador de calidad
