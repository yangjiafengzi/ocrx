# -- coding: utf-8 --
"""向导外壳与主视图组件测试（撤回窗口，文件对话框用 monkeypatch）。"""

import time
import tkinter as tk

import pytest

from ocrx.config import ConfigManager
from ocrx.gui.controllers.prompt_controller import PromptController
from ocrx.gui.session_state import SessionState
from ocrx.gui.theme_tokens import COLORS
from ocrx.gui.views.config_step import ConfigStep
from ocrx.gui.views.files_step import FilesStep
from ocrx.gui.views.prompt_step import PromptStep
from ocrx.gui.views.run_step import RunStep
from ocrx.gui.views.wizard_nav import WizardNav
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


@pytest.fixture
def tk_root():
    root = None
    last_error = None
    for _ in range(3):
        try:
            root = tk.Tk()
            break
        except tk.TclError as exc:
            last_error = exc
            time.sleep(0.2)
    if root is None:
        pytest.skip(f"当前环境无可用 Tcl/Tk 显示：{last_error}")
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def test_wizard_nav_selects_steps(tk_root):
    seen = []
    nav = WizardNav(tk_root, ["配置", "文件", "提示词", "执行"], on_change=seen.append)
    nav.set_current(1)
    assert seen[-1] == 1


def test_wizard_nav_initial_highlight_without_on_change(tk_root):
    seen = []
    nav = WizardNav(tk_root, ["配置", "文件", "提示词", "执行"], on_change=seen.append)
    assert seen == []
    assert nav.current == 0
    assert str(nav.buttons[0].cget("fg_color")) == COLORS["primary"]
    assert str(nav.buttons[1].cget("fg_color")) == COLORS["border"]
    assert str(nav.buttons[0].cget("text_color")) == "#FFFFFF"
    assert str(nav.buttons[3].cget("text_color")) == COLORS["text"]


def test_wizard_nav_set_current_still_paints_and_notifies(tk_root):
    seen = []
    nav = WizardNav(tk_root, ["配置", "文件", "提示词", "执行"], on_change=seen.append)
    nav.set_current(2)
    assert seen == [2]
    assert str(nav.buttons[2].cget("fg_color")) == COLORS["primary"]
    assert str(nav.buttons[0].cget("fg_color")) == COLORS["border"]


def test_files_step_collect(tk_root, monkeypatch):
    state = SessionState()
    step = FilesStep()
    step.build(tk_root)
    monkeypatch.setattr(step, "pick_files", lambda: ["a.png"])
    step.add_files()
    step.collect(state)
    assert state.file_paths == ["a.png"]


def test_config_step_fields_cover_required_keys(tk_root):
    step = ConfigStep()
    step.build(tk_root)
    assert set(step.fields) == {
        "BASE_URL",
        "API_KEY",
        "MODEL_NAME",
        "OUTPUT_DIR",
        "MAX_WORKERS",
        "PDF_SCALE_FACTOR",
    }


def test_config_step_collect_writes_config_dict(tk_root, tmp_path):
    cfg = ConfigManager(str(tmp_path / "cfg.json"))
    cfg.load()
    state = SessionState()
    step = ConfigStep()
    step.build(tk_root)
    step.fields["BASE_URL"].insert(0, "https://api.example.com/v1")
    step.fields["API_KEY"].insert(0, "sk-test")
    step.fields["MODEL_NAME"].insert(0, "gpt-4o")
    step.fields["OUTPUT_DIR"].insert(0, str(tmp_path / "out"))
    step.fields["MAX_WORKERS"].insert(0, "4")
    step.fields["PDF_SCALE_FACTOR"].insert(0, "2.5")
    step.collect(state, cfg)
    assert cfg.config["BASE_URL"] == "https://api.example.com/v1"
    assert cfg.config["API_KEY"] == "sk-test"
    assert cfg.config["MODEL_NAME"] == "gpt-4o"
    assert cfg.config["OUTPUT_DIR"] == str(tmp_path / "out")
    assert cfg.config["MAX_WORKERS"] == "4"
    assert cfg.config["PDF_SCALE_FACTOR"] == "2.5"
    assert state.output_dir == str(tmp_path / "out")


