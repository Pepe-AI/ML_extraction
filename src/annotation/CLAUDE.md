# src/annotation/ — Schema v1, validación y pre-anotación

> **Especificación autoritativa:** `docs/specs/spec_schema_v1.md`.
> Este archivo es un resumen orientativo. Ante cualquier conflicto, manda el spec.

## Orden de implementación

```
schema_v1.py → validate.py → preannotate_from_db.py → preannotate_from_ocr.py
```

Los dos primeros son prerrequisito de todo lo demás en Fase 1.

## Schema v1 — Estructura del JSON anotado

Todos los campos de datos se envuelven en `FieldWithEvidence[T]` (clase genérica única, decisión 1 del spec):

```json
{
  "schema_version": "v1",
  "preprocess_version": "preprocess@a3f8b21",
  "doc_id": "ESC_28060",
  "file_name": "escritura_28060.pdf",
  "annotator": "nombre_anotador",
  "labeled_at": "2026-04-15",
  "observaciones": "",
  "qa_flags": [],
  "sections": [
    {
      "section_norm": "DECLARACIONES",
      "raw_title": "ANTECEDENTES",
      "page_start": 1,
      "page_end": 2,
      "evidence": [
        {"section_norm": "DECLARACIONES", "page": 1, "lines": "1-2", "source_text": "..."}
      ]
    }
  ],
  "fields": {
    "numero_escritura":     {"value": "2307",       "evidence": [...]},
    "fecha_documento":      {"value": "2023-05-05", "evidence": [...]},
    "valor_catastral_bool": {"value": true,         "evidence": [...]},
    "monto_operacion":      {"value": 8654.00, "currency": "MXN", "evidence": [...]},
    "numero_notaria":       {"value": "35",         "evidence": [...]},
    "nombre_notario":       {"value": "RIGOBERTO OCHOA TORRES", "evidence": [...]},
    "municipio":            {"value": "TEPIC, NAYARIT", "evidence": [...]}
  },
  "titulares": [
    {
      "id": "T1",
      "nombre":         {"value": "INMOBILIARIA X S.A. DE C.V.", "evidence": [...]},
      "tipo":           {"value": "MORAL", "evidence": [...]},
      "estado_civil":   {"value": null, "evidence": []},
      "tipo_sociedad":  {"value": "SOCIEDAD ANONIMA DE CV", "evidence": [...]},
      "edad":           {"value": null, "evidence": []},
      "rfc":            {"value": "INX800101AB1", "evidence": [...]},
      "curp":           {"value": null, "evidence": []},
      "representantes": [
        {
          "id": "T1_R1",
          "nombre":          {"value": "JUAN PEREZ LOPEZ", "evidence": [...]},
          "actua_por":       {"value": "INMOBILIARIA X S.A. DE C.V.", "evidence": [...]},
          "en_calidad":      {"value": "APODERADO LEGAL", "evidence": [...]},
          "poder_escritura": {"value": "63", "evidence": [...]},
          "fecha_poder":     {"value": "2020-04-15", "evidence": [...]}
        }
      ],
      "entity_flags": []
    }
  ],
  "adquirientes": [
    {
      "id": "A1",
      "nombre":         {"value": "JOSE PEREZ SANCHEZ", "evidence": [...]},
      "tipo":           {"value": "FISICA", "evidence": [...]},
      "estado_civil":   {"value": "CASADO", "evidence": [...]},
      "tipo_sociedad":  {"value": null, "evidence": []},
      "edad":           {"value": 38, "evidence": [...]},
      "rfc":            {"value": "PESJ850515ABC", "evidence": [...]},
      "curp":           {"value": "PESJ850515HNTRZN08", "evidence": [...]},
      "representantes": [],
      "entity_flags": []
    }
  ]
}
```

## Titulares vs Adquirientes

**Estructuralmente iguales.** Ambos usan la misma clase `Entity` con todos los mismos campos. La diferencia es **qué campos típicamente se llenan** según el rol legal:

| Campo | Titulares (vendedor) | Adquirientes (comprador) |
|---|---|---|
| `nombre` | ✅ siempre | ✅ siempre |
| `tipo` (FISICA/MORAL) | ✅ siempre | ✅ siempre |
| `estado_civil` | ❌ normalmente null | ✅ típico cuando FISICA |
| `tipo_sociedad` | ✅ típico cuando MORAL | ❌ normalmente null |
| `edad` | ❌ normalmente null | ✅ típico cuando FISICA |
| `rfc` | ⚠️ a veces | ✅ típico |
| `curp` | ❌ normalmente null | ✅ típico cuando FISICA |
| `representantes[]` | ✅ requerido si MORAL | ✅ requerido si MORAL |
| `entity_flags` | ✅ siempre (puede ser []) | ✅ siempre (puede ser []) |

**Por qué unificamos la estructura**: el modelo de ML aprende un solo patrón de salida. La distinción FISICA/MORAL conduce qué campos van llenos. Más limpio para training que dos JSONs con shape distinto.

## Training targets vs campos de QA

Para el training del modelo, **solo** se usan `value` y `source_text`.

Los campos `section_norm`, `page`, `lines` dentro de cada `Evidence` son para **control de calidad interno** (auditoría, debug de OCR). Los anotadores capturan los 4 elementos, pero el dataset de training los descarta antes de armar las parejas (input, output).

