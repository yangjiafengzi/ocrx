# -- coding: utf-8 --
"""向导第 2 步：文件选择与页码范围。"""

from tkinter import filedialog

import customtkinter as ctk


class FilesStep:
    """多选 PDF/图片文件并设置页码范围。"""

    def __init__(self):
        self.frame = None
        self.listbox = None
        self.page_range = None
        self._paths: list[str] = []

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.listbox = ctk.CTkTextbox(self.frame, height=180)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.page_range = ctk.CTkEntry(
            self.frame, placeholder_text="页码范围，如 1,3,5-10"
        )
        self.page_range.pack(fill="x", padx=8, pady=4)
        btns = ctk.CTkFrame(self.frame)
        btns.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(btns, text="添加文件", command=self.add_files).pack(
            side="left", padx=4
        )
        ctk.CTkButton(btns, text="清空", command=self.clear_files).pack(
            side="left", padx=4
        )
        self._paths = []
        return self.frame

    def pick_files(self):
        return filedialog.askopenfilenames(
            filetypes=[
                ("支持的文件", "*.pdf *.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("所有文件", "*.*"),
            ]
        )

    def add_files(self):
        for path in self.pick_files() or []:
            if path not in self._paths:
                self._paths.append(path)
        self._refresh_listbox()

    def clear_files(self):
        self._paths.clear()
        self._refresh_listbox()

    def _refresh_listbox(self):
        self.listbox.delete("1.0", "end")
        self.listbox.insert("1.0", "\n".join(self._paths))

    def load_state(self, state, config) -> None:
        self._paths = list(state.file_paths)
        self.page_range.delete(0, "end")
        self.page_range.insert(0, state.page_range)
        self._refresh_listbox()

    def collect(self, state, config=None) -> None:
        state.file_paths = list(self._paths)
        state.page_range = self.page_range.get().strip()
