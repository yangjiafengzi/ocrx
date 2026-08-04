# -- coding: utf-8 --
"""
真实 UI 窗口测试（需要可用的桌面环境，否则自动跳过）。

使用 Miniconda 等自带完整 Tcl/Tk 的 Python 运行：
    C:\\Users\\DHQ\\miniconda3\\python.exe -m pytest tests/test_ui_window.py -v
"""

import tkinter as tk
from tkinter import ttk
import time
from types import SimpleNamespace

import pytest

from ocrx.config import ConfigManager
from ocrx.example_library import ExampleLibrary
from ocrx.gui import main_window as mw_mod
from ocrx.logger import StructuredLogger


@pytest.fixture
def ui_app(tmp_path, monkeypatch):
    root = None
    last_error = None
    for _ in range(3):
        try:
            root = tk.Tk()
            break
        except tk.TclError as e:
            last_error = e
            time.sleep(0.5)
    if root is None:
        pytest.skip(f"当前环境无可用 Tcl/Tk 显示：{last_error}")

    class TestLogger(StructuredLogger):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("log_file_path", str(tmp_path / "ui.log"))
            super().__init__(*args, **kwargs)

    test_cfg = ConfigManager(str(tmp_path / "ui_config.json"))
    test_cfg.load()

    monkeypatch.setattr(mw_mod, "ConfigManager", lambda: test_cfg)
    monkeypatch.setattr(mw_mod, "StructuredLogger", TestLogger)
    monkeypatch.setattr(
        mw_mod,
        "ExampleLibrary",
        lambda: ExampleLibrary(str(tmp_path / "example_library")),
    )

    app = mw_mod.MainWindow(root)
    root.update_idletasks()
    root.update()
    yield app
    try:
        app.logger.close()
    finally:
        root.destroy()


def test_window_title_and_size(ui_app):
    assert ui_app.root.title() == "OCRX-智能文字识别"
    assert ui_app.root.winfo_width() >= 900
    assert ui_app.root.winfo_height() >= 700


def test_notebook_tabs(ui_app):
    tabs = [ui_app.notebook.tab(tab, "text") for tab in ui_app.notebook.tabs()]
    assert tabs == ["主要配置", "少样本示例库", "运行日志", "剪贴板历史", "识别结果"]


def test_key_widgets_exist(ui_app):
    assert ui_app.base_url_entry is not None
    assert ui_app.api_key_entry is not None
    assert ui_app.model_name_entry is not None
    assert ui_app.file_paths_entry is not None
    assert ui_app.output_dir_entry is not None
    assert ui_app.prompt_text is not None
    assert ui_app.progress_bar is not None
    assert ui_app.result_text is not None
    assert ui_app.clipboard_tree is not None


def test_bottom_buttons(ui_app):
    texts = []

    def walk(widget):
        for child in widget.winfo_children():
            try:
                text = child.cget("text")
                if text:
                    texts.append(text)
            except tk.TclError:
                pass
            walk(child)

    walk(ui_app.root)
    for expected in ["识别并保存", "识别并复制", "停止", "保存配置", "重置配置", "关于"]:
        assert expected in texts, f"缺少按钮：{expected}"


def test_prompt_presets_loaded(ui_app):
    values = list(ui_app.prompt_preset_combobox["values"])
    assert "手写笔记" in values
    assert "印刷材料" in values
    assert ui_app.prompt_preset_var.get() == "手写笔记"
    # 启动时应自动填充默认预设内容，而不是留空
    content = ui_app.prompt_text.get("1.0", tk.END)
    assert "手写笔记识别专家" in content


def test_prompt_preset_selection_updates_text(ui_app):
    ui_app.prompt_preset_var.set("印刷材料")
    ui_app.on_prompt_preset_selected()
    content = ui_app.prompt_text.get("1.0", tk.END)
    assert "光学字符识别" in content


def test_result_text_initial_state(ui_app):
    assert ui_app.result_text.cget("state") == "disabled"
    content = ui_app.result_text.get("1.0", tk.END)
    assert "识别结果将显示在这里" in content


def test_display_result_switches_tab_and_disables(ui_app):
    ui_app._display_result("窗口测试结果")
    ui_app.root.update_idletasks()
    ui_app.root.update()
    assert ui_app.notebook.select() == str(ui_app.result_frame)
    content = ui_app.result_text.get("1.0", tk.END).strip()
    assert content == "窗口测试结果"
    assert ui_app.result_text.cget("state") == "disabled"


def test_example_library_tab_refresh(ui_app):
    # 切换到少样本示例库页，确认列表和统计标签存在
    for i, tab_id in enumerate(ui_app.notebook.tabs()):
        if ui_app.notebook.tab(tab_id, "text") == "少样本示例库":
            ui_app.notebook.select(i)
            break
    ui_app.root.update_idletasks()
    assert ui_app.example_manager_ui.stats_label.cget("text") == "共 0 个示例"
    assert ui_app.example_manager_ui.tree.get_children() == ()


def test_save_config_silent_on_close(ui_app, monkeypatch):
    """回归测试：关闭窗口时保存配置不应弹出对话框。"""
    dialogs = []
    monkeypatch.setattr(mw_mod.messagebox, "showinfo", lambda *a: dialogs.append(a))
    ui_app.save_config(show_dialog=False)
    assert dialogs == []


def test_config_page_scrollable_when_window_small(ui_app):
    """回归测试：窗口缩小时配置页应有纵向滚动条，滚轮可滚动到被遮挡内容。"""
    ui_app.root.minsize(400, 300)
    ui_app.root.geometry("900x450")
    ui_app.root.update_idletasks()
    ui_app.root.update()

    canvas = ui_app.config_canvas
    assert canvas.winfo_exists()
    assert ui_app.config_scrollbar.winfo_exists()
    assert ui_app.config_scrollbar.winfo_ismapped(), "窗口缩小时滚动条应可见"

    # 内容应高于可视区域（复现“被遮挡”场景）
    top, bottom = canvas.yview()
    assert bottom < 1.0, "配置页内容未超出可视区，无法复现遮挡问题"

    # 向下滚动应生效
    before = canvas.yview()
    ui_app._on_config_mousewheel(SimpleNamespace(delta=-120))
    ui_app.root.update_idletasks()
    after = canvas.yview()
    assert after[0] > before[0], "鼠标滚轮未生效"

    # 向上滚回顶部
    ui_app._on_config_mousewheel(SimpleNamespace(delta=120))
    ui_app.root.update_idletasks()
    assert canvas.yview()[0] < after[0]

    # 模拟画布高度足够大：内容放得下时滚动条自动隐藏
    ui_app.config_canvas.winfo_height = lambda: 2000
    ui_app._update_config_scrollbar_visibility()
    assert not ui_app.config_scrollbar.winfo_ismapped(), "内容放得下时滚动条应隐藏"


def test_all_text_scrollbars_unified(ui_app):
    """回归测试：提示词/日志/结果页的滚动条都应是统一的 ttk 细窄样式。"""
    for widget in (ui_app.prompt_text, ui_app.log_text, ui_app.result_text):
        assert isinstance(widget.vbar, ttk.Scrollbar), (
            f"{widget} 的滚动条未统一为 ttk 样式"
        )
    # 日志页为深色控制台，滚动条应使用深色适配样式
    assert str(ui_app.log_text.vbar.cget("style")) == "Dark.Vertical.TScrollbar"
    assert str(ui_app.prompt_text.vbar.cget("style")) == "Vertical.TScrollbar"
    assert str(ui_app.result_text.vbar.cget("style")) == "Vertical.TScrollbar"
