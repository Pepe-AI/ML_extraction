# src/training/ — QLoRA fine-tuning de Qwen3-4B

## Modelo

- **Primario:** Qwen3-4B (4B params, denso, Apache 2.0)
- **Alternativa:** Qwen3-8B (comparar en Fase 4)
- **Tokenizer:** BBPE, 151,669 tokens, eficiente para español
- **Non-thinking mode:** `enable_thinking=False` siempre para extracción

## Hiperparámetros iniciales

| Parámetro | Valor | Rango Optuna |
|-----------|-------|-------------|
| LoRA rank (r) | 32 | 8, 16, 32, 64 |
| LoRA alpha | 64 | alpha = 2 × r |
| Learning rate | 2e-4 | 1e-5 a 5e-4 |
| Épocas | 5 | 3 a 10 |
| Batch size | 4 | sujeto a profiling |
| Gradient accum. | 4 | effective batch = 16 |
| Seq length | 16,384 | fijo |
| Target modules | q, k, v, o + MLP (gate, up, down) | ~20M params (~0.6%) |

## VRAM estimada (Qwen3-4B, seq=16384)

| Componente | Mejor caso | Peor caso |
|-----------|-----------|-----------|
| Modelo base 4-bit NF4 | ~4 GB | ~5 GB |
| LoRA adapters + optimizador | ~2 GB | ~3 GB |
| Activaciones (BS=4, gradient checkpoint) | ~10 GB | ~16 GB |
| **Total** | **~16 GB** | **~24 GB** |

Tabla de decisión según profiling VRAM real (Fase 3.0):
- < 24 GB → proceder con BS=4
- 24-28 GB → proceder pero monitorear
- 28-32 GB → reducir BS=2, gradient_accum=8
- > 32 GB → BS=1, gradient_accum=16 o reducir seq_len

## Formato del dataset (chat-style)

```
<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{texto_ocr_preprocesado}<|im_end|>
<|im_start|>assistant
{json_compacto}<|im_end|>
```

### JSON de salida: SIEMPRE compacto
```python
json.dumps(output, ensure_ascii=False, separators=(",",":"))
```
NUNCA usar indent en training. Ahorra ~25-29% de tokens de output.

### Budget de secuencia
- Total: 16,384 tokens
- System prompt: ~90 tokens
- Chat overhead: ~20 tokens
- Output JSON (caso complejo): ~1,399 tokens
- **Disponible para input OCR: ~14,879 tokens**

## Configuración de entrenamiento

- Cargar modelo base en 4-bit NF4 con bitsandbytes
- SFTTrainer de TRL
- Gradient checkpointing: **obligatorio** a seq=16384
- Early stopping por eval_loss
- W&B logging: métricas escalares (loss, eval_loss, learning_rate)

## Splits según milestone

| Milestone | Split | Test set |
|-----------|-------|----------|
| 200 | 80/20 (train/val) | Sin test set. Solo valida plomería |
| 700 | 70/15/15 estratificado | Test set CONGELADO |
| 1500 | Nuevos datos solo a train/val | Mismo test set congelado |

## W&B: gestión de storage

- Free tier: 100GB máximo
- Optuna runs: loggear SOLO métricas escalares, no artifacts ni gradients
- Guardar solo el mejor checkpoint por run
- Plan B si se agota: migrar a MLflow local
