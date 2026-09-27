# -- coding: utf-8 --
"""
进度显示处理器
管理进度条和进度信息显示
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from .base_handler import BaseHandler


class ProgressHandler(BaseHandler):
    """进度显示处理器"""

    def __init__(self, main_window):
        """初始化处理器"""
        super().__init__(main_window)
        self.progress_var: Optional[tk.StringVar] = None
        self.progress_label: Optional[ttk.Label] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.current_task_label: Optional[ttk.Label] = None
        self.detail_progress_var: Optional[tk.StringVar] = None
        self.detail_progress_label: Optional[ttk.Label] = None

    def create_widgets(self, parent, row: int):
        """
        创建进度条区域

        Args:
            parent: 父容器
            row: 行位置
        """
        progress_frame = ttk.LabelFrame(parent, text="整体进度")
        progress_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)

        # 当前阶段
        ttk.Label(progress_frame, text="当前阶段:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.current_task_label = ttk.Label(progress_frame, text="等待开始...", foreground="gray")
        self.current_task_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # 整体进度
        ttk.Label(progress_frame, text="整体进度:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.progress_var = tk.StringVar(value="0%")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var, foreground="blue")
        self.progress_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.progress_bar['value'] = 0

        # 详细信息
        ttk.Label(progress_frame, text="详细信息:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.detail_progress_var = tk.StringVar(value="等待开始...")
        self.detail_progress_label = ttk.Label(progress_frame, textvariable=self.detail_progress_var, foreground="gray")
        self.detail_progress_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)

    def update_progress(self, current: int, total: int, percent: float, phase: str):
        """
        更新进度显示

        Args:
            current: 当前进度
            total: 总进度
            percent: 百分比
            phase: 当前阶段
        """
        if self.progress_var:
            self.progress_var.set(f"{percent:.1f}% ({current}/{total})")
        if self.current_task_label:
            self.current_task_label.config(text=f"{phase}: {current}/{total}")
        if self.progress_bar:
            self.progress_bar['value'] = percent
        if self.detail_progress_var:
            self.detail_progress_var.set(f"{phase}: {current}/{total}")

    def update_status(self, status: str):
        """
        更新状态显示

        Args:
            status: 状态文本
        """
        if self.current_task_label:
            self.current_task_label.config(text=status)
        if self.detail_progress_var:
            self.detail_progress_var.set(status)

    def reset(self):
        """重置进度显示"""
        if self.progress_var:
            self.progress_var.set("0%")
        if self.current_task_label:
            self.current_task_label.config(text="等待开始...")
        if self.progress_bar:
            self.progress_bar['value'] = 0
        if self.detail_progress_var:
            self.detail_progress_var.set("等待开始...")
