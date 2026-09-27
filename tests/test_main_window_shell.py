# -- coding: utf-8 --
"""MainWindow wizard shell tests (real widgets; skip without a display).

The shell owns navigation, lifecycle, and job orchestration only. Workflows
run through SaveController/CopyController on worker threads; progress is
marshalled to RunStep via ProgressController.
"""

import threading
import time
import tkinter as tk

import pytest

from ocrx.example_library import ExampleLibrary
from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow
from ocrx.gui.session_state import SessionState


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


@pytest.fixture
def ctx(tmp_path):
    return AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "examples"),
        log_path=str(tmp_path / "app.log"),
    )


@pytest.fixture
def win(tk_root, ctx):
    window = MainWindow(tk_root, context=ctx)
    tk_root.update_idletasks()
    try:
        yield window
    finally:
        try:
            window.on_closing()
        except Exception:
            pass


class FakeService:
    """Stand-in for ProcessingService: records calls, never touches the network."""

    def __init__(self):
        self.calls = []
        self.updated = {}
        self.cancelled = False
        self.progress_cb = None
        self.status_cb = None
        self.save_results = {"a.png": (True, "")}
        self.copy_result = (True, "识别内容")
        self.raise_error = None

    def set_progress_callback(self, callback):
        self.progress_cb = callback

    def set_status_callback(self, callback):
        self.status_cb = callback

    def update_config(self, **kwargs):
        self.updated.update(kwargs)

    def reset_cancel(self):
        self.cancelled = False

    def request_cancel(self):
        self.cancelled = True

    def process_files(self, file_paths, prompt, page_range_str, example_images=None):
        self.calls.append(
            {
                "mode": "save",
                "file_paths": list(file_paths),
                "prompt": prompt,
                "page_range_str": page_range_str,
                "example_images": example_images,
            }
        )
        if self.raise_error is not None:
            raise self.raise_error
        return self.save_results

    def process_and_copy(self, file_paths, prompt, page_range_str, example_images=None):
        self.calls.append(
            {
                "mode": "copy",
                "file_paths": list(file_paths),
                "prompt": prompt,
                "page_range_str": page_range_str,
                "example_images": example_images,
            }
        )
        if self.raise_error is not None:
            raise self.raise_error
        return self.copy_result


def _prepare_ready_to_run(window, tmp_path):
    """Fill preflight fields (widgets + config) and install a FakeService."""
    png = tmp_path / "a.png"
    if not png.exists():
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
    cfg = window.context.config.config
    cfg["API_KEY"] = "sk-test"
    cfg["BASE_URL"] = "http://127.0.0.1:1/v1"
    cfg["MODEL_NAME"] = "gpt-4o"
    cfg["OUTPUT_DIR"] = str(tmp_path / "out")
    window.config_step.load_state(window.session, window.context.config)
    window.files_step._paths = [str(png)]
    window.files_step._refresh_listbox()
    window.files_step.page_range.delete(0, "end")
    window.prompt_step.textbox.delete("1.0", "end")
    window.prompt_step.textbox.insert("1.0", "识别文字")
    service = FakeService()
    window.context.service = service
    window._wire_service_progress()
    return service


def test_main_window_builds_wizard(tk_root, ctx):
    win = MainWindow(tk_root, context=ctx)
    assert win.wizard is not None
    assert win.current_step == 0
    assert len(win.wizard.buttons) == 4
    win.on_closing()


def test_secondary_views_present(win):
    assert win.examples_view is not None
    assert win.examples_view.manager is not None
    assert win.clipboard_view is not None
    assert win.clipboard_view.tree is not None
    assert win.logs_view is not None
    assert win.logs_view.textbox is not None


def test_wizard_navigation_updates_current_step(win, tk_root):
    win.wizard.set_current(2)
    assert win.current_step == 2
    win.wizard.set_current(3)
    assert win.current_step == 3
    assert win.run_step.save_btn is not None


def test_buttons_and_helpers_share_start_job_path(win, monkeypatch):
    seen = []
    monkeypatch.setattr(win, "_start_job", lambda mode: seen.append(mode))
    win.run_save_now()
    win.run_copy_now()
    win.run_step.save_btn.invoke()
    win.run_step.copy_btn.invoke()
    assert seen == ["save", "copy", "save", "copy"]


