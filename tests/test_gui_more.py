# -- coding: utf-8 --
"""更多 GUI 处理器逻辑测试（全部使用假控件，无需真实窗口）。"""

import threading
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

from ocrx.clipboard import ClipboardHistory
from ocrx.example_library import ExampleLibrary
from ocrx.gui.example_manager_ui import ExampleManagerUI
from ocrx.gui.handlers.base_handler import BaseHandler
from ocrx.gui.handlers.clipboard_handler import ClipboardHandler
from ocrx.gui.handlers.copy_handler import CopyHandler
from ocrx.gui.handlers.progress_handler import ProgressHandler
from ocrx.gui.handlers.result_handler import ResultHandler
from ocrx.gui.handlers.save_handler import SaveHandler
from ocrx.gui import main_window as mw_mod
from ocrx.logger import StructuredLogger

import ocrx.gui.handlers.result_handler as rh_mod
import ocrx.gui.handlers.clipboard_handler as ch_mod


class FakeRoot:
    def __init__(self):
        self.scheduled = []

    def after(self, delay, fn, *args):
        self.scheduled.append((delay, fn, args))


class FakeMainWindow:
    def __init__(self, tmp_path):
        self.root = FakeRoot()
        self.logger = StructuredLogger(str(tmp_path / "gui_more.log"))
        self.clipboard_history = ClipboardHistory()
        self.processing_service = None
        self.DISPLAY_MAX_LENGTH = 5000
        self.COPY_MAX_PAGES = 10
        self.status_updates = []
        self.progress_updates = []
        self.displayed = []

    def _on_status_update(self, status):
        self.status_updates.append(status)

    def _on_progress_update(self, *args):
        self.progress_updates.append(args)

    def _display_result(self, content):
        self.displayed.append(content)


class FakeText:
    def __init__(self, content="", raise_tcl=False):
        self.content = content
        self.raise_tcl = raise_tcl
        self.states = []

    def config(self, state=None):
        self.states.append(state)

    def get(self, *args):
        if self.raise_tcl and args:
            raise tk.TclError("no selection")
        return self.content

    def delete(self, *args):
        self.content = ""

    def insert(self, index, content):
        self.content = content

    def see(self, *args):
        pass


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeLabel:
    def __init__(self):
        self.text = None

    def config(self, text=None):
        self.text = text


class FakeBar:
    def __init__(self):
        self.data = {}

    def __setitem__(self, key, value):
        self.data[key] = value


class FakeTree:
    def __init__(self):
        self.children = []
        self.rows = {}
        self.next_id = 0
        self.selected = []
        self.identify_region = "cell"
        self.identify_col = "#1"
        self.identify_row_id = "r0"

    def get_children(self):
        return list(self.children)

    def delete(self, item):
        if item in self.children:
            self.children.remove(item)
        self.rows.pop(item, None)

    def insert(self, parent, index, values=None, tags=()):
        item = f"r{self.next_id}"
        self.next_id += 1
        self.children.append(item)
        self.rows[item] = {"values": list(values or []), "tags": list(tags)}
        return item

    def item(self, item, option=None, **kwargs):
        if kwargs:
            self.rows[item].update(kwargs)
            return
        if option is None:
            return dict(self.rows[item])
        return self.rows[item][option]

    def selection(self):
        return list(self.selected)

    def index(self, item):
        return self.children.index(item)

    def identify(self, what, x, y):
        if what == "region":
            return self.identify_region
        if what == "column":
            return self.identify_col
        if what == "row":
            return self.identify_row_id
        return ""

    def identify_column(self, x):
        return self.identify_col

    def identify_row(self, y):
        return self.identify_row_id


# ---------- BaseHandler ----------


