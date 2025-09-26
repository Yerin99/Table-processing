#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/yerin/Table-processing"
PARSER="$ROOT/tools/dots.ocr/dots_ocr/parser.py"
OUT_DIR="$ROOT/outputs/dotsocr"
DOC_DIR="$ROOT/documents"
LOG="$ROOT/outputs/dotsocr_run.log"
MD_SUMMARY="$OUT_DIR/summary.md"

mkdir -p "$OUT_DIR"

# Force HF path to avoid FlashAttention2 even on GPU
export USE_FLASH_ATTENTION_2=0
export HF_USE_FLASH_ATTENTION_2=0
export TRANSFORMERS_ATTENTION_IMPLEMENTATION=eager

# require local weights to avoid online download
if [ ! -d "$ROOT/tools/dots.ocr/weights/DotsOCR" ]; then
  echo "[dots.ocr] skip: local weights not found at tools/dots.ocr/weights/DotsOCR" | tee -a "$LOG"
  echo "[dots.ocr] place pre-downloaded weights at that path to enable offline runs." | tee -a "$LOG"
  exit 0
fi

# run over all PDFs
for pdf in "$DOC_DIR"/*.pdf; do
  [ -e "$pdf" ] || continue
  echo "[dots.ocr] parsing: $(basename "$pdf")" | tee -a "$LOG"
  (cd "$ROOT/tools/dots.ocr" && python "$PARSER" "$pdf" \
    --output "$OUT_DIR" \
    --prompt prompt_layout_all_en \
    --use_hf True \
    --num_thread 1 | tee -a "$LOG") || true
 done

echo "[dots.ocr] done. outputs at $OUT_DIR" | tee -a "$LOG"

# build a simple md preview with tables if present
{
  echo "# dots.ocr"
  echo
  for md in "$OUT_DIR"/*/*.md; do
    [ -e "$md" ] || continue
    if grep -qi "<table" "$md"; then
      echo "## $(basename "$(dirname "$md")")"
      echo
      awk 'BEGIN{IGNORECASE=1} /<table/{printit=1} printit{print} /<\/table>/{printit=0}' "$md"
      echo
    fi
  done
} > "$MD_SUMMARY" || true


