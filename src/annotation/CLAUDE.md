# src/annotation/ — Schema v1, validación y pre-anotación

Orden de implementación: schema_v1.py → validate.py → preannotate_from_db.py → preannotate_from_ocr.py

## Schema v1 — Estructura completa del JSON anotado

```json
{
  "schema_version": "v1",
  "doc_id": "ESC_28060",
  "file_name": "escritura_28060.pdf",
  "annotator": "nombre_anotador",
  "labeled_at": "YYYY-MM-DD",
  "preprocess_version": "v1.0",
  "observaciones": "",
  "qa_flags": [],
  "sections": [
    {
      "section_norm": "DECLARACIONES",
      "raw_title": "título original del OCR",
      "page_start": 1,
      "page_end": 2,
      "evidence": [{"section_norm": "DECLARACIONES", "page": 1, "lines": "1-2", "source_text": "..."}]
    }
  ],
  "fields": {
    "numero_escritura":   {"value": "2307", "evidence": [{"section_norm": "...", "page": 1, "lines": "...", "source_text": "..."}]},
    "fecha_documento":    {"value": "2023-05-05", "evidence": [...]},
    "valor_catastral_bool": {"value": true, "evidence": [...]},
    "monto_operacion":    {"value": 8654.00, "currency": "MXN", "evidence": [...]},
    "numero_notaria":     {"value": "35", "evidence": [...]},
    "nombre_notario":     {"value": "RIGOBERTO OCHOA TORRES", "evidence": [...]},
    "municipio":          {"value": "TEPIC, NAYARIT", "evidence": [...]}
  },
  "titulares": [
    {
      "id": "T1",
      "nombre":    {"value": "NOMBRE DEL VENDEDOR", "evidence": [...]},
      "tipo":      {"value": "MORAL", "evidence": [...]},
      "representantes": [
        {
          "id": "T1_R1",
          "nombre":          {"value": "...", "evidence": [...]},
          "actua_por":       {"value": "...", "evidence": [...]},
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
      "nombre":        {"value": "NOMBRE DEL COMPRADOR", "evidence": [...]},
      "tipo":          {"value": "FISICA", "evidence": [...]},
      "estado_civil":  {"value": "CASADO", "evidence": [...]},
      "tipo_sociedad": null,
      "edad":          {"value": 38, "evidence": [...]},
      "rfc":           {"value": "PESJ850515ABC", "evidence": [...]},
      "curp":          {"value": "PESJ850515HNTRZN08", "evidence": [...]},
      "representantes": [],
      "entity_flags": []
    }
  ]
}
```

## Diferencia titulares vs adquirientes

| Campo | Titulares | Adquirientes |
|-------|-----------|--------------|
| nombre | ✅ | ✅ |
| tipo (FISICA/MORAL) | ✅ | ✅ |
| estado_civil | ❌ | ✅ |
| tipo_sociedad | ❌ | ✅ |
| edad | ❌ | ✅ |
| rfc | ❌ | ✅ |
| curp | ❌ | ✅ |
| representantes[] | ✅ | ✅ |
| entity_flags | ✅ | ✅ |

## Training targets vs campos de QA

Para el training del modelo, SOLO se usan `value` y `source_text`.
Los campos `section_norm`, `page`, `lines` son para control de calidad interno.
Los anotadores capturan los 4 elementos de evidence, pero el dataset de training los descarta.

## Reglas de validación Pydantic (schema_v1.py)

### Campos obligatorios del documento
`numero_escritura`, `fecha_documento`, `numero_notaria`, `nombre_notario`, `municipio`, `valor_catastral_bool`
- Si falta un obligatorio: `value = "NA"`, agregar `"NA:{campo}"` a qa_flags

### Validadores cross-field
- `valor_catastral_bool = false` → `monto_operacion` DEBE ser `null`
- `valor_catastral_bool = true` y monto falta → `value = "NA"`, agregar `"NA:monto_operacion"` a qa_flags
- `tipo = MORAL` y `representantes` vacío → agregar `"MORAL_SIN_REPRESENTANTE_ENCONTRADO"` a entity_flags
- Campos opcionales: solo aceptar `null` (no aplica) o `"NA"` (no encontrado). Rechazar `""`

### Validadores de formato
- `fecha_documento`: regex `^\d{4}-\d{2}-\d{2}$`
- `monto_operacion.value`: float, 2 decimales
- `rfc` / `curp`: mayúsculas, sin espacios
- `tipo`: solo `FISICA` o `MORAL`

## Pre-anotación: Camino A (PostgreSQL)

Script: `preannotate_from_db.py --doc_id=XXXX`
- Conexión desde `.env`: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- BD fuente: `erpp` en 192.168.200.156
- Mapping erpp → schema v1: **TBD — explorar tablas antes de implementar**
- Campos no encontrados en BD: dejar con `value = null` para que anotador complete
- Llenar automáticamente: schema_version, doc_id, preprocess_version
- Guardar en: `data/annotated/{doc_id}.json`

## Pre-anotación: Camino B (Azure OCR + LLM)

Script: `preannotate_from_ocr.py --pdf=ruta/doc.pdf`
- Azure OCR: variables AZURE_ENDPOINT, AZURE_KEY
- LLM fallback: LLM_PROVIDER (deepseek|gemini), LLM_API_KEY
- Guardar OCR en: `data/raw/{doc_id}_ocr.txt`
- Marcar en observaciones: "Pre-anotado por LLM, requiere verificación humana"
- Validar con Pydantic antes de guardar

## Validación: validate.py

- Recibe ruta a JSON o directorio de JSONs
- Valida cada uno contra el modelo Pydantic
- Reporte: cuántos pasaron, cuáles fallaron, detalle de errores
- Uso: `python src/annotation/validate.py data/annotated/`
