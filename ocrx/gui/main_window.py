# -- coding: utf-8 --
"""
主窗口模块（简化版）
OCRX 应用程序的主界面 - 只使用处理器
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading

from ..config import ConfigManager
from ..logger import StructuredLogger
from ..clipboard import ClipboardHistory
from ..processing_service import ProcessingService

# 导入处理器
from .handlers import (
    SaveHandler, CopyHandler, ClipboardHandler,
    ResultHandler, PromptHandler, ProgressHandler
)


class MainWindow:
    """OCRX 主窗口"""

    def __init__(self, root: tk.Tk):
        """初始化主窗口"""
        self.root = root
        self.root.title("OCRX-智能文字识别")
        self.root.geometry("1200x900")
        self.root.minsize(900, 700)

        # 任务执行状态
        self.is_running = False
        self.current_task = None

        # 剪贴板历史记录
        self.clipboard_history = ClipboardHistory()

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.current_config = self.config_manager.load()

        # 初始化结构化日志系统
        self.logger = StructuredLogger(gui_callback=self.log_callback)
        self.logger.info("应用程序启动", "System")

        # 初始化处理服务
        self.processing_service = None
        self._init_processing_service()

        # 建议值列表
        self.scale_options = ["1.0", "2.0", "3.0", "4.0", "5.0"]
        self.worker_options = ["1", "5", "10", "15", "20"]

        # 提示词模板
        self.prompt_templates = self.config_manager.get_prompt_templates()

        # 页面范围
        self.page_range_var = tk.StringVar(value="")

        # 常量配置
        self.DISPLAY_MAX_LENGTH = 5000
        self.COPY_MAX_PAGES = 10

        # 初始化处理器
        self._init_handlers()

        # 创建界面
        self.create_widgets()

        # 加载配置到界面
        self.populate_fields_from_config()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _init_handlers(self):
        """初始化处理器"""
        self.save_handler = SaveHandler(self)
        self.copy_handler = CopyHandler(self)
        self.clipboard_handler = ClipboardHandler(self)
        self.result_handler = ResultHandler(self)
        self.prompt_handler = PromptHandler(self)
        self.prompt_handler.set_templates(self.prompt_templates)
        self.progress_handler = ProgressHandler(self)
        self.logger.info("所有处理器初始化成功", "System")

    def _init_processing_service(self):
        """初始化处理服务"""
        try:
            api_key = self.current_config.get("API_KEY", "")
            base_url = self.current_config.get("BASE_URL", "")
            model_name = self.current_config.get("MODEL_NAME", "")
            output_dir = self.current_config.get("OUTPUT_DIR", "")
            max_workers = int(self.current_config.get("MAX_WORKERS", "10"))
            pdf_scale = float(self.current_config.get("PDF_SCALE_FACTOR", "3.0"))

            self.processing_service = ProcessingService(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                output_dir=output_dir,
                max_workers=max_workers,
                pdf_scale=pdf_scale,
                logger_inst=self.logger
            )

            self.processing_service.set_progress_callback(self._on_progress_update)
            self.processing_service.set_status_callback(self._on_status_update)

            self.logger.info("处理服务初始化成功", "System")
        except Exception as e:
            self.logger.error(f"处理服务初始化失败：{e}", "System")

    def create_widgets(self):
        """创建所有界面组件"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建 notebook 用于分页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 主要配置页面
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="主要配置")

        # 日志页面
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="运行日志")

        # 剪贴板历史页面
        clipboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(clipboard_frame, text="剪贴板历史")

        # 识别结果页面
        result_frame = ttk.Frame(self.notebook)
        self.notebook.add(result_frame, text="识别结果")

        # 创建各页面组件
        self.create_config_widgets(config_frame)
        self.create_log_widgets(log_frame)
        self.create_clipboard_widgets(clipboard_frame)
        self.create_result_widgets(result_frame)
        self.create_bottom_buttons(main_frame)

    def create_config_widgets(self, parent):
        """创建配置页面组件"""
        parent.grid_columnconfigure(1, weight=1)
        row = 0

        # Base URL
        ttk.Label(parent, text="Base URL:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.base_url_entry = ttk.Entry(parent, width=70)
        self.base_url_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # API Key
        ttk.Label(parent, text="API Key:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.api_key_entry = ttk.Entry(parent, width=70, show="*")
        self.api_key_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # Model Name
        ttk.Label(parent, text="Model Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.model_name_entry = ttk.Entry(parent, width=70)
        self.model_name_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        row += 1

        # 文件路径
        ttk.Label(parent, text="文件路径:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.file_paths_entry = ttk.Entry(parent, width=70)
        self.file_paths_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")

        file_button_frame = ttk.Frame(parent)
        file_button_frame.grid(row=row, column=2, padx=5, sticky='w')
        ttk.Button(file_button_frame, text="选择文件", command=self.select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_button_frame, text="清空", command=self.clear_file_paths).pack(side=tk.LEFT, padx=2)
        row += 1

        # 输出目录
        ttk.Label(parent, text="输出目录:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.output_dir_entry = ttk.Entry(parent, width=70)
        self.output_dir_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        ttk.Button(parent, text="选择目录", command=self.select_output_dir).grid(row=row, column=2, padx=5)
        row += 1

        # 缩放比例
        ttk.Label(parent, text="PDF 缩放比例:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.scale_combobox = ttk.Combobox(parent, values=self.scale_options, width=10, state="readonly")
        self.scale_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(parent, text="(建议值：1.0 ~ 5.0)").grid(row=row, column=1, sticky="w", padx=120, pady=5)
        row += 1

        # 并发数
        ttk.Label(parent, text="最大并发数:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.workers_combobox = ttk.Combobox(parent, values=self.worker_options, width=10, state="readonly")
        self.workers_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(parent, text="(建议值：5 ~ 20)").grid(row=row, column=1, sticky="w", padx=120, pady=5)
        row += 1

        # 提示词预设
        ttk.Label(parent, text="OCR 提示词预设:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.prompt_preset_var = tk.StringVar()
        self.prompt_preset_combobox = ttk.Combobox(
            parent, textvariable=self.prompt_preset_var,
            values=list(self.prompt_templates.keys()), state="readonly", width=20
        )
        self.prompt_preset_combobox.bind("<<ComboboxSelected>>", self.on_prompt_preset_selected)
        self.prompt_preset_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)

        # 提示词预设管理按钮（在同一行）
        self.prompt_handler.set_widgets(
            self.prompt_preset_var,
            self.prompt_preset_combobox,
            None  # 暂时设置为 None，后面再更新
        )
        self.prompt_handler.create_preset_buttons(parent, row, 2)
        row += 1

        # 提示词编辑区
        ttk.Label(parent, text="自定义提示词:").grid(row=row, column=0, sticky="nw", padx=10, pady=5)
        self.prompt_text = scrolledtext.ScrolledText(parent, width=80, height=8)
        self.prompt_text.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="nsew")
        parent.grid_rowconfigure(row, weight=1)
        row += 1

        # 更新 PromptHandler 的 prompt_text 引用
        self.prompt_handler.set_widgets(
            self.prompt_preset_var,
            self.prompt_preset_combobox,
            self.prompt_text
        )

        # 页面范围选择（PDF）
        ttk.Label(parent, text="指定页码范围 (PDF):").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.page_range_var = tk.StringVar(value="")
        self.page_range_entry = ttk.Entry(parent, textvariable=self.page_range_var, width=20)
        self.page_range_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(parent, text="(例如: 1,3,5-10，留空表示全部)").grid(row=row, column=1, sticky="w", padx=150, pady=5)
        row += 1

        # 进度条区域
        self.progress_handler.create_widgets(parent, row)
        self.current_task_label = self.progress_handler.current_task_label
        self.progress_var = self.progress_handler.progress_var
        self.progress_bar = self.progress_handler.progress_bar
        self.detail_progress_var = self.progress_handler.detail_progress_var
        row += 1

    def create_log_widgets(self, parent):
        """创建日志页面组件"""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, width=120, height=40)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def create_clipboard_widgets(self, parent):
        """创建剪贴板历史页面组件"""
        self.clipboard_handler.create_widgets(parent)
        self.clipboard_tree = self.clipboard_handler.tree

    def create_result_widgets(self, parent):
        """创建识别结果页面组件"""
        self.result_handler.create_widgets(parent)
        self.result_text = self.result_handler.text_widget

    def create_bottom_buttons(self, parent):
        """创建底部按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="识别并保存", command=self.start_ocr_and_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="识别并复制", command=self.start_ocr_and_copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="停止", command=self.stop_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置配置", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关于", command=self.show_about).pack(side=tk.RIGHT, padx=5)

    def log_callback(self, log_entry: dict):
        """日志回调函数"""
        if hasattr(self, 'log_text'):
            self.root.after(0, self.update_single_log_entry, log_entry)

    def update_single_log_entry(self, log_entry: dict):
        """更新单条日志条目到 GUI"""
        try:
            self.log_text.config(state='normal')
            formatted_message = f"{log_entry['timestamp']} - [{log_entry['level']}] {log_entry['component']} - {log_entry['message']}\n"
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        except Exception as e:
            print(f"更新日志显示失败：{e}")

    def _on_progress_update(self, current: int, total: int, percent: float, phase: str):
        """进度更新回调"""
        def update():
            self.progress_handler.update_progress(current, total, percent, phase)
        self.root.after(0, update)

    def _on_status_update(self, status: str):
        """状态更新回调"""
        def update():
            self.progress_handler.update_status(status)
        self.root.after(0, update)

    def populate_fields_from_config(self):
        """将配置数据填充到 GUI 控件中"""
        entries_map = {
            "API_KEY": getattr(self, 'api_key_entry', None),
            "BASE_URL": getattr(self, 'base_url_entry', None),
            "MODEL_NAME": getattr(self, 'model_name_entry', None),
            "OUTPUT_DIR": getattr(self, 'output_dir_entry', None),
        }

        for key, widget in entries_map.items():
            if widget:
                value = self.current_config.get(key, "")
                widget.delete(0, tk.END)
                widget.insert(0, value)

        if hasattr(self, 'scale_combobox'):
            scale_val = self.current_config.get("PDF_SCALE_FACTOR", "3.0")
            self.scale_combobox.set(scale_val)

        if hasattr(self, 'workers_combobox'):
            worker_val = self.current_config.get("MAX_WORKERS", "10")
            self.workers_combobox.set(worker_val)

        if hasattr(self, 'prompt_preset_combobox'):
            self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
            self.prompt_preset_var.set("手写笔记")

    def select_files(self):
        """选择文件"""
        filetypes = [
            ("PDF 文件", "*.pdf"),
            ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
            ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(title="选择文件", filetypes=filetypes)
        if files:
            self.file_paths_entry.delete(0, tk.END)
            self.file_paths_entry.insert(0, ";".join(files))

    def clear_file_paths(self):
        """清空文件路径"""
        self.file_paths_entry.delete(0, tk.END)

    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)

    def on_prompt_preset_selected(self, event=None):
        """提示词预设选择"""
        self.prompt_handler.on_preset_selected(event)

    def _validate_and_prepare(self):
        """验证配置并准备参数"""
        api_key = self.api_key_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        model_name = self.model_name_entry.get().strip()

        if not api_key or not base_url or not model_name:
            messagebox.showerror("错误", "请填写完整的 API 配置信息")
            return None

        file_paths = self.file_paths_entry.get().strip()
        if not file_paths:
            messagebox.showerror("错误", "请选择要处理的文件")
            return None

        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if not prompt:
            messagebox.showerror("错误", "请填写提示词")
            return None

        page_range = self.page_range_var.get().strip()

        self.processing_service.update_config(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            output_dir=self.output_dir_entry.get().strip(),
            max_workers=int(self.workers_combobox.get().strip()),
            pdf_scale=float(self.scale_combobox.get().strip())
        )

        return (file_paths.split(';'), prompt, page_range)

    def start_ocr_and_save(self):
        """识别并保存"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行")
            return

        params = self._validate_and_prepare()
        if not params:
            return

        file_paths, prompt, page_range = params

        self.is_running = True

        def run_save():
            try:
                results = self.save_handler.process_files(file_paths, prompt, page_range)
            finally:
                self.is_running = False
                self.current_task = None
                self._on_status_update("等待开始...")
                self._on_progress_update(0, 1, 0.0, "idle")

        self.current_task = threading.Thread(target=run_save, daemon=True)
        self.current_task.start()
        self.logger.info("开始识别并保存任务", "Task")

    def start_ocr_and_copy(self):
        """识别并复制"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行")
            return

        params = self._validate_and_prepare()
        if not params:
            return

        file_paths, prompt, page_range = params

        passed, total_pages, msg = self.copy_handler.check_page_limit(file_paths, page_range)
        if not passed:
            messagebox.showwarning("页数超限", msg)
            return

        self.is_running = True

        def run_copy():
            try:
                success, result = self.copy_handler.process_files(file_paths, prompt, page_range)
            finally:
                self.is_running = False
                self.current_task = None
                self._on_status_update("等待开始...")
                self._on_progress_update(0, 1, 0.0, "idle")

        self.current_task = threading.Thread(target=run_copy, daemon=True)
        self.current_task.start()
        self.logger.info("开始识别并复制任务", "Task")

    def stop_processing(self):
        """停止处理"""
        if not self.is_running:
            messagebox.showinfo("提示", "当前没有运行的任务")
            return

        self.is_running = False
        self.logger.info("任务已停止", "Task")
        messagebox.showinfo("提示", "任务已停止")

    def save_config(self):
        """保存配置"""
        config_data = {
            "BASE_URL": self.base_url_entry.get().strip(),
            "MODEL_NAME": self.model_name_entry.get().strip(),
            "OUTPUT_DIR": self.output_dir_entry.get().strip(),
            "API_KEY": self.api_key_entry.get().strip(),
            "PDF_SCALE_FACTOR": self.scale_combobox.get().strip(),
            "MAX_WORKERS": self.workers_combobox.get().strip(),
            "prompt_templates": self.prompt_handler.get_templates()
        }

        self.config_manager.save(config_data)
        messagebox.showinfo("提示", "配置已保存")

    def reset_to_defaults(self):
        """重置配置为默认值"""
        if self.is_running:
            messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再重置配置。")
            return

        result = messagebox.askokcancel(
            "确认重置",
            "此操作将把配置项恢复为最初版本的默认值，是否继续？"
        )
        if result:
            self.config_manager.reset_to_defaults()
            self.current_config = self.config_manager.load()
            self.prompt_templates = self.config_manager.get_prompt_templates()
            self.prompt_handler.set_templates(self.prompt_templates)
            self.populate_fields_from_config()
            self.on_prompt_preset_selected()
            messagebox.showinfo("重置完成", "配置已恢复为默认值。")

    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于 OCRX",
            "OCRX 智能文字识别系统 v2.0\n\n"
            "基于 AI 的 OCR 文字识别工具\n"
            "支持 PDF 和图片格式\n"
            "支持批量处理"
        )

    def _display_result(self, content: str):
        """显示结果到常驻页面"""
        self.result_handler.display(content)

        def switch_tab():
            self.notebook.select(3)
        self.root.after(0, switch_tab)

    def on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if messagebox.askokcancel("退出", "任务正在运行，确定要退出吗？"):
                self.is_running = False
                self.save_config()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()
