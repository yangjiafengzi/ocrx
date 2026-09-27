# -- coding: utf-8 --
"""Copy workflow controller.

Delegates recognition/copy to ``ProcessingService.process_and_copy``.
Worker failures are returned as ``(False, message)`` instead of raising.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..validation import ERR_NO_FILES, validate_preflight


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
        if config is not None:
            errors = validate_preflight(config, file_paths, page_range)
            if errors:
                return False, "\n".join(errors)
        try:
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

    def cancel(self) -> None:
        self.service.request_cancel()
