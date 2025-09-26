#!/usr/bin/env bash
# NOTE: GPU is the default for all tools. Use --cpu, --cpu-mineru, --cpu-dotsocr, or --cpu-dolphin to force CPU.
set -euo pipefail

ROOT="/home/yerin/Table-processing"

TARGETS=("$@")

CPU_MINERU=0
CPU_DOTS=0
GPU_DOLPHIN=1

# parse flags
PARSED=()
for arg in "${TARGETS[@]:-}"; do
  case "$arg" in
    --cpu)
      CPU_MINERU=1; CPU_DOTS=1 ;;
    --cpu-mineru)
      CPU_MINERU=1 ;;
    --cpu-dotsocr)
      CPU_DOTS=1 ;;
    --cpu-dolphin)
      GPU_DOLPHIN=0 ;;
    *) PARSED+=("$arg") ;;
  esac
done
TARGETS=("${PARSED[@]}")

# default to all when no specific targets
if [ ${#TARGETS[@]} -eq 0 ] || [[ " ${TARGETS[*]} " =~ " all " ]]; then
  TARGETS=(mineru rapidtable dotsocr dolphin)
fi

run_mineru() {
  echo "[mineru] pipeline -> content_list.json + md"
  if [ "$CPU_MINERU" -eq 1 ]; then
    conda run -n tableproc_mineru bash -lc 'CUDA_VISIBLE_DEVICES="" python '"$ROOT"'/scripts/run_mineru_pipeline.py --lang en'
  else
    conda run -n tableproc_mineru python "$ROOT/scripts/run_mineru_pipeline.py" --lang en
  fi
}

run_rapidtable() {
  echo "[rapidtable]"
  conda run -n tableproc_rapidtable python -u "$ROOT/scripts/run_rapidtable.py" --limit-pages 5 --model-type unitable --scale 3.5
}

run_dotsocr() {
  echo "[dots.ocr] HF"
  if [ "$CPU_DOTS" -eq 1 ]; then
    conda run -n tableproc_dotsocr bash -lc 'CUDA_VISIBLE_DEVICES="" bash '"$ROOT"'/scripts/run_dotsocr.sh'
  else
    conda run -n tableproc_dotsocr bash "$ROOT/scripts/run_dotsocr.sh"
  fi
}

run_dolphin() {
  echo "[dolphin] HF local"
  if [ "$GPU_DOLPHIN" -eq 0 ]; then
    conda run -n tableproc_dolphin bash -lc 'CUDA_VISIBLE_DEVICES="" python '"$ROOT"'/scripts/run_dolphin_hf.py --model-path '"$ROOT"'/tools/Dolphin/hf_model'
  else
    conda run -n tableproc_dolphin python "$ROOT/scripts/run_dolphin_hf.py" --model-path "$ROOT/tools/Dolphin/hf_model"
  fi
}


for t in "${TARGETS[@]}"; do
  case "$t" in
    mineru) run_mineru ;;
    rapidtable) run_rapidtable ;;
    dotsocr) run_dotsocr ;;
    dolphin) run_dolphin ;;
    *) echo "[warn] unknown target: $t" ;;
  esac
done

echo "[done] See outputs/ for results."


