# -- coding: utf-8 --
"""
OCRX 界面主题。
统一配置 ttk 样式：配色、字体、按钮、卡片分组、标签页、进度条等。
"""

import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk

# 配色
PRIMARY = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"
PRIMARY_LIGHT = "#DBEAFE"
BG = "#F1F5F9"
SURFACE = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#0F172A"
MUTED = "#64748B"
SUCCESS = "#16A34A"
SUCCESS_HOVER = "#15803D"
DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"

FONT_FAMILY = "Microsoft YaHei UI"


def setup_styles(root: tk.Tk):
    """应用全局主题样式（幂等，可重复调用）。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # 基础
    style.configure(".", font=(FONT_FAMILY, 9), background=BG, foreground=TEXT)

    # 框架与卡片
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure(
        "Card.TLabelframe",
        background=SURFACE,
        bordercolor=BORDER,
        borderwidth=1,
        relief="solid",
        padding=8,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=SURFACE,
        foreground=PRIMARY,
        font=(FONT_FAMILY, 10, "bold"),
    )

    # 页头
    style.configure("Header.TFrame", background=PRIMARY)
    style.configure(
        "HeaderTitle.TLabel",
        background=PRIMARY,
        foreground="#FFFFFF",
        font=(FONT_FAMILY, 15, "bold"),
    )
    style.configure(
        "HeaderSub.TLabel",
        background=PRIMARY,
        foreground="#DBEAFE",
        font=(FONT_FAMILY, 9),
    )

    # 标签
    style.configure("TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 9))
    style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED)
    style.configure("Section.TLabel", font=(FONT_FAMILY, 10, "bold"))

    # 按钮
    style.configure(
        "TButton",
        font=(FONT_FAMILY, 9),
        padding=(12, 6),
        background=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        focuscolor=PRIMARY,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", "#F1F5F9"), ("pressed", "#E2E8F0")],
        bordercolor=[("active", PRIMARY)],
    )
    style.configure(
        "Secondary.TButton",
        font=(FONT_FAMILY, 9),
        padding=(12, 6),
        background=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        focuscolor=PRIMARY,
        relief="flat",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#F1F5F9"), ("pressed", "#E2E8F0")],
        bordercolor=[("active", PRIMARY)],
    )
    style.configure(
        "Primary.TButton",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(16, 7),
        background=PRIMARY,
        foreground="#FFFFFF",
        bordercolor=PRIMARY,
        focuscolor="#FFFFFF",
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)],
        foreground=[("disabled", "#CBD5E1")],
    )
    style.configure(
        "Success.TButton",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(16, 7),
        background=SUCCESS,
        foreground="#FFFFFF",
        bordercolor=SUCCESS,
        focuscolor="#FFFFFF",
        relief="flat",
    )
    style.map(
        "Success.TButton",
        background=[("active", SUCCESS_HOVER), ("pressed", SUCCESS_HOVER)],
        foreground=[("disabled", "#CBD5E1")],
    )
    style.configure(
        "Danger.TButton",
        font=(FONT_FAMILY, 9, "bold"),
        padding=(12, 6),
        background=DANGER,
        foreground="#FFFFFF",
        bordercolor=DANGER,
        focuscolor="#FFFFFF",
        relief="flat",
    )
    style.map(
        "Danger.TButton",
        background=[("active", DANGER_HOVER), ("pressed", DANGER_HOVER)],
        foreground=[("disabled", "#CBD5E1")],
    )

    # 输入框
    style.configure(
        "TEntry",
        fieldbackground=SURFACE,
        bordercolor=BORDER,
        padding=6,
        insertcolor=TEXT,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", PRIMARY)],
        lightcolor=[("focus", PRIMARY)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE,
        bordercolor=BORDER,
        padding=6,
        arrowcolor=MUTED,
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", PRIMARY)],
        fieldbackground=[("readonly", SURFACE)],
        selectbackground=[("readonly", SURFACE)],
        selectforeground=[("readonly", TEXT)],
    )

    # 标签页
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(6, 6, 6, 0))
    style.configure(
        "TNotebook.Tab",
        background="#E2E8F0",
        foreground=TEXT,
        padding=(12, 4),
        font=(FONT_FAMILY, 9),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", SURFACE)],
        foreground=[("selected", PRIMARY)],
    )

    # 表格
    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        rowheight=28,
        borderwidth=0,
        font=(FONT_FAMILY, 9),
    )
    style.configure(
        "Treeview.Heading",
        background="#F8FAFC",
        foreground=TEXT,
        padding=6,
        relief="flat",
        font=(FONT_FAMILY, 9, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", "#EEF2F7")])

    # 进度条
    style.configure(
        "Horizontal.TProgressbar",
        background=SUCCESS,
        troughcolor="#E2E8F0",
        bordercolor="#E2E8F0",
        lightcolor=SUCCESS,
        darkcolor=SUCCESS,
        thickness=12,
    )

    # 滚动条：细窄、无箭头、现代扁平样式。
    # 设计原则：轨道颜色与所在区域背景一致（视觉上“隐形”），
    # 滑块颜色明显区别于轨道，悬停/按压时加深。
    _scrollbar_layout = [
        (
            "Vertical.Scrollbar.trough",
            {
                "sticky": "ns",
                "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "ns"}),
                ],
            },
        )
    ]
    _scrollbar_layout_h = [
        (
            "Horizontal.Scrollbar.trough",
            {
                "sticky": "ew",
                "children": [
                    ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "ew"}),
                ],
            },
        )
    ]

    # 默认滚动条：一整条可见滑轨 + 浅色滑块（用于白色背景的文本框/表格）
    style.configure(
        "Vertical.TScrollbar",
        background="#E2E8F0",  # 滑块（浅色）
        troughcolor="#94A3B8",  # 滑轨（深色，一整条可见）
        bordercolor="#94A3B8",
        lightcolor="#94A3B8",
        darkcolor="#94A3B8",
        arrowcolor="#94A3B8",
        relief="flat",
        borderwidth=0,
        width=12,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", "#FFFFFF"), ("pressed", "#CBD5E1")],
    )
    style.layout("Vertical.TScrollbar", _scrollbar_layout)

    # 页面背景滚动条：用于配置页画布（同样的可见滑轨设计）
    style.configure(
        "Page.Vertical.TScrollbar",
        background="#E2E8F0",
        troughcolor="#94A3B8",
        bordercolor="#94A3B8",
        lightcolor="#94A3B8",
        darkcolor="#94A3B8",
        arrowcolor="#94A3B8",
        relief="flat",
        borderwidth=0,
        width=12,
    )
    style.map(
        "Page.Vertical.TScrollbar",
        background=[("active", "#FFFFFF"), ("pressed", "#CBD5E1")],
    )
    style.layout("Page.Vertical.TScrollbar", _scrollbar_layout)

    style.configure(
        "Horizontal.TScrollbar",
        background="#E2E8F0",
        troughcolor="#94A3B8",
        bordercolor="#94A3B8",
        lightcolor="#94A3B8",
        darkcolor="#94A3B8",
        arrowcolor="#94A3B8",
        relief="flat",
        borderwidth=0,
        height=12,
    )
    style.map(
        "Horizontal.TScrollbar",
        background=[("active", "#FFFFFF"), ("pressed", "#CBD5E1")],
    )
    style.layout("Horizontal.TScrollbar", _scrollbar_layout_h)

    # 深色页面（运行日志）滚动条：深色滑轨 + 浅色滑块
    style.configure(
        "Dark.Vertical.TScrollbar",
        background="#E2E8F0",
        troughcolor="#334155",
        bordercolor="#334155",
        lightcolor="#334155",
        darkcolor="#334155",
        arrowcolor="#334155",
        relief="flat",
        borderwidth=0,
        width=12,
    )
    style.map(
        "Dark.Vertical.TScrollbar",
        background=[("active", "#FFFFFF"), ("pressed", "#CBD5E1")],
    )
    style.layout("Dark.Vertical.TScrollbar", _scrollbar_layout)


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
