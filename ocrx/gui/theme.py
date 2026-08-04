# -- coding: utf-8 --
"""
OCRX 界面主题。
统一配置 ttk 样式：配色、字体、按钮、卡片分组、标签页、进度条等。
"""

import tkinter as tk
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
        padding=(16, 6),
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

    # 滚动条：细窄、无箭头、现代扁平样式
    style.configure(
        "Vertical.TScrollbar",
        background="#94A3B8",
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=BG,
        relief="flat",
        borderwidth=0,
        width=10,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", "#64748B"), ("pressed", "#475569")],
    )
    style.layout(
        "Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "ns"}),
                    ],
                },
            )
        ],
    )
    style.configure(
        "Horizontal.TScrollbar",
        background="#94A3B8",
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=BG,
        relief="flat",
        borderwidth=0,
        height=10,
    )
    style.map(
        "Horizontal.TScrollbar",
        background=[("active", "#64748B"), ("pressed", "#475569")],
    )
    style.layout(
        "Horizontal.TScrollbar",
        [
            (
                "Horizontal.Scrollbar.trough",
                {
                    "sticky": "ew",
                    "children": [
                        ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "ew"}),
                    ],
                },
            )
        ],
    )
