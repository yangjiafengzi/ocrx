# -- coding: utf-8 --
"""
OCRX 界面主题。
提供设计配色常量与统一的 ttk 滚动条工具（按需显示、最小滑块、滑轨翻页）。
全局样式由 CustomTkinter + theme_tokens 负责；本模块只保留滚动条辅助。
"""

import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk

# 设计色板唯一来源：theme_tokens（COLORS / FONT）
from .theme_tokens import COLORS, FONT

# 配色
PRIMARY = COLORS["primary"]
PRIMARY_HOVER = COLORS["primary_hover"]
PRIMARY_LIGHT = "#DBEAFE"
BG = COLORS["bg"]
SURFACE = COLORS["surface"]
BORDER = COLORS["border"]
TEXT = COLORS["text"]
MUTED = COLORS["muted"]
SUCCESS = COLORS["success"]
SUCCESS_HOVER = "#15803D"
DANGER = COLORS["danger"]
DANGER_HOVER = "#B91C1C"

FONT_FAMILY = FONT[0]


def apply_themed_scrollbar(
    text_widget: scrolledtext.ScrolledText,
    scrollbar_style: str = "Vertical.TScrollbar",
) -> ttk.Scrollbar:
    """把 ScrolledText 内置的原生滚动条替换为统一风格的 ttk 滚动条。

    滚动条按需显示：内容放得下时隐藏，溢出时出现并保证滑块可见可拖。
    """
    frame = text_widget.frame
    try:
        # 让滚动条所在的内层 Frame 与文本框背景一致，避免轨道周围露出浅色边框
        frame.configure(bg=text_widget.cget("bg"))
    except tk.TclError:
        pass
    try:
        text_widget.vbar.destroy()
    except tk.TclError:
        pass
    vbar = ttk.Scrollbar(
        frame,
        orient="vertical",
        command=text_widget.yview,
        style=scrollbar_style,
    )
    text_widget.vbar = vbar
    vbar.pack(side=tk.RIGHT, fill=tk.Y)
    attach_scrollbar(vbar, text_widget, orient="vertical", manager="pack")
    bind_scrollbar_paging(vbar)
    return vbar


def themed_scrolled_text(
    parent,
    scrollbar_style: str = "Vertical.TScrollbar",
    **kwargs,
) -> scrolledtext.ScrolledText:
    """创建带统一风格滚动条的 ScrolledText。"""
    widget = scrolledtext.ScrolledText(parent, **kwargs)
    apply_themed_scrollbar(widget, scrollbar_style)
    return widget


def bind_scrollbar_paging(scrollbar: ttk.Scrollbar):
    """点击滑轨翻页、滚轮在滚动条上滚动。"""

    def _on_click(event):
        try:
            element = scrollbar.identify(event.x, event.y)
        except tk.TclError:
            return
        if element != "trough":
            return
        command = scrollbar.cget("command")
        if not command:
            return
        orient = str(scrollbar.cget("orient"))
        size = (
            scrollbar.winfo_height()
            if orient == "vertical"
            else scrollbar.winfo_width()
        )
        pos = event.y if orient == "vertical" else event.x
        first, last = (float(x) for x in scrollbar.get())
        thumb_start = first * size
        thumb_end = last * size
        if pos < thumb_start:
            command("scroll", -1, "pages")
        elif pos > thumb_end:
            command("scroll", 1, "pages")

    def _on_wheel(event):
        command = scrollbar.cget("command")
        if command:
            command("scroll", -1 if event.delta > 0 else 1, "units")

    scrollbar.bind("<Button-1>", _on_click, add="+")
    scrollbar.bind("<MouseWheel>", _on_wheel, add="+")


def bind_tree_scroll(tree: ttk.Treeview, xscrollbar=None):
    """让表格支持滚轮滚动（纵向 + Shift 横向）。"""

    def _on_wheel(event):
        tree.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def _on_shift_wheel(event):
        tree.xview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    tree.bind("<MouseWheel>", _on_wheel, add="+")
    tree.bind("<Shift-MouseWheel>", _on_shift_wheel, add="+")
    if xscrollbar is not None:
        xscrollbar.bind("<MouseWheel>", _on_shift_wheel, add="+")


def attach_scrollbar(
    scrollbar: ttk.Scrollbar,
    target,
    orient: str = "vertical",
    manager: str = "grid",
    min_thumb_px: int = 40,
):
    """把滚动条接到目标控件。

    - 内容放得下时自动隐藏，不显示“满条假滑块”；
    - 内容溢出时显示，并保证滑块至少 min_thumb_px 高/宽（内容极多时滑块不会细到消失）。
    """
    grid_opts = {}
    if manager == "grid" and scrollbar.winfo_manager() == "grid":
        info = scrollbar.grid_info()
        if info:
            grid_opts = {
                "row": info["row"],
                "column": info["column"],
                "sticky": info.get("sticky"),
            }

    def _show():
        try:
            if manager == "grid":
                if not scrollbar.winfo_ismapped():
                    scrollbar.grid(**grid_opts)
            else:
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        except tk.TclError:
            pass

    def _hide():
        try:
            if manager == "grid":
                scrollbar.grid_remove()
            else:
                scrollbar.pack_forget()
        except tk.TclError:
            pass

    def _set(*args):
        try:
            first, last = float(args[0]), float(args[1])
        except (TypeError, ValueError):
            return
        # 内容放得下：隐藏，不显示假满条
        if first <= 0.0 and last >= 1.0:
            _hide()
            return
        # 最小滑块尺寸
        size = (
            scrollbar.winfo_height()
            if orient == "vertical"
            else scrollbar.winfo_width()
        )
        if size > 0:
            min_frac = min(0.5, min_thumb_px / size)
            if last - first < min_frac:
                if first <= 0.0:
                    # 贴顶：只向底部扩展，保证最小尺寸
                    last = max(last, min_frac)
                elif last >= 1.0:
                    # 贴底：只向顶部扩展
                    first = min(first, 1.0 - min_frac)
                else:
                    center = (first + last) / 2
                    first = max(0.0, center - min_frac / 2)
                    last = min(1.0, center + min_frac / 2)
        scrollbar.set(first, last)
        _show()

    if orient == "vertical":
        target.configure(yscrollcommand=_set)
    else:
        target.configure(xscrollcommand=_set)
    try:
        view = target.yview() if orient == "vertical" else target.xview()
        _set(*view)
    except tk.TclError:
        pass
    return _set
