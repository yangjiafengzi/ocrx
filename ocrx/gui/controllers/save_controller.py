# -- coding: utf-8 --
"""Save workflow controller.

Delegates batch recognition/save to ``ProcessingService.process_files``.
Processing stays in ``ocrx/processing_service.py``; this layer only wires
arguments through and surfaces worker failures in a ``SaveResult`` so callers
on the Tk mainloop never see an exception escape and can show why a run
failed.
"""

from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from ..validation import ERR_EMPTY_PROMPT, ERR_NO_FILES, validate_preflight


class SaveResult(NamedTuple):
    """Outcome of a save run.

    ``ok`` is True when the run completed and ``results`` holds the per-file
    mapping from ``ProcessingService.process_files`` (filename -> (success,
    output path or None)). ``error`` is empty on success and otherwise carries
    the same message ``CopyController`` would return for the matching failure
    (no files, preflight rejection, or worker exception).
    """

    ok: bool
    results: Dict[str, Tuple[bool, Optional[str]]]
    error: str


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
    ) -> SaveResult:
        if not file_paths:
            return SaveResult(False, {}, ERR_NO_FILES)
        if not (prompt or "").strip():
            return SaveResult(False, {}, ERR_EMPTY_PROMPT)
        if config is not None:
            errors = validate_preflight(config, file_paths, page_range, prompt)
            if errors:
                return SaveResult(False, {}, "\n".join(errors))
        try:
            results = self.service.process_files(
                file_paths=file_paths,
                prompt=prompt,
                page_range_str=page_range,
                example_images=example_images,
            )
            return SaveResult(True, results, "")
        except Exception as exc:  # never crash the mainloop
            if self.logger is not None:
                try:
                    self.logger.error(f"识别并保存失败: {exc}", "SaveController")
                except Exception:
                    pass
            return SaveResult(False, {}, str(exc))

    def cancel(self) -> None:
        self.service.request_cancel()
