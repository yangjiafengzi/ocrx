# -- coding: utf-8 --
"""Full wizard GUI e2e with tiny generated fixtures and mock OpenAI.

Covers save / copy / cancel and the empty-prompt preflight failure. Fixtures
are generated in-process (32x24 PNG, 1-page PDF); no binary assets. The UI is
driven programmatically through MainWindow helpers — no screenshots.
"""

import os
import threading
import time
import tkinter as tk
from pathlib import Path

import fitz
import pytest
from PIL import Image

from ocrx.clipboard import ClipboardHistory
from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow
from ocrx.gui.validation import ERR_EMPTY_PROMPT
from tests.mock_openai import MockOpenAIServer


pytestmark = pytest.mark.skipif(
    os.environ.get("OCRX_ALLOW_GUI", "1") != "1",
    reason="GUI e2e disabled",
)


def _tiny_png(path):
    Image.new("RGB", (32, 24), (200, 30, 30)).save(path, "PNG")
    return path


def _tiny_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Page 1")
    doc.save(str(path))
    doc.close()
    return path


def _prepare_run(win, files, prompt="识别文字", page_range=""):
    """Fill wizard step state the way a user would, without leaving the test thread."""
    win.files_step._paths = [str(p) for p in files]
    win.files_step._refresh_listbox()
    win.files_step.page_range.delete(0, "end")
    if page_range:
        win.files_step.page_range.insert(0, page_range)
    win.prompt_step.textbox.delete("1.0", "end")
    if prompt:
        win.prompt_step.textbox.insert("1.0", prompt)


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
        pytest.skip(f"当前环境无可用 Tcl/Tk 显示: {last_error}")
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


@pytest.fixture
def gui_window(tk_root, tmp_path, mock_openai_server):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    ctx = AppContext(
        config_path=str(tmp_path / "gui_cfg.json"),
        example_path=str(tmp_path / "gui_examples"),
        log_path=str(tmp_path / "gui.log"),
        root=tk_root,
    )
    ctx.config.set("BASE_URL", mock_openai_server.base_url)
    ctx.config.set("API_KEY", "test-key")
    ctx.config.set("MODEL_NAME", "test-model")
    ctx.config.set("OUTPUT_DIR", str(out_dir))
    ctx.config.set("MAX_WORKERS", "2")
    ctx.config.set("PDF_SCALE_FACTOR", "1.5")
    ctx.rebuild_service()
    win = MainWindow(tk_root, context=ctx)
    tk_root.update_idletasks()
    tk_root.update()
    try:
        yield win
    finally:
        try:
            win.on_closing()
        except Exception:
            pass


def test_gui_save_mode_writes_markdown(gui_window, mock_openai_server, tmp_path):
    win = gui_window
    out_dir = Path(win.context.config.get("OUTPUT_DIR"))
    png = _tiny_png(tmp_path / "a.png")
    pdf = _tiny_pdf(tmp_path / "doc.pdf")
    _prepare_run(win, [png, pdf], prompt="识别文字")

    win.run_save_now()
    assert win.wait_idle(timeout=15)

    md_files = sorted(out_dir.glob("*_ocr.md"))
    assert len(md_files) == 2
    saved_text = "\n".join(p.read_text(encoding="utf-8") for p in md_files)
    assert "识别结果-" in saved_text
    assert win.session.last_result
    assert mock_openai_server.wait_requests(2)
    assert win._running is False
    assert str(win.run_step.save_btn.cget("state")) == "normal"
    assert str(win.run_step.stop_btn.cget("state")) == "disabled"


def test_gui_copy_mode_records_clipboard_history(
    gui_window, mock_openai_server, tmp_path, monkeypatch
):
    win = gui_window
    out_dir = Path(win.context.config.get("OUTPUT_DIR"))
    png = _tiny_png(tmp_path / "a.png")
    _prepare_run(win, [png], prompt="识别文字")

    def fake_copy_to_clipboard(self, content, max_retries=3):
        # Record a success entry without clobbering the developer OS clipboard.
        self.add_record(content, success=True, method="test-double")
        return True

    monkeypatch.setattr(ClipboardHistory, "copy_to_clipboard", fake_copy_to_clipboard)

    win.run_copy_now()
    assert win.wait_idle(timeout=15)

    history = win.context.clipboard.get_history()
    successful = [
        record
        for record in history
        if record.get("success") and record.get("content")
    ]
    assert successful, "clipboard history should record a successful copy"
    joined = "\n".join(record.get("content") or "" for record in successful)
    assert "识别结果-" in joined
    assert win.session.last_result
    assert not list(out_dir.glob("*_ocr.md"))
    assert mock_openai_server.wait_requests(1)
    assert win._running is False


def test_gui_cancel_path_unlocks_controls(gui_window, mock_openai_server, tmp_path):
    win = gui_window
    # ConfigStep widgets are the source of truth once the wizard is built.
    entry = win.config_step.fields["MAX_WORKERS"]
    entry.delete(0, "end")
    entry.insert(0, "1")
    win.context.config.set("MAX_WORKERS", "1")
    release = threading.Event()

    def slow_respond(body, call_index):
        release.wait(timeout=5.0)
        return 200, MockOpenAIServer.response(f"取消内容-{call_index}")

    mock_openai_server.respond = slow_respond
    pngs = [_tiny_png(tmp_path / f"p{i}.png") for i in range(2)]
    _prepare_run(win, pngs, prompt="识别文字")

    win.run_save_now()
    try:
        assert mock_openai_server.wait_requests(1, timeout=5)
        win.stop_now()
    finally:
        release.set()

    assert win.wait_idle(timeout=10)
    assert win._running is False
    # controls unlocked (S7) and the app is still stable
    assert str(win.run_step.save_btn.cget("state")) == "normal"
    assert str(win.run_step.stop_btn.cget("state")) == "disabled"
    assert win.root.winfo_exists()
    win.run_step.set_status("stable")
    win.run_step.set_result("stable")
    assert isinstance(win.run_step.get_full_text(), str)
    # cooperative cancel: the second page was never submitted
    with mock_openai_server.lock:
        assert len(mock_openai_server.requests) == 1


def test_gui_preflight_empty_prompt_never_calls_server(gui_window, mock_openai_server, tmp_path):
    win = gui_window
    png = _tiny_png(tmp_path / "a.png")
    _prepare_run(win, [png], prompt="")

    win.run_save_now()
    assert win.wait_idle(timeout=5)

    assert ERR_EMPTY_PROMPT in str(win.run_step.status.cget("text"))
    assert ERR_EMPTY_PROMPT in win.run_step.get_full_text()
    assert win._running is False
    assert str(win.run_step.save_btn.cget("state")) == "normal"
    with mock_openai_server.lock:
        assert len(mock_openai_server.requests) == 0
    assert mock_openai_server.wait_requests(1, timeout=0.2) is False
