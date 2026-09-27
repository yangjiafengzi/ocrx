# -- coding: utf-8 --
"""Copy workflow controller.

Delegates recognition/copy to ``ProcessingService.process_and_copy``.
Worker failures are returned as ``(False, message)`` instead of raising.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..validation import (
    COPY_MAX_PAGES,
    ERR_EMPTY_PROMPT,
    ERR_NO_FILES,
    copy_page_limit_error,
    count_run_pages,
    validate_preflight,
)


class CopyController:
    def __init__(self, service, logger=None):
        self.service = service
        self.logger = logger

    def run(
        self,
        file_paths: List[str],
        prompt: str,
        page_range: str,
        example_images: Optional[List[Tuple[str, bytes]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if not file_paths:
            return False, ERR_NO_FILES
        if not (prompt or "").strip():
            return False, ERR_EMPTY_PROMPT
        if config is not None:
            errors = validate_preflight(config, file_paths, page_range, prompt)
            if errors:
                return False, "\n".join(errors)
        try:
            page_error = self._check_page_limit(file_paths, page_range)
            if page_error:
                return False, page_error
            return self.service.process_and_copy(
                file_paths=file_paths,
                prompt=prompt,
                page_range_str=page_range,
                example_images=example_images,
            )
        except Exception as exc:  # never crash the mainloop
            if self.logger is not None:
                try:
                    self.logger.error(f"识别并复制失败: {exc}", "CopyController")
                except Exception:
                    pass
            return False, str(exc)

    def _check_page_limit(self, file_paths: List[str], page_range: str) -> str:
        """Return the copy page-limit error, or "" when the run fits."""
        total_pages = count_run_pages(file_paths, page_range, self._pdf_page_count)
        if total_pages > COPY_MAX_PAGES:
            return copy_page_limit_error(total_pages)
        return ""

    def _pdf_page_count(self, file_path: str) -> int:
        pdf_processor = getattr(self.service, "pdf_processor", None)
        if pdf_processor is None:
            from ...pdf_processor import PDFProcessor

            pdf_processor = PDFProcessor()
        return int(pdf_processor.get_pdf_page_count(file_path))

    def cancel(self) -> None:
        self.service.request_cancel()
