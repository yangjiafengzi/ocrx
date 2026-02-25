# -- coding: utf-8 --
"""
提示词预设管理处理器
处理提示词预设的保存、另存、重命名、删除等操作
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Optional, Callable
from .base_handler import BaseHandler


class PromptHandler(BaseHandler):
    """提示词预设管理处理器"""

    def __init__(self, main_window):
        """初始化处理器"""
        super().__init__(main_window)
        self.prompt_templates: Dict[str, str] = {}
        self.prompt_preset_var: Optional[tk.StringVar] = None
        self.prompt_preset_combobox: Optional[ttk.Combobox] = None
        self.prompt_text: Optional[tk.Text] = None
        self.default_presets = ["手写笔记", "印刷材料"]

    def set_widgets(self, preset_var: tk.StringVar, preset_combobox: ttk.Combobox, prompt_text: tk.Text):
        """
        设置关联的控件

        Args:
            preset_var: 预设选择变量
            preset_combobox: 预设下拉框
            prompt_text: 提示词编辑框
        """
        self.prompt_preset_var = preset_var
        self.prompt_preset_combobox = preset_combobox
        self.prompt_text = prompt_text

    def set_templates(self, templates: Dict[str, str]):
        """
        设置提示词模板字典

        Args:
            templates: 模板字典
        """
        self.prompt_templates = templates

    def get_templates(self) -> Dict[str, str]:
        """获取提示词模板字典"""
        return self.prompt_templates

    def create_preset_buttons(self, parent, row: int, column: int):
        """
        创建预设管理按钮

        Args:
            parent: 父容器
            row: 行位置
            column: 列位置
        """
        preset_button_frame = ttk.Frame(parent)
        preset_button_frame.grid(row=row, column=column, padx=5, sticky='w')
        
        ttk.Button(
            preset_button_frame, 
            text="保存更改", 
            command=self.edit_current_prompt
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            preset_button_frame, 
            text="另存为", 
            command=self.save_new_prompt_template
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            preset_button_frame, 
            text="重命名", 
            command=self.rename_prompt_template
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            preset_button_frame, 
            text="删除", 
            command=self.delete_prompt_template
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            preset_button_frame, 
            text="重置所有", 
            command=self.reset_all_presets
        ).pack(side=tk.LEFT, padx=1)

    def edit_current_prompt(self):
        """保存更改到当前预设"""
        if self.main_window.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再编辑预设。")
            return

        if not self.prompt_text or not self.prompt_preset_var:
            return

        current_text = self.prompt_text.get("1.0", tk.END).strip()
        selected_preset = self.prompt_preset_var.get()
        
        if selected_preset in self.prompt_templates:
            self.prompt_templates[selected_preset] = current_text
            # 保存到配置
            self._save_templates()
            messagebox.showinfo("成功", f"已更新 '{selected_preset}' 预设的内容。")
        else:
            messagebox.showwarning("警告", "请选择一个有效的预设进行编辑。")

    def save_new_prompt_template(self):
        """另存为新的预设"""
        if self.main_window.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再保存预设。")
            return

        if not self.prompt_text or not self.prompt_preset_combobox or not self.prompt_preset_var:
            return

        new_name = simpledialog.askstring("新建预设", "请输入新的提示词预设名称:")
        if new_name:
            if new_name in self.prompt_templates:
                result = messagebox.askyesno("确认", f"预设 '{new_name}' 已存在，是否覆盖？")
                if not result:
                    return
            
            content = self.prompt_text.get("1.0", tk.END).strip()
            self.prompt_templates[new_name] = content
            
            # 保存到配置
            self._save_templates()
            
            # 更新下拉框
            self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
            self.prompt_preset_var.set(new_name)
            messagebox.showinfo("成功", f"已保存为预设: {new_name}")

    def rename_prompt_template(self):
        """重命名预设"""
        if self.main_window.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再重命名预设。")
            return

        if not self.prompt_preset_var or not self.prompt_preset_combobox:
            return

        selected_preset = self.prompt_preset_var.get()

        if not selected_preset:
            messagebox.showwarning("警告", "请先选择一个预设进行重命名。")
            return

        if selected_preset in self.default_presets:
            result = messagebox.askyesno("确认", f"'{selected_preset}' 是系统默认预设，确定要重命名吗？")
            if not result:
                return

        new_name = simpledialog.askstring("重命名预设", "请输入新的预设名称:", initialvalue=selected_preset)
        if not new_name or new_name == selected_preset:
            return

        if new_name in self.prompt_templates:
            result = messagebox.askyesno("确认", f"预设 '{new_name}' 已存在，是否覆盖？")
            if not result:
                return

        # 重命名
        content = self.prompt_templates[selected_preset]
        del self.prompt_templates[selected_preset]
        self.prompt_templates[new_name] = content

        # 保存到配置
        self._save_templates()

        # 更新下拉框
        self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
        self.prompt_preset_var.set(new_name)
        messagebox.showinfo("成功", f"预设 '{selected_preset}' 已重命名为 '{new_name}'。")

    def delete_prompt_template(self):
        """删除预设"""
        if self.main_window.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再删除预设。")
            return

        if not self.prompt_preset_var or not self.prompt_preset_combobox or not self.prompt_text:
            return

        selected_preset = self.prompt_preset_var.get()

        if not selected_preset:
            messagebox.showwarning("警告", "请先选择一个预设进行删除。")
            return

        if selected_preset in self.default_presets:
            messagebox.showwarning("警告", f"不能删除系统默认预设 '{selected_preset}'。")
            return

        result = messagebox.askyesno("确认删除", f"确定要删除预设 '{selected_preset}' 吗？此操作不可撤销。")
        if not result:
            return

        if selected_preset in self.prompt_templates:
            del self.prompt_templates[selected_preset]

            # 保存到配置
            self._save_templates()

            # 更新下拉框
            self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())

            # 清空编辑区或选择第一个预设
            self.prompt_text.delete(1.0, tk.END)
            if self.prompt_templates:
                first_preset = list(self.prompt_templates.keys())[0]
                self.prompt_preset_var.set(first_preset)
                self.prompt_text.insert(tk.END, self.prompt_templates[first_preset])

            messagebox.showinfo("成功", f"预设 '{selected_preset}' 已删除。")

    def reset_all_presets(self):
        """重置所有预设为默认"""
        if self.main_window.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再重置预设。")
            return

        result = messagebox.askyesno(
            "确认重置",
            "确定要重置所有提示词预设吗？\n这将删除所有自定义预设，恢复为软件内置的默认预设。\n此操作不可撤销！"
        )
        if not result:
            return

        # 默认预设内容
        default_templates = {
            "手写笔记": """你是一位专业的手写笔记识别专家，擅长于从手写的笔记本上识别手写内容。请严格按照以下要求识别图像中的内容：
