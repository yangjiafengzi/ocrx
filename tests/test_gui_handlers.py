# -- coding: utf-8 --
"""GUI 处理器关键逻辑测试（避免真实弹窗和真实窗口）。"""

from types import SimpleNamespace

from ocrx.clipboard import ClipboardHistory
from ocrx.gui.handlers.copy_handler import CopyHandler
from ocrx.gui.handlers.result_handler import ResultHandler
from ocrx.gui.main_window import MainWindow
from ocrx.logger import StructuredLogger
from ocrx.pdf_processor import PDFProcessor


class FakeRoot:
    def __init__(self):
        self.scheduled = []

    def after(self, delay, fn, *args):
        self.scheduled.append((delay, fn, args))


class FakeMainWindow:
    def __init__(self, tmp_path):
        self.root = FakeRoot()
        self.logger = StructuredLogger(str(tmp_path / "gui_test.log"))
        self.clipboard_history = ClipboardHistory()
        self.processing_service = SimpleNamespace(pdf_processor=PDFProcessor())
        self.DISPLAY_MAX_LENGTH = 5000
        self.COPY_MAX_PAGES = 10

    def _on_status_update(self, status):
        pass

    def _on_progress_update(self, *args):
        pass

    def _display_result(self, content):
        pass


def test_check_page_limit_pdf_counts_real_pages(tmp_path, sample_pdf):
    """回归测试：PDF 的页数限制检查应统计真实页数，而不是按 1 页计算。"""
    mw = FakeMainWindow(tmp_path)
    handler = CopyHandler(mw)
    passed, total, msg = handler.check_page_limit([str(sample_pdf)], "")
    assert passed is True
    assert total == 3
    assert msg == ""


def test_check_page_limit_over_limit(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = CopyHandler(mw)
    paths = []
    for i in range(11):
        p = tmp_path / f"p{i}.png"
        p.write_bytes(b"png")
        paths.append(str(p))
    passed, total, msg = handler.check_page_limit(paths, "")
    assert passed is False
    assert total == 11
    assert "10 页以下" in msg


def test_check_page_limit_with_range(tmp_path, sample_pdf):
    mw = FakeMainWindow(tmp_path)
    handler = CopyHandler(mw)
    passed, total, msg = handler.check_page_limit([str(sample_pdf)], "1-2")
    assert passed is True
    assert total == 2


def test_estimate_page_range_count():
    mw = FakeMainWindow.__new__(FakeMainWindow)
    handler = CopyHandler.__new__(CopyHandler)
    assert handler._estimate_page_range_count("") == 0
    assert handler._estimate_page_range_count("1,3,5-10") == 8
    assert handler._estimate_page_range_count("10-5") == 0
    assert handler._estimate_page_range_count("abc") == 1


def test_result_display_reenables_disabled(tmp_path):
    """回归测试：显示新结果后文本框应重新置为只读。"""

    class FakeText:
        def __init__(self):
            self.states = []
            self.content = ""

        def config(self, state=None):
            self.states.append(state)

        def delete(self, *args):
            self.content = ""

        def insert(self, index, content):
            self.content = content

        def get(self, *args):
            return self.content

    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    fake_text = FakeText()
    handler.text_widget = fake_text

    handler.display("新内容")
    # 执行 after(0, update) 中排队的回调
    assert len(mw.root.scheduled) == 1
    mw.root.scheduled[0][1]()

    assert fake_text.content == "新内容"
    assert fake_text.states[-1] == "disabled"


def test_main_window_display_result_selects_result_tab():
    """回归测试：结果显示后应切换到“识别结果”页，而不是剪贴板历史页。"""
    selected = []
    result_frame = object()
    mw = MainWindow.__new__(MainWindow)
    mw.notebook = SimpleNamespace(select=lambda frame: selected.append(frame))
    mw.result_frame = result_frame
    mw.result_handler = SimpleNamespace(display=lambda content: None)
    mw.root = SimpleNamespace(after=lambda delay, fn: fn())

    MainWindow._display_result(mw, "内容")
    assert selected == [result_frame]


def test_show_about_uses_current_version(monkeypatch):
    from ocrx.gui import main_window as mw_mod

    captured = {}
    monkeypatch.setattr(
        mw_mod.messagebox,
        "showinfo",
        lambda title, msg: captured.update(title=title, msg=msg),
    )
    mw_mod.MainWindow.show_about(object())
    assert f"v{mw_mod.__version__}" in captured["msg"]
