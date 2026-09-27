# -- coding: utf-8 --
"""Save workflow controller.

Delegates batch recognition/save to ``ProcessingService.process_files``.
Processing stays in ``ocrx/processing_service.py``; this layer only wires
arguments through and surfaces worker failures as a result dict so callers
on the Tk mainloop never see an exception escape.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..validation import validate_preflight


class SaveController:
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
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        if not file_paths:
            return {}
        if config is not None:
            errors = validate_preflight(config, file_paths, page_range)
            if errors:
                return {}
        try:
            return self.service.process_files(
                file_paths=file_paths,
                prompt=prompt,
                page_range_str=page_range,
                example_images=example_images,
            )
        except Exception as exc:  # never crash the mainloop
            if self.logger is not None:
                try:
                    self.logger.error(f"识别并保存失败: {exc}", "SaveController")
                except Exception:
                    pass
            return {}

    def cancel(self) -> None:
        self.service.request_cancel()
