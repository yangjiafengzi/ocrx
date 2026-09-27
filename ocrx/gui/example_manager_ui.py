# -- coding: utf-8 --
"""
示例库管理界面
用于GUI中管理少样本提示的示例
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, List, Optional
from pathlib import Path

from PIL import Image, ImageTk

from ..example_library import ExampleLibrary, Example
from .theme import (
    BORDER,
    TEXT,
    attach_scrollbar,
    bind_scrollbar_paging,
    bind_tree_scroll,
)


class ExampleManagerUI:
    """示例库管理界面"""

    on_data_change: Optional[Callable[[], None]] = None
    
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
        self.on_data_change: Optional[Callable[[], None]] = None
        
        # 创建界面
        self._create_ui()
        
        # 刷新列表
        self.refresh_list()
    
    def _create_ui(self):
        """创建界面组件"""
        # 主框架
        self.main_frame = ttk.LabelFrame(
            self.parent,
            text="少样本示例库",
            style="Card.TLabelframe",
            padding=8,
        )
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 工具栏
        toolbar = ttk.Frame(self.main_frame, style="Card.TFrame")
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="添加示例", style="Secondary.TButton", command=self._on_add_example).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除选中", style="Secondary.TButton", command=self._on_delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新列表", style="Secondary.TButton", command=self.refresh_list).pack(side=tk.LEFT, padx=2)
        
        # 统计信息
        self.stats_label = ttk.Label(toolbar, text="共 0 个示例", style="Section.TLabel")
        self.stats_label.pack(side=tk.RIGHT, padx=5)
        
        # 列表面板
        list_frame = ttk.Frame(self.main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建Treeview
        columns = ('select', 'id', 'description', 'text_preview')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            selectmode='none',
            height=4,
        )
        # 高度变化时按像素放大可见行，避免小面板只剩固定 8 行
        self.tree.bind(
            '<Configure>',
            lambda e, tv=self.tree: self._fit_rows(tv, e.height),
            add='+',
        )
        
        # 定义列
        self.tree.heading('select', text='选择')
        self.tree.heading('id', text='ID')
        self.tree.heading('description', text='描述')
        self.tree.heading('text_preview', text='文本预览')
        
        # 固定列宽：窗口变窄时产生真实横向溢出，横向滚动条才有意义
        self.tree.column('select', width=50, anchor='center', stretch=False)
        self.tree.column('id', width=100, stretch=False)
        self.tree.column('description', width=150, stretch=False)
        self.tree.column('text_preview', width=300, stretch=False)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        attach_scrollbar(scrollbar_y, self.tree, orient="vertical", manager="grid")
        attach_scrollbar(scrollbar_x, self.tree, orient="horizontal", manager="grid")
        bind_tree_scroll(self.tree, xscrollbar=scrollbar_x)
        bind_scrollbar_paging(scrollbar_y)
        bind_scrollbar_paging(scrollbar_x)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定点击事件
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)
        self.tree.bind('<Double-1>', self._on_row_double_click)
        
        # 底部提示
        hint_text = "提示：点击复选框选择要在识别时使用的示例（建议1-3个）"
        ttk.Label(
            self.main_frame,
            text=hint_text,
            style="Muted.TLabel",
        ).pack(anchor='w', pady=5)
    
    @staticmethod
    def _fit_rows(tree, pixel_height: int) -> None:
        """按控件像素高度调整可见行数。"""
        row_h = 22
        rows = max(3, int(pixel_height // row_h) - 1)
        try:
            tree.configure(height=rows)
        except tk.TclError:
            pass

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

    @staticmethod
    def _make_preview(text: str, max_units: int = 30) -> str:
        """
        生成按显示宽度截断的预览文本（CJK 按 2 个半角单位计）。
        避免长文本在列宽内被硬切、省略号不可见。
        """
        preview = text.replace('\n', ' ').strip()
        units = 0
        out = []
        for ch in preview:
            units += 2 if ord(ch) > 0x2E7F else 1
            if units > max_units:
                break
            out.append(ch)
        result = ''.join(out)
        if result != preview:
            return result + "…"
        return preview
    
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
        
        text_frame = ttk.Frame(dialog, style="Card.TFrame")
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            width=50,
            height=8,
            font=("Microsoft YaHei UI", 10),
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            insertbackground=TEXT,
            padx=8,
            pady=8,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=text_widget.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=text_scrollbar.set)
        
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

            # 文本预览（按显示宽度截断，保证省略号可见）
            text_preview = self._make_preview(example.text)
            
            self.tree.insert('', tk.END, values=(
                check_mark,
                self._make_preview(example.id, max_units=16),
                example.description or "无描述",
                text_preview
            ), tags=(example.id,))
        
        # 更新统计
        self.stats_label.config(text=f"共 {len(examples)} 个示例")
        
        # 列表内容变化（增删改/刷新）后通知外部同步少样本列表
        if self.on_data_change:
            self.on_data_change()

    def _on_row_double_click(self, event):
        """双击示例行：打开预览与编辑框。"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        tags = self.tree.item(item, 'tags')
        ex_id = tags[0] if tags else None
        example = self.library.get_example(ex_id) if ex_id else None
        if example:
            self._open_editor(example)

    def _open_editor(self, example: Example):
        """打开示例预览与编辑对话框。"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("示例预览与编辑")
        dialog.geometry("560x540")
        dialog.transient(self.parent)
        dialog.grab_set()
        self._editor_dialog = dialog

        # 图片预览
        try:
            img = Image.open(example.image_path)
            img.thumbnail((260, 180))
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(dialog, image=photo, bg="#FFFFFF")
            img_label.image = photo  # 保持引用，防止被回收
            img_label.pack(pady=8)
        except Exception:
            ttk.Label(
                dialog,
                text=f"图片预览不可用：{example.image_path}",
                style="Muted.TLabel",
            ).pack(pady=8)

        ttk.Label(dialog, text="正确识别结果：").pack(anchor="w", padx=12)
        text_frame = ttk.Frame(dialog, style="Card.TFrame")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            height=8,
            font=("Microsoft YaHei UI", 10),
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            insertbackground=TEXT,
            padx=8,
            pady=8,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=text_scroll.set)
        text_widget.insert("1.0", example.text)
        self._editor_text = text_widget

        ttk.Label(dialog, text="描述/标签：").pack(anchor="w", padx=12)
        desc_var = tk.StringVar(value=example.description)
        desc_entry = ttk.Entry(dialog, textvariable=desc_var, width=60)
        desc_entry.pack(fill=tk.X, padx=12, pady=4)
        self._editor_desc = desc_entry

        def on_save():
            new_text = text_widget.get("1.0", tk.END).strip()
            if not new_text:
                messagebox.showwarning("提示", "识别文本不能为空", parent=dialog)
                return
            if self.library.update_example(
                example.id,
                text=new_text,
                description=desc_var.get().strip(),
            ):
                self.refresh_list()
                messagebox.showinfo("成功", "示例已更新", parent=self.parent)
            else:
                messagebox.showerror("错误", "更新示例失败", parent=dialog)
            dialog.destroy()

        self._editor_on_save = on_save
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="保存", style="Primary.TButton", command=on_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="取消", style="Secondary.TButton", command=dialog.destroy).pack(side=tk.LEFT, padx=6)
    
    def get_selected_examples(self) -> List[str]:
        """获取选中的示例ID列表"""
        return self.selected_examples.copy()
    
    def set_selection_change_callback(self, callback: Callable[[List[str]], None]):
        """设置选择变化回调"""
        self.on_selection_change = callback

    def set_data_change_callback(self, callback: Callable[[], None]):
        """设置示例库数据变更回调（列表刷新后触发）"""
        self.on_data_change = callback
    
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
