# -- coding: utf-8 --
"""
处理器基类
提供通用的功能和接口
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import threading


class BaseHandler:
    """处理器基类"""

    def __init__(self, main_window):
        """
        初始化处理器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.root = main_window.root
        self.logger = main_window.logger
        self.clipboard_history = main_window.clipboard_history
        self.processing_service = main_window.processing_service
        
        # 常量配置
        self.DISPLAY_MAX_LENGTH = main_window.DISPLAY_MAX_LENGTH
        self.COPY_MAX_PAGES = main_window.COPY_MAX_PAGES

    def _update_status(self, status: str):
        """更新状态"""
        if hasattr(self.main_window, '_on_status_update'):
            self.main_window._on_status_update(status)

    def _update_progress(self, current: int, total: int, phase: str = ""):
        """更新进度"""
        if hasattr(self.main_window, '_on_progress_update'):
            self.main_window._on_progress_update(current, total, phase)

    def _display_result(self, content: str):
        """显示结果到常驻页面"""
        if hasattr(self.main_window, '_display_result'):
            self.main_window._display_result(content)

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """
        显示消息对话框

        Args:
            title: 标题
            message: 消息内容
            msg_type: 消息类型 (info/warning/error)
        """
        def show():
            if msg_type == "info":
                messagebox.showinfo(title, message)
            elif msg_type == "warning":
                messagebox.showwarning(title, message)
            elif msg_type == "error":
                messagebox.showerror(title, message)
        
        self.root.after(0, show)

    def run_in_thread(self, target, args=(), daemon=True):
        """
        在后台线程中运行函数

        Args:
            target: 目标函数
            args: 参数元组
            daemon: 是否为守护线程

        Returns:
            Thread 实例
        """
        thread = threading.Thread(target=target, args=args, daemon=daemon)
        thread.start()
        return thread
