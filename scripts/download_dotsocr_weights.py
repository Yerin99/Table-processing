#!/usr/bin/env python3
"""
Download dots.ocr weights into tools/dots.ocr/weights/DotsOCR for online prep.

This uses the upstream helper provided by the repo to ensure the right folder name (DotsOCR).
"""
import os
import subprocess
import sys


ROOT = "/home/yerin/Table-processing"
SCRIPT = os.path.join(ROOT, "tools", "dots.ocr", "tools", "download_model.py")
TARGET_DIR = os.path.join(ROOT, "tools", "dots.ocr", "weights", "DotsOCR")


def main() -> None:
    os.makedirs(os.path.dirname(TARGET_DIR), exist_ok=True)
    if os.path.isdir(TARGET_DIR) and os.listdir(TARGET_DIR):
        print(f"[dots.ocr] already present: {TARGET_DIR}")
        return
    if not os.path.isfile(SCRIPT):
        print(f"download script not found: {SCRIPT}")
        sys.exit(1)
    print("[dots.ocr] downloading weights via repo helper...")
    subprocess.check_call([sys.executable, SCRIPT])
    if not os.path.isdir(TARGET_DIR):
        print("[dots.ocr] download finished but target not found. Check logs.")
    else:
        print(f"[dots.ocr] weights ready: {TARGET_DIR}")


if __name__ == "__main__":
    main()


