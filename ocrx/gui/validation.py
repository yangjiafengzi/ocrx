# -- coding: utf-8 --
"""Preflight validation helpers for wizard run step."""

from pathlib import Path

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def parse_page_range(page_range: str, total_pages: int) -> list[int] | None:
    text = (page_range or "").strip()
    if not text:
        return list(range(1, total_pages + 1))
    pages: set[int] = set()
    try:
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start > end:
                    return None
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
    except ValueError:
        return None
    ordered = sorted(pages)
    if not ordered or ordered[0] < 1 or ordered[-1] > total_pages:
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
        for part in page_range.replace("-", ",").split(","):
            if part.strip() and not part.strip().isdigit():
                errors.append("页码范围格式应如 1,3,5-10")
                break
    return errors
