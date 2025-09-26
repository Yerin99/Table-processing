#!/usr/bin/env python3
"""
Run RapidTable directly on PDFs in documents/ without MinerU.
For each page, render to image (pypdfium2) and run rapid_table CLI per page to produce HTML.
Outputs: outputs/rapidtable_html/<doc>/page_<k>.html
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Optional

import pypdfium2 as pdfium
import tempfile


PROJECT_ROOT = "/home/yerin/Table-processing"
DOCS_DIR = os.path.join(PROJECT_ROOT, "documents")
OUT_HTML_DIR = os.path.join(PROJECT_ROOT, "outputs", "rapidtable")


def list_pdfs(doc_dir: str) -> List[Path]:
    p = Path(doc_dir)
    return sorted([x for x in p.iterdir() if x.suffix.lower() == ".pdf"])


def render_pages(pdf_path: str, scale: float, tmp_dir: str) -> List[Path]:
    # Render each page to a temporary PNG file inside tmp_dir and return paths
    out_dir = Path(tmp_dir)
    page_paths: List[Path] = []

    doc = pdfium.PdfDocument(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc.get_page(i)
            pil = page.render(scale=scale).to_pil()
            page.close()
            out_path = out_dir / f"{Path(pdf_path).stem}_page_{i:04d}.png"
            pil.save(out_path)
            page_paths.append(out_path)
    finally:
        doc.close()
    return page_paths


def run_rapid_table(image_path: str, timeout_sec: int = 45, model_type: Optional[str] = None) -> Optional[str]:
    import subprocess
    candidates = []
    if model_type:
        candidates.append(model_type)
    # preferred order for English
    for mt in ["ppstructure_en", "unitable", "slanet_plus"]:
        if mt not in candidates:
            candidates.append(mt)
    try:
        for mt in candidates:
            cmd = ["rapid_table", image_path, "-m", mt]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=timeout_sec,
            )
            if proc.returncode == 0 and proc.stdout and "<table" in proc.stdout.lower():
                return proc.stdout
            # fallback with visualization flag
            cmd_v = ["rapid_table", image_path, "-m", mt, "-v"]
            proc2 = subprocess.run(
                cmd_v,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=timeout_sec,
            )
            if proc2.returncode == 0 and proc2.stdout and "<table" in proc2.stdout.lower():
                return proc2.stdout
        return None
    except Exception:
            return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="Basenames to run (without extension)")
    parser.add_argument("--scale", type=float, default=3.0, help="PDF render scale")
    parser.add_argument("--model-type", type=str, default=None, help="rapid_table model type (ppstructure_en/unitable/slanet_plus)")
    parser.add_argument("--limit-pages", type=int, default=0, help="Limit pages per doc (0=all)")
    args = parser.parse_args()

    pdfs = list_pdfs(DOCS_DIR)
    if args.only:
        only = set([s.strip() for s in args.only])
        pdfs = [p for p in pdfs if p.stem in only]
    if not pdfs:
        print("No PDFs found in documents/")
        return

    for pdf in pdfs:
        with tempfile.TemporaryDirectory() as tmp_dir:
            page_imgs = render_pages(str(pdf), scale=args.scale, tmp_dir=tmp_dir)
            if args.limit_pages > 0:
                page_imgs = page_imgs[: args.limit_pages]

            out_dir = Path(OUT_HTML_DIR) / pdf.stem
            out_dir.mkdir(parents=True, exist_ok=True)

            html_ok = 0
            md_lines = [f"# {pdf.stem}", ""]
            for idx, img_path in enumerate(page_imgs):
                html = run_rapid_table(str(img_path), model_type=args.model_type)
                out_path = out_dir / f"page_{idx:04d}.html"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html if html else "<!-- no table detected -->\n")
                if html:
                    html_ok += 1
                    md_lines.append(html)
                    md_lines.append("")

            print(f"[RapidTable] {pdf.name}: pages={len(page_imgs)} html={html_ok}")
            # write md preview if any tables
            if html_ok > 0:
                md_path = out_dir / f"{pdf.stem}.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(md_lines))


if __name__ == "__main__":
    main()
