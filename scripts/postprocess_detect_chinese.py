#!/usr/bin/env python3
"""
중국어 포함 여부를 outputs/ 하위의 md, json 파일에서 검사하는 스크립트.

입력:
- 하나 이상의 탐색 루트 디렉터리 경로 (없으면 기본값으로 outputs/mineru, outputs/dolphin 사용)

동작:
- 재귀적으로 파일을 검색하고, 확장자가 .md 또는 .json 인 파일만 텍스트로 열어 중국어 문자(\u4e00-\u9fff) 포함 여부 검사
- 결과를 JSON으로 요약하여 outputs/chinese_presence.json 에 저장

출력:
- 표준출력에 요약 경로를 안내하고, 파일 내 true/false 카운트를 간단히 표시

설계 노트:
- 간단한 정규식 기반 검출로 시작하고, 필요시 확장(확장 평면, 기호범위 등) 가능
- 파일 수가 많을 수 있으므로 메모리 사용을 줄이기 위해 스트리밍 방식으로 파일을 읽음
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Iterable, List, Dict, Any


# 2글자 이상 연속 CJK(중국어/일본어 한자 포함)만 유효로 간주하여 단일 문자(예: 二) 노이즈를 줄임
CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")

# 라텍스 수식 블록 제거를 위한 패턴들 ($...$, $$...$$, \(...\), \[...\])
LATEX_INLINE_DOLLAR_RE = re.compile(r"\$(?:[^$\\]|\\.)*\$")
LATEX_DISPLAY_DOLLAR_RE = re.compile(r"\$\$(?:[^$\\]|\\.|\$(?!\$))*\$\$")
LATEX_PAREN_RE = re.compile(r"\\\((?:[^\\]|\\.)*\\\)")
LATEX_BRACKET_RE = re.compile(r"\\\[(?:[^\\]|\\.)*\\\]")

# 확실한 중국어 단어 화이트리스트(단일 문자 제외 예외 허용 시 사용 가능)
CHINESE_WHITELIST_WORDS = {
    "参考文献",
    "參考資料",
}


@dataclass
class FileCheckResult:
    """단일 파일의 중국어 포함 여부 결과.

    file_path: 파일의 절대 경로
    relative_path: 프로젝트 루트로부터의 상대 경로(가능한 경우)
    contains_chinese: 중국어 문자 포함 여부
    matches: 중국어가 포함된 라인 정보 목록 [{line: int, text: str}]
    """

    file_path: str
    relative_path: str
    contains_chinese: bool
    matches: List[Dict[str, Any]]


def iter_target_files(root_dirs: Iterable[str]) -> Iterable[str]:
    """루트 디렉터리들에서 재귀적으로 .md/.json 파일 경로를 생성한다."""
    for root in root_dirs:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext in {".md", ".json"}:
                    yield os.path.join(dirpath, name)


def find_chinese_lines(
    file_path: str,
    max_matches: int = 200,
    max_line_length: int = 2000,
) -> List[Dict[str, Any]]:
    """파일을 라인 단위로 검사하여 중국어가 포함된 라인을 반환한다.

    max_matches: 파일당 최대 수집 라인 수
    max_line_length: JSON 폭증 방지를 위한 라인 길이 상한 (초과 시 잘라냄)
    """
    matches: List[Dict[str, Any]] = []
    def strip_latex_math(text: str) -> str:
        # 순서대로 제거 (display 먼저 제거해 중첩 혼동 줄임)
        text = LATEX_DISPLAY_DOLLAR_RE.sub(" ", text)
        text = LATEX_INLINE_DOLLAR_RE.sub(" ", text)
        text = LATEX_PAREN_RE.sub(" ", text)
        text = LATEX_BRACKET_RE.sub(" ", text)
        return text

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, start=1):
                raw = line.rstrip("\n")
                sanitized = strip_latex_math(raw)
                has_run = bool(CHINESE_RUN_RE.search(sanitized))
                in_whitelist = any(w in sanitized for w in CHINESE_WHITELIST_WORDS)
                if has_run or in_whitelist:
                    text = raw
                    if len(text) > max_line_length:
                        text = text[: max_line_length - 3] + "..."
                    matches.append({"line": idx, "text": text})
                    if len(matches) >= max_matches:
                        break
    except Exception:
        # 읽기 실패 시 빈 목록 반환
        return []
    return matches


def to_relative(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except Exception:
        return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        help="검색할 루트 디렉터리. 미지정 시 outputs/mineru, outputs/dolphin 사용",
    )
    parser.add_argument(
        "--project-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="상대 경로 계산 기준 루트 (기본: 스크립트 상위 디렉터리)",
    )
    parser.add_argument(
        "--out",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "chinese_presence.json")),
        help="요약 JSON 저장 경로",
    )
    args = parser.parse_args()

    default_dirs = [
        os.path.abspath(os.path.join(args.project_root, "outputs", "mineru")),
        os.path.abspath(os.path.join(args.project_root, "outputs", "dolphin")),
    ]
    roots: List[str] = [os.path.abspath(p) for p in (args.paths or default_dirs)]

    results: List[FileCheckResult] = []
    for file_path in iter_target_files(roots):
        matched_lines = find_chinese_lines(file_path)
        results.append(
            FileCheckResult(
                file_path=file_path,
                relative_path=to_relative(file_path, args.project_root),
                contains_chinese=bool(matched_lines),
                matches=matched_lines,
            )
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)

    total = len(results)
    num_true = sum(1 for r in results if r.contains_chinese)
    num_false = total - num_true
    print(f"Saved summary -> {args.out}")
    print(f"Files: {total}, contains_chinese: {num_true}, none: {num_false}")


if __name__ == "__main__":
    main()


