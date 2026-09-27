# -- coding: utf-8 --
"""
结果展示功能处理器
处理识别结果的显示和操作
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from .base_handler import BaseHandler


class ResultHandler(BaseHandler):
    """结果展示功能处理器"""

    def __init__(self, main_window):
        """初始化处理器"""
        super().__init__(main_window)
        self.text_widget = None

    def create_widgets(self, parent):
        """
        创建识别结果页面组件

        Args:
            parent: 父容器
        """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
        # 创建文本框显示识别结果
        self.text_widget = scrolledtext.ScrolledText(
            parent, 
            wrap=tk.WORD,
            font=("Consolas", 11),
            padx=10,
            pady=10
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # 添加按钮
        ttk.Button(
            button_frame, 
            text="📋 复制全部", 
            command=self.copy_all
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="📄 复制选中项", 
            command=self.copy_selection
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="💾 保存到文件", 
            command=self.save_to_file
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="🗑️ 清空", 
            command=self.clear
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="🔄 刷新", 
            command=self.refresh
        ).pack(side=tk.LEFT, padx=5)
        
        # 初始提示
        self._set_initial_text()
        
        # 添加右键菜单
        self._create_context_menu()

    def _set_initial_text(self):
        """设置初始提示文本"""
        initial_text = (
            "识别结果将显示在这里...\n\n"
            "使用说明：\n"
            "1. 点击'识别并保存'或'识别并复制'按钮进行识别\n"
            "2. 识别结果会自动显示在此页面\n"
            "3. 可以手动复制或保存结果"
        )
        self.text_widget.insert(1.0, initial_text)
        self.text_widget.config(state=tk.DISABLED)

    def display(self, content: str):
        """
        显示内容到结果页面

        Args:
            content: 要显示的内容
        """
        def update():
            try:
                # 启用编辑
                self.text_widget.config(state=tk.NORMAL)
                # 清空并插入新内容
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(1.0, content)
                self.logger.info("识别结果已显示到结果页面")
            except Exception as e:
                self.logger.error(f"显示结果失败: {e}")
        
        # 在主线程中执行
        self.root.after(0, update)

    def copy_all(self):
        """复制全部内容到剪贴板"""
        content = self.text_widget.get(1.0, tk.END)
        if content.strip():
            if self.clipboard_history.copy_to_clipboard(content):
                messagebox.showinfo("成功", "已复制到剪贴板！")
            else:
                messagebox.showwarning("失败", "复制失败，请手动复制")
        else:
            messagebox.showwarning("提示", "没有内容可复制")

    def copy_selection(self):
        """复制选中的文本到剪贴板"""
        try:
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected.strip():
                if self.clipboard_history.copy_to_clipboard(selected):
                    messagebox.showinfo("成功", "选中内容已复制到剪贴板！")
                else:
                    messagebox.showwarning("失败", "复制失败")
            else:
                messagebox.showwarning("提示", "选中的内容为空")
        except tk.TclError:
            messagebox.showwarning("提示", "请先选择要复制的内容")

    def save_to_file(self):
        """保存内容到文件"""
        content = self.text_widget.get(1.0, tk.END)
        if content.strip():
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[
                    ("Markdown 文件", "*.md"), 
                    ("文本文件", "*.txt"), 
                    ("所有文件", "*.*")
                ],
                initialfile="ocr_result.md"
            )
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    messagebox.showinfo("成功", f"已保存到：{file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存失败：{e}")
        else:
            messagebox.showwarning("提示", "没有内容可保存")

    def clear(self):
        """清空内容"""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self._set_initial_text()

    def refresh(self):
        """刷新显示（重新加载当前内容）"""
        # 获取当前内容
        content = self.text_widget.get(1.0, tk.END)
        
        # 如果内容为空或者是初始提示，显示提示
        if not content.strip() or "识别结果将显示在这里" in content:
            self.clear()
            messagebox.showinfo("提示", "暂无识别结果，请先进行识别操作")
        else:
            # 重新显示当前内容（刷新界面）
            self.text_widget.config(state=tk.NORMAL)
            current_content = self.text_widget.get(1.0, tk.END)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, current_content)
            self.text_widget.see(1.0)  # 滚动到顶部
            messagebox.showinfo("成功", "界面已刷新")

    def _create_context_menu(self):
        """创建右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="复制", command=self._context_copy)
        context_menu.add_command(label="全选", command=self._context_select_all)
        context_menu.add_separator()
        context_menu.add_command(label="复制全部", command=self.copy_all)
        
        # 绑定右键点击事件
        def show_menu(event):
            context_menu.post(event.x_root, event.y_root)
        
        self.text_widget.bind('<Button-3>', show_menu)
        
        # 点击左键时隐藏菜单
        def hide_menu(event):
            context_menu.unpost()
        
        self.text_widget.bind('<Button-1>', hide_menu)

    def _context_copy(self):
        """右键菜单 - 复制选中"""
        try:
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                self.clipboard_history.copy_to_clipboard(selected)
        except tk.TclError:
            pass

    def _context_select_all(self):
        """右键菜单 - 全选"""
        self.text_widget.tag_add(tk.SEL, 1.0, tk.END)
        self.text_widget.mark_set(tk.INSERT, 1.0)
        self.text_widget.see(tk.INSERT)
        self.text_widget.focus_set()