def test_save_success_sets_result_and_unlocks(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    out = tmp_path / "out" / "a_ocr.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("保存的识别内容", encoding="utf-8")
    service.save_results = {"a": (True, str(out))}

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True

    assert service.calls and service.calls[0]["mode"] == "save"
    shown = win.run_step.result.get("1.0", "end-1c")
    assert "保存的识别内容" in shown
    assert win.context.session_state.last_result == shown
    assert str(win.run_step.save_btn.cget("state")) == "normal"
    assert str(win.run_step.copy_btn.cget("state")) == "normal"


def test_save_failure_shows_error_and_unlocks(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    service.raise_error = RuntimeError("后端炸了")

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True

    status = win.run_step.status.cget("text")
    shown = win.run_step.result.get("1.0", "end-1c")
    assert "后端炸了" in status
    assert "后端炸了" in shown
    assert str(win.run_step.save_btn.cget("state")) == "normal"


def test_save_all_failed_shows_error_not_success(win, tk_root, tmp_path):
    """SaveResult.ok 但 0 个文件成功时不得显示“识别并保存完成”。"""
    service = _prepare_ready_to_run(win, tmp_path)
    service.save_results = {"a": (False, None), "b": (False, None)}

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True

    status = win.run_step.status.cget("text")
    shown = win.run_step.result.get("1.0", "end-1c")
    assert "识别并保存完成" not in status
    assert "识别并保存完成" not in shown
    assert "0/2" in status
    assert str(win.run_step.save_btn.cget("state")) == "normal"


def test_save_partial_reports_partial_not_full_success(win, tk_root, tmp_path):
    """部分文件失败时状态应为部分成功，而不是“识别并保存完成”。"""
    service = _prepare_ready_to_run(win, tmp_path)
    out = tmp_path / "out" / "a_ocr.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("保存的识别内容", encoding="utf-8")
    service.save_results = {"a": (True, str(out)), "b": (False, None)}

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True

    status = win.run_step.status.cget("text")
    assert "识别并保存完成" not in status
    assert "1/2" in status
    assert "保存的识别内容" in win.run_step.result.get("1.0", "end-1c")
    assert str(win.run_step.save_btn.cget("state")) == "normal"


def test_copy_success_sets_clipboard_and_result(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    copied = []
    threads = []

    def fake_copy(content):
        threads.append(threading.current_thread())
        copied.append(content)
        return True

    win.context.clipboard.copy_to_clipboard = fake_copy
    service.copy_result = (True, "复制的内容")

    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True

    assert service.calls and service.calls[0]["mode"] == "copy"
    assert copied == ["复制的内容"]
    assert threads and threads[0] is not threading.current_thread()
    shown = win.run_step.result.get("1.0", "end-1c")
    assert "复制的内容" in shown
    assert win.context.session_state.last_result == "复制的内容"
    assert str(win.run_step.copy_btn.cget("state")) == "normal"


def test_copy_failure_shows_error_and_unlocks(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    service.copy_result = (False, "没有可处理的图像")

    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True

    assert "没有可处理的图像" in win.run_step.status.cget("text")
    assert "没有可处理的图像" in win.run_step.result.get("1.0", "end-1c")
    assert str(win.run_step.copy_btn.cget("state")) == "normal"


def test_copy_failure_path_offers_copy_all(win, tk_root, tmp_path):
    """自动复制失败后，复制全部按钮可带走完整结果。"""
    service = _prepare_ready_to_run(win, tmp_path)
    copied = []
    auto = {"n": 0}

    def fake_copy(content):
        auto["n"] += 1
        copied.append(content)
        return auto["n"] > 1  # 自动复制失败，手动复制成功

    win.context.clipboard.copy_to_clipboard = fake_copy
    full = "完整结果" + "x" * 6000
    service.copy_result = (True, full)

    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True
    assert "自动复制失败" in win.run_step.status.cget("text")

    win.run_step.copy_all_btn.invoke()
    assert win.wait_idle(timeout=5.0) is True
    assert copied[-1] == full
    assert copied[-1] == win.session.last_result
    assert "已复制到剪贴板" in win.run_step.status.cget("text")


def test_copy_full_result_runs_on_worker_thread(win):
    """copy_full_result 不得在 UI 线程上执行 copy_to_clipboard（可能 sleep）。"""
    threads = []

    def fake_copy(content):
        threads.append(threading.current_thread())
        return True

    win.context.clipboard.copy_to_clipboard = fake_copy
    win.session.last_result = "手动复制内容"

    win.copy_full_result()
    assert win.wait_idle(timeout=5.0) is True

    assert threads and threads[0] is not threading.current_thread()
    assert "已复制到剪贴板" in win.run_step.status.cget("text")


def test_copy_history_entry_runs_on_worker_thread(win):
    """剪贴板历史复制同样要离开 UI 线程执行。"""
    threads = []

    def fake_copy(content):
        threads.append(threading.current_thread())
        return True

    win.context.clipboard.copy_to_clipboard = fake_copy

    win._copy_history_entry("历史记录内容")
    assert win.wait_idle(timeout=5.0) is True

    assert threads and threads[0] is not threading.current_thread()
    assert "已复制到剪贴板" in win.run_step.status.cget("text")


def test_stop_now_requests_cancel(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    win._start_job("save")
    win.stop_now()
    assert service.cancelled is True
    assert win.wait_idle(timeout=10.0) is True


def test_example_selection_feeds_load_example_images(win, tk_root, tmp_path, sample_png):
    service = _prepare_ready_to_run(win, tmp_path)
    example = win.context.examples.add_example(str(sample_png), "示例文本", "描述")
    assert example is not None
    win.prompt_step.refresh_examples()
    win.prompt_step.set_selected_example_ids([example.id])

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True

    sent = service.calls[0]["example_images"]
    assert sent and sent[0][0] == "示例文本"
    assert sent[0][1]


def test_examples_change_refreshes_prompt_step_few_shot(win, sample_png):
    """示例库增删改后提示词页少样本列表必须能选中新 id。"""
    example = win.context.examples.add_example(str(sample_png), "示例文本", "描述")
    assert example.id not in win.prompt_step.example_checks

    # ExampleManagerUI 在增删改后调用 refresh_list → data change → 同步
    win.examples_view.refresh()
    assert example.id in win.prompt_step.example_checks

    win.prompt_step.set_selected_example_ids([example.id])
    assert win.prompt_step.get_selected_example_ids() == [example.id]


def test_prompt_tab_switch_refreshes_few_shot_list(win, sample_png):
    example = win.context.examples.add_example(str(sample_png), "示例文本", "描述")
    win.wizard.set_current(2)
    assert example.id in win.prompt_step.example_checks
    win.prompt_step.set_selected_example_ids([example.id])
    out = SessionState()
    win.prompt_step.collect(out)
    assert out.selected_example_ids == [example.id]


def test_progress_marshalled_to_run_step(win, tk_root):
    win.progress.handle_progress(2, 4, 50.0, "OCR识别")
    win.progress.handle_status("正在识别")
    win.progress.flush()
    tk_root.update_idletasks()
    text = win.run_step.status.cget("text")
    assert "2/4" in text or text == "正在识别"


def test_wait_idle_true_when_no_job(win):
    assert win.wait_idle(timeout=1.0) is True


def test_on_closing_saves_config(tk_root, ctx, tmp_path):
    win = MainWindow(tk_root, context=ctx)
    win.config_step.fields["MODEL_NAME"].delete(0, "end")
    win.config_step.fields["MODEL_NAME"].insert(0, "saved-model")
    win.on_closing()
    text = (tmp_path / "cfg.json").read_text(encoding="utf-8")
    assert "saved-model" in text


def test_run_failure_keeps_window_alive(win, tk_root, tmp_path):
    """Background exceptions must not crash the mainloop (S7)."""
    service = _prepare_ready_to_run(win, tmp_path)
    service.raise_error = ValueError("boom")
    win.run_copy_now()
    win.run_save_now()  # second start while running must be a no-op
    assert win.wait_idle(timeout=10.0) is True
    assert tk_root.winfo_exists()
    assert len(service.calls) == 1


def test_empty_prompt_rejected_before_job_start(win, tk_root, tmp_path):
    """Empty prompt errors 请填写提示词 and never reaches the service."""
    service = _prepare_ready_to_run(win, tmp_path)
    win.prompt_step.textbox.delete("1.0", "end")

    win.run_save_now()
    assert win.wait_idle(timeout=10.0) is True
    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True

    assert service.calls == []
    assert win.run_step.status.cget("text") == "请填写提示词"
    assert "请填写提示词" in win.run_step.result.get("1.0", "end-1c")
    assert str(win.run_step.save_btn.cget("state")) == "normal"
    assert str(win.run_step.copy_btn.cget("state")) == "normal"
    assert win._running is False


def test_copy_run_rejects_batch_over_page_limit(win, tk_root, tmp_path):
    """run_copy_now refuses copy runs above the 10-page cap (product guard)."""
    service = _prepare_ready_to_run(win, tmp_path)
    paths = [str(tmp_path / f"p{i}.png") for i in range(11)]
    win.files_step._paths = paths
    win.files_step._refresh_listbox()

    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True

    shown = win.run_step.status.cget("text") + win.run_step.result.get("1.0", "end-1c")
    assert service.calls == []
    assert "识别并保存" in shown
    assert "页面范围" in shown
    assert "10" in shown
    assert str(win.run_step.copy_btn.cget("state")) == "normal"


def test_copy_run_allows_batch_at_page_limit(win, tk_root, tmp_path):
    service = _prepare_ready_to_run(win, tmp_path)
    win.files_step._paths = [str(tmp_path / f"p{i}.png") for i in range(10)]
    win.files_step._refresh_listbox()

    win.run_copy_now()
    assert win.wait_idle(timeout=10.0) is True

    assert service.calls and service.calls[0]["mode"] == "copy"
    assert len(service.calls[0]["file_paths"]) == 10