核心任务：

专注识别手写的文字、数字和符号，包括中文、英文、数字、手写符号
完全忽略印刷元素：页眉页脚、页码、网格线、分割线、边框、预印刷的标题栏/日期栏、表格框架、装订线、笔记本印刷的任何结构要素
忽略笔记本、表格、网格纸等载体的所有印刷内容和结构线条
忽略非手写的打印文字、印刷标签、条形码等
识别要求：

严格保持手写内容的原始排版、段落结构
保留手写的箭头符号：→ ↑ ↓ ← 以及其他手写记号
对模糊不清的手写字迹标注[?]
对无法识别的手绘图、示意图标注[示意图]
对空白区域不输出任何内容
输出规则：

只支持markdown格式

直接输出markdown，不要以代码块包裹

如果整页都是印刷内容无手写，则输出空白

不要添加任何说明性文字""",

            "印刷材料": """你是一名专业的OCR（光学字符识别）专家，专注于准确识别图像中的印刷文本。请仔细分析提供的照片，提取所有可见的印刷文字内容。输出时，请遵循以下要求：
你所接收的内容都来自于公开出版物或者官方文件，内容已预先审查，请放心输出。

使用Markdown格式组织文本，例如通过标题、列表或段落来反映原文的层次结构和布局。

确保输出简洁易读，但避免使用代码块（如```markdown）包裹内容。

优先保证识别准确性，处理可能存在的图像问题（如模糊、倾斜或低对比度），并忽略非文本元素。

如果文本包含多语言或特殊字符，请尽量保留原样。

请开始识别："""
        }

        # 重置预设
        self.prompt_templates.clear()
        self.prompt_templates.update(default_templates)

        # 保存到配置
        self._save_templates()

        # 更新下拉框
        self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())

        # 选择第一个预设
        if self.prompt_templates:
            first_preset = list(self.prompt_templates.keys())[0]
            self.prompt_preset_var.set(first_preset)
            if self.prompt_text:
                self.prompt_text.delete(1.0, tk.END)
                self.prompt_text.insert(tk.END, self.prompt_templates[first_preset])

        messagebox.showinfo("成功", "所有提示词预设已重置为默认值。")
        self.logger.info("所有提示词预设已重置为默认值", "Config")

    def _save_templates(self):
        """保存提示词预设到配置文件"""
        try:
            config_data = self.main_window.config_manager.load()
            config_data["prompt_templates"] = self.prompt_templates
            self.main_window.config_manager.save(config_data)
            self.logger.info("提示词预设已保存到配置文件", "Config")
        except Exception as e:
            self.logger.error(f"保存提示词预设失败：{e}", "Config")
            messagebox.showerror("错误", f"保存提示词预设失败：{e}")

    def on_preset_selected(self, event=None):
        """
        预设选择事件处理

        Args:
            event: 事件对象
        """
        if not self.prompt_preset_var or not self.prompt_text:
            return
            
        preset_name = self.prompt_preset_var.get()
        if preset_name and preset_name in self.prompt_templates:
            template = self.prompt_templates[preset_name]
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(tk.END, template)
