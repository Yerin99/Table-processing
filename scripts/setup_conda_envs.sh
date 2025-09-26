#!/usr/bin/env bash
set -euo pipefail

# This script creates separate conda environments for each library to avoid dependency conflicts.
# - Requires: conda installed and available in PATH
# - Usage: bash scripts/setup_conda_envs.sh

ROOT_DIR="/home/yerin/Table-processing"

create_env() {
  local env_name="$1"
  local py_ver="$2"
  echo "[conda] creating env: ${env_name} (python=${py_ver})"
  conda create -y -n "${env_name}" python="${py_ver}"
}

install_mineru() {
  local env_name="$1"
  echo "[mineru] installing into ${env_name}"
  conda run -n "${env_name}" python -m pip install --upgrade pip
  # install mineru (pipeline mode for CPU) from local source
  conda run -n "${env_name}" python -m pip install -e "${ROOT_DIR}/tools/MinerU[pipeline]"
}

install_dotsocr() {
  local env_name="$1"
  echo "[dots.ocr] installing into ${env_name}"
  conda run -n "${env_name}" python -m pip install --upgrade pip
  # CPU-safe install to avoid fragile CUDA/cu122 wheel pinning
  conda run -n "${env_name}" python -m pip install --no-deps -e "${ROOT_DIR}/tools/dots.ocr"
  conda run -n "${env_name}" python -m pip install \
    transformers==4.51.3 huggingface_hub qwen-vl-utils PyMuPDF pydantic openai \
    accelerate tqdm \
    torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
}

install_rapidtable() {
  local env_name="$1"
  echo "[RapidTable] installing into ${env_name}"
  conda run -n "${env_name}" python -m pip install --upgrade pip
  # Prefer PyPI wheel to avoid setup-time helper import issues
  conda run -n "${env_name}" python -m pip install rapid-table rapidocr>=3.0.0 pypdfium2 tqdm onnxruntime>=1.17.0
}

install_dolphin_hf() {
  local env_name="$1"
  echo "[Dolphin HF] installing into ${env_name}"
  conda run -n "${env_name}" python -m pip install --upgrade pip
  conda run -n "${env_name}" python -m pip install -r "${ROOT_DIR}/tools/Dolphin/requirements.txt"
}

install_monkeyocr() {
  local env_name="$1"
  echo "[MonkeyOCR repo] installing into ${env_name}"
  conda run -n "${env_name}" python -m pip install --upgrade pip
  # repo base requirements (leave torch per repo spec)
  conda run -n "${env_name}" python -m pip install -r "${ROOT_DIR}/tools/MonkeyOCR/requirements.txt"
  # PaddlePaddle + PaddleX for PP-DocLayout_plus-L (GPU preferred; fallback to CPU if wheel not available)
  conda run -n "${env_name}" bash -lc 'python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu122/ || python -m pip install paddlepaddle==3.0.0'
  conda run -n "${env_name}" python -m pip install "paddlex[base]"
  # utilities
  conda run -n "${env_name}" python -m pip install pypdfium2 opencv-contrib-python
}

main() {
  # Python versions chosen for broad compatibility
  create_env tableproc_mineru 3.10
  create_env tableproc_dotsocr 3.12
  create_env tableproc_rapidtable 3.10
  create_env tableproc_dolphin 3.10
  # MonkeyOCR excluded due to CUDA 12.2 incompatibility in current environment

  install_mineru tableproc_mineru
  install_dotsocr tableproc_dotsocr
  install_rapidtable tableproc_rapidtable
  install_dolphin_hf tableproc_dolphin
  # skip MonkeyOCR install

  echo "[done] environments created. To activate: conda activate <env_name>"
}

main "$@"


