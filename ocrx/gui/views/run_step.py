# -- coding: utf-8 --
"""向导第 4 步：执行、进度与结果预览。"""

import customtkinter as ctk


MAX_RESULT_CHARS = 5000


class RunStep:
    """识别执行页：保存/复制/停止按钮 + 进度 + 结果。"""

    def __init__(self):
        self.frame = None
        self.actions = None
        self.save_btn = None
        self.copy_btn = None
        self.stop_btn = None
        self.progress = None
        self.status = None
        self.result = None
        self._on_save = None
        self._on_copy = None
        self._on_stop = None

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.actions = ctk.CTkFrame(self.frame)
        self.save_btn = ctk.CTkButton(
            self.actions, text="识别并保存", command=self._emit_save
        )
        self.copy_btn = ctk.CTkButton(
            self.actions, text="识别并复制", command=self._emit_copy
        )
        self.stop_btn = ctk.CTkButton(
            self.actions,
            text="停止",
            fg_color="#DC2626",
            command=self._emit_stop,
        )
        self.progress = ctk.CTkProgressBar(self.frame)
        self.status = ctk.CTkLabel(self.frame, text="就绪")
        self.result = ctk.CTkTextbox(self.frame, height=260)
        for w in (self.save_btn, self.copy_btn, self.stop_btn):
            w.pack(side="left", padx=4)
        self.actions.pack(fill="x", padx=8, pady=8)
        self.progress.pack(fill="x", padx=8, pady=4)
        self.status.pack(anchor="w", padx=8)
        self.result.pack(fill="both", expand=True, padx=8, pady=8)
        return self.frame

    # ---- 回调（可选 setter）----

    @property
    def on_save(self):
        return self._on_save

    @on_save.setter
    def on_save(self, callback):
        self._on_save = callback

    @property
    def on_copy(self):
        return self._on_copy

    @on_copy.setter
    def on_copy(self, callback):
        self._on_copy = callback

    @property
    def on_stop(self):
        return self._on_stop

    @on_stop.setter
    def on_stop(self, callback):
        self._on_stop = callback

    def set_on_save(self, callback) -> None:
        self.on_save = callback

    def set_on_copy(self, callback) -> None:
        self.on_copy = callback

    def set_on_stop(self, callback) -> None:
        self.on_stop = callback

    def _emit_save(self):
        if self._on_save is not None:
            self._on_save()

    def _emit_copy(self):
        if self._on_copy is not None:
            self._on_copy()

    def _emit_stop(self):
        if self._on_stop is not None:
            self._on_stop()

    # ---- 状态更新 ----

    def set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.save_btn.configure(state=state)
        self.copy_btn.configure(state=state)
        self.stop_btn.configure(state="normal" if running else "disabled")

    def set_progress(self, current, total, percent, phase) -> None:
        value = 0 if total <= 0 else current / total
        self.progress.set(value)
        self.status.configure(text=f"{phase} {current}/{total} ({percent:.0f}%)")

    def set_result(self, text: str) -> None:
        self.result.delete("1.0", "end")
        self.result.insert("1.0", (text or "")[:MAX_RESULT_CHARS])

    # ---- 状态同步 ----

    def load_state(self, state, config) -> None:
        if state is not None:
            self.set_result(getattr(state, "last_result", "") or "")

    def collect(self, state, config=None) -> None:
        return None
