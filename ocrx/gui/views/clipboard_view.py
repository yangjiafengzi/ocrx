# -- coding: utf-8 --
"""剪贴板历史次级视图。

只渲染 :class:`ClipboardHistory` 并回传用户意图；
实际复制/清空动作由外壳（MainWindow）执行。
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


PREVIEW_MAX = 60


def _preview(text: str, limit: int = PREVIEW_MAX) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


class ClipboardView:
    """剪贴板历史列表 + 复制/清空/刷新意图回调。"""

    def __init__(self, clipboard=None):
        self.clipboard = clipboard
        self.frame = None
        self.tree = None
        self._on_copy: Optional[Callable[[str], None]] = None
        self._on_clear: Optional[Callable[[], None]] = None

    def build(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        bar = ttk.Frame(self.frame)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        ttk.Button(bar, text="复制选中项", command=self._emit_copy).pack(
            side="left", padx=2
        )
        ttk.Button(bar, text="清空历史", command=self._emit_clear).pack(
            side="left", padx=2
        )
        ttk.Button(bar, text="刷新", command=self.refresh).pack(side="left", padx=2)

        columns = ("时间", "长度", "状态", "预览")
        # height 仅为最小行数；<Configure> 里按像素高度放大，小窗口也不会只剩几行
        self.tree = ttk.Treeview(
            self.frame, columns=columns, show="headings", height=4
        )
        self.tree.heading("时间", text="时间")
        self.tree.heading("长度", text="长度")
        self.tree.heading("状态", text="状态")
        self.tree.heading("预览", text="预览")
        self.tree.column("时间", width=140, anchor="w")
        self.tree.column("长度", width=60, anchor="center")
        self.tree.column("状态", width=60, anchor="center")
        self.tree.column("预览", width=320, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(
            self.frame, orient="vertical", command=self.tree.yview
        )
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind(
            "<Configure>",
            lambda e, tv=self.tree: self._fit_rows(tv, e.height),
            add="+",
        )
        self.refresh()
        return self.frame

    @staticmethod
    def _fit_rows(tree, pixel_height: int) -> None:
        """按控件像素高度调整可见行数，保证填满面板。"""
        row_h = 22
        rows = max(3, int(pixel_height // row_h) - 1)
        try:
            tree.configure(height=rows)
        except tk.TclError:
            pass

    def refresh(self) -> None:
        """按当前历史记录重建表格。"""
        if self.tree is None:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        history = []
        if self.clipboard is not None:
            try:
                history = list(self.clipboard.get_history())
            except Exception:
                history = []
        for record in history:
            self.tree.insert(
                "",
                "end",
                values=(
                    record.get("timestamp", ""),
                    record.get("content_length", 0),
                    "成功" if record.get("success") else "失败",
                    _preview(record.get("content_preview") or record.get("content", "")),
                ),
            )

    def selected_content(self) -> Optional[str]:
        """返回选中记录的完整内容（按记录顺序的第一个）。"""
        if self.tree is None or self.clipboard is None:
            return None
        selection = self.tree.selection()
        if not selection:
            return None
        children = list(self.tree.get_children())
        try:
            index = children.index(selection[0])
        except ValueError:
            return None
        return self.clipboard.get_content_by_index(index)

    # ---- 回调（可选 setter）----

    @property
    def on_copy(self):
        return self._on_copy

    @on_copy.setter
    def on_copy(self, callback):
        self._on_copy = callback

    def set_on_copy(self, callback) -> None:
        self.on_copy = callback

    @property
    def on_clear(self):
        return self._on_clear

    @on_clear.setter
    def on_clear(self, callback):
        self._on_clear = callback

    def set_on_clear(self, callback) -> None:
        self.on_clear = callback

    def _emit_copy(self) -> None:
        if self._on_copy is not None:
            self._on_copy(self.selected_content())

    def _emit_clear(self) -> None:
        if self._on_clear is not None:
            self._on_clear()
