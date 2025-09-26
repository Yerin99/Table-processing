# Table-processing
영문 선급 PDF 문서에서 테이블을 HTML/Markdown으로 추출하기 위한 통합 러너 프로젝트.

## Quickstart

1) Conda 환경 생성 및 설치

```bash
bash scripts/setup_conda_envs.sh
```

생성되는 환경
- tableproc_mineru: MinerU 파이프라인
- tableproc_rapidtable: RapidTable
- tableproc_dotsocr: dots.ocr
- tableproc_dolphin: Dolphin (HF)
<!-- MonkeyOCR: excluded for CUDA 12.2 env -->

2) 문서 위치
- 입력 PDF: `documents/` (예: `documents/DNV-CG-0550 77-84.pdf`)

3) 통합 실행

```bash
bash scripts/run_all.sh
```

기본값은 GPU 사용이며, CPU 강제는 플래그로 설정합니다. 또한 원하는 대상만 선택 실행할 수 있습니다.

선택 실행 예시
- 전체: `bash scripts/run_all.sh`
- 일부만: `bash scripts/run_all.sh mineru rapidtable`
- 단일: `bash scripts/run_all.sh dotsocr`

CPU 강제 플래그
- MinerU+dots.ocr 모두 CPU: `bash scripts/run_all.sh all --cpu`
- MinerU만 CPU: `bash scripts/run_all.sh mineru --cpu-mineru`
- dots.ocr만 CPU: `bash scripts/run_all.sh dotsocr --cpu-dotsocr`

참고: 각 단계는 `conda run -n tableproc_<tool>`로 분리된 환경에서 실행됩니다.

## 개별 실행

### MinerU (pipeline)
`content_list.json` 생성

```bash
conda activate tableproc_mineru
python scripts/run_mineru_pipeline.py --lang en
```

출력:
- JSON: `outputs/mineru/<doc>/auto/<doc>_content_list.json`
- 미리보기(MD, table은 HTML): `outputs/mineru/<doc>/auto/<doc>.md`
  (이 파일은 테이블 블록만 모아둔 미리보기입니다.)

### RapidTable

```bash
conda activate tableproc_rapidtable
python scripts/run_rapidtable.py --limit-pages 5
```

출력:
- HTML: `outputs/rapidtable/<doc>/page_XXXX.html`
- 미리보기(MD): `outputs/rapidtable/<doc>/<doc>.md`

### dots.ocr (HF 단일 머신)

```bash
conda activate tableproc_dotsocr
bash scripts/run_dotsocr_cpu.sh
```

출력:
- 각 문서별 MD: `outputs/dotsocr_hf/<doc>/*.md`
- 요약(MD, table만 추출): `outputs/dotsocr_hf/summary.md`

### Dolphin (HF)

```bash
conda activate tableproc_dolphin
python scripts/run_dolphin_hf.py --model-path tools/Dolphin/hf_model
```

출력: `outputs/dolphin/<doc>/markdown/*.md` (표가 `<table>`로 포함)

### MonkeyOCR 제외 사유
현재 서버의 CUDA 12.2 환경은 공식 가이드(지원 CUDA 12.6/11.8)와 불일치하여 PaddleX/LMDeploy 백엔드 설치·실행이 반복 실패했습니다. 따라서 본 통합 실행 대상에서 MonkeyOCR은 제외합니다. 추후 CUDA 12.6 환경에서 재시도 권장. 참고: `docs/install_cuda_pp.md`.

## 참고
- 도구 소스는 `tools/` 하위에 정리되어 있으며, 문서는 `documents/`에 위치합니다.
- 각 러너 스크립트는 CPU에서도 작동하도록 작성했으나, 가속기가 있을 경우 자동으로 CUDA를 사용합니다.

### 사후 처리: 중국어(한자) 포함 여부 점검
결과물(`outputs/`)에 중국어가 섞여 있는지 빠르게 점검하려면 아래를 실행하세요.

```bash
conda run -n tableproc_mineru python scripts/postprocess_detect_chinese.py \
  outputs/mineru outputs/dolphin outputs/rapidtable
```

요약이 `outputs/chinese_presence.json`에 저장되며, 각 파일별로 중국어 포함 여부와 해당 라인 일부를 제공합니다.

## 온라인/오프라인 모델 준비

### 온라인 준비 (완료)
- dots.ocr 가중치 다운로드:
  ```bash
  conda activate tableproc_dotsocr
  python scripts/download_dotsocr_weights.py
  ```
  - 결과: `tools/dots.ocr/weights/DotsOCR`

<!-- MonkeyOCR steps removed due to environment incompatibility (CUDA 12.2) -->

### 오프라인 실행(이식 환경)
- 인터넷 없이도 동작하도록 모든 러너는 로컬 경로만 사용합니다.
- 필수 조건:
  - dots.ocr: `tools/dots.ocr/weights/DotsOCR` 존재
  - Dolphin: `tools/Dolphin/hf_model` 존재
  - MonkeyOCR: 현재 제외

### RapidTable 주의사항
- `rapid-table==3.0.1` + `rapidocr>=3.0.0` 조합에서 일부 PDF에서 테이블이 검출되지 않을 수 있습니다. 권장 호출: `--model-type unitable --scale 3.5` → 실패 시 `ppstructure_en` 또는 `slanet_plus`로 폴백.
