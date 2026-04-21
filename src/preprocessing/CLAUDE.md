# src/preprocessing/ — Limpieza OCR determinística

Script principal: `preprocess_ocr.py`
Este script se usa en training (Fase 2) y en producción (Fase 6). DEBEN ser idénticos.

## Principio: determinístico, sin LLM

Todo el preprocesamiento usa regex y fingerprints de contenido. Nunca se invoca un LLM.

## Lista 1 — Secciones a eliminar (fingerprints de contenido)

NO buscar por título de sección (frágil ante errores OCR). Buscar por frases de contenido.
Matching: `fingerprint.lower() in bloque.lower()` — case-insensitive.

| # | Sección | Fingerprints |
|---|---------|-------------|
| 1 | Régimen fiscal / ISR / IVA / ISAI | `"impuesto sobre la renta"`, `"ISAI"`, `"ley del ISR"`, `"impuesto sobre adquisición"` |
| 2 | Aviso de privacidad | `"datos personales"`, `"derechos ARCO"`, `"protección de datos"` |
| 3 | Apéndice | `"agregados al protocolo"`, `"apéndice"` |
| 4 | Certificación notarial | `"certifico y doy fe"`, `"doy fe de"`, `"fe pública"` |
| 5 | Primer testimonio / cierre | `"primer testimonio"`, `"primera copia"`, `"cierre registral"` |
| 6 | Autorización definitiva | `"autorizo definitivamente"`, `"autorización definitiva"` |
| 7 | Declaraciones institucionales | `"FOVISSSTE"`, `"INFONAVIT"`, `"INSUS"`, `"IPROVINAY"`, `"CORETT"` |
| 8 | Cláusulas 5+ | `"evicción"`, `"saneamiento"`, `"vicios ocultos"`, `"vicios del consentimiento"` |
| 9 | Sellos y artefactos OCR | Patrones: líneas cortas en mayúsculas, alta densidad de chars no-alfanuméricos |

**Estos fingerprints son un punto de partida. Calibrar con los 19 documentos reales.**

## Lista 2 — Secciones que se retienen ÍNTEGRAS

- Encabezado / proemio (numero_escritura, fecha, notario, municipio)
- Cláusulas 1-4 (monto_operacion, transmisión, posesión)
- Generales de comparecientes (RFC, CURP, estado_civil, edad, nombres)
- Personalidad / poderes (representante.escritura, representante.fecha_poder)

## Corte fino de antecedentes

De la sección de antecedentes, solo retener el monto/avalúo.
Eliminar: cadena de transmisiones previas, descripciones de fideicomisos, datos registrales.

## Logging obligatorio

Cada ejecución DEBE producir un log con:
- Secciones detectadas y eliminadas (con el fingerprint que hizo match)
- Caracteres/líneas eliminados por sección
- Secciones de Lista 1 que NO se detectaron (posibles falsos negativos)
- Tokens antes y después del preprocesamiento

## Versionado

- El script se congela con DVC antes de iniciar la anotación
- Cada JSON anotado incluye `preprocess_version` en sus metadatos
- Si el script cambia: re-procesar documentos afectados + validar source_text

## Validación antes de producción

Correr sobre los 19 documentos reales y verificar manualmente en 3-5:
1. Lista 1 eliminada correctamente
2. Lista 2 retenida íntegra
3. Corte de antecedentes correcto (solo monto/avalúo)
4. Sin pérdida de info relevante para schema v1
