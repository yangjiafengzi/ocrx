# -- coding: utf-8 --
"""向导第 1 步：API 与处理参数配置。"""

import customtkinter as ctk


FIELD_LABELS = (
    ("BASE_URL", "Base URL"),
    ("API_KEY", "API Key"),
    ("MODEL_NAME", "Model Name"),
    ("OUTPUT_DIR", "输出目录"),
    ("MAX_WORKERS", "最大并发数"),
    ("PDF_SCALE_FACTOR", "PDF 缩放比例"),
)


class ConfigStep:
    """API/输出/并发等配置表单。"""

    def __init__(self):
        self.frame = None
        self.fields: dict[str, ctk.CTkEntry] = {}

    def build(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.fields = {}
        for key, label in FIELD_LABELS:
            row = ctk.CTkFrame(self.frame)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, show="*" if key == "API_KEY" else "")
            entry.pack(side="left", fill="x", expand=True, padx=4)
            self.fields[key] = entry
        return self.frame

    def load_state(self, state, config) -> None:
        if not self.fields:
            return
        data = getattr(config, "config", config) or {}
        for key, entry in self.fields.items():
            entry.delete(0, "end")
            entry.insert(0, str(data.get(key, "")))

    def collect(self, state, config=None) -> None:
        values = {key: entry.get().strip() for key, entry in self.fields.items()}
        if config is not None:
            data = getattr(config, "config", config)
            data.update(values)
        if state is not None:
            state.output_dir = values.get("OUTPUT_DIR", "")
