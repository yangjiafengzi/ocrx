# -- coding: utf-8 --
"""Coalesce progress/status events onto the Tk main thread.

ProcessingService 的工作线程会高频推送进度/状态事件。为避免从工作线程
调用任何 Tk API，handle_* 只把事件放入 queue.Queue；由在 Tk 主线程上经
root.after 调度的单一 pump 合并出最新待发值后，再按 min_interval_ms
（默认 100ms ≈ 10Hz）回调视图。

线程模型：
- handle_progress / handle_status：任意线程可调用，只入队，不碰 Tk。
- flush()：主线程调用时同步发出待发值（无需事件循环）；工作线程调用时
  只入队一个 flush 标记，由主线程 pump 发射——视图回调绝不会在工作
  线程上执行。
- close() 之后（或 root.destroy() 之后）handle_* 与 pump 静默丢弃事件，
  不再抛异常。

节流细节：同一窗口内只保留/发射合并后的最新值；空闲后的首个事件不等
满一个窗口；空 flush 不推进 _last_emit。
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from typing import Any, Callable, Optional

ProgressPayload = tuple[int, int, float, str]

_PROGRESS = "progress"
_STATUS = "status"
_FLUSH = "flush"

# 空闲时 pump 的轮询间隔（毫秒）。必须明显小于节流窗口，否则空闲后的
# 首个事件会被推迟接近一整个窗口。
_IDLE_POLL_MS = 15


class ProgressController:
    """节流/合并进度与状态事件的控制器（线程安全）。

    请在 Tk 主线程构造：构造时会启动一个经 root.after 调度的 pump。
    跨线程边界只有 queue.Queue；待发值/节流状态仅在主线程读写。
    """

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
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._pending_progress: Optional[ProgressPayload] = None
        self._pending_status: Optional[str] = None
        self._scheduled = False
        self._after_id: Optional[str] = None
        self._last_emit: Optional[float] = None
        self._destroyed = False
        self._main_ident = threading.get_ident()
        self._schedule_pump(self._idle_poll_ms())

    # -- public API（任意线程可调用，不碰 Tk） ------------------------

    def handle_progress(self, current: int, total: int, percent: float, phase: str) -> None:
        """记录最新进度（覆盖未发的旧值）；只入队，不触发 Tk 调用。"""
        if self._destroyed:
            return
        try:
            self._queue.put((_PROGRESS, (current, total, percent, phase)))
        except Exception:
            pass

    def handle_status(self, status: str) -> None:
        """记录最新状态（覆盖未发的旧值）；只入队，不触发 Tk 调用。"""
        if self._destroyed:
            return
        try:
            self._queue.put((_STATUS, status))
        except Exception:
            pass

    def flush(self) -> None:
        """立即发出待发的进度/状态，不等待节流窗口。

        主线程调用：同步发射（无需事件循环）。工作线程调用：只入队一个
        flush 标记，由主线程 pump 发射，视图回调绝不在工作线程执行。
        """
        if self._destroyed:
            return
        if self._on_main_thread():
            if not self._root_alive():
                return
            self._process_queue(final_flush=True)
        else:
            try:
                self._queue.put((_FLUSH, None))
            except Exception:
                pass

    def close(self) -> None:
        """停止 pump 并静默丢弃后续事件（在 Tk 主线程调用）。"""
        self._destroyed = True
        self._cancel_schedule()
        self._pending_progress = None
        self._pending_status = None
        self._drain_queue()

    # -- 主线程 pump -------------------------------------------------

    def _pump(self) -> None:
        """排空队列、合并最新值并按节流发射；销毁后静默返回。"""
        self._after_id = None
        self._scheduled = False
        if self._destroyed:
            return
        try:
            if not self._root_alive():
                return
            self._process_queue(final_flush=False)
            self._emit_pending(force=False)
            if self._root_alive():
                self._reschedule()
        except tk.TclError:
            self._destroyed = True

    def _process_queue(self, *, final_flush: bool) -> bool:
        """排空事件队列；flush 标记是同步点，立即发射当时待发值。"""
        emitted = False
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break
            if kind == _PROGRESS:
                self._pending_progress = payload
            elif kind == _STATUS:
                self._pending_status = payload
            elif kind == _FLUSH:
                emitted = self._emit_pending(force=True) or emitted
        if final_flush:
            emitted = self._emit_pending(force=True) or emitted
        return emitted

    def _emit_pending(self, *, force: bool = False) -> bool:
        """发射合并后的待发值；force 忽略节流窗口。空发射不推进 _last_emit。"""
        if self._destroyed:
            self._pending_progress = None
            self._pending_status = None
            return False
        if not force and not self._emit_due():
            return False
        progress, self._pending_progress = self._pending_progress, None
        status, self._pending_status = self._pending_status, None
        if progress is None and status is None:
            return False
        if progress is not None:
            self.on_progress(*progress)
        if status is not None:
            self.on_status(status)
        self._last_emit = time.monotonic() * 1000.0
        return True

    def _emit_due(self) -> bool:
        if self._last_emit is None:
            return True
        elapsed = time.monotonic() * 1000.0 - self._last_emit
        return elapsed >= self.min_interval_ms

    def _reschedule(self) -> None:
        if self._destroyed or self._scheduled:
            return
        if self._pending_progress is not None or self._pending_status is not None:
            # 有待发值但仍在节流窗口内：在窗口结束时唤醒（首个/空闲不等满窗口）。
            delay = 0
            if self._last_emit is not None:
                elapsed = time.monotonic() * 1000.0 - self._last_emit
                delay = max(0, int(self.min_interval_ms - elapsed))
            self._schedule_pump(delay)
        else:
            self._schedule_pump(self._idle_poll_ms())

    def _schedule_pump(self, delay_ms: int) -> None:
        if self._destroyed or self._scheduled:
            return
        try:
            self._after_id = self.root.after(max(0, int(delay_ms)), self._pump)
            self._scheduled = True
        except Exception:
            self._destroyed = True

    def _cancel_schedule(self) -> None:
        if self._scheduled and self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._scheduled = False
        self._after_id = None

    def _drain_queue(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except Exception:
            pass

    def _idle_poll_ms(self) -> int:
        if self.min_interval_ms <= 0:
            return 1
        return max(1, min(_IDLE_POLL_MS, self.min_interval_ms))

    def _on_main_thread(self) -> bool:
        return threading.get_ident() == self._main_ident

    def _root_alive(self) -> bool:
        if self._destroyed:
            return False
        try:
            return bool(self.root.winfo_exists())
        except Exception:
            self._destroyed = True
            return False
