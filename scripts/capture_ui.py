# -- coding: utf-8 --
"""
开发工具：启动 OCRX 主窗口并截取各向导步骤/次级标签截图（需要完整 Tcl/Tk 的 Python）。

用法：
    python scripts/capture_ui.py <输出目录> [窗口几何] [滚动步数]

滚动步数仅作用于执行步的结果预览区（旧行为是已废弃的 config_canvas）。
"""

import os
import sys
import tempfile
from pathlib import Path

import tkinter as tk

from PIL import Image, ImageGrab

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main():
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)

    # 隔离用户目录，避免写入真实配置
    td = Path(tempfile.mkdtemp(prefix="ocrx_capture_"))
    os.environ["USERPROFILE"] = str(td)

    from ocrx.gui.app_context import AppContext
    from ocrx.gui.main_window import MainWindow

    sample = td / "sample.png"
    Image.new("RGB", (220, 140), (90, 140, 220)).save(sample, "PNG")

    root = tk.Tk()
    ctx = AppContext(
        config_path=str(td / "cfg.json"),
        example_path=str(td / "lib"),
        log_path=str(td / "ui.log"),
        root=root,
    )
    app = MainWindow(root, context=ctx)
    geometry = sys.argv[2] if len(sys.argv) > 2 else "1200x900"
    root.geometry(geometry)

    # 填充示例数据，让截图更真实
    fields = app.config_step.fields
    fields["BASE_URL"].insert(0, "https://api.example.com/v1")
    fields["API_KEY"].insert(0, "sk-demo-xxxxxxxx")
    fields["MODEL_NAME"].insert(0, "gpt-4o")
    fields["OUTPUT_DIR"].insert(0, str(td / "output"))
    app.files_step._paths = [str(sample), "C:\\docs\\扫描件.pdf", "C:\\docs\\笔记.png"]
    app.files_step._refresh_listbox()
    app.prompt_step.textbox.insert("1.0", "请识别图片中的文字，按原排版输出。")
    for i in range(30):
        ctx.examples.add_example(
            str(sample), f"示例 {i} 的识别文本内容，用于展示列表滚动效果。", f"标签 {i}"
        )
    app.examples_view.refresh()
    result_lines = ["# 识别结果示例", ""]
    for i in range(60):
        result_lines.append(f"第 {i} 段内容：这是一段由 AI 识别出的 Markdown 文本，用于展示结果区滚动效果。")
    app.run_step.set_result("\n".join(result_lines))
    ctx.logger.info("应用程序启动", "System")
    ctx.logger.info("处理服务初始化完成", "System")
    for i in range(40):
        ctx.logger.info(f"日志行 {i}：模拟运行日志内容，用于展示日志区滚动效果。", "System")
    for i in range(15):
        ctx.clipboard.add_record(f"剪贴板历史记录 {i} 的内容预览", success=True, method="tkinter")
    app.clipboard_view.refresh()
    root.update_idletasks()
    root.update()

    hwnd = root.winfo_id()

    def snap(name):
        root.update_idletasks()
        root.update()
        ImageGrab.grab(window=hwnd).save(outdir / name)
        print(name, "saved")

    step_names = ["config", "files", "prompt", "run"]
    for index, name in enumerate(step_names):
        app.wizard.set_current(index)
        if name == "run":
            scroll_units = int(sys.argv[3]) if len(sys.argv) > 3 else 0
            for _ in range(scroll_units):
                app.run_step.result.yview_scroll(1, "units")
        snap(f"ui_step_{index + 1}_{name}.png")

    for tab, name in (("示例库", "examples"), ("剪贴板", "clipboard"), ("运行日志", "log")):
        app.secondary.set(tab)
        snap(f"ui_tab_{name}.png")

    app.on_closing()


if __name__ == "__main__":
    main()
