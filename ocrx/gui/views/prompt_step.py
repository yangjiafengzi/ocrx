# -- coding: utf-8 --
"""向导第 3 步：提示词预设编辑。"""

from tkinter import simpledialog

import customtkinter as ctk


class PromptStep:
    """提示词预设下拉 + 正文编辑框。

    预设的增删改走 :class:`PromptController`（构造时可选传入），
    视图自身不读写配置文件。
    """

    def __init__(self, prompt_controller=None):
        self.prompt_controller = prompt_controller
        self.frame = None
        self.preset = None
        self.textbox = None
        self.status = None

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        top = ctk.CTkFrame(self.frame)
        top.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(top, text="预设").pack(side="left", padx=4)
        self.preset = ctk.CTkComboBox(top, values=[""], width=180, state="readonly")
        self.preset.pack(side="left", padx=4)
        ctk.CTkButton(top, text="保存", width=64, command=self._on_save).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="另存为", width=64, command=self._on_save_new).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="删除", width=64, command=self._on_delete).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="重置", width=64, command=self.reset).pack(
            side="left", padx=4
        )
        self.textbox = ctk.CTkTextbox(self.frame, height=220)
        self.textbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.status = ctk.CTkLabel(self.frame, text="")
        self.status.pack(anchor="w", padx=8, pady=(0, 6))
        return self.frame

    # ---- PromptController 委托（可选）----

    def save(self, name: str, text: str) -> bool:
        """保存到已存在的预设；名称不存在时转新建。"""
        if self.prompt_controller is None:
            return False
        if self.update(name, text):
            return True
        return self.save_new(name, text)

    def save_new(self, name: str, text: str) -> bool:
        if self.prompt_controller is None:
            return False
        return bool(self.prompt_controller.save_new(name, text))

    def update(self, name: str, text: str) -> bool:
        if self.prompt_controller is None:
            return False
        return bool(self.prompt_controller.update(name, text))

    def delete(self, name: str) -> bool:
        if self.prompt_controller is None:
            return False
        return bool(self.prompt_controller.delete(name))

    def reset(self) -> None:
        if self.prompt_controller is None:
            return
        self.prompt_controller.reset()

    # ---- 控件事件 ----

    def _current_text(self) -> str:
        return self.textbox.get("1.0", "end-1c")

    def _on_save(self):
        name = self.preset.get().strip()
        ok = self.save(name, self._current_text())
        self.status.configure(text="已保存" if ok else "保存失败")

    def _on_save_new(self):
        name = simpledialog.askstring("另存为", "请输入新的提示词预设名称:")
        if not name:
            return
        ok = self.save_new(name.strip(), self._current_text())
        self.status.configure(text="已保存" if ok else "保存失败")

    def _on_delete(self):
        name = self.preset.get().strip()
        ok = self.delete(name)
        self.status.configure(text="已删除" if ok else "删除失败")

    # ---- 状态同步 ----

    def load_state(self, state, config) -> None:
        names: list[str] = []
        if config is not None:
            templates = config.get_prompt_templates()
            names = list(templates.keys())
        if self.preset is not None:
            self.preset.configure(values=names or [""])
            if names:
                self.preset.set(names[0])
        text = ""
        if state is not None and getattr(state, "prompt_text", ""):
            text = state.prompt_text
        elif config is not None and names:
            text = config.get_prompt_template(self.preset.get())
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

    def collect(self, state, config=None) -> None:
        if state is not None:
            state.prompt_text = self._current_text()
