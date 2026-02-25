# -- coding: utf-8 --
"""
剪贴板功能处理器
处理剪贴板历史相关的操作
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from .base_handler import BaseHandler


class ClipboardHandler(BaseHandler):
    """剪贴板功能处理器"""

    def create_widgets(self, parent):
        """
        创建剪贴板历史页面组件

        Args:
            parent: 父容器
        """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # 控制按钮框架
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        ttk.Button(
            control_frame, 
            text="复制选中项", 
            command=self.copy_selected
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, 
            text="清空历史", 
            command=self.clear_history
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, 
            text="刷新", 
            command=self.refresh_history
        ).pack(side=tk.LEFT, padx=5)

        # 历史记录列表
        columns = ('时间', '长度', '状态', '方法', '预览')
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
        
        # 设置列标题和宽度
        self.tree.heading('时间', text='时间')
        self.tree.heading('长度', text='长度')
        self.tree.heading('状态', text='状态')
        self.tree.heading('方法', text='方法')
        self.tree.heading('预览', text='预览')
        
        self.tree.column('时间', width=150)
        self.tree.column('长度', width=80)
        self.tree.column('状态', width=80)
        self.tree.column('方法', width=100)
        self.tree.column('预览', width=400)

        self.tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 绑定双击事件
        self.tree.bind('<Double-1>', self.show_detail)

    def copy_selected(self):
        """复制选中的剪贴板历史项"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要复制的项")
            return

        # 获取选中项的索引
        item_id = selected[0]
        index = self.tree.index(item_id)
        
        # 获取完整内容
        content = self.clipboard_history.get_content_by_index(index)
        
        if not content:
            messagebox.showerror("错误", "无法获取选中项的内容")
            return
        
        try:
            if self.clipboard_history.copy_to_clipboard(content):
                messagebox.showinfo("成功", "已复制到剪贴板")
            else:
                messagebox.showerror("错误", "复制失败")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{e}")

    def clear_history(self):
        """清空剪贴板历史"""
        if messagebox.askyesno("确认", "确定要清空剪贴板历史吗？"):
            self.clipboard_history.clear_history()
            self.refresh_history()
            messagebox.showinfo("完成", "剪贴板历史已清空")

    def refresh_history(self):
        """刷新剪贴板历史显示"""
        # 清空现有项
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加历史记录
        for record in self.clipboard_history.get_history():
            self.tree.insert('', tk.END, values=(
                record['timestamp'],
                record['content_length'],
                '成功' if record['success'] else '失败',
                record['method'],
                record['content_preview']
            ))

    def show_detail(self, event):
        """显示剪贴板历史详细信息"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            if len(values) >= 5:
                detail_msg = (
                    f"时间: {values[0]}\n"
                    f"长度: {values[1]}\n"
                    f"状态: {values[2]}\n"
                    f"方法: {values[3]}\n"
                    f"预览: {values[4]}"
                )
                messagebox.showinfo("剪贴板历史详情", detail_msg)
