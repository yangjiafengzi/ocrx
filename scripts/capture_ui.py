# -- coding: utf-8 -*-
"""
开发工具：启动 OCRX 主窗口并截取各标签页截图（需要完整 Tcl/Tk 的 Python）。

用法：
    python scripts/capture_ui.py <输出目录>
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

    from ocrx.config import ConfigManager
    from ocrx.example_library import ExampleLibrary
    from ocrx.gui import main_window as mw_mod
    from ocrx.logger import StructuredLogger

    sample = td / "sample.png"
    Image.new("RGB", (220, 140), (90, 140, 220)).save(sample, "PNG")

    root = tk.Tk()
    cfg = ConfigManager(str(td / "cfg.json"))
    cfg.load()

    class TestLogger(StructuredLogger):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("log_file_path", str(td / "ui.log"))
            super().__init__(*args, **kwargs)

    mw_mod.ConfigManager = lambda: cfg
    mw_mod.StructuredLogger = TestLogger
    mw_mod.ExampleLibrary = lambda: ExampleLibrary(str(td / "lib"))

    geometry = sys.argv[2] if len(sys.argv) > 2 else "1200x900"
    scroll_units = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    app = mw_mod.MainWindow(root)
    root.geometry(geometry)
    if int(geometry.split("x")[1]) < 700:
        root.minsize(400, 300)

    # 填充示例数据，让截图更真实
    app.base_url_entry.insert(0, "https://api.example.com/v1")
    app.api_key_entry.insert(0, "sk-demo-xxxxxxxx")
    app.model_name_entry.insert(0, "gpt-4o")
    app.file_paths_entry.insert(0, "C:\\docs\\扫描件.pdf;C:\\docs\\笔记.png")
    app.output_dir_entry.insert(0, str(td / "output"))
    for i in range(30):
        app.example_library.add_example(
            str(sample), f"示例 {i} 的识别文本内容，用于展示列表滚动效果。", f"标签 {i}"
        )
    result_lines = ["# 识别结果示例", ""]
    for i in range(60):
        result_lines.append(f"第 {i} 段内容：这是一段由 AI 识别出的 Markdown 文本，用于展示结果区滚动效果。")
    app._display_result("\n".join(result_lines))
    app.logger.info("应用程序启动", "System")
    app.logger.info("处理服务初始化完成", "System")
    for i in range(40):
        app.logger.info(f"日志行 {i}：模拟运行日志内容，用于展示日志区滚动效果。", "System")
    for i in range(15):
        app.clipboard_history.add_record(f"剪贴板历史记录 {i} 的内容预览", success=True, method="tkinter")
    root.update_idletasks()
    root.update()

    hwnd = root.winfo_id()

    def snap(name, tab):
        app.notebook.select(tab)
        root.update_idletasks()
        root.update()
        for _ in range(scroll_units):
            app.config_canvas.yview_scroll(1, "units")
        root.update_idletasks()
        root.update()
        ImageGrab.grab(window=hwnd).save(outdir / name)
        print(name, "saved")

    snap("ui_main.png", 0)
    snap("ui_examples.png", 1)
    snap("ui_log.png", 2)
    snap("ui_result.png", 4)

    app.logger.close()
    root.destroy()


if __name__ == "__main__":
    main()
