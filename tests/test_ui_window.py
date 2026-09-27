# -- coding: utf-8 --
"""真实 UI 窗口冒烟测试（需要可用的桌面环境，否则自动跳过）。

旧 notebook 主题/滚动条回归用例已随 ttk 旧界面一并移除；
滚动条工具覆盖见 tests/test_gui_more.py，外壳行为见
tests/test_main_window_shell.py。
"""

import time

import pytest

from ocrx.gui.app_context import AppContext
from ocrx.gui.main_window import MainWindow


@pytest.fixture
def ui_app(tmp_path):
    tkinter = pytest.importorskip("tkinter")
    root = None
    last_error = None
    for _ in range(3):
        try:
            root = tkinter.Tk()
            break
        except tkinter.TclError as e:
            last_error = e
            time.sleep(0.5)
    if root is None:
        pytest.skip(f"当前环境无可用 Tcl/Tk 显示：{last_error}")
    root.withdraw()
    ctx = AppContext(
        config_path=str(tmp_path / "ui_config.json"),
        example_path=str(tmp_path / "example_library"),
        log_path=str(tmp_path / "ui.log"),
    )
    app = MainWindow(root, context=ctx)
    root.update_idletasks()
    root.update()
    yield app
    try:
        app.on_closing()
    except Exception:
        try:
            root.destroy()
        except Exception:
            pass


def test_window_title(ui_app):
    assert "OCRX" in ui_app.root.title()
    assert ui_app.root.winfo_width() >= 900
    assert ui_app.root.winfo_height() >= 680


def test_wizard_shell_built(ui_app):
    assert ui_app.wizard is not None
    assert ui_app.current_step == 0
    assert [btn.cget("text") for btn in ui_app.wizard.buttons] == [
        "1. 配置",
        "2. 文件",
        "3. 提示词",
        "4. 执行",
    ]
    assert ui_app.container is not None


def test_run_step_action_buttons(ui_app):
    texts = [
        str(ui_app.run_step.save_btn.cget("text")),
        str(ui_app.run_step.copy_btn.cget("text")),
        str(ui_app.run_step.stop_btn.cget("text")),
    ]
    assert texts == ["识别并保存", "识别并复制", "停止"]
    assert str(ui_app.run_step.save_btn.cget("state")) == "normal"
    assert str(ui_app.run_step.stop_btn.cget("state")) == "disabled"


def test_secondary_surfaces_present(ui_app):
    assert ui_app.secondary is not None
    for title in ("示例库", "剪贴板", "运行日志"):
        assert ui_app.secondary.tab(title) is not None
    assert ui_app.examples_view.manager is not None
    assert ui_app.clipboard_view.tree is not None
    assert ui_app.logs_view.textbox is not None


def test_config_fields_present(ui_app):
    assert set(ui_app.config_step.fields) == {
        "BASE_URL",
        "API_KEY",
        "MODEL_NAME",
        "OUTPUT_DIR",
        "MAX_WORKERS",
        "PDF_SCALE_FACTOR",
    }


def test_save_config_silent_on_close(ui_app, tmp_path):
    """回归测试：关闭窗口时保存配置不弹对话框，且写出配置文件。"""
    ui_app.config_step.fields["MODEL_NAME"].delete(0, "end")
    ui_app.config_step.fields["MODEL_NAME"].insert(0, "smoke-model")
    ui_app.on_closing()
    assert "smoke-model" in (tmp_path / "ui_config.json").read_text(encoding="utf-8")