def test_base_handler_proxies_and_thread(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = BaseHandler(mw)
    handler._update_status("状态")
    handler._update_progress(1, 2, "阶段")
    handler._display_result("结果")
    assert mw.status_updates == ["状态"]
    assert mw.progress_updates == [(1, 2, "阶段")]
    assert mw.displayed == ["结果"]

    done = threading.Event()
    thread = handler.run_in_thread(done.set)
    thread.join(timeout=5)
    assert done.is_set()


# ---------- ResultHandler ----------


def test_result_clear_resets_to_initial(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("旧内容")
    handler.clear()
    assert "识别结果将显示在这里" in handler.text_widget.content
    assert handler.text_widget.states[-1] == "disabled"


def test_result_refresh_preserves_content(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("真实结果")
    monkeypatch.setattr(rh_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.refresh()
    assert handler.text_widget.content == "真实结果"
    assert handler.text_widget.states[-1] == "disabled"


def test_result_refresh_no_content_shows_hint(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("识别结果将显示在这里...")
    infos = []
    monkeypatch.setattr(rh_mod.messagebox, "showinfo", lambda *a: infos.append(a))
    handler.refresh()
    assert infos


def test_result_copy_all(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("要复制的内容")
    copied = []
    monkeypatch.setattr(handler.clipboard_history, "copy_to_clipboard", lambda c: copied.append(c) or True)
    monkeypatch.setattr(rh_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.copy_all()
    assert copied == ["要复制的内容"]


def test_result_copy_selection(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("选中内容")
    copied = []
    monkeypatch.setattr(handler.clipboard_history, "copy_to_clipboard", lambda c: copied.append(c) or True)
    monkeypatch.setattr(rh_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.copy_selection()
    assert copied == ["选中内容"]


def test_result_copy_selection_no_selection_warns(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("内容", raise_tcl=True)
    warnings = []
    monkeypatch.setattr(rh_mod.messagebox, "showwarning", lambda *a: warnings.append(a))
    handler.copy_selection()
    assert warnings


def test_result_save_to_file(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("# 保存的内容")
    out = tmp_path / "saved.md"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **k: str(out))
    monkeypatch.setattr(rh_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.save_to_file()
    assert out.read_text(encoding="utf-8") == "# 保存的内容"


def test_result_save_to_file_cancel(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ResultHandler(mw)
    handler.text_widget = FakeText("内容")
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **k: None)
    handler.save_to_file()
    assert not list(tmp_path.glob("*.md"))


# ---------- ProgressHandler ----------


def test_progress_handler_update_and_reset(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = ProgressHandler(mw)
    handler.progress_var = FakeVar()
    handler.current_task_label = FakeLabel()
    handler.progress_bar = FakeBar()
    handler.detail_progress_var = FakeVar()
    handler.update_progress(2, 10, 25.0, "OCR识别")
    assert handler.progress_var.value == "25.0% (2/10)"
    assert handler.progress_bar.data["value"] == 25.0
    assert "OCR识别" in handler.current_task_label.text
    handler.update_status("等待开始...")
    assert handler.current_task_label.text == "等待开始..."
    handler.reset()
    assert handler.progress_var.value == "0%"
    assert handler.progress_bar.data["value"] == 0


# ---------- ClipboardHandler ----------


def test_clipboard_handler_refresh(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = ClipboardHandler(mw)
    mw.clipboard_history.add_record("第一条", success=True, method="tkinter")
    handler.tree = FakeTree()
    handler.refresh_history()
    assert len(handler.tree.children) == 1
    values = handler.tree.item(handler.tree.children[0], "values")
    assert values[2] == "成功"
    assert "第一条" in values[4]


def test_clipboard_handler_copy_selected(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ClipboardHandler(mw)
    mw.clipboard_history.add_record("完整内容", success=True, method="tkinter")
    handler.tree = FakeTree()
    handler.tree.insert("", 0, values=(1, 2, 3, 4, 5))
    handler.tree.selected = [handler.tree.children[0]]
    copied = []
    monkeypatch.setattr(handler.clipboard_history, "copy_to_clipboard", lambda c: copied.append(c) or True)
    monkeypatch.setattr(ch_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.copy_selected()
    assert copied == ["完整内容"]


def test_clipboard_handler_clear_history(tmp_path, monkeypatch):
    mw = FakeMainWindow(tmp_path)
    handler = ClipboardHandler(mw)
    mw.clipboard_history.add_record("内容")
    handler.tree = FakeTree()
    handler.tree.insert("", 0, values=(1,))
    monkeypatch.setattr(ch_mod.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(ch_mod.messagebox, "showinfo", lambda *a, **k: None)
    handler.clear_history()
    assert mw.clipboard_history.get_history() == []
    assert handler.tree.children == []


# ---------- SaveHandler / CopyHandler ----------


def test_save_handler_prepare_display_truncates(tmp_path):
    mw = FakeMainWindow(tmp_path)
    handler = SaveHandler(mw)
    handler.DISPLAY_MAX_LENGTH = 30
    path = tmp_path / "a_ocr.md"
    path.write_text("内容" * 30, encoding="utf-8")
    out = handler._prepare_display_content({"a": (True, str(path))})
    assert "=== a ===" in out
    assert "截断" in out


def test_save_handler_process_files_happy_path(tmp_path):
    mw = FakeMainWindow(tmp_path)
    mw.processing_service = SimpleNamespace(
        process_files=lambda **kw: {"a": (True, str(tmp_path / "a_ocr.md"))}
    )
    handler = SaveHandler(mw)
    results = handler.process_files(["a.png"], "p", "")
    assert results == {"a": (True, str(tmp_path / "a_ocr.md"))}
    assert mw.root.scheduled  # 完成消息通过 after 调度


def test_copy_handler_process_files_happy_path(tmp_path):
    mw = FakeMainWindow(tmp_path)
    mw.processing_service = SimpleNamespace(
        process_and_copy=lambda **kw: (True, "识别内容")
    )
    handler = CopyHandler(mw)
    ok, content = handler.process_files(["a.png"], "p", "")
    assert ok is True
    assert content == "识别内容"
    assert mw.displayed == ["识别内容"]
    assert mw.root.scheduled  # 复制动作通过 after 调度到主线程


def test_copy_handler_process_files_failure_path(tmp_path):
    mw = FakeMainWindow(tmp_path)
    mw.processing_service = SimpleNamespace(
        process_and_copy=lambda **kw: (False, "识别失败：网络错误")
    )
    handler = CopyHandler(mw)
    ok, content = handler.process_files(["a.png"], "p", "")
    assert ok is False
    assert "网络错误" in content


# ---------- ExampleManagerUI 逻辑 ----------


def make_example_ui(tmp_path):
    library = ExampleLibrary(str(tmp_path / "library"))
    ui = ExampleManagerUI.__new__(ExampleManagerUI)
    ui.library = library
    ui.selected_examples = []
    ui.on_selection_change = None
    ui.tree = FakeTree()
    ui.stats_label = FakeLabel()
    return library, ui


def test_example_ui_refresh_list(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    library.add_example(str(sample_png), "示例文本", "标签")
    ui.refresh_list()
    assert len(ui.tree.children) == 1
    assert ui.stats_label.text == "共 1 个示例"
    values = ui.tree.item(ui.tree.children[0], "values")
    assert values[0] == "☐"
    assert values[2] == "标签"


def test_example_ui_selection_toggle(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    example = library.add_example(str(sample_png), "文本")
    ui.refresh_list()
    changes = []
    ui.on_selection_change = lambda ids: changes.append(ids)
    ui.tree.identify_row_id = ui.tree.children[0]
    event = SimpleNamespace(x=0, y=0)
    ui._on_tree_click(event)
    assert ui.selected_examples == [example.id]
    assert changes == [[example.id]]
    assert ui.tree.item(ui.tree.children[0], "values")[0] == "☑"
    ui._on_tree_click(event)
    assert ui.selected_examples == []
    assert ui.tree.item(ui.tree.children[0], "values")[0] == "☐"


def test_example_ui_delete_selected(tmp_path, sample_png, monkeypatch):
    library, ui = make_example_ui(tmp_path)
    example = library.add_example(str(sample_png), "文本")
    ui.refresh_list()
    ui.selected_examples = [example.id]
    monkeypatch.setattr("ocrx.gui.example_manager_ui.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("ocrx.gui.example_manager_ui.messagebox.showinfo", lambda *a, **k: None)
    ui._on_delete_selected()
    assert library.get_stats()["total_examples"] == 0
    assert ui.tree.children == []


def test_example_ui_select_all_and_by_description(tmp_path, sample_png):
    library, ui = make_example_ui(tmp_path)
    library.add_example(str(sample_png), "a", "手写")
    library.add_example(str(sample_png), "b", "印刷")
    ui.refresh_list()
    ui.select_all()
    assert len(ui.selected_examples) == 2
    ui.clear_selection()
    assert ui.selected_examples == []
    ui.select_by_description("手写")
    assert len(ui.selected_examples) == 1


# ---------- MainWindow 轻量逻辑 ----------


def test_main_window_log_callback(tmp_path):
    mw = mw_mod.MainWindow.__new__(mw_mod.MainWindow)
    mw.root = FakeRoot()
    mw.log_text = FakeText()
    entry = {"timestamp": "2026-01-01", "level": "INFO", "component": "System", "message": "测试日志"}
    mw.log_callback(entry)
    assert len(mw.root.scheduled) == 1
    mw.root.scheduled[0][1](entry)
    assert "测试日志" in mw.log_text.content
    assert mw.log_text.states[-1] == "disabled"


def test_main_window_progress_and_status_callbacks(tmp_path):
    mw = mw_mod.MainWindow.__new__(mw_mod.MainWindow)
    mw.root = FakeRoot()
    updates = []
    mw.progress_handler = SimpleNamespace(
        update_progress=lambda *a: updates.append(("progress", a)),
        update_status=lambda s: updates.append(("status", s)),
    )
    mw._on_progress_update(1, 2, 25.0, "阶段")
    mw._on_status_update("状态")
    assert len(mw.root.scheduled) == 2
    for _, fn, args in mw.root.scheduled:
        fn(*args)
    assert ("progress", (1, 2, 25.0, "阶段")) in updates
    assert ("status", "状态") in updates


def test_main_window_example_selection_callback(tmp_path):
    mw = mw_mod.MainWindow.__new__(mw_mod.MainWindow)
    logs = []
    mw.logger = SimpleNamespace(info=lambda *a, **k: logs.append(a), debug=lambda *a, **k: logs.append(a))
    mw._on_example_selection_change(["id1", "id2"])
    assert mw.selected_example_ids == ["id1", "id2"]
    assert logs
