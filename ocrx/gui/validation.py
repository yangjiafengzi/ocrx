# -- coding: utf-8 --
"""Preflight validation helpers for wizard run step.

UI preflight here is strict: malformed page-range input is rejected with a
validation error instead of being silently dropped. ``ocrx.pdf_processor._parse_page_range``
remains the lenient batch parser (bad tokens ignored) until the two are
consolidated later.
"""

from pathlib import Path
from typing import Callable

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# Message shown when the run starts with no input files selected.
ERR_NO_FILES = "请至少选择一个文件"

# Message shown when the run starts with a blank prompt.
ERR_EMPTY_PROMPT = "请填写提示词"

# Copy mode is a clipboard workflow: refuse runs above this page budget and
# steer the user to save mode or an explicit page range instead.
COPY_MAX_PAGES = 10

# Upper bound on how many page numbers a single input may expand to. Keeps the
# validity path from materializing absurd ranges like "1-99999999".
MAX_PAGE_SPAN = 10000


def _parse_page_number(token: str) -> int | None:
    """Return a positive page number for an ASCII decimal token, else None.

    Rejects empty tokens and non-ASCII numerals (e.g. "²", which
    ``str.isdigit()`` accepts but ``int()`` raises on). The ``try/except``
    also guards against ``ValueError`` from Python's int-string digit limit.
    """
    if not token or not token.isascii() or not token.isdecimal():
        return None
    try:
        value = int(token)
    except ValueError:
        return None
    return value if value >= 1 else None


def parse_page_range_tokens(page_range: str) -> list[int] | None:
    """Parse page-range structure without requiring a total page count.

    Returns the sorted unique page numbers on success, or None when the
    structure is invalid (non-integer tokens, zero/negative pages, reversed or
    malformed ranges, expansions above MAX_PAGE_SPAN).

    Empty contract: empty, whitespace-only, and separator-only input (e.g.
    "", "   ", ",") all return [] meaning "no explicit tokens" (i.e. all
    pages). Empty segments between tokens are ignored ("1,,2," -> [1, 2]).
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
            start = _parse_page_number(start_s)
            end = _parse_page_number(end_s)
            if start is None or end is None or start > end:
                return None
            if end - start + 1 > MAX_PAGE_SPAN:
                return None
            pages.update(range(start, end + 1))
            if len(pages) > MAX_PAGE_SPAN:
                return None
        else:
            page = _parse_page_number(part)
            if page is None:
                return None
            pages.add(page)
    if not pages:
        return []
    return sorted(pages)


def parse_page_range(page_range: str, total_pages: int) -> list[int] | None:
    ordered = parse_page_range_tokens(page_range)
    if ordered is None:
        return None
    if not ordered:
        # empty contract: no explicit tokens means all pages
        return list(range(1, total_pages + 1))
    if ordered[-1] > total_pages:
        return None
    return ordered


def count_run_pages(
    file_paths: list[str],
    page_range: str,
    get_pdf_page_count: Callable[[str], int],
) -> int:
    """Estimate how many pages a run would process (copy-mode cap check).

    Mirrors ``ProcessingService._prepare_images``: page ranges select a subset
    of PDF pages, while image files always contribute exactly one page (the
    service ignores page ranges for images). Unreadable PDFs count as one page,
    matching the old CopyHandler fallback, so a broken file cannot mask a run
    that is over budget.
    """
    tokens = parse_page_range_tokens(page_range or "")
    total = 0
    for file_path in file_paths:
        if Path(file_path).suffix.lower() == ".pdf":
            try:
                page_count = int(get_pdf_page_count(file_path))
            except Exception:
                page_count = 1
            if tokens:
                page_count = sum(1 for page in tokens if page <= page_count)
            total += page_count
        else:
            total += 1
    return total


def copy_page_limit_error(total_pages: int) -> str:
    """Chinese error for copy runs above :data:`COPY_MAX_PAGES` pages."""
    return (
        f"识别并复制模式最多支持 {COPY_MAX_PAGES} 页，当前共 {total_pages} 页。\n"
        f"建议：\n"
        f"1. 使用「识别并保存」模式处理大文档\n"
        f"2. 或使用页面范围指定不超过 {COPY_MAX_PAGES} 页"
    )


def validate_preflight(
    config: dict,
    file_paths: list[str],
    page_range: str,
    prompt: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if prompt is not None and not prompt.strip():
        errors.append(ERR_EMPTY_PROMPT)
    if not (config.get("API_KEY") or "").strip():
        errors.append("请填写 API Key")
    if not (config.get("BASE_URL") or "").strip():
        errors.append("请填写 Base URL")
    if not (config.get("MODEL_NAME") or "").strip():
        errors.append("请填写 Model Name")
    if not file_paths:
        errors.append(ERR_NO_FILES)
    for path in file_paths:
        if Path(path).suffix.lower() not in SUPPORTED_SUFFIXES:
            errors.append(f"不支持的文件类型：{Path(path).name}")
    if (page_range or "").strip():
        # full page-count check happens after opening the PDF in controllers
        if parse_page_range_tokens(page_range) is None:
            errors.append("页码范围格式应如 1,3,5-10")
    return errors
