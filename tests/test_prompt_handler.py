# -- coding: utf-8 --
"""PromptHandler 关键流程测试（使用假控件，不创建真实窗口）。"""

from types import SimpleNamespace

import ocrx.gui.handlers.prompt_handler as ph_mod
from ocrx.clipboard import ClipboardHistory
from ocrx.config import ConfigManager
from ocrx.gui.handlers.prompt_handler import PromptHandler
from ocrx.logger import StructuredLogger
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeText:
    def __init__(self, content=""):
        self.content = content

    def get(self, *args):
        return self.content

    def delete(self, *args):
        self.content = ""

    def insert(self, index, content):
        self.content = content


class FakeCombobox:
    def __init__(self):
        self.data = {}
        self.values = []

    def __setitem__(self, key, value):
        self.data[key] = value
        if key == "values":
            self.values = list(value)

    def __getitem__(self, key):
        return self.data.get(key)


class FakeRoot:
    def after(self, *args):
        pass


def make_handler(tmp_path):
    mw = SimpleNamespace(
        is_running=False,
        root=FakeRoot(),
        logger=StructuredLogger(str(tmp_path / "log.txt")),
        clipboard_history=ClipboardHistory(),
        processing_service=None,
        DISPLAY_MAX_LENGTH=5000,
        COPY_MAX_PAGES=10,
        config_manager=ConfigManager(str(tmp_path / "cfg.json")),
    )
    mw.config_manager.load()
    handler = PromptHandler(mw)
    handler.set_templates(dict(DEFAULT_PROMPT_TEMPLATES))
    var = FakeVar("手写笔记")
    combo = FakeCombobox()
    text = FakeText(DEFAULT_PROMPT_TEMPLATES["手写笔记"])
    handler.set_widgets(var, combo, text)
    return mw, handler, var, combo, text


def test_edit_current_prompt_saves(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    monkeypatch.setattr(ph_mod.messagebox, "showinfo", lambda *a, **k: None)
    text.content = "修改后的提示词"
    handler.edit_current_prompt()
    assert handler.prompt_templates["手写笔记"] == "修改后的提示词"
    # 配置落盘
    mw.config_manager.load()
    assert mw.config_manager.get_prompt_template("手写笔记") == "修改后的提示词"


def test_edit_invalid_preset_warns(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    warnings = []
    monkeypatch.setattr(ph_mod.messagebox, "showwarning", lambda *a: warnings.append(a))
    var.set("不存在的预设")
    handler.edit_current_prompt()
    assert warnings


def test_save_new_template(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    monkeypatch.setattr(ph_mod.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(ph_mod.simpledialog, "askstring", lambda *a, **k: "新预设")
    text.content = "新预设内容"
    handler.save_new_prompt_template()
    assert handler.prompt_templates["新预设"] == "新预设内容"
    assert var.value == "新预设"
    assert "新预设" in combo.values


def test_rename_preserves_content(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    monkeypatch.setattr(ph_mod.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(ph_mod.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(ph_mod.simpledialog, "askstring", lambda *a, **k: "改名后")
    handler.rename_prompt_template()
    assert "手写笔记" not in handler.prompt_templates
    assert handler.prompt_templates["改名后"] == DEFAULT_PROMPT_TEMPLATES["手写笔记"]
    assert var.value == "改名后"


def test_delete_custom_template(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    monkeypatch.setattr(ph_mod.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(ph_mod.messagebox, "askyesno", lambda *a, **k: True)
    handler.prompt_templates["自定义"] = "内容"
    var.set("自定义")
    handler.delete_prompt_template()
    assert "自定义" not in handler.prompt_templates
    assert "手写笔记" in handler.prompt_templates


def test_delete_default_template_blocked(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    warnings = []
    monkeypatch.setattr(ph_mod.messagebox, "showwarning", lambda *a: warnings.append(a))
    var.set("手写笔记")
    handler.delete_prompt_template()
    assert warnings
    assert "手写笔记" in handler.prompt_templates


def test_reset_all_restores_defaults(tmp_path, monkeypatch):
    mw, handler, var, combo, text = make_handler(tmp_path)
    monkeypatch.setattr(ph_mod.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(ph_mod.messagebox, "askyesno", lambda *a, **k: True)
    handler.prompt_templates["自定义"] = "内容"
    handler.reset_all_presets()
    assert handler.prompt_templates == DEFAULT_PROMPT_TEMPLATES
    assert "自定义" not in handler.prompt_templates


def test_on_preset_selected_updates_text(tmp_path):
    mw, handler, var, combo, text = make_handler(tmp_path)
    var.set("印刷材料")
    handler.on_preset_selected()
    assert text.content == DEFAULT_PROMPT_TEMPLATES["印刷材料"]
