#!/usr/bin/env python3
"""
Run MinerU (pipeline backend) over PDFs in documents/ and dump content_list.json.

Outputs:
  /home/yerin/Table-processing/outputs/mineru/<doc>/auto/<doc>_content_list.json

Usage:
  conda activate tableproc_mineru
  python scripts/run_mineru_pipeline.py --lang en --start 0 --end -1
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.model_json_to_middle_json import (
    result_to_middle_json as pipeline_result_to_middle_json,
)
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import (
    union_make as pipeline_union_make,
)
from mineru.cli.common import prepare_env, read_fn, convert_pdf_bytes_to_bytes_by_pypdfium2
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.enum_class import MakeMode


PROJECT_ROOT = "/home/yerin/Table-processing"
DOC_DIR = os.path.join(PROJECT_ROOT, "documents")
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "mineru")


def list_pdfs(doc_dir: str) -> List[Path]:
    p = Path(doc_dir)
    files = sorted([x for x in p.iterdir() if x.suffix.lower() == ".pdf"])
    return files


def run_pipeline(pdf_paths: List[Path], lang: str, start_page_id: int, end_page_id: int | None) -> None:
    file_names: List[str] = []
    pdf_bytes_list: List[bytes] = []
    lang_list: List[str] = []

    for path in pdf_paths:
        file_names.append(path.stem)
        raw_bytes = read_fn(str(path))
        clipped = convert_pdf_bytes_to_bytes_by_pypdfium2(
            raw_bytes, start_page_id, end_page_id if end_page_id is not None and end_page_id >= 0 else None
        )
        pdf_bytes_list.append(clipped)
        lang_list.append(lang)

    (
        infer_results,
        all_image_lists,
        all_pdf_docs,
        lang_list2,
        ocr_enabled_list,
    ) = pipeline_doc_analyze(pdf_bytes_list, lang_list, parse_method="auto", formula_enable=True, table_enable=True)

    for idx, model_list in enumerate(infer_results):
        model_json = list(model_list)
        pdf_file_name = file_names[idx]
        local_image_dir, local_md_dir = prepare_env(OUT_DIR, pdf_file_name, "auto")
        image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

        images_list = all_image_lists[idx]
        pdf_doc = all_pdf_docs[idx]
        _lang = lang_list2[idx]
        _ocr_enable = ocr_enabled_list[idx]

        middle_json = pipeline_result_to_middle_json(
            model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, True
        )

        pdf_info = middle_json["pdf_info"]

        # dump content_list.json
        image_dir = str(os.path.basename(local_image_dir))
        content_list = pipeline_union_make(pdf_info, MakeMode.CONTENT_LIST, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}_content_list.json",
            __import__("json").dumps(content_list, ensure_ascii=False, indent=4),
        )

        # dump markdown preview (tables as HTML when available)
        try:
            lines = [f"# {pdf_file_name}", ""]
            for item in content_list:
                if not isinstance(item, dict):
                    continue
                # MinerU table keys may vary: table_body (HTML), html, table_html
                html = item.get("table_body") or item.get("html") or item.get("table_html")
                if isinstance(html, str) and "<table" in html.lower():
                    lines.append(html)
                    lines.append("")
            if len(lines) > 2:
                md_writer.write_string(
                    f"{pdf_file_name}.md",
                    "\n".join(lines),
                )
        except Exception:
            pass

        # also keep middle and model jsons for debugging
        md_writer.write_string(
            f"{pdf_file_name}_middle.json",
            __import__("json").dumps(middle_json, ensure_ascii=False, indent=4),
        )
        md_writer.write_string(
            f"{pdf_file_name}_model.json",
            __import__("json").dumps(model_json, ensure_ascii=False, indent=4),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, default="en")
    parser.add_argument("--start", type=int, default=0, help="Start page index (inclusive)")
    parser.add_argument("--end", type=int, default=-1, help="End page index (inclusive), -1 for all")
    parser.add_argument("--only", nargs="*", help="Process only specific basenames without extension")
    args = parser.parse_args()

    pdfs = list_pdfs(DOC_DIR)
    if args.only:
        only_set = set([s.strip() for s in args.only])
        pdfs = [p for p in pdfs if p.stem in only_set]
    if not pdfs:
        print("No PDFs found in documents/")
        return

    end_idx = args.end if args.end >= 0 else None
    run_pipeline(pdfs, args.lang, args.start, end_idx)
    print(f"MinerU pipeline done. outputs at {OUT_DIR}")


if __name__ == "__main__":
    main()


