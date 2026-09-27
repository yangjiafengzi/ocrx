# -- coding: utf-8 --
"""Coalesce progress/status events onto the Tk main thread.

ProcessingService 的工作线程会高频推送进度/状态事件；本控制器只保留
最新的待发值，按 min_interval_ms（默认 100ms ≈ 10Hz）通过 root.after
调度到 Tk 主线程后再回调视图。flush() 立即发出当前待发值。
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

ProgressPayload = tuple[int, int, float, str]


class ProgressController:
    """节流/合并进度与状态事件的控制器。"""

    def __init__(
        self,
        root: Any,
        on_progress: Callable[[int, int, float, str], None],
        on_status: Callable[[str], None],
        min_interval_ms: int = 100,
    ):
        self.root = root
        self.on_progress = on_progress
        self.on_status = on_status
        self.min_interval_ms = max(0, int(min_interval_ms))
        self._pending_progress: Optional[ProgressPayload] = None
        self._pending_status: Optional[str] = None
        self._scheduled = False
        self._after_id: Optional[str] = None
        self._last_emit = 0.0

    def handle_progress(self, current: int, total: int, percent: float, phase: str) -> None:
        """记录最新进度（覆盖未发的旧值）并调度合并后的回调。"""
        self._pending_progress = (current, total, percent, phase)
        self._schedule()

    def handle_status(self, status: str) -> None:
        """记录最新状态（覆盖未发的旧值）并调度合并后的回调。"""
        self._pending_status = status
        self._schedule()

    def flush(self) -> None:
        """立即发出待发的进度/状态，不等待节流窗口。"""
        self._cancel_schedule()
        self._emit_pending()

    def _schedule(self) -> None:
        if self._scheduled:
            return
        self._scheduled = True
        delay = self.min_interval_ms
        elapsed = time.monotonic() * 1000.0 - self._last_emit
        if elapsed < delay:
            delay = int(delay - elapsed)
        self._after_id = self.root.after(delay, self._on_timer)

    def _on_timer(self) -> None:
        self._scheduled = False
        self._after_id = None
        self._emit_pending()

    def _emit_pending(self) -> None:
        self._last_emit = time.monotonic() * 1000.0
        progress, self._pending_progress = self._pending_progress, None
        status, self._pending_status = self._pending_status, None
        if progress is not None:
            self.on_progress(*progress)
        if status is not None:
            self.on_status(status)

    def _cancel_schedule(self) -> None:
        if self._scheduled and self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._scheduled = False
        self._after_id = None
