# -- coding: utf-8 --
"""Throttled progress controller unit tests."""

import time
import tkinter as tk

import pytest

from ocrx.gui.controllers.progress_controller import ProgressController


@pytest.fixture
def tk_root():
    root = None
    last_error = None
    for _ in range(3):
        try:
            root = tk.Tk()
            break
        except tk.TclError as exc:
            last_error = exc
            time.sleep(0.2)
    if root is None:
        pytest.skip(f"当前环境无可用 Tcl/Tk 显示：{last_error}")
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_progress_burst_coalesces_to_latest_payload(tk_root):
    """快速连发的进度事件不应逐条触发视图回调。"""
    seen = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
    )
    n = 40
    for i in range(n):
        ctrl.handle_progress(i, n, i * 2.5, "ocr")
    # 未 flush 前不应同步回调（可能来自工作线程）。
    assert seen == []
    ctrl.flush()
    assert seen, "flush 后应至少有一次进度回调"
    assert len(seen) < n
    assert len(seen) <= 2
    assert seen[-1] == (n - 1, n, (n - 1) * 2.5, "ocr")


def test_status_burst_coalesces_to_latest(tk_root):
    statuses = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: None,
        on_status=statuses.append,
    )
    n = 25
    for i in range(n):
        ctrl.handle_status(f"status-{i}")
    assert statuses == []
    ctrl.flush()
    assert statuses
    assert len(statuses) < n
    assert statuses[-1] == f"status-{n - 1}"


def test_flush_emits_immediately_without_event_loop(tk_root):
    seen = []
    statuses = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=statuses.append,
    )
    ctrl.handle_progress(3, 10, 30.0, "ocr")
    ctrl.handle_status("working")
    ctrl.flush()
    assert seen == [(3, 10, 30.0, "ocr")]
    assert statuses == ["working"]


def test_flush_without_pending_is_noop(tk_root):
    seen = []
    statuses = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=statuses.append,
    )
    ctrl.flush()
    assert seen == []
    assert statuses == []


def test_flush_then_new_events_emits_again(tk_root):
    seen = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
    )
    ctrl.handle_progress(1, 10, 10.0, "ocr")
    ctrl.flush()
    ctrl.handle_progress(2, 10, 20.0, "ocr")
    ctrl.flush()
    assert seen == [(1, 10, 10.0, "ocr"), (2, 10, 20.0, "ocr")]


def test_timer_emits_coalesced_payload(tk_root):
    """事件循环推进后仍只发出合并后的最新值。"""
    seen = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
        min_interval_ms=20,
    )
    n = 10
    for i in range(n):
        ctrl.handle_progress(i, n, i * 10.0, "ocr")
    deadline = time.monotonic() + 2.0
    while not seen and time.monotonic() < deadline:
        tk_root.update()
        time.sleep(0.01)
    assert seen, "定时器触发后应发出进度"
    assert len(seen) < n
    assert seen[-1] == (n - 1, n, (n - 1) * 10.0, "ocr")


def test_throttle_rate_limits_emissions(tk_root):
    """持续事件流下，回调次数应受 min_interval_ms 约束。"""
    seen = []
    min_interval_ms = 50
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
        min_interval_ms=min_interval_ms,
    )
    n = 30
    start = time.monotonic()
    for i in range(n):
        ctrl.handle_progress(i, n, (i / n) * 100.0, "ocr")
        tk_root.update()
        time.sleep(0.01)
    elapsed = time.monotonic() - start
    ctrl.flush()
    assert seen
    assert seen[-1][0] == n - 1
    # 理论上限：elapsed / interval + 一次尾随 flush。
    max_expected = int(elapsed * 1000.0 / min_interval_ms) + 2
    assert len(seen) <= max_expected
    assert len(seen) < n


def test_interleaved_progress_and_status_keep_latest(tk_root):
    seen = []
    statuses = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=statuses.append,
    )
    for i in range(15):
        ctrl.handle_progress(i, 15, i * (100.0 / 15), "ocr")
        ctrl.handle_status(f"step-{i}")
    ctrl.flush()
    assert len(seen) < 15
    assert len(statuses) < 15
    assert seen[-1][0] == 14
    assert statuses[-1] == "step-14"


def test_default_min_interval_is_100ms(tk_root):
    ctrl = ProgressController(tk_root, on_progress=lambda *a: None, on_status=lambda s: None)
    assert ctrl.min_interval_ms == 100
