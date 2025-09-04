# Models

Lägg nedladdade modeller här. Rekommenderat:

- multilingual-e5-small (ONNX) + tokenizer.json
- XNLI (xlm-roberta-xnli) ONNX + tokenizer

Hälsokontroller:

- NLU läser `E5_ONNX_PATH` och `E5_TOKENIZER_JSON`
- XNLI läses via `XNLI_ONNX_PATH` och `XNLI_TOKENIZER_DIR`

Kör `./scripts/download_models.sh` för att hämta.
