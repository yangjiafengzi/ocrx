# -- coding: utf-8 --
"""
主窗口模块（简化版）
OCRX 应用程序的主界面 - 只使用处理器
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from typing import List, Optional

from .. import __version__
from ..config import ConfigManager
from ..logger import StructuredLogger
from ..clipboard import ClipboardHistory
from ..processing_service import ProcessingService
from ..example_library import ExampleLibrary

# 导入处理器
from .example_manager_ui import ExampleManagerUI
from .theme import BG, BORDER, PRIMARY, TEXT, setup_styles, themed_scrolled_text
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
        setup_styles(self.root)

        # 任务执行状态
        self.is_running = False
        self.current_task = None

        # 剪贴板历史记录
        self.clipboard_history = ClipboardHistory(root=self.root)

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

        # 示例库
        self.example_library = ExampleLibrary()
        self.selected_example_ids: List[str] = []

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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 页头
        header = ttk.Frame(main_frame, style="Header.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            header,
            text="OCRX 智能文字识别",
            style="HeaderTitle.TLabel",
        ).pack(side=tk.LEFT, padx=18, pady=(6, 0))
        ttk.Label(
            header,
            text=f"基于 AI 的批量 OCR 工具 · v{__version__}",
            style="HeaderSub.TLabel",
        ).pack(side=tk.LEFT, padx=4, pady=(10, 0))

        # 创建 notebook 用于分页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 主要配置页面
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="主要配置")

        # 示例库管理页面（少样本提示）
        example_frame = ttk.Frame(self.notebook)
        self.notebook.add(example_frame, text="少样本示例库")
        self.example_manager_ui = ExampleManagerUI(example_frame, self.example_library)
        self.example_manager_ui.set_selection_change_callback(self._on_example_selection_change)

        # 日志页面
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="运行日志")

        # 剪贴板历史页面
        clipboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(clipboard_frame, text="剪贴板历史")

        # 识别结果页面
        result_frame = ttk.Frame(self.notebook)
        self.notebook.add(result_frame, text="识别结果")
        self.result_frame = result_frame

        # 创建各页面组件
        self.create_config_widgets(config_frame)
        self.create_log_widgets(log_frame)
        self.create_clipboard_widgets(clipboard_frame)
        self.create_result_widgets(result_frame)
        self.create_bottom_buttons(main_frame)

    def create_config_widgets(self, parent):
        """创建配置页面组件（可滚动，窗口缩小时内容不会被遮挡）"""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # 可滚动画布 + 纵向滚动条
        self.config_canvas = tk.Canvas(parent, bg=BG, highlightthickness=0, borderwidth=0)
        self.config_scrollbar = ttk.Scrollbar(
            parent, orient="vertical", command=self.config_canvas.yview
        )
        self.config_canvas.configure(yscrollcommand=self.config_scrollbar.set)
        self.config_canvas.grid(row=0, column=0, sticky="nsew")
        self.config_scrollbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(self.config_canvas)
        self._config_window_id = self.config_canvas.create_window(
            (0, 0), window=inner, anchor="nw"
        )
        inner.grid_columnconfigure(0, weight=1)
        row = 0

        # ===== API 设置 =====
        api_frame = ttk.LabelFrame(inner, text="API 设置", style="Card.TLabelframe")
        api_frame.grid(row=row, column=0, sticky="ew", padx=14, pady=(8, 3))
        api_frame.grid_columnconfigure(1, weight=1)
        api_frame.grid_columnconfigure(3, weight=1)

        ttk.Label(api_frame, text="Base URL:").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        self.base_url_entry = ttk.Entry(api_frame)
        self.base_url_entry.grid(row=0, column=1, columnspan=3, padx=8, pady=3, sticky="ew")

        ttk.Label(api_frame, text="API Key:").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        self.api_key_entry = ttk.Entry(api_frame, show="*")
        self.api_key_entry.grid(row=1, column=1, padx=8, pady=3, sticky="ew")

        ttk.Label(api_frame, text="Model Name:").grid(row=1, column=2, sticky="w", padx=8, pady=3)
        self.model_name_entry = ttk.Entry(api_frame)
        self.model_name_entry.grid(row=1, column=3, padx=8, pady=3, sticky="ew")
        row += 1

        # ===== 文件与输出 =====
        files_frame = ttk.LabelFrame(inner, text="文件与输出", style="Card.TLabelframe")
        files_frame.grid(row=row, column=0, sticky="ew", padx=14, pady=3)
        files_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(files_frame, text="文件路径:").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        self.file_paths_entry = ttk.Entry(files_frame)
        self.file_paths_entry.grid(row=0, column=1, padx=8, pady=3, sticky="ew")

        file_button_frame = ttk.Frame(files_frame, style="Card.TFrame")
        file_button_frame.grid(row=0, column=2, padx=6, sticky="w")
        ttk.Button(file_button_frame, text="选择文件", style="Secondary.TButton", command=self.select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_button_frame, text="清空", style="Secondary.TButton", command=self.clear_file_paths).pack(side=tk.LEFT, padx=2)

        format_hint = ttk.Label(
            files_frame,
            text="支持格式：PDF、JPG、PNG、BMP、GIF、TIFF、WebP、HEIC、RAW(CR2/NEF/ARW/DNG)",
            style="Muted.TLabel",
        )
        format_hint.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 2))

        ttk.Label(files_frame, text="输出目录:").grid(row=2, column=0, sticky="w", padx=8, pady=3)
        self.output_dir_entry = ttk.Entry(files_frame)
        self.output_dir_entry.grid(row=2, column=1, padx=8, pady=3, sticky="ew")
        ttk.Button(
            files_frame,
            text="选择目录",
            style="Secondary.TButton",
            command=self.select_output_dir,
        ).grid(row=2, column=2, padx=8, pady=3)
        row += 1

        # ===== 识别参数 =====
        params_frame = ttk.LabelFrame(inner, text="识别参数", style="Card.TLabelframe")
        params_frame.grid(row=row, column=0, sticky="ew", padx=14, pady=3)
        params_frame.grid_columnconfigure(1, weight=1)
        params_frame.grid_columnconfigure(3, weight=1)

        ttk.Label(params_frame, text="PDF 缩放比例 (1~5):").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        self.scale_combobox = ttk.Combobox(params_frame, values=self.scale_options, width=8, state="readonly")
        self.scale_combobox.grid(row=0, column=1, sticky="w", padx=8, pady=3)
        ttk.Label(params_frame, text="最大并发数 (5~20):").grid(row=0, column=2, sticky="w", padx=8, pady=3)
        self.workers_combobox = ttk.Combobox(params_frame, values=self.worker_options, width=8, state="readonly")
        self.workers_combobox.grid(row=0, column=3, sticky="w", padx=8, pady=3)

        ttk.Label(params_frame, text="页码范围 (PDF):").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        self.page_range_var = tk.StringVar(value="")
        self.page_range_entry = ttk.Entry(params_frame, textvariable=self.page_range_var, width=20)
        self.page_range_entry.grid(row=1, column=1, sticky="w", padx=8, pady=3)
        ttk.Label(
            params_frame,
            text="例如: 1,3,5-10，留空表示全部",
            style="Muted.TLabel",
        ).grid(row=1, column=2, columnspan=2, sticky="w", padx=8, pady=3)
        row += 1

        # ===== 提示词 =====
        prompt_frame = ttk.LabelFrame(inner, text="提示词", style="Card.TLabelframe")
        prompt_frame.grid(row=row, column=0, sticky="nsew", padx=14, pady=3)
        prompt_frame.grid_columnconfigure(1, weight=1)
        prompt_frame.grid_rowconfigure(1, weight=1)

        ttk.Label(prompt_frame, text="预设:").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        self.prompt_preset_var = tk.StringVar()
        self.prompt_preset_combobox = ttk.Combobox(
            prompt_frame, textvariable=self.prompt_preset_var,
            values=list(self.prompt_templates.keys()), state="readonly", width=20
        )
        self.prompt_preset_combobox.bind("<<ComboboxSelected>>", self.on_prompt_preset_selected)
        self.prompt_preset_combobox.grid(row=0, column=1, sticky="w", padx=8, pady=3)

        # 提示词预设管理按钮（在同一行）
        self.prompt_handler.set_widgets(
            self.prompt_preset_var,
            self.prompt_preset_combobox,
            None  # 暂时设置为 None，后面再更新
        )
        self.prompt_handler.create_preset_buttons(prompt_frame, 0, 2)

        ttk.Label(prompt_frame, text="自定义提示词:").grid(row=1, column=0, sticky="nw", padx=8, pady=3)
        self.prompt_text = themed_scrolled_text(
            prompt_frame,
            width=80,
            height=4,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            bg="#FFFFFF",
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            insertbackground=TEXT,
            padx=10,
            pady=8,
        )
        self.prompt_text.grid(row=1, column=1, columnspan=2, padx=8, pady=3, sticky="nsew")
        row += 1

        # 更新 PromptHandler 的 prompt_text 引用
        self.prompt_handler.set_widgets(
            self.prompt_preset_var,
            self.prompt_preset_combobox,
            self.prompt_text
        )

        # 进度条区域
        self.progress_handler.create_widgets(inner, row)
        self.current_task_label = self.progress_handler.current_task_label
        self.progress_var = self.progress_handler.progress_var
        self.progress_bar = self.progress_handler.progress_bar
        self.detail_progress_var = self.progress_handler.detail_progress_var
        row += 1

        # 滚动区域联动
        self.config_canvas.bind("<Configure>", self._on_config_canvas_configure)
        inner.bind("<Configure>", self._on_config_inner_configure)
        self._bind_mousewheel(inner)

    def _on_config_canvas_configure(self, event):
        """画布宽度变化时，让内容区跟随宽度。"""
        if hasattr(self, "_config_window_id"):
            self.config_canvas.itemconfigure(self._config_window_id, width=event.width)
        self._update_config_scrollbar_visibility()

    def _on_config_inner_configure(self, event):
        """内容尺寸变化时更新滚动范围。"""
        self.config_canvas.configure(scrollregion=self.config_canvas.bbox("all"))
        self._update_config_scrollbar_visibility()

    def _update_config_scrollbar_visibility(self):
        """内容未超出可视区时隐藏滚动条，避免常驻一条空轨道。"""
        try:
            bbox = self.config_canvas.bbox("all")
            view_h = self.config_canvas.winfo_height()
            if bbox and view_h > 0 and bbox[3] <= view_h + 1:
                self.config_scrollbar.grid_remove()
            else:
                self.config_scrollbar.grid()
        except tk.TclError:
            pass

    def _bind_mousewheel(self, widget):
        """递归绑定鼠标滚轮，保证滚动条在配置页任意位置可用。"""
        widget.bind("<MouseWheel>", self._on_config_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _on_config_mousewheel(self, event):
        if hasattr(self, "config_canvas"):
            self.config_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def create_log_widgets(self, parent):
        """创建日志页面组件"""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.log_text = themed_scrolled_text(
            parent,
            wrap=tk.WORD,
            width=120,
            height=40,
            font=("Consolas", 10),
            bg="#0F172A",
            fg="#E2E8F0",
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            insertbackground="#E2E8F0",
            padx=10,
            pady=10,
        )
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
        button_frame.pack(fill=tk.X, pady=(8, 2))

        ttk.Button(button_frame, text="识别并保存", style="Primary.TButton", command=self.start_ocr_and_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="识别并复制", style="Success.TButton", command=self.start_ocr_and_copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="停止", style="Danger.TButton", command=self.stop_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存配置", style="Secondary.TButton", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置配置", style="Secondary.TButton", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关于", style="Secondary.TButton", command=self.show_about).pack(side=tk.RIGHT, padx=5)

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
    
    def _on_example_selection_change(self, selected_ids: List[str]):
        """示例选择变化回调"""
        self.selected_example_ids = selected_ids.copy()
        if len(selected_ids) > 0:
            self.logger.info(f"示例选择变化：选中 {len(selected_ids)} 个示例", "FewShot")
        else:
            self.logger.debug("示例选择清空", "FewShot")

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
            # 默认选中第一个预设，并同步填充提示词编辑区
            self.on_prompt_preset_selected()

    def select_files(self):
        """选择文件"""
        filetypes = [
            ("PDF 文件", "*.pdf"),
            ("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp *.heic *.heif *.raw *.cr2 *.nef *.arw *.dng"),
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

        # 获取选中的少样本示例
        example_images = None
        if self.selected_example_ids:
            # 限制示例数量
            if len(self.selected_example_ids) > 3:
                result = messagebox.askyesno(
                    "提示",
                    f"你选中了 {len(self.selected_example_ids)} 个示例，建议不超过 3 个以节省 token 和费用。\n是否继续？"
                )
                if not result:
                    return None
            
            example_images = []
            found_count = 0
            for ex_id in self.selected_example_ids:
                example = self.example_library.get_example(ex_id)
                if example:
                    found_count += 1
                    # 读取示例图片数据
                    try:
                        with open(example.image_path, 'rb') as f:
                            img_data = f.read()
                        example_images.append((example.text, img_data))
                        self.logger.debug(f"加载示例：{example.id} - {example.description}", "FewShot")
                    except Exception as e:
                        self.logger.error(f"读取示例失败 {ex_id}: {e}", "FewShot")
                else:
                    self.logger.warning(f"示例不存在：{ex_id}，跳过", "FewShot")
            
            self.logger.info(f"选中 {len(self.selected_example_ids)} 个，实际找到 {found_count} 个，准备了 {len(example_images)} 个少样本示例", "FewShot")

        page_range = self.page_range_var.get().strip()

        try:
            max_workers = int(self.workers_combobox.get().strip())
            pdf_scale = float(self.scale_combobox.get().strip())
        except (TypeError, ValueError):
            messagebox.showerror("错误", "最大并发数或 PDF 缩放比例不是有效数字")
            return None

        output_dir = self.output_dir_entry.get().strip()
        if not output_dir:
            output_dir = str(Path.home() / "Documents")

        if self.processing_service is None:
            messagebox.showerror("错误", "处理服务初始化失败，请检查依赖（如 PyMuPDF）后重启程序。")
            return None

        self.processing_service.update_config(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            output_dir=output_dir,
            max_workers=max_workers,
            pdf_scale=pdf_scale
        )

        return (file_paths.split(';'), prompt, page_range, example_images)

    def start_ocr_and_save(self):
        """识别并保存"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行")
            return

        params = self._validate_and_prepare()
        if not params:
            return

        if self.processing_service is None:
            messagebox.showerror("错误", "处理服务初始化失败，请检查依赖后重启程序。")
            return

        # 使用更安全的参数解包，支持向后兼容
        file_paths, prompt, page_range, *optional_params = params
        example_images = optional_params[0] if optional_params else None

        self.is_running = True

        def run_save():
            try:
                if self.processing_service:
                    self.processing_service.reset_cancel()
                results = self.save_handler.process_files(file_paths, prompt, page_range, example_images)
            finally:
                self.is_running = False
                self.current_task = None
                if self.processing_service:
                    self.processing_service.reset_cancel()
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

        if self.processing_service is None:
            messagebox.showerror("错误", "处理服务初始化失败，请检查依赖后重启程序。")
            return

        # 使用更安全的参数解包，支持向后兼容
        file_paths, prompt, page_range, *optional_params = params
        example_images = optional_params[0] if optional_params else None

        passed, total_pages, msg = self.copy_handler.check_page_limit(file_paths, page_range)
        if not passed:
            messagebox.showwarning("页数超限", msg)
            return

        self.is_running = True

        def run_copy():
            try:
                if self.processing_service:
                    self.processing_service.reset_cancel()
                success, result = self.copy_handler.process_files(file_paths, prompt, page_range, example_images)
            finally:
                self.is_running = False
                self.current_task = None
                if self.processing_service:
                    self.processing_service.reset_cancel()
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

        if self.processing_service:
            self.processing_service.request_cancel()
        self.logger.info("已请求停止任务，等待当前页面收尾", "Task")
        messagebox.showinfo("提示", "已请求停止，正在识别的页面完成后将自动结束。")

    def save_config(self, show_dialog: bool = True):
        """保存配置

        Args:
            show_dialog: 是否在保存后弹出提示框（关闭窗口时应静默保存）
        """
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
        if show_dialog:
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
            f"OCRX 智能文字识别系统 v{__version__}\n\n"
            "基于 AI 的 OCR 文字识别工具\n"
            "支持 PDF 和图片格式\n"
            "支持批量处理"
        )

    def _display_result(self, content: str):
        """显示结果到常驻页面"""
        self.result_handler.display(content)

        def switch_tab():
            self.notebook.select(self.result_frame)
        self.root.after(0, switch_tab)

    def on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if messagebox.askokcancel("退出", "任务正在运行，确定要退出吗？"):
                self.is_running = False
                self.save_config(show_dialog=False)
                self.root.destroy()
                self.logger.close()
        else:
            self.save_config(show_dialog=False)
            self.root.destroy()
            self.logger.close()
