# -- coding: utf-8 --
"""
OCRX 智能文字识别 - 程序入口
开发时直接运行此文件进行调试
"""

import sys
from pathlib import Path

# 确保可以导入当前目录的模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入重构后的模块
from ocrx.gui.main_window import MainWindow


def main():
    """程序主函数"""
    import tkinter as tk

    root = tk.Tk()
    app = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
