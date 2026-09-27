# -- coding: utf-8 --
"""运行日志次级视图。"""

import customtkinter as ctk


MAX_LOG_LINES = 2000


class LogsView:
    """追加式日志文本框；只渲染，不写日志文件。"""

    def __init__(self):
        self.frame = None
        self.textbox = None
        self.vbar = None

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.frame.pack(fill="both", expand=True)
        bar = ctk.CTkFrame(self.frame)
        bar.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(bar, text="清空", width=70, command=self.clear).pack(
            side="left", padx=4
        )
        body = ctk.CTkFrame(self.frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(body, height=100)
        self.textbox.grid(row=0, column=0, sticky="nsew")
        # 常显纵向滚动条：内容溢出时可拖，不依赖悬停
        self.vbar = ctk.CTkScrollbar(body, command=self.textbox.yview)
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.textbox.configure(yscrollcommand=self.vbar.set)
        return self.frame

    def append(self, entry) -> None:
        """追加一条日志（支持 StructuredLogger 的 dict 或纯字符串）。"""
        if self.textbox is None:
            return
        if isinstance(entry, dict):
            line = (
                f"{entry.get('timestamp', '')} - [{entry.get('level', '')}] "
                f"{entry.get('component', '')} - {entry.get('message', '')}\n"
            )
        else:
            line = f"{entry}\n"
        self.textbox.insert("end", line)
        self._trim()
        self.textbox.see("end")

    def clear(self) -> None:
        if self.textbox is not None:
            self.textbox.delete("1.0", "end")

    def _trim(self) -> None:
        """行数超限时丢弃头部，避免文本框无限膨胀。"""
        if self.textbox is None:
            return
        # CTkTextbox 未暴露 count()，取其底层 tk.Text 统计行数
        inner = getattr(self.textbox, "_textbox", self.textbox)
        counted = inner.count("1.0", "end-1c", "lines")
        line_count = int(counted[0]) if counted else 0
        if line_count > MAX_LOG_LINES:
            excess = line_count - MAX_LOG_LINES
            self.textbox.delete("1.0", f"{excess + 1}.0")