def test_config_step_load_state_fills_fields(tk_root, tmp_path):
    cfg = ConfigManager(str(tmp_path / "cfg.json"))
    cfg.load()
    cfg.config["BASE_URL"] = "https://api.example.com/v1"
    cfg.config["API_KEY"] = "sk-test"
    cfg.config["MODEL_NAME"] = "gpt-4o"
    cfg.config["OUTPUT_DIR"] = "D:/out"
    cfg.config["MAX_WORKERS"] = "4"
    cfg.config["PDF_SCALE_FACTOR"] = "2.5"
    state = SessionState()
    step = ConfigStep()
    step.build(tk_root)
    step.load_state(state, cfg)
    assert step.fields["BASE_URL"].get() == "https://api.example.com/v1"
    assert step.fields["API_KEY"].get() == "sk-test"
    assert step.fields["MODEL_NAME"].get() == "gpt-4o"
    assert step.fields["OUTPUT_DIR"].get() == "D:/out"
    assert step.fields["MAX_WORKERS"].get() == "4"
    assert step.fields["PDF_SCALE_FACTOR"].get() == "2.5"


def test_files_step_load_state_and_collect_roundtrip(tk_root):
    state = SessionState(file_paths=["a.png", "b.pdf"], page_range="1,3")
    step = FilesStep()
    step.build(tk_root)
    step.load_state(state, None)
    assert step._paths == ["a.png", "b.pdf"]
    out = SessionState()
    step.collect(out)
    assert out.file_paths == ["a.png", "b.pdf"]
    assert out.page_range == "1,3"


def test_files_step_add_files_deduplicates(tk_root, monkeypatch):
    step = FilesStep()
    step.build(tk_root)
    monkeypatch.setattr(step, "pick_files", lambda: ["a.png", "b.pdf"])
    step.add_files()
    monkeypatch.setattr(step, "pick_files", lambda: ["a.png", "c.png"])
    step.add_files()
    assert step._paths == ["a.png", "b.pdf", "c.png"]
    step.clear_files()
    assert step._paths == []


def test_files_step_listbox_read_only_collect_authoritative(tk_root, monkeypatch):
    state = SessionState()
    step = FilesStep()
    step.build(tk_root)
    assert str(step.listbox.cget("state")) == "disabled"
    monkeypatch.setattr(step, "pick_files", lambda: ["a.png"])
    step.add_files()
    # 只读文本框：直接写入被忽略，显示内容不变。
    step.listbox.insert("1.0", "hacked.txt")
    assert step.listbox.get("1.0", "end-1c") == "a.png"
    # 即使强行改写文本框，collect() 仍以内部 _paths 为准。
    step.listbox.configure(state="normal")
    step.listbox.delete("1.0", "end")
    step.listbox.insert("1.0", "hacked.txt")
    step.listbox.configure(state="disabled")
    step.collect(state)
    assert state.file_paths == ["a.png"]


def test_prompt_step_collect_and_load_state(tk_root):
    state = SessionState(prompt_text="识别手写内容")
    step = PromptStep()
    step.build(tk_root)
    step.load_state(state, None)
    out = SessionState()
    step.collect(out)
    assert out.prompt_text == "识别手写内容"


def test_prompt_step_few_shot_selection_collect_and_load_state(tk_root):
    state = SessionState(
        prompt_text="识别手写内容",
        selected_example_ids=["ex1", "ex3"],
    )
    step = PromptStep(examples=["ex1", "ex2", "ex3"])
    step.build(tk_root)
    step.load_state(state, None)
    assert step.get_selected_example_ids() == ["ex1", "ex3"]
    out = SessionState()
    step.collect(out)
    assert out.prompt_text == "识别手写内容"
    assert out.selected_example_ids == ["ex1", "ex3"]


def test_prompt_step_few_shot_widget_drives_selection(tk_root):
    step = PromptStep(examples=["ex1", "ex2"])
    step.build(tk_root)
    step.example_checks["ex2"].select()
    out = SessionState()
    step.collect(out)
    assert out.selected_example_ids == ["ex2"]
    step.example_checks["ex2"].deselect()
    step.example_checks["ex1"].select()
    out2 = SessionState()
    step.collect(out2)
    assert out2.selected_example_ids == ["ex1"]


def test_prompt_step_few_shot_without_library_uses_simple_list(tk_root):
    step = PromptStep()
    step.build(tk_root)
    step.set_examples(["a", "b", "c"])
    assert set(step.example_checks) == {"a", "b", "c"}
    step.set_selected_example_ids(["a", "c"])
    out = SessionState()
    step.collect(out)
    assert out.selected_example_ids == ["a", "c"]
    # 未展示的 id 也保留，load_state/collect 往返不丢数据。
    step2 = PromptStep()
    step2.build(tk_root)
    step2.load_state(SessionState(selected_example_ids=["x", "y"]), None)
    out2 = SessionState()
    step2.collect(out2)
    assert out2.selected_example_ids == ["x", "y"]


