# -- coding: utf-8 --
"""Throttled progress controller unit tests."""

import threading
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


def test_worker_thread_producer_while_mainloop_runs(tk_root):
    """工作线程推送进度时主循环仍在跑：不抛异常，事件在主线程送达。"""
    seen = []
    callback_threads = []
    errors = []
    main_ident = threading.get_ident()

    def on_progress(*a):
        callback_threads.append(threading.get_ident())
        seen.append(a)

    ctrl = ProgressController(
        tk_root,
        on_progress=on_progress,
        on_status=lambda s: None,
        min_interval_ms=10,
    )
    total = 25

    def producer():
        try:
            for i in range(total):
                ctrl.handle_progress(i, total, i * 4.0, "ocr")
                time.sleep(0.004)
            ctrl.flush()
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    worker = threading.Thread(target=producer, name="progress-producer")
    worker.start()

    def check():
        if seen and seen[-1][0] == total - 1:
            tk_root.quit()
        else:
            tk_root.after(15, check)

    tk_root.after(15, check)
    tk_root.after(3000, tk_root.quit)
    tk_root.mainloop()
    worker.join(timeout=2)
    ctrl.close()

    assert errors == [], f"worker handle_*/flush raised: {errors}"
    assert seen, "工作线程事件应在主循环运行期间送达"
    assert seen[-1][0] == total - 1, "flush/合并后应送达最新进度"
    assert all(ident == main_ident for ident in callback_threads), (
        "视图回调必须运行在 Tk 主线程"
    )


def test_handle_after_destroy_does_not_raise(tk_root):
    """root.destroy() 之后 handle_*/flush/pump 不得抛异常，事件静默丢弃。"""
    seen = []
    statuses = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=statuses.append,
    )
    tk_root.destroy()
    ctrl.handle_progress(1, 2, 50.0, "ocr")  # must not raise
    ctrl.handle_status("done")  # must not raise
    ctrl.flush()  # must not raise
    ctrl._pump()  # must not raise
    assert seen == []
    assert statuses == []


def test_flush_from_worker_thread_does_not_run_callbacks_on_worker(tk_root):
    """工作线程调用 flush() 不得在该线程回调视图；投递发生在主线程。"""
    seen = []
    callback_threads = []
    main_ident = threading.get_ident()

    def on_progress(*a):
        callback_threads.append(threading.get_ident())
        seen.append(a)

    ctrl = ProgressController(
        tk_root,
        on_progress=on_progress,
        on_status=lambda s: None,
    )
    ctrl.handle_progress(5, 10, 50.0, "ocr")

    def worker():
        ctrl.flush()

    thread = threading.Thread(target=worker, name="flush-worker")
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert callback_threads == [], "flush() 在工作线程上不得触发视图回调"

    deadline = time.monotonic() + 2.0
    while not seen and time.monotonic() < deadline:
        tk_root.update()
        time.sleep(0.01)
    ctrl.close()

    assert seen == [(5, 10, 50.0, "ocr")]
    assert callback_threads == [main_ident], "回调必须在 Tk 主线程执行"


def test_first_emit_is_not_delayed_a_full_window(tk_root):
    """空闲后的首个事件不应被整整一个节流窗口延迟。"""
    seen = []
    min_interval_ms = 250
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
        min_interval_ms=min_interval_ms,
    )
    start = time.monotonic()
    ctrl.handle_progress(1, 2, 50.0, "ocr")
    deadline = start + 2.0
    while not seen and time.monotonic() < deadline:
        tk_root.update()
        time.sleep(0.005)
    elapsed = time.monotonic() - start
    ctrl.close()
    assert seen
    assert elapsed < min_interval_ms / 1000.0, (
        f"first emit took {elapsed:.3f}s, a full throttle window"
    )


def test_empty_flush_does_not_bump_last_emit(tk_root):
    """空 flush 不得推进 _last_emit，以免无端推迟下一次发射。"""
    ctrl = ProgressController(tk_root, on_progress=lambda *a: None, on_status=lambda s: None)
    assert ctrl._last_emit is None
    ctrl.flush()
    assert ctrl._last_emit is None
    ctrl.handle_progress(1, 2, 50.0, "ocr")
    ctrl.flush()
    assert ctrl._last_emit is not None
    previous = ctrl._last_emit
    ctrl.flush()
    assert ctrl._last_emit == previous
    ctrl.close()


def test_close_drops_further_events(tk_root):
    """close() 之后 handle_*/flush 静默丢弃，不再送达视图。"""
    seen = []
    ctrl = ProgressController(
        tk_root,
        on_progress=lambda *a: seen.append(a),
        on_status=lambda s: None,
    )
    ctrl.handle_progress(1, 2, 50.0, "ocr")
    ctrl.close()
    ctrl.handle_progress(2, 2, 100.0, "ocr")
    ctrl.flush()
    ctrl._pump()
    for _ in range(5):
        tk_root.update()
        time.sleep(0.01)
    assert seen == []
