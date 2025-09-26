#!/usr/bin/env python3
"""
Run Dolphin (HF) by invoking the repo's demo CLI as in the README.

Usage example (per README): see https://github.com/bytedance/Dolphin/blob/master/README.md
This wrapper calls tools/Dolphin/demo_page_hf.py with local hf_model and inputs from documents/.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List
import subprocess

PROJECT_ROOT = "/home/yerin/Table-processing"
DOC_DIR = os.path.join(PROJECT_ROOT, "documents")
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "dolphin")
DEMO_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "Dolphin", "demo_page_hf.py")
DEMO_CWD = os.path.join(PROJECT_ROOT, "tools", "Dolphin")


def list_pdfs(doc_dir: str) -> List[Path]:
    p = Path(doc_dir)
    return sorted([x for x in p.iterdir() if x.suffix.lower() == ".pdf"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default=os.path.join(PROJECT_ROOT, "tools", "Dolphin", "hf_model"))
    parser.add_argument("--only", nargs="*", help="Basenames to run (without extension)")
    args = parser.parse_args()

    # strictly use local path; do not trigger HF downloads
    if not os.path.isfile(DEMO_SCRIPT):
        raise FileNotFoundError(f"Dolphin demo script not found: {DEMO_SCRIPT}")
    if not os.path.isdir(args.model_path):
        raise FileNotFoundError(f"Local Dolphin HF model path not found: {args.model_path}")

    pdfs = list_pdfs(DOC_DIR)
    if args.only:
        only = set([s.strip() for s in args.only])
        pdfs = [p for p in pdfs if p.stem in only]
    if not pdfs:
        print("No PDFs found")
        return

    # If selection provided, run per-file; else run once with the folder
    if args.only:
        for pdf_path in pdfs:
            out_dir = os.path.join(OUT_DIR, pdf_path.stem)
            os.makedirs(out_dir, exist_ok=True)
            print(f"[Dolphin HF] {pdf_path.name}")
            cmd = [
                "python", "-u", os.path.basename(DEMO_SCRIPT),
                "--model_path", args.model_path,
                "--input_path", str(pdf_path),
                "--save_dir", out_dir,
                "--max_batch_size", "16",
            ]
            print("[Dolphin HF] exec:", " ".join(cmd), "(cwd=tools/Dolphin)")
            subprocess.run(cmd, cwd=DEMO_CWD, check=False)
    else:
        os.makedirs(OUT_DIR, exist_ok=True)
        print(f"[Dolphin HF] folder {DOC_DIR}")
        cmd = [
            "python", "-u", os.path.basename(DEMO_SCRIPT),
            "--model_path", args.model_path,
            "--input_path", DOC_DIR,
            "--save_dir", OUT_DIR,
            "--max_batch_size", "16",
        ]
        print("[Dolphin HF] exec:", " ".join(cmd), "(cwd=tools/Dolphin)")
        subprocess.run(cmd, cwd=DEMO_CWD, check=False)

    print(f"Dolphin HF done. outputs at {OUT_DIR}")


if __name__ == "__main__":
    main()