def test_prompt_step_accepts_example_library(tk_root, tmp_path):
    from ocrx.example_library import Example, ExampleLibrary

    lib = ExampleLibrary(str(tmp_path / "lib"))
    lib.examples.append(
        Example(id="ex1", image_path="x.png", text="t1", description="样例一")
    )
    step = PromptStep(examples=lib)
    step.build(tk_root)
    assert "ex1" in step.example_checks
    step.example_checks["ex1"].select()
    out = SessionState()
    step.collect(out)
    assert out.selected_example_ids == ["ex1"]


def test_prompt_step_uses_prompt_controller(tk_root):
    calls = []

    class FakeController:
        def save_new(self, name, text):
            calls.append(("save_new", name, text))
            return True

        def update(self, name, text):
            calls.append(("update", name, text))
            return False

        def delete(self, name):
            calls.append(("delete", name))
            return True

        def reset(self):
            calls.append(("reset",))

    step = PromptStep(prompt_controller=FakeController())
    step.build(tk_root)
    assert step.save_new("自定义", "内容") is True
    assert step.update("自定义", "新内容") is False
    assert step.delete("自定义") is True
    step.reset()
    assert step.save("自定义", "内容") is True  # update 未知名称 -> save_new
    assert calls == [
        ("save_new", "自定义", "内容"),
        ("update", "自定义", "新内容"),
        ("delete", "自定义"),
        ("reset",),
        ("update", "自定义", "内容"),
        ("save_new", "自定义", "内容"),
    ]


def test_prompt_step_crud_refreshes_combo_and_textbox(tk_root, tmp_path):
    cfg = ConfigManager(str(tmp_path / "cfg.json"))
    cfg.load()
    step = PromptStep(prompt_controller=PromptController(cfg))
    step.build(tk_root)
    step.load_state(SessionState(), cfg)
    defaults = list(DEFAULT_PROMPT_TEMPLATES.keys())
    assert list(step.preset.cget("values")) == defaults

    # save_new：下拉出现新名称，正文与配置一致。
    assert step.save_new("自定义", "新内容") is True
    values = list(step.preset.cget("values"))
    assert "自定义" in values
    assert step.preset.get() == "自定义"
    assert step.textbox.get("1.0", "end-1c") == "新内容"

    # delete：下拉移除该名称，正文回到剩余预设。
    assert step.delete("自定义") is True
    values = list(step.preset.cget("values"))
    assert "自定义" not in values
    assert step.preset.get() == defaults[0]
    assert step.textbox.get("1.0", "end-1c") == DEFAULT_PROMPT_TEMPLATES[defaults[0]]

    # reset：下拉与正文回到默认模板。
    assert step.save_new("临时", "临时内容") is True
    step.reset()
    values = list(step.preset.cget("values"))
    assert "临时" not in values
    assert values == defaults
    assert step.textbox.get("1.0", "end-1c") == DEFAULT_PROMPT_TEMPLATES[step.preset.get()]


def test_run_step_set_running_toggles_buttons(tk_root):
    step = RunStep()
    step.build(tk_root)
    step.set_running(True)
    assert str(step.save_btn.cget("state")) == "disabled"
    assert str(step.copy_btn.cget("state")) == "disabled"
    assert str(step.stop_btn.cget("state")) == "normal"
    step.set_running(False)
    assert str(step.save_btn.cget("state")) == "normal"
    assert str(step.copy_btn.cget("state")) == "normal"
    assert str(step.stop_btn.cget("state")) == "disabled"


def test_run_step_set_progress_and_result(tk_root):
    step = RunStep()
    step.build(tk_root)
    step.set_progress(1, 4, 25.0, "ocr")
    assert "1/4" in step.status.cget("text")
    step.set_result("x" * 6000)
    assert len(step.result.get("1.0", "end-1c")) == 5000


def test_run_step_callbacks(tk_root):
    step = RunStep()
    step.build(tk_root)
    seen = []
    step.set_on_save(lambda: seen.append("save"))
    step.set_on_copy(lambda: seen.append("copy"))
    step.set_on_stop(lambda: seen.append("stop"))
    step.save_btn.invoke()
    step.copy_btn.invoke()
    step.stop_btn.invoke()
    assert seen == ["save", "copy", "stop"]