## Estados de los campos (decisión 6)

| Estado | Significado | Aplica a |
|---|---|---|
| Valor real | Dato encontrado | Todos |
| `"NA"` | Campo **obligatorio** no encontrado | Solo obligatorios |
| `null` | Campo **opcional** no aplica al documento | Solo opcionales |
| `""` | **PROHIBIDO siempre** (excepto `observaciones`) | Ningún campo |

**Obligatorios del documento** (admiten `"NA"`):
`numero_escritura`, `fecha_documento`, `numero_notaria`, `nombre_notario`, `municipio`

**Obligatorios con valor concreto** (sin `"NA"`):
`valor_catastral_bool`, `Entity.tipo`

**Opcionales** (admiten `null`):
`edad`, `estado_civil`, `tipo_sociedad`, `rfc`, `curp`

## Reglas de validación (5 cross-field)

1. `valor_catastral_bool=false` → `monto_operacion` debe ser `null`
2. `valor_catastral_bool=true` + monto no encontrado → `monto_operacion.value="NA"` + qa_flag `"NA:monto_operacion"`
3. `tipo="MORAL"` con `representantes=[]` → entity_flag `"MORAL_SIN_REPRESENTANTE_ENCONTRADO"` requerido
4. Campo obligatorio con `value="NA"` → qa_flag `"NA:{campo}"` requerido
5. Strings vacíos prohibidos en cualquier `value` (excepto `observaciones`)

## Normalizaciones automáticas (4 grupos, mode='before')

1. `rfc` / `curp`: `upper() + remove spaces & dashes`
2. `monto_operacion.value`: `round(_, 2)`
3. Enums (`tipo`, `currency`, `section_norm`): `strip().upper()` + validación Enum
4. Fechas (`fecha_documento`, `labeled_at`, `fecha_poder`): **estricto YYYY-MM-DD**. Rechazar formatos en español.

## `preprocess_version` — Versionamiento por SHA de git

Formato: `"preprocess@<sha7>"` donde `<sha7>` es el SHA corto del último commit que tocó `src/preprocessing/preprocess_ocr.py`. Se genera automáticamente con:

```bash
git log -1 --format=%h -- src/preprocessing/preprocess_ocr.py
```

Si el archivo aún no se ha committeado, retornar `"preprocess@uncommitted"`.

Sirve para detectar JSONs anotados con una versión obsoleta del preprocesador y disparar re-preprocesamiento.

## `validate.py` — Único entry point

Patrón Registry:

```python
SCHEMA_REGISTRY: dict[str, Type[BaseModel]] = {
    "v1": AnnotationV1,
    # "v2": AnnotationV2,  ← cuando llegue
}
```

Nadie importa `AnnotationV1` directamente. Todo pasa por `validate_annotation(data)` que enruta por `schema_version`. Cuando llegue v2, son 3 líneas de cambio.

CLI: `python -m src.annotation.validate <archivos>`. Exit 0 si todo pasa, 1 si hay errores, 2 si no se encontraron archivos.

## Pre-anotación Camino A — PostgreSQL `erpp`

Script: `preannotate_from_db.py --doc_id=XXXX`

- Credenciales desde `.env`: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- BD fuente: `erpp` en 192.168.200.156
- **Pendiente:** mapeo erpp → schema v1 (requiere revisar estructura real de tablas)
- Campos no encontrados en BD: `value=null` para opcionales, `value="NA"` + qa_flag para obligatorios
- Genera automáticamente: `schema_version`, `preprocess_version`, `doc_id`, `file_name`
- Output: `data/annotated/{doc_id}.json`
- **Antes de guardar:** validar con `validate_annotation()`. Si falla, abortar.

## Pre-anotación Camino B — Azure OCR + LLM

Script: `preannotate_from_ocr.py --pdf=ruta/doc.pdf`

- Azure: `AZURE_ENDPOINT`, `AZURE_KEY`
- LLM fallback: `LLM_PROVIDER` (deepseek|gemini), `LLM_API_KEY`
- OCR crudo se guarda en `data/raw/{doc_id}_ocr.txt`
- En `observaciones`: `"Pre-anotado por LLM, requiere verificación humana"`
- **Antes de guardar:** validar con `validate_annotation()`. Si falla, abortar.

## Tests

- `tests/test_annotation/test_schema_v1.py` — un test por regla + iteración sobre golden files
- `tests/test_annotation/test_validate.py` — tests del dispatcher y CLI
- `tests/test_annotation/golden/` — fixtures JSON válidos e inválidos por regla

## Comandos útiles

```bash
# Correr tests del módulo
pytest tests/test_annotation/ -v

# Validar JSONs anotados
python -m src.annotation.validate data/annotated/*.json

# Validar con check de preprocess_version
python -m src.annotation.validate --check-preprocess data/annotated/*.json
```

## Notas

- `observaciones` es el único campo donde `""` está permitido (no es un campo de datos, es nota libre del anotador).
- `evidence=[]` solo está permitido cuando `value=null` (campo opcional no aplica). Cualquier otro caso requiere al menos 1 evidencia.
- El `id` de entities sigue regex `^(T|A)\d+$`; el de representantes `^(T|A)\d+_R\d+$`. Mal formato falla.
