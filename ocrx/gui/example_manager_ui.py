# -- coding: utf-8 --
"""
示例库管理界面
用于GUI中管理少样本提示的示例
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, List, Optional
from pathlib import Path

from ..example_library import ExampleLibrary, Example


class ExampleManagerUI:
    """示例库管理界面"""
    
    def __init__(self, parent: tk.Widget, example_library: ExampleLibrary):
        """
        初始化示例库管理界面
        
        Args:
            parent: 父容器
            example_library: 示例库实例
        """
        self.parent = parent
        self.library = example_library
        
        # 选中的示例ID列表
        self.selected_examples: List[str] = []
        
        # 回调函数
        self.on_selection_change: Optional[Callable[[List[str]], None]] = None
        
        # 创建界面
        self._create_ui()
        
        # 刷新列表
        self.refresh_list()
    
    def _create_ui(self):
        """创建界面组件"""
        # 主框架
        self.main_frame = ttk.LabelFrame(self.parent, text="少样本示例库", padding=5)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 工具栏
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="添加示例", command=self._on_add_example).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除选中", command=self._on_delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新列表", command=self.refresh_list).pack(side=tk.LEFT, padx=2)
        
        # 统计信息
        self.stats_label = ttk.Label(toolbar, text="共 0 个示例")
        self.stats_label.pack(side=tk.RIGHT, padx=5)
        
        # 列表面板
        list_frame = ttk.Frame(self.main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建Treeview
        columns = ('select', 'id', 'description', 'text_preview')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='none')
        
        # 定义列
        self.tree.heading('select', text='选择')
        self.tree.heading('id', text='ID')
        self.tree.heading('description', text='描述')
        self.tree.heading('text_preview', text='文本预览')
        
        self.tree.column('select', width=50, anchor='center')
        self.tree.column('id', width=100)
        self.tree.column('description', width=150)
        self.tree.column('text_preview', width=300)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定点击事件
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)
        
        # 底部提示
        hint_text = "提示：点击复选框选择要在识别时使用的示例（建议1-3个）"
        ttk.Label(self.main_frame, text=hint_text, foreground="gray", font=("微软雅黑", 8)).pack(anchor='w', pady=5)
    
    def _on_tree_click(self, event):
        """处理Treeview点击事件"""
        # 获取点击的区域
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        # 获取点击的列和行
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        
        if not item:
            return
        
        # 只有点击选择列才切换
        if column == '#1':  # select列
            # 从tags获取完整ID，values[1]是截断显示
            tags = self.tree.item(item, 'tags')
            ex_id = tags[0]  # tags第一个就是完整ID
            
            if ex_id in self.selected_examples:
                self.selected_examples.remove(ex_id)
            else:
                self.selected_examples.append(ex_id)
            
            # 刷新显示
            self._update_tree_item(item, ex_id in self.selected_examples)
            
            # 触发回调
            if self.on_selection_change:
                self.on_selection_change(self.selected_examples.copy())
    
    def _update_tree_item(self, item, is_selected):
        """更新Treeview行的显示"""
        values = list(self.tree.item(item, 'values'))
        values[0] = "☑" if is_selected else "☐"
        self.tree.item(item, values=values)
    
    def _on_add_example(self):
        """添加示例按钮回调"""
        # 选择图片文件
        file_path = filedialog.askopenfilename(
            title="选择示例图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 输入正确文本
        dialog = tk.Toplevel(self.parent)
        dialog.title("输入示例文本")
        dialog.geometry("500x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="该图片的正确识别结果：").pack(pady=5)
        
        text_widget = tk.Text(dialog, wrap=tk.WORD, width=50, height=8)
        text_widget.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        ttk.Label(dialog, text="描述/标签（可选）：").pack(pady=5)
        desc_entry = ttk.Entry(dialog, width=50)
        desc_entry.pack(padx=10, pady=5)
        
        def on_ok():
            text = text_widget.get(1.0, tk.END).strip()
            if not text:
                messagebox.showwarning("提示", "请输入正确文本", parent=dialog)
                return
            
            description = desc_entry.get().strip()
            
            # 添加到库
            example = self.library.add_example(file_path, text, description)
            
            if example:
                messagebox.showinfo("成功", f"示例添加成功！\nID: {example.id}", parent=self.parent)
                self.refresh_list()
            else:
                messagebox.showerror("错误", "添加示例失败", parent=self.parent)
            
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def _on_delete_selected(self):
        """删除选中示例"""
        if not self.selected_examples:
            messagebox.showinfo("提示", "请先选择要删除的示例")
            return
        
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(self.selected_examples)} 个示例吗？\n此操作不可恢复！"
        )
        
        if not result:
            return
        
        success_count = 0
        failed_ids = []
        
        for ex_id in self.selected_examples:
            if self.library.remove_example(ex_id):
                success_count += 1
            else:
                failed_ids.append(ex_id)
        
        # 清空选择
        self.selected_examples.clear()
        
        # 刷新列表
        self.refresh_list()
        
        # 显示结果
        if failed_ids:
            messagebox.showwarning(
                "删除结果",
                f"成功删除 {success_count} 个示例\n失败 {len(failed_ids)} 个：{', '.join(failed_ids[:5])}"
            )
        else:
            messagebox.showinfo("成功", f"已成功删除 {success_count} 个示例")
    
    def refresh_list(self):
        """刷新示例列表"""
        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取所有示例
        examples = self.library.get_all_examples()
        
        # 添加到树
        for example in examples:
            is_selected = example.id in self.selected_examples
            check_mark = "☑" if is_selected else "☐"
            
            # 文本预览（前50个字符）
            text_preview = example.text[:50] + "..." if len(example.text) > 50 else example.text
            text_preview = text_preview.replace('\n', ' ')
            
            self.tree.insert('', tk.END, values=(
                check_mark,
                example.id[:8] + "...",  # 缩短ID显示
                example.description or "无描述",
                text_preview
            ), tags=(example.id,))
        
        # 更新统计
        self.stats_label.config(text=f"共 {len(examples)} 个示例")
        
        # 触发回调
        if self.on_selection_change:
            self.on_selection_change(self.selected_examples.copy())
    
    def get_selected_examples(self) -> List[str]:
        """获取选中的示例ID列表"""
        return self.selected_examples.copy()
    
    def set_selection_change_callback(self, callback: Callable[[List[str]], None]):
        """设置选择变化回调"""
        self.on_selection_change = callback
    
    def clear_selection(self):
        """清空选择"""
        self.selected_examples.clear()
        self.refresh_list()
    
    def select_all(self):
        """全选"""
        examples = self.library.get_all_examples()
        self.selected_examples = [ex.id for ex in examples]
        self.refresh_list()
    
    def select_by_description(self, keyword: str):
        """根据描述关键词选择"""
        examples = self.library.get_examples_by_description(keyword)
        for ex in examples:
            if ex.id not in self.selected_examples:
                self.selected_examples.append(ex.id)
        self.refresh_list()