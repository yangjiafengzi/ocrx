# -- coding: utf-8 --
"""Preflight validation helpers for wizard run step."""

from pathlib import Path

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def parse_page_range_tokens(page_range: str) -> list[int] | None:
    """Parse page-range structure without requiring a total page count.

    Returns the sorted unique page numbers on success, or None when the
    structure is invalid (non-integer tokens, zero/negative pages, reversed or
    malformed ranges). Empty or whitespace-only input returns [] meaning
    "no explicit tokens" (i.e. all pages).
    """
    text = (page_range or "").strip()
    if not text:
        return []
    pages: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            pieces = part.split("-")
            if len(pieces) != 2:
                return None
            start_s, end_s = pieces[0].strip(), pieces[1].strip()
            if not (start_s.isdigit() and end_s.isdigit()):
                return None
            start, end = int(start_s), int(end_s)
            if start < 1 or start > end:
                return None
            pages.update(range(start, end + 1))
        else:
            if not part.isdigit():
                return None
            page = int(part)
            if page < 1:
                return None
            pages.add(page)
    if not pages:
        return None
    return sorted(pages)


def parse_page_range(page_range: str, total_pages: int) -> list[int] | None:
    text = (page_range or "").strip()
    if not text:
        return list(range(1, total_pages + 1))
    ordered = parse_page_range_tokens(page_range)
    if not ordered or ordered[-1] > total_pages:
        return None
    return ordered


def validate_preflight(config: dict, file_paths: list[str], page_range: str) -> list[str]:
    errors: list[str] = []
    if not (config.get("API_KEY") or "").strip():
        errors.append("请填写 API Key")
    if not (config.get("BASE_URL") or "").strip():
        errors.append("请填写 Base URL")
    if not (config.get("MODEL_NAME") or "").strip():
        errors.append("请填写 Model Name")
    if not file_paths:
        errors.append("请至少选择一个文件")
    for path in file_paths:
        if Path(path).suffix.lower() not in SUPPORTED_SUFFIXES:
            errors.append(f"不支持的文件类型：{Path(path).name}")
    if (page_range or "").strip():
        # full page-count check happens after opening the PDF in controllers
        if parse_page_range_tokens(page_range) is None:
            errors.append("页码范围格式应如 1,3,5-10")
    return errors
