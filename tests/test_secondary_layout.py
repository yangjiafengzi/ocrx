# -- coding: utf-8 --
"""小窗口下次要页签高度与滚动条布局测试。"""

import tkinter as tk

import pytest

from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow, SECONDARY_TABS


@pytest.fixture
def win(tmp_path):
    root = None
    for _ in range(3):
        try:
            root = tk.Tk()
            break
        except tk.TclError:
            continue
    if root is None:
        pytest.skip("no display")
    # 需要真实映射/重排，withdrawn 下 CTk 不会算高度
    root.deiconify()
    root.geometry("900x680")
    ctx = AppContext(
        config_path=str(tmp_path / "cfg.json"),
        example_path=str(tmp_path / "ex"),
        log_path=str(tmp_path / "log"),
        root=root,
    )
    window = MainWindow(root, context=ctx)
    root.update()
    yield window
    try:
        window.on_closing()
    except Exception:
        root.destroy()


def _sync(root, geometry=None):
    if geometry:
        root.geometry(geometry)
    root.update_idletasks()
    root.update()


def test_secondary_tab_fills_and_has_scrollbars(win):
    _sync(win.root, "900x680")

    secondary = win.secondary
    assert secondary.winfo_manager()
    # 次要页签应拿到可观高度（不再是被压扁的一条）
    assert secondary.winfo_height() >= 180

    # 切到剪贴板页再测（CTkTabview 仅映射当前页）
    win.secondary.set(SECONDARY_TABS[1])
    _sync(win.root)
    clipboard_frame = win.clipboard_view.frame
    assert clipboard_frame.winfo_manager()
    assert clipboard_frame.winfo_height() >= 120
    assert win.clipboard_view.tree.winfo_height() >= 40
    children = clipboard_frame.winfo_children()
    assert any("Scrollbar" in c.winfo_class() for c in children)

    # 切到日志页再测
    win.secondary.set(SECONDARY_TABS[2])
    _sync(win.root)
    logs_frame = win.logs_view.frame
    assert logs_frame.winfo_manager()
    assert win.logs_view.textbox.winfo_height() >= 40
    assert win.logs_view.vbar.winfo_manager()

    # 示例库面板已创建（非当前页时可能未映射）
    assert win.examples_view.manager is not None


def test_secondary_grows_when_window_grows(win):
    _sync(win.root, "900x680")
    small_h = win.secondary.winfo_height()

    _sync(win.root, "1100x900")
    large_h = win.secondary.winfo_height()
    assert large_h > small_h


def test_secondary_shrinks_but_stays_usable_on_small_window(win):
    _sync(win.root, "900x560")
    h = win.secondary.winfo_height()
    assert h >= 160
    assert win.logs_view.vbar.winfo_manager()
    assert any(
        "Scrollbar" in c.winfo_class()
        for c in win.clipboard_view.frame.winfo_children()
    )
