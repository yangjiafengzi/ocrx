# -- coding: utf-8 --
import os
import base64
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
from pathlib import Path
from openai import OpenAI
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from PIL import Image, ImageTk
import io
import logging
from datetime import datetime
import traceback
import hashlib
import re

# 新增导入用于剪贴板操作
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
    print("使用 pyperclip 进行剪贴板操作")
except ImportError:
    try:
        from tkinter import Tk
        CLIPBOARD_AVAILABLE = True
        print("使用 tkinter 进行剪贴板操作")
    except ImportError:
        CLIPBOARD_AVAILABLE = False
        print("无法使用剪贴板功能")


class ClipboardHistory:
    """剪贴板历史记录管理"""

    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history

    def add_record(self, content, success=True, method="auto", error_msg=""):
        """添加复制记录"""
        record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'content_preview': content[:100] + "..." if len(content) > 100 else content,
            'content_length': len(content),
            'content_hash': hashlib.md5(content.encode('utf-8')).hexdigest()[:8],
            'success': success,
            'method': method,
            'error_msg': error_msg
        }

        self.history.append(record)
        # 保持历史记录数量限制
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self):
        """获取历史记录"""
        return self.history

    def clear_history(self):
        """清空历史记录"""
        self.history.clear()


class StructuredLogger:
    """结构化日志系统"""

def __init__(self, log_file_path=None, gui_callback=None):
    self.log_file_path = log_file_path or Path.home() / ".ocrx_gui.log"
    self.logs = []
    self.gui_callback = gui_callback  # 回调函数，用于实时更新GUI

    # 设置日志级别
    self.levels = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'CRITICAL': 4
    }
    self.current_level = 'DEBUG'  # 默认显示所有日志

    # 初始化文件日志
    self._setup_file_logger()
    print(f"日志系统初始化完成，日志文件: {self.log_file_path}")

def _setup_file_logger(self):
    """设置文件日志记录器"""
    self.logger = logging.getLogger('OCRXGUI')
    self.logger.setLevel(logging.DEBUG)

    # 清除现有的处理器
    for handler in self.logger.handlers[:]:
        self.logger.removeHandler(handler)

    # 创建文件处理器
    try:
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        print("文件日志记录器设置成功")
    except Exception as e:
        print(f"文件日志记录器设置失败: {e}")

def log(self, level, message, component="General"):
    """记录结构化日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'component': component,
        'message': message
    }

    # 添加到内存日志
    self.logs.append(log_entry)

    # 写入文件日志
    try:
        if level == 'ERROR':
            self.logger.error(f"[{component}] {message}")
        elif level == 'WARNING':
            self.logger.warning(f"[{component}] {message}")
        elif level == 'INFO':
            self.logger.info(f"[{component}] {message}")
        elif level == 'DEBUG':
            self.logger.debug(f"[{component}] {message}")
    except Exception as e:
        print(f"写入日志文件失败: {e}")

    print(f"[{timestamp}][{level}] {component} - {message}")  # 控制台输出

    # 调用GUI回调函数实时更新日志显示
    if self.gui_callback:
        try:
            self.gui_callback(log_entry)
        except Exception as e:
            print(f"GUI回调失败: {e}")

    return log_entry

def debug(self, message, component="General"):
    if self.levels[self.current_level] <= self.levels['DEBUG']:
        return self.log('DEBUG', message, component)

def info(self, message, component="General"):
    if self.levels[self.current_level] <= self.levels['INFO']:
        return self.log('INFO', message, component)

def warning(self, message, component="General"):
    if self.levels[self.current_level] <= self.levels['WARNING']:
        return self.log('WARNING', message, component)

def error(self, message, component="General"):
    return self.log('ERROR', message, component)

def critical(self, message, component="General"):
    return self.log('CRITICAL', message, component)

def get_logs(self, level=None):
    """获取指定级别的日志"""
    if level:
        return [log for log in self.logs if log['level'] == level]
    return self.logs

def export_logs(self, file_path=None):
    """导出日志到文件"""
    if not file_path:
        file_path = Path.home() / f"ocrx_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for log in self.logs:
                f.write(f"{log['timestamp']} - [{log['level']}] {log['component']} - {log['message']}\n")
        return str(file_path)
    except Exception as e:
        self.error(f"导出日志失败: {e}", "Logger")
        return None

def clear_logs(self):
    """清空日志"""
    self.logs.clear()
class OCRClient: """增强的OCR客户端，支持重试机制"""

def __init__(self, api_key, base_url, max_retries=3, retry_delay=1, logger=None):
    self.client = OpenAI(api_key=api_key, base_url=base_url)
    self.max_retries = max_retries
    self.retry_delay = retry_delay
    self.logger = logger or StructuredLogger()

def chat_completions_create(self, model, messages, timeout=300):
    """带重试机制的API调用"""
    last_exception = None

    for attempt in range(self.max_retries + 1):
        try:
            self.logger.debug(f"API调用尝试 {attempt + 1}/{self.max_retries + 1}")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=timeout
            )
            self.logger.debug("API调用成功")
            return response

        except Exception as e:
            last_exception = e
            self.logger.warning(f"API调用失败 (尝试 {attempt + 1}): {str(e)}")

            if attempt < self.max_retries:
                self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                time.sleep(self.retry_delay)
                self.retry_delay *= 2  # 指数退避
            else:
                self.logger.error(f"API调用最终失败: {str(e)}")
                raise last_exception

    raise last_exception


class OCRXGUIClass:
    def __init__(self, root):
        self.root = root
        self.root.title("OCRX-智能文字识别")
        self.root.geometry("1200x900")
        self.root.minsize(900, 700)  # 支持窗口调整

        # 任务执行状态
        self.is_running = False
        self.current_task = None
        self.task_lock = threading.Lock()

        # 进度跟踪变量
        self.total_pages_global = 0  # 全局总页数
        self.completed_pages_global = 0  # 全局已完成页数
        self.current_phase = "idle"  # "preprocess", "ocr", "merge"
        self.phase_descriptions = {
            "idle": "等待开始...",
            "preprocess": "图像预处理",
            "ocr": "文字识别",
            "merge": "合并结果"
        }

        # 剪贴板历史记录
        self.clipboard_history = ClipboardHistory()

        # 初始化结构化日志系统
        self.logger = StructuredLogger(gui_callback=self.log_callback)
        self.logger.info("应用程序启动", "System")

        # 初始化 OCR 客户端（带重试机制）
        self.ocr_client = None

        # --- 最初版本的默认值 ---
        self.resettable_defaults = {
            "MAX_WORKERS": "10",
            "PDF_SCALE_FACTOR": "3.0",
            "prompt_templates": {
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

请开始识别："""} }

    # 初始化 prompt_templates
    self.prompt_templates = self.resettable_defaults["prompt_templates"].copy()

    # --- 建议值列表 ---
    self.scale_options = ["1.0", "2.0", "3.0", "4.0", "5.0"]
    self.worker_options = ["1", "5", "10", "15", "20"]

    # --- 配置文件路径 ---
    self.config_file_path = Path.home() / ".ocrx_gui_config.json"

    # --- 加载配置 ---
    self.current_config = self.load_config()

    # --- 创建界面 ---
    self.create_widgets()

    # --- 加载配置到界面 ---
    self.populate_fields_from_config()

    # --- 绑定窗口调整事件 ---
    self.root.bind('<Configure>', self.on_window_resize)

def log_callback(self, log_entry):
    """日志回调函数，用于实时更新GUI日志显示"""
    if hasattr(self, 'log_text'):
        self.root.after(0, self.update_single_log_entry, log_entry)

def update_single_log_entry(self, log_entry):
    """更新单条日志条目到GUI"""
    try:
        self.log_text.config(state='normal')
        formatted_message = f"{log_entry['timestamp']} - [{log_entry['level']}] {log_entry['component']} - {log_entry['message']}\n"
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    except Exception as e:
        print(f"更新日志显示失败: {e}")

def on_window_resize(self, event):
    """响应窗口大小调整"""
    pass

def load_config(self):
    """从文件加载配置，如果文件不存在则使用初始默认值"""
    config = self.resettable_defaults.copy()

    if "OUTPUT_DIR" not in config or not config["OUTPUT_DIR"]:
        config["OUTPUT_DIR"] = str(Path.home() / "Documents")

    if self.config_file_path.exists():
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            for key in ["MAX_WORKERS", "PDF_SCALE_FACTOR"]:
                if key in loaded_config:
                    config[key] = loaded_config[key]

            if "prompt_templates" in loaded_config:
                merged_templates = config["prompt_templates"].copy()
                merged_templates.update(loaded_config["prompt_templates"])
                config["prompt_templates"] = merged_templates

            # 仅加载 API Key 和其他需要持久化的配置
            for key in ["BASE_URL", "MODEL_NAME", "OUTPUT_DIR", "API_KEY"]:
                if key in loaded_config:
                    config[key] = loaded_config[key]

        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}", "Config")
    else:
        self.logger.info("配置文件不存在，将使用默认配置", "Config")

    config.setdefault("API_KEY", "")
    return config

def save_config(self):
    """保存当前配置到文件"""
    config_to_save = {}
    config_to_save["MAX_WORKERS"] = self.workers_combobox.get().strip()
    config_to_save["PDF_SCALE_FACTOR"] = self.scale_combobox.get().strip()
    config_to_save["prompt_templates"] = self.prompt_templates

    # 仅保存 API Key 和其他需要持久化的配置
    for key in ["BASE_URL", "MODEL_NAME", "OUTPUT_DIR", "API_KEY"]:
        entry_widget = getattr(self, f"{key.lower()}_entry", None)
        if entry_widget:
            val = entry_widget.get().strip()
            if val:
                config_to_save[key] = val
        else:
            val = self.current_config.get(key, "").strip()
            if val:
                config_to_save[key] = val

    try:
        with open(self.config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
        self.logger.info(f"配置已保存至 {self.config_file_path}", "Config")
    except Exception as e:
        self.logger.error(f"保存配置文件失败: {e}", "Config")

def reset_to_defaults(self):
    """精确地重置指定的配置项为最初版本的默认值"""
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再重置配置。")
        return

    result = messagebox.askokcancel(
        "确认重置",
        "此操作将把以下配置项恢复为最初版本的默认值：\n"
        "- 最大并发数 (MAX_WORKERS)\n"
        "- PDF缩放比例 (PDF_SCALE_FACTOR)\n"
        "- 提示词预设 (Prompt Templates)\n\n"
        "其他配置（如 API Key, Base URL 等）不受影响。\n是否继续？"
    )
    if result:
        self.current_config.update(self.resettable_defaults)
        self.current_config.setdefault("OUTPUT_DIR", str(Path.home() / "Documents"))
        self.prompt_templates = self.resettable_defaults["prompt_templates"].copy()
        self.populate_fields_from_config(reset_specific_only=True)
        self.on_prompt_preset_selected()
        messagebox.showinfo("重置完成", "指定配置项已恢复为默认值。")

def populate_fields_from_config(self, reset_specific_only=False):
    """
    将 current_config 中的数据填充到GUI控件中。
    :param reset_specific_only: 如果为True，则只更新参与重置的字段。
    """
    if not reset_specific_only:
        entries_map = {
            "API_KEY": self.api_key_entry,
            "BASE_URL": self.base_url_entry,
            "MODEL_NAME": self.model_name_entry,
            "OUTPUT_DIR": self.output_dir_entry,
        }
        for key, widget in entries_map.items():
            value = self.current_config.get(key, "")
            widget.delete(0, tk.END)
            widget.insert(0, value)

    scale_val = self.current_config.get("PDF_SCALE_FACTOR", self.resettable_defaults["PDF_SCALE_FACTOR"])
    worker_val = self.current_config.get("MAX_WORKERS", self.resettable_defaults["MAX_WORKERS"])

    self.scale_combobox.set(scale_val)
    self.workers_combobox.set(worker_val)

    self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
    default_preset = "手写笔记"
    self.prompt_preset_var.set(default_preset)

def create_widgets(self):
    # 创建主框架
    main_frame = ttk.Frame(self.root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 创建notebook用于分页
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    # 主要配置页面
    config_frame = ttk.Frame(notebook)
    notebook.add(config_frame, text="主要配置")

    # 日志页面
    log_frame = ttk.Frame(notebook)
    notebook.add(log_frame, text="运行日志")

    # 剪贴板历史页面
    clipboard_frame = ttk.Frame(notebook)
    notebook.add(clipboard_frame, text="剪贴板历史")

    # 创建配置页面的组件
    self.create_config_widgets(config_frame)

    # 创建日志页面的组件
    self.create_log_widgets(log_frame)

    # 创建剪贴板历史页面的组件
    self.create_clipboard_widgets(clipboard_frame)

    # 创建底部按钮区域
    self.create_bottom_buttons(main_frame)

    def create_config_widgets(self, parent):
        """创建配置页面的组件"""
        # 使用 Grid 布局管理器
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

        # 文件路径（单个或多个）
        ttk.Label(parent, text="文件路径:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.file_paths_entry = ttk.Entry(parent, width=70)
        self.file_paths_entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")

        # 文件操作按钮框架
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
    ttk.Label(parent, text="PDF缩放比例:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    self.scale_combobox = ttk.Combobox(parent, values=self.scale_options, width=10, state="readonly")
    self.scale_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
    ttk.Label(parent, text="(建议值: 1.0 ~ 5.0)").grid(row=row, column=1, sticky="w", padx=120, pady=5)
    row += 1

    # 并发数
    ttk.Label(parent, text="最大并发数:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    self.workers_combobox = ttk.Combobox(parent, values=self.worker_options, width=10, state="readonly")
    self.workers_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
    ttk.Label(parent, text="(建议值: 5 ~ 20)").grid(row=row, column=1, sticky="w", padx=120, pady=5)
    row += 1

    # 提示词预设
    ttk.Label(parent, text="OCR提示词预设:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    self.prompt_preset_var = tk.StringVar()
    self.prompt_preset_combobox = ttk.Combobox(
        parent, textvariable=self.prompt_preset_var,
        values=list(self.prompt_templates.keys()), state="readonly", width=20
    )
    self.prompt_preset_combobox.bind("<<ComboboxSelected>>", self.on_prompt_preset_selected)
    self.prompt_preset_combobox.grid(row=row, column=1, sticky="w", padx=10, pady=5)

    # 提示词预设管理按钮框架（修改按钮文本）
    preset_button_frame = ttk.Frame(parent)
    preset_button_frame.grid(row=row, column=2, padx=5, sticky='w')

    ttk.Button(preset_button_frame, text="保存更改", command=self.edit_current_prompt).pack(side=tk.LEFT, padx=1)
    ttk.Button(preset_button_frame, text="另存为", command=self.save_new_prompt_template).pack(side=tk.LEFT, padx=1)
    ttk.Button(preset_button_frame, text="重命名", command=self.rename_prompt_template).pack(side=tk.LEFT, padx=1)
    ttk.Button(preset_button_frame, text="删除", command=self.delete_prompt_template).pack(side=tk.LEFT, padx=1)
    row += 1

    # 提示词编辑区
    ttk.Label(parent, text="自定义提示词:").grid(row=row, column=0, sticky="nw", padx=10, pady=5)
    self.prompt_text = scrolledtext.ScrolledText(parent, width=80, height=8)
    self.prompt_text.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="nsew")
    parent.grid_rowconfigure(row, weight=1)
    row += 1

    # --- 新增：指定页面范围 ---
    ttk.Label(parent, text="指定页码范围 (PDF):").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    self.page_range_var = tk.StringVar(value="")  # 默认为空，表示全部页面
    self.page_range_entry = ttk.Entry(parent, textvariable=self.page_range_var, width=20)
    self.page_range_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
    ttk.Label(parent, text="例如: 1,3,5-10 (逗号分隔, 连字符表示范围)").grid(row=row, column=1, sticky="w",
                                                                             padx=150, pady=5)
    row += 1

    # 实时进度显示区域（修改为整体进度）
    progress_frame = ttk.LabelFrame(parent, text="整体进度")
    progress_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    progress_frame.grid_columnconfigure(1, weight=1)

    ttk.Label(progress_frame, text="当前阶段:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    self.current_task_label = ttk.Label(progress_frame, text="等待开始...", foreground="gray")
    self.current_task_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(progress_frame, text="整体进度:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    self.progress_var = tk.StringVar(value="0%")
    self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var, foreground="blue")
    self.progress_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

    # 进度条
    self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
    self.progress_bar.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
    self.progress_bar['value'] = 0

    # 详细进度信息
    ttk.Label(progress_frame, text="详细信息:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    self.detail_progress_var = tk.StringVar(value="等待开始...")
    self.detail_progress_label = ttk.Label(progress_frame, textvariable=self.detail_progress_var,
                                           foreground="green")
    self.detail_progress_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)

    row += 1

def create_log_widgets(self, parent):
    """创建日志页面的组件"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    # 日志控制按钮
    log_control_frame = ttk.Frame(parent)
    log_control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

    ttk.Button(log_control_frame, text="清空日志", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
    ttk.Button(log_control_frame, text="导出日志", command=self.export_logs).pack(side=tk.LEFT, padx=5)

    # 日志级别选择
    ttk.Label(log_control_frame, text="日志级别:").pack(side=tk.LEFT, padx=(20, 5))
    self.log_level_var = tk.StringVar(value="DEBUG")
    log_level_combo = ttk.Combobox(
        log_control_frame,
        textvariable=self.log_level_var,
        values=["DEBUG", "INFO", "WARNING", "ERROR"],
        state="readonly",
        width=10
    )
    log_level_combo.pack(side=tk.LEFT, padx=5)
    log_level_combo.bind("<<ComboboxSelected>>", self.change_log_level)

    # 日志显示区域
    ttk.Label(parent, text="运行日志:").grid(row=1, column=0, sticky="nw", padx=10, pady=5)
    self.log_text = scrolledtext.ScrolledText(parent, width=120, height=25, state='disabled')
    self.log_text.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

def create_clipboard_widgets(self, parent):
    """创建剪贴板历史页面的组件"""
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=1)

    # 剪贴板历史控制按钮
    clipboard_control_frame = ttk.Frame(parent)
    clipboard_control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

    ttk.Button(clipboard_control_frame, text="清空历史", command=self.clear_clipboard_history).pack(side=tk.LEFT,
                                                                                                    padx=5)
    ttk.Button(clipboard_control_frame, text="刷新", command=self.refresh_clipboard_history).pack(side=tk.LEFT,
                                                                                                  padx=5)

    # 剪贴板历史显示区域
    ttk.Label(parent, text="剪贴板历史记录:").grid(row=1, column=0, sticky="nw", padx=10, pady=5)

    # 创建Treeview来显示历史记录
    columns = ('时间', '长度', '哈希', '状态', '方法', '预览')
    self.clipboard_tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)

    # 定义列标题
    for col in columns:
        self.clipboard_tree.heading(col, text=col)
        self.clipboard_tree.column(col, width=100)

    # 调整特定列的宽度
    self.clipboard_tree.column('时间', width=150)
    self.clipboard_tree.column('长度', width=80)
    self.clipboard_tree.column('哈希', width=80)
    self.clipboard_tree.column('状态', width=80)
    self.clipboard_tree.column('方法', width=80)
    self.clipboard_tree.column('预览', width=300)

    # 添加滚动条
    clipboard_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.clipboard_tree.yview)
    self.clipboard_tree.configure(yscrollcommand=clipboard_scrollbar.set)

    # 布局
    self.clipboard_tree.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
    clipboard_scrollbar.grid(row=1, column=1, padx=5, pady=5, sticky="ns")

    # 双击事件：查看详细信息
    self.clipboard_tree.bind('<Double-1>', self.show_clipboard_detail)

def show_clipboard_detail(self, event):
    """显示剪贴板历史详细信息"""
    selection = self.clipboard_tree.selection()
    if selection:
        item = self.clipboard_tree.item(selection[0])
        values = item['values']
        if len(values) >= 6:
            detail_msg = f"时间: {values[0]}\n长度: {values[1]}\n哈希: {values[2]}\n状态: {values[3]}\n方法: {values[4]}\n预览: {values[5]}"
            messagebox.showinfo("剪贴板历史详情", detail_msg)

def refresh_clipboard_history(self):
    """刷新剪贴板历史显示"""
    # 清空现有项目
    for item in self.clipboard_tree.get_children():
        self.clipboard_tree.delete(item)

    # 添加历史记录
    for record in self.clipboard_history.get_history():
        self.clipboard_tree.insert('', tk.END, values=(
            record['timestamp'],
            record['content_length'],
            record['content_hash'],
            '成功' if record['success'] else '失败',
            record['method'],
            record['content_preview']
        ))

def clear_clipboard_history(self):
    """清空剪贴板历史"""
    self.clipboard_history.clear_history()
    self.refresh_clipboard_history()
    self.logger.info("剪贴板历史已清空", "Clipboard")

def create_bottom_buttons(self, parent):
    """创建底部按钮区域"""
    # 按钮区域
    button_frame = ttk.Frame(parent)
    button_frame.pack(fill=tk.X, pady=10)

    self.save_button = ttk.Button(button_frame, text="识别并保存", command=self.start_ocr_and_save_thread,
                                  width=15)
    self.save_button.pack(side=tk.LEFT, padx=5)

    self.copy_button = ttk.Button(button_frame, text="识别并复制", command=self.start_ocr_only_thread,
                                  width=15)
    self.copy_button.pack(side=tk.LEFT, padx=5)

    self.reset_button = ttk.Button(button_frame, text="重置为默认值", command=self.reset_to_defaults,
                                   width=15)
    self.reset_button.pack(side=tk.LEFT, padx=5)

    # 取消按钮（初始隐藏）
    self.cancel_button = ttk.Button(button_frame, text="取消任务", command=self.cancel_current_task,
                                    width=15, state='disabled')
    self.cancel_button.pack(side=tk.LEFT, padx=5)

def change_log_level(self, event=None):
    """改变日志级别"""
    level = self.log_level_var.get()
    self.logger.current_level = level
    self.logger.info(f"日志级别已更改为: {level}", "Logger")

def clear_logs(self):
    """清空日志显示"""
    self.log_text.config(state='normal')
    self.log_text.delete(1.0, tk.END)
    self.log_text.config(state='disabled')
    self.logger.clear_logs()
    self.logger.info("日志已清空", "Logger")

def export_logs(self):
    """导出日志到文件"""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="导出日志文件"
    )
    if file_path:
        exported_path = self.logger.export_logs(file_path)
        if exported_path:
            self.logger.info(f"日志已导出至: {exported_path}", "Logger")
            messagebox.showinfo("成功", f"日志已导出至:\n{exported_path}")
        else:
            messagebox.showerror("错误", "日志导出失败！")

def update_log_display(self):
    """更新日志显示区域（批量更新）"""
    self.log_text.config(state='normal')
    self.log_text.delete(1.0, tk.END)

    # 显示最新的3000条日志（进一步增加数量）
    logs = self.logger.get_logs()[-3000:] if len(self.logger.get_logs()) > 3000 else self.logger.get_logs()

    for log_entry in logs:
        formatted_message = f"{log_entry['timestamp']} - [{log_entry['level']}] {log_entry['component']} - {log_entry['message']}\n"
        self.log_text.insert(tk.END, formatted_message)

    self.log_text.see(tk.END)
    self.log_text.config(state='disabled')

def parse_page_range(self, page_range_str, total_pages):
    """
    解析页码范围字符串，例如 "1,3,5-10"，返回一个页码列表。
    :param page_range_str: 页码范围字符串
    :param total_pages: PDF总页数
    :return: 有效的页码列表 (从1开始)
    """
    if not page_range_str.strip():
        return list(range(1, total_pages + 1))  # 空字符串返回全部页

    pages = set()
    parts = page_range_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if 1 <= start <= end <= total_pages:
                    pages.update(range(start, end + 1))
                else:
                    self.logger.warning(f"页码范围 '{part}' 超出有效范围 (1-{total_pages}) 或无效，已忽略。",
                                        "PageRange")
            except ValueError:
                self.logger.warning(f"无法解析页码范围 '{part}'，已忽略。", "PageRange")
        else:
            try:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    pages.add(page_num)
                else:
                    self.logger.warning(f"页码 '{page_num}' 超出有效范围 (1-{total_pages})，已忽略。", "PageRange")
            except ValueError:
                self.logger.warning(f"无法解析页码 '{part}'，已忽略。", "PageRange")

    sorted_pages = sorted(list(pages))
    self.logger.info(f"解析得到指定页码: {sorted_pages}", "PageRange")
    return sorted_pages

def update_overall_progress(self, phase, detail_info="", completed_pages=None, total_pages=None):
    """
    更新整体进度显示，包含阶段和百分比。
    :param phase: 阶段名称 ("preprocess", "ocr", "merge", "idle")
    :param detail_info: 详细的进度信息文本
    :param completed_pages: 已完成的页数 (用于 "ocr" 阶段)
    :param total_pages: 总页数 (用于 "ocr" 阶段)
    """
    self.current_phase = phase
    description = self.phase_descriptions.get(phase, "未知阶段")

    self.current_task_label.config(text=description)
    self.detail_progress_var.set(detail_info)

    percentage = 0
    if phase == "preprocess":
        # 预处理阶段：0% - 20%
        percentage = 20  # 简化处理，预处理完成后直接到20%
    elif phase == "ocr":
        # 识别阶段：21% - 99%
        if total_pages and total_pages > 0 and completed_pages is not None:
            # 计算识别阶段的百分比 (21-99% -> 78%的跨度)
            ocr_percentage = int((completed_pages / total_pages) * 78)
            percentage = 21 + ocr_percentage
            # 确保不超过99%
            percentage = min(percentage, 99)
            self.progress_var.set(f"{completed_pages}/{total_pages} 页 ({percentage}%)")
        else:
            percentage = 21
            self.progress_var.set("开始识别...")
    elif phase == "merge":
        # 合并阶段：99% - 100%
        percentage = 99
        self.progress_var.set("合并结果...")
    elif phase == "idle":
        percentage = 100
        self.progress_var.set("完成")

    self.progress_bar['value'] = percentage
    self.root.update_idletasks()

def reset_progress(self):
    """重置进度显示"""
    self.progress_var.set("0%")
    self.detail_progress_var.set("等待开始...")
    self.progress_bar['value'] = 0
    self.current_task_label.config(text="等待开始...")
    self.current_phase = "idle"
    self.total_pages_global = 0
    self.completed_pages_global = 0
    self.root.update_idletasks()

def select_files(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再选择文件。")
        return

    file_paths = filedialog.askopenfilenames(
        filetypes=[
            ("All Supported Files", "*.pdf *.jpg *.jpeg *.png"),
            ("PDF files", "*.pdf"),
            ("Image files", "*.jpg *.jpeg *.png")
        ]
    )
    if file_paths:
        self.file_paths_entry.delete(0, tk.END)
        self.file_paths_entry.insert(0, "; ".join(file_paths))

def clear_file_paths(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再清空文件。")
        return
    self.file_paths_entry.delete(0, tk.END)

def select_output_dir(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再选择输出目录。")
        return

    dir_path = filedialog.askdirectory()
    if dir_path:
        self.output_dir_entry.delete(0, tk.END)
        self.output_dir_entry.insert(0, dir_path)

def on_prompt_preset_selected(self, event=None):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再更改预设。")
        return

    selected = self.prompt_preset_var.get()
    if selected in self.prompt_templates:
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(tk.END, self.prompt_templates[selected])

def edit_current_prompt(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再编辑预设。")
        return

    current_text = self.prompt_text.get("1.0", tk.END).strip()
    selected_preset = self.prompt_preset_var.get()
    if selected_preset in self.prompt_templates:
        self.prompt_templates[selected_preset] = current_text
        messagebox.showinfo("成功", f"已更新 '{selected_preset}' 预设的内容。")
    else:
        messagebox.showwarning("警告", "请选择一个有效的预设进行编辑。")

def save_new_prompt_template(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再保存预设。")
        return

    new_name = simpledialog.askstring("新建预设", "请输入新的提示词预设名称:")
    if new_name:
        if new_name in self.prompt_templates:
            result = messagebox.askyesno("确认", f"预设 '{new_name}' 已存在，是否覆盖？")
            if not result:
                return
        content = self.prompt_text.get("1.0", tk.END).strip()
        self.prompt_templates[new_name] = content
        self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
        self.prompt_preset_var.set(new_name)
        messagebox.showinfo("成功", f"已保存为预设: {new_name}")

def rename_prompt_template(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再重命名预设。")
        return

    selected_preset = self.prompt_preset_var.get()

    if not selected_preset:
        messagebox.showwarning("警告", "请先选择一个预设进行重命名。")
        return

    default_presets = ["手写笔记", "印刷材料"]
    if selected_preset in default_presets:
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

    content = self.prompt_templates[selected_preset]
    del self.prompt_templates[selected_preset]
    self.prompt_templates[new_name] = content

    self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())
    self.prompt_preset_var.set(new_name)

    messagebox.showinfo("成功", f"预设 '{selected_preset}' 已重命名为 '{new_name}'。")

def delete_prompt_template(self):
    # 检查是否有正在运行的任务
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再删除预设。")
        return

    selected_preset = self.prompt_preset_var.get()

    if not selected_preset:
        messagebox.showwarning("警告", "请先选择一个预设进行删除。")
        return

    default_presets = ["手写笔记", "印刷材料"]
    if selected_preset in default_presets:
        messagebox.showwarning("警告", f"不能删除系统默认预设 '{selected_preset}'。")
        return

    result = messagebox.askyesno("确认删除", f"确定要删除预设 '{selected_preset}' 吗？此操作不可撤销。")
    if not result:
        return

    if selected_preset in self.prompt_templates:
        del self.prompt_templates[selected_preset]

        self.prompt_preset_combobox['values'] = list(self.prompt_templates.keys())

        if self.prompt_preset_var.get() == selected_preset:
            self.prompt_text.delete(1.0, tk.END)
            if self.prompt_templates:
                first_preset = list(self.prompt_templates.keys())[0]
                self.prompt_preset_var.set(first_preset)
                self.prompt_text.insert(tk.END, self.prompt_templates[first_preset])
            else:
                self.prompt_preset_var.set("")

        messagebox.showinfo("成功", f"预设 '{selected_preset}' 已删除。")
    else:
        messagebox.showwarning("警告", "预设不存在。")

def pdf_to_images(self, pdf_path, scale_factor, page_range_str=None):
    """
    将PDF转换为图片，支持指定页码范围。
    :param pdf_path: PDF文件路径
    :param scale_factor: 缩放因子
    :param page_range_str: 页码范围字符串 (e.g., "1,3,5-10")
    :return: [(page_num, image_data), ...]
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    self.logger.info(f"PDF总页数: {total_pages}", "PDFProcessing")

    解析页码范围
    specified_pages = self.parse_page_range(page_range_str, total_pages)
    self.logger.info(f"需要处理的页码: {specified_pages}", "PDFProcessing")

    images = []
    for page_num in specified_pages:
        # fitz 页码从0开始
        page_index = page_num - 1
        try:
            page = doc.load_page(page_index)
            mat = fitz.Matrix(scale_factor, scale_factor)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            images.append((page_num, img_data))  # 返回用户指定的页码(从1开始)
            self.logger.debug(f"已转换第 {page_num} 页", "PDFProcessing")
        except Exception as e:
            self.logger.error(f"转换第 {page_num} 页失败: {e}", "PDFProcessing")
    doc.close()
    self.logger.info(f"成功转换 {len(images)} 页图像。", "PDFProcessing")
    return images

def image_file_to_bytes(self, image_path):
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')
            return byte_arr.getvalue()
    except Exception as e:
        self.logger.error(f"处理图片文件 {image_path} 失败: {e}", "ImageProcessing")
        return None

def image_to_base64(self, image_data):
    return base64.b64encode(image_data).decode('utf-8')

def process_single_image(self, client, model_name, prompt, identifier, image_data):
    """处理单张图片（PDF页或图片文件转换后的）"""
    try:
        image_base64 = self.image_to_base64(image_data)
        response = client.chat_completions_create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            timeout=60
        )
        return (identifier, response.choices[0].message.content)
    except Exception as e:
        error_msg = f"识别失败: {str(e)}"
        self.logger.error(f"页面识别异常: {error_msg}", "OCR")
        return (identifier, error_msg)

def merge_contents_to_markdown(self, results):
    results.sort(key=lambda x: x[0])  # 按页码排序

    valid_contents = []

    for identifier, content in results:
        if content is not None:
            content_str = str(content).strip()
            if content_str and not content_str.startswith("识别失败"):
                valid_contents.append(content_str)
            elif content_str.startswith("识别失败"):
                # 对于识别失败的页面，添加注释
                file_stem, page_num = identifier
                failure_note = f"\n<!-- 第{page_num}页识别失败 -->\n"
                valid_contents.append(failure_note)
                self.logger.warning(f"页面 {identifier} 识别失败，已添加注释", "Merge")

    if valid_contents:
        combined_content = '\n\n'.join(valid_contents)
        return combined_content
    else:
        return "*未识别到有效内容*"

def process_single_file_for_save(self, file_path, client, model_name, ocr_prompt, scale_factor, max_workers,
                                 page_range_str=None):
    path_obj = Path(file_path)
    if not path_obj.exists():
        self.logger.warning(f"文件不存在，跳过: {file_path}", "FileProcessing")
        return (False, None, None)

    source_file_stem = path_obj.stem
    self.logger.info(f"开始处理文件: {path_obj.name}", "FileProcessing")

    images_to_process = []
    suffix_lower = path_obj.suffix.lower()

    if suffix_lower == '.pdf':
        try:
            self.logger.info(f"正在将PDF {path_obj.name} 转换为图片...", "PDFProcessing")
            # 传递页码范围
            images_to_process = self.pdf_to_images(str(path_obj), scale_factor, page_range_str)
            self.logger.info(f"成功转换 {len(images_to_process)} 页图像 from {path_obj.name}.", "PDFProcessing")
        except Exception as e:
            self.logger.error(f"PDF转换失败 {path_obj.name}: {e}", "PDFProcessing")
            return (False, None, source_file_stem)
    elif suffix_lower in ['.jpg', '.jpeg', '.png']:
        # 图片文件不支持页码范围，忽略 page_range_str
        if page_range_str:
            self.logger.info(f"图片文件 {path_obj.name} 不支持指定页码范围，将处理整个文件。", "ImageProcessing")
        try:
            self.logger.info(f"正在准备图片文件 {path_obj.name} ...", "ImageProcessing")
            img_data = self.image_file_to_bytes(str(path_obj))
            if img_data:
                images_to_process = [(1, img_data)]
            else:
                self.logger.warning(f"图片文件 {path_obj.name} 数据为空，跳过。", "ImageProcessing")
                return (False, None, source_file_stem)
        except Exception as e:
            self.logger.error(f"图片处理失败 {path_obj.name}: {e}", "ImageProcessing")
            return (False, None, source_file_stem)
    else:
        self.logger.warning(f"不支持的文件类型，跳过: {file_path}", "FileProcessing")
        return (False, None, source_file_stem)

    if not images_to_process:
        self.logger.warning(f"文件 {path_obj.name} 没有可处理的内容。", "FileProcessing")
        return (False, None, source_file_stem)

    total_pages = len(images_to_process)
    self.logger.info(f"开始识别文件 {path_obj.name} 的 {total_pages} 页...", "OCR")

    # 更新全局进度变量
    self.total_pages_global = total_pages
    self.completed_pages_global = 0

    results = []
    completed_pages = 0

    # 更新进度到预处理完成 (20%)
    self.update_overall_progress("preprocess", f"已处理文件: {path_obj.name}")

    # 进入OCR阶段
    self.update_overall_progress("ocr", f"开始识别第 {completed_pages + 1} 页...", 0, total_pages)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(images_to_process))) as executor:
        future_to_page = {
            executor.submit(self.process_single_image, client, model_name, ocr_prompt, (source_file_stem, page_num),
                            img_data): page_num
            for page_num, img_data in images_to_process
        }

        for future in as_completed(future_to_page):
            if not self.is_running:  # 检查是否被取消
                self.logger.info("任务被用户取消", "OCR")
                return (False, None, source_file_stem)

            page_num = future_to_page[future]
            try:
                identifier, content = future.result(timeout=120)
                results.append((identifier, content))
                completed_pages += 1
                self.completed_pages_global += 1
                self.logger.info(f"{path_obj.name} - {completed_pages}/{total_pages} - 第 {page_num} 页识别完成。",
                                 "OCRProgress")
                # 更新整体进度（OCR阶段）
                self.update_overall_progress(
                    "ocr",
                    f"正在识别第 {completed_pages + 1 if completed_pages < total_pages else completed_pages} 页...",
                    completed_pages,
                    total_pages
                )
            except Exception as e:
                error_msg = f"识别失败: {str(e)}"
                results.append(((source_file_stem, page_num), error_msg))
                completed_pages += 1
                self.completed_pages_global += 1
                self.logger.error(
                    f"{path_obj.name} - {completed_pages}/{total_pages} - 第 {page_num} 页处理异常: {e}",
                    "OCRError")
                # 更新整体进度
                self.update_overall_progress(
                    "ocr",
                    f"正在识别第 {completed_pages + 1 if completed_pages < total_pages else completed_pages} 页...",
                    completed_pages,
                    total_pages
                )

    # 进入合并阶段
    self.update_overall_progress("merge", "正在合并识别结果...")

    self.logger.info(f"正在合并 {path_obj.name} 的识别结果...", "Merge")
    markdown_content = self.merge_contents_to_markdown(results)

    self.logger.info(f"文件 {path_obj.name} 识别完成。", "FileProcessing")
    return (True, markdown_content, source_file_stem)

def prepare_all_images_with_order(self, file_list, scale_factor, page_ranges_dict):
    """
    准备批量处理的所有图像数据，支持指定页码。
    :param file_list: 文件路径列表
    :param scale_factor: 缩放因子
    :param page_ranges_dict: {file_path: page_range_str} 的字典
    :return: [(file_index, file_name, page_num, image_data), ...]
    """
    all_images = []
    for file_index, file_path in enumerate(file_list):
        if not self.is_running:  # 检查是否被取消
            self.logger.info("任务被用户取消", "BatchProcessing")
            return []

        path_obj = Path(file_path)
        if not path_obj.exists():
            self.logger.warning(f"文件不存在，跳过: {file_path}", "BatchProcessing")
            continue

        page_range_str = page_ranges_dict.get(file_path, "")  # 获取该文件的页码范围

        suffix_lower = path_obj.suffix.lower()
        images_for_this_file = []

        if suffix_lower == '.pdf':
            try:
                self.logger.info(
                    f"正在将PDF {path_obj.name} 转换为图片 (页码范围: {page_range_str if page_range_str else '全部'})...",
                    "BatchPDF")
                # 传递页码范围
                images_for_this_file = self.pdf_to_images(str(path_obj), scale_factor, page_range_str)
            except Exception as e:
                self.logger.error(f"PDF转换失败 {path_obj.name}: {e}", "BatchPDF")
                continue
        elif suffix_lower in ['.jpg', '.jpeg', '.png']:
            if page_range_str:
                self.logger.info(f"图片文件 {path_obj.name} 不支持指定页码范围，将处理整个文件。", "BatchImage")
            try:
                img_data = self.image_file_to_bytes(str(path_obj))
                if img_data:
                    images_for_this_file = [(1, img_data)]
                else:
                    self.logger.warning(f"图片文件 {path_obj.name} 数据为空，跳过。", "BatchImage")
                    continue
            except Exception as e:
                self.logger.error(f"图片处理失败 {path_obj.name}: {e}", "BatchImage")
                continue
        else:
            self.logger.warning(f"不支持的文件类型，跳过: {file_path}", "BatchProcessing")
            continue

        for page_num, img_data in images_for_this_file:
            all_images.append((file_index, path_obj.name, page_num, img_data))

    return all_images

def start_ocr_and_save_thread(self):
    """启动识别并保存任务"""
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再开始新任务。")
        return

    # 在新线程中启动任务
    thread = threading.Thread(target=self._run_ocr_logic, args=(True,))
    thread.daemon = True
    thread.start()

def start_ocr_only_thread(self):
    """启动识别并复制任务"""
    if self.is_running:
        messagebox.showwarning("警告", "当前有任务正在运行，请等待完成后再开始新任务。")
        return

    # 在新线程中启动任务
    thread = threading.Thread(target=self._run_ocr_logic, args=(False,))
    thread.daemon = True
    thread.start()

def cancel_current_task(self):
    """取消当前任务"""
    if self.is_running:
        result = messagebox.askyesno("确认取消", "确定要取消当前任务吗？")
        if result:
            self.is_running = False
            self.logger.info("用户请求取消任务", "MainProcess")
            messagebox.showinfo("提示", "任务取消请求已发送，请等待当前操作完成。")

def _enhanced_copy_to_clipboard(self, text_to_copy, method="auto", max_retries=4):
    """
    增强的剪贴板复制函数，包含严格验证和自动重试机制
    """
    if not CLIPBOARD_AVAILABLE:
        error_msg = "剪贴板功能不可用"
        self.logger.warning(error_msg, "Clipboard")
        self.clipboard_history.add_record(text_to_copy, success=False, method=method, error_msg=error_msg)
        return False, error_msg

    try:
        text_length = len(text_to_copy)
        self.logger.info(f"准备复制文本，长度: {text_length} 字符", "Clipboard")

        if text_length == 0:
            error_msg = "文本为空，无需复制"
            self.logger.warning(error_msg, "Clipboard")
            self.clipboard_history.add_record(text_to_copy, success=False, method=method, error_msg=error_msg)
            return False, error_msg

        # 尝试复制（带重试机制）
        last_error = ""
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"剪贴板复制尝试 {attempt + 1}/{max_retries}", "Clipboard")

                # 执行复制操作
                if 'pyperclip' in globals():
                    self.logger.debug("使用 pyperclip 复制到剪贴板", "Clipboard")
                    pyperclip.copy(text_to_copy)
                else:
                    self.logger.debug("使用 tkinter 复制到剪贴板", "Clipboard")
                    dummy_root = tk.Tk()
                    dummy_root.withdraw()
                    dummy_root.clipboard_clear()
                    dummy_root.clipboard_append(text_to_copy)
                    dummy_root.update()
                    dummy_root.destroy()

                # 添加延迟确保复制完成
                delay_time = min(0.1 + (attempt * 0.1), 0.5)  # 逐步增加延迟，最大500ms
                time.sleep(delay_time)

                # 严格验证复制结果
                verification_result = self._strict_verify_clipboard_content(text_to_copy)
                if verification_result['success']:
                    self.logger.info(f"剪贴板复制验证成功 (尝试 {attempt + 1})", "Clipboard")
                    self.clipboard_history.add_record(text_to_copy, success=True, method=method)
                    return True, "复制成功"
                else:
                    last_error = verification_result['error']
                    self.logger.warning(f"剪贴板验证失败 (尝试 {attempt + 1}): {last_error}", "Clipboard")

            except Exception as e:
                last_error = f"复制异常: {str(e)}"
                self.logger.warning(f"剪贴板复制异常 (尝试 {attempt + 1}): {last_error}", "Clipboard")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = min(0.2 * (2 ** attempt), 1.0)  # 指数退避，最大1秒
                self.logger.info(f"等待 {wait_time} 秒后重试...", "Clipboard")
                time.sleep(wait_time)

        # 所有重试都失败了
        error_msg = f"剪贴板复制最终失败: {last_error}"
        self.logger.error(error_msg, "Clipboard")
        self.clipboard_history.add_record(text_to_copy, success=False, method=method, error_msg=error_msg)
        self.refresh_clipboard_history()  # 更新历史显示
        return False, error_msg

    except Exception as e:
        error_msg = f"剪贴板复制过程异常: {str(e)}"
        self.logger.error(error_msg, "Clipboard")
        self.clipboard_history.add_record(text_to_copy, success=False, method=method, error_msg=error_msg)
        self.refresh_clipboard_history()  # 更新历史显示
        return False, error_msg

def _strict_verify_clipboard_content(self, expected_content):
    """
    严格的剪贴板内容验证 (更新版)
    返回: {'success': bool, 'error': str}
    """
    try:
        if not CLIPBOARD_AVAILABLE:
            return {'success': False, 'error': '剪贴板功能不可用'}

        # 获取剪贴板内容
        if 'pyperclip' in globals():
            clipboard_content = pyperclip.paste()
        else:
            # tkinter 方式获取剪贴板内容
            dummy_root = tk.Tk()
            dummy_root.withdraw()
            try:
                clipboard_content = dummy_root.clipboard_get()
            except tk.TclError:
                dummy_root.destroy()
                return {'success': False, 'error': '无法获取剪贴板内容'}
            dummy_root.destroy()

        # 验证内容
        expected_length = len(expected_content)
        clipboard_length = len(clipboard_content)

        self.logger.debug(f"预期长度: {expected_length}, 实际长度: {clipboard_length}", "Clipboard")

        # 1. 长度完全相同，直接比较内容
        if expected_length == clipboard_length:
            if clipboard_content == expected_content:
                return {'success': True, 'error': ''}
            else:
                # 尝试找出差异位置
                mismatch_pos = -1
                for i in range(min(len(expected_content), len(clipboard_content))):
                    if expected_content[i] != clipboard_content[i]:
                        mismatch_pos = i
                        break
                return {'success': False, 'error': f'内容不匹配，第一个差异位置: {mismatch_pos}'}

        # 2. 长度不同，检查误差是否在千分之五以内
        length_diff = abs(expected_length - clipboard_length)
        tolerance = expected_length * 0.005

        if length_diff <= tolerance:
            # 误差在千分之五内，验证首尾各20字符
            head_len = min(20, expected_length, clipboard_length)
            tail_len = min(20, expected_length, clipboard_length)

            expected_head = expected_content[:head_len]
            expected_tail = expected_content[-tail_len:]
            clipboard_head = clipboard_content[:head_len]
            clipboard_tail = clipboard_content[-tail_len:]

            if expected_head == clipboard_head and expected_tail == clipboard_tail:
                return {'success': True, 'error': f'长度略有差异({length_diff}字符)，但首尾内容匹配'}
            else:
                return {'success': False, 'error': f'长度略有差异({length_diff}字符)，且首尾内容不匹配'}
        else:
            # 3. 误差超过千分之五，直接不通过
            return {'success': False, 'error': f'长度差异过大({length_diff}字符 > {tolerance:.2f}字符)'}

    except Exception as e:
        return {'success': False, 'error': f'验证过程异常: {str(e)}'}

def _save_to_temp_file(self, text_content, output_dir):
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_file = output_path / f"ocr_result_{timestamp}.md"

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(text_content)

        self.logger.info(f"结果已保存到临时文件: {temp_file}", "FileSave")
        return str(temp_file)
    except Exception as e:
        self.logger.error(f"保存临时文件失败: {e}", "FileSave")
        return None

def _process_and_copy_all_unified(self, client, model_name, ocr_prompt, scale_factor, max_workers, file_list,
                                  output_dir, page_ranges_dict):
    self.logger.info("正在准备所有文件的图像数据...", "BatchProcessing")
    # 传递页码范围字典
    all_images_info = self.prepare_all_images_with_order(file_list, scale_factor, page_ranges_dict)

    if not self.is_running:
        return

    if not all_images_info:
        self.logger.error("没有任何有效的图像可供识别。", "BatchProcessing")
        messagebox.showwarning("警告", "没有任何有效的图像可供识别。")
        return

    total_images = len(all_images_info)
    self.logger.info(f"总共 {total_images} 页图像待识别...", "BatchProcessing")

    # 更新全局进度变量
    self.total_pages_global = total_images
    self.completed_pages_global = 0

    # 更新进度到预处理完成 (20%)
    self.update_overall_progress("preprocess", "批量文件预处理完成")

    batch_size = 50
    results = []
    completed_pages = 0

    # 进入OCR阶段
    self.update_overall_progress("ocr", f"开始识别第 {completed_pages + 1} 页...", 0, total_images)

    for i in range(0, total_images, batch_size):
        if not self.is_running:  # 检查是否被取消
            self.logger.info("任务被用户取消", "BatchProcessing")
            return

        batch = all_images_info[i:i + batch_size]
        batch_number = (i // batch_size) + 1
        total_batches = (total_images + batch_size - 1) // batch_size

        self.logger.info(f"开始处理第 {batch_number}/{total_batches} 批，共 {len(batch)} 页...", "BatchProcessing")

        batch_results = []
        batch_completed = 0

        current_max_workers = min(max_workers, len(batch))
        self.logger.debug(f"当前批次使用 {current_max_workers} 个工作线程", "BatchProcessing")

        with ThreadPoolExecutor(max_workers=current_max_workers) as executor:
            future_to_info = {
                executor.submit(
                    self.process_single_image,
                    client,
                    model_name,
                    ocr_prompt,
                    (info[0], info[2]),  # (file_index, page_num)
                    info[3]  # image_data
                ): info for info in batch
            }

            for future in as_completed(future_to_info):
                if not self.is_running:  # 检查是否被取消
                    self.logger.info("任务被用户取消", "BatchProcessing")
                    return

                info = future_to_info[future]
                try:
                    identifier, content = future.result(timeout=120)
                    batch_results.append((identifier, content))
                    batch_completed += 1
                    completed_pages += 1
                    self.completed_pages_global += 1
                    self.logger.info(
                        f"批次 {batch_number} - {batch_completed}/{len(batch)} - 总进度 {completed_pages}/{total_images}",
                        "BatchProgress")
                    # 更新整体进度 (OCR阶段)
                    self.update_overall_progress(
                        "ocr",
                        f"正在识别第 {completed_pages + 1 if completed_pages < total_images else completed_pages} 页...",
                        completed_pages,
                        total_images
                    )
                except Exception as e:
                    error_msg = f"识别失败: {str(e)}"
                    batch_results.append(((info[0], info[2]), error_msg))
                    batch_completed += 1
                    completed_pages += 1
                    self.completed_pages_global += 1
                    self.logger.error(f"页面识别异常: {e}", "BatchError")
                    self.logger.info(
                        f"批次 {batch_number} - {batch_completed}/{len(batch)} - 总进度 {completed_pages}/{total_images}",
                        "BatchProgress")
                    # 更新整体进度
                    self.update_overall_progress(
                        "ocr",
                        f"正在识别第 {completed_pages + 1 if completed_pages < total_images else completed_pages} 页...",
                        completed_pages,
                        total_images
                    )

        results.extend(batch_results)
        self.logger.info(f"第 {batch_number}/{total_batches} 批处理完成", "BatchProcessing")

    if not self.is_running:
        return

    self.logger.info("正在排序识别结果...", "BatchProcessing")
    results.sort(key=lambda x: x[0])

    success_count = sum(1 for _, content in results if content and not str(content).startswith("识别失败"))
    fail_count = len(results) - success_count
    self.logger.info(f"识别完成 - 成功: {success_count} 页, 失败: {fail_count} 页", "BatchStats")

    # 进入合并阶段
    self.update_overall_progress("merge", "正在合并识别结果...")

    self.logger.info("正在合并所有识别结果...", "BatchProcessing")
    merged_md = self.merge_contents_to_markdown(results)

    title_line = "# 合并识别结果\n"
    final_md = title_line + merged_md if merged_md else "*未识别到有效内容*"

    result_length = len(final_md)
    self.logger.info(f"合并完成，最终文本长度: {result_length} 字符", "BatchProcessing")

    self.logger.info("正在复制结果到剪贴板...", "Clipboard")
    copy_success, copy_msg = self._enhanced_copy_to_clipboard(final_md, method="batch_copy", max_retries=4)

    if copy_success:
        self.logger.info("剪贴板复制最终验证成功", "Clipboard")
        messagebox.showinfo("完成",
                            f"识别并复制完成！\n总共处理 {total_images} 页，成功 {success_count} 页。\n结果已复制到剪贴板。")
    else:
        self.logger.warning(f"剪贴板复制最终验证失败: {copy_msg}", "Clipboard")
        temp_file_path = self._save_to_temp_file(final_md, output_dir)
        if temp_file_path:
            messagebox.showinfo("完成",
                                f"识别完成但剪贴板复制失败！\n结果已保存到临时文件: {temp_file_path}\n错误信息: {copy_msg}")
        else:
            messagebox.showerror("错误", f"剪贴板复制和文件保存都失败了！\n错误信息: {copy_msg}")

def _run_ocr_logic(self, save_to_file=True):
    """主OCR处理逻辑"""
    # 使用锁确保一次只执行一个任务
    with self.task_lock:
        if self.is_running:
            self.logger.warning("任务已在运行中", "TaskManager")
            return

        self.is_running = True
        self.current_task = "OCR处理"

        # 更新UI状态
        self.root.after(0, self._update_ui_for_running_state, True)

        try:
            self.logger.info("开始OCR处理流程", "MainProcess")

            api_key = self.api_key_entry.get().strip()
            base_url = self.base_url_entry.get().strip()
            model_name = self.model_name_entry.get().strip()
            output_dir = self.output_dir_entry.get().strip() if save_to_file or not save_to_file else self.current_config.get(
                "OUTPUT_DIR", str(Path.home() / "Documents"))
            scale_factor = float(self.scale_combobox.get().strip())
            max_workers = int(self.workers_combobox.get().strip())
            ocr_prompt = self.prompt_text.get("1.0", tk.END).strip()
            # 获取页码范围输入
            page_range_input = self.page_range_var.get().strip()

            if not api_key or not base_url or not model_name:
                self.logger.error("请填写API Key, Base URL和Model Name！", "Validation")
                messagebox.showerror("错误", "请填写API Key, Base URL和Model Name！")
                return

            if not output_dir:
                output_dir = str(Path.home() / "Documents")
                self.logger.info(f"未指定输出目录，使用默认目录: {output_dir}", "Config")

            self.current_config.update({
                "API_KEY": api_key,
                "BASE_URL": base_url,
                "MODEL_NAME": model_name,
                "OUTPUT_DIR": output_dir,
                "MAX_WORKERS": str(max_workers),
                "PDF_SCALE_FACTOR": str(scale_factor),
            })

# 使用带重试机制的OCR客户端
            self.ocr_client = OCRClient(api_key, base_url, max_retries=3, retry_delay=1, logger=self.logger)

            file_paths_str = self.file_paths_entry.get().strip()
            if not file_paths_str:
                self.logger.error("请选择至少一个文件！", "Validation")
                messagebox.showerror("错误", "请选择至少一个文件！")
                return

            file_list = [fp.strip() for fp in file_paths_str.split(';') if fp.strip()]
            if not file_list:
                self.logger.error("文件列表为空！", "Validation")
                messagebox.showerror("错误", "文件列表为空！")
                return

            self.logger.info(f"处理模式: {'保存' if save_to_file else '复制'}，文件数量: {len(file_list)}",
                             "MainProcess")

            # 处理页码范围
            page_ranges_dict = {}  # {file_path: page_range_str}
            if len(file_list) == 1:
                # 单文件模式，直接使用输入框的值
                page_ranges_dict[file_list[0]] = page_range_input
                self.logger.info(f"单文件模式，指定页码范围: {page_range_input if page_range_input else '全部'}",
                                 "PageRange")
            else:
                # 多文件模式，需要解析输入框的值
                # 简单处理：如果输入框有内容且文件数>1，则尝试将其作为所有文件的通用范围
                if page_range_input:
                    self.logger.info(f"多文件模式，将尝试将页码范围 '{page_range_input}' 应用于所有文件。",
                                     "PageRange")
                    for file_path in file_list:
                        page_ranges_dict[file_path] = page_range_input
                else:
                    self.logger.info(f"多文件模式，未指定页码范围，将处理所有文件的全部页面。", "PageRange")

            if save_to_file:
                total_files = len(file_list)
                success_count = 0

                for i, file_path in enumerate(file_list):
                    if not self.is_running:  # 检查是否被取消
                        self.logger.info("任务被用户取消", "BatchSave")
                        break

                    self.logger.info(f"({i + 1}/{total_files}) 开始识别并保存: {Path(file_path).name}", "BatchSave")
                    # 更新进度到预处理阶段
                    self.update_overall_progress("preprocess",
                                                 f"准备处理第 {i + 1}/{total_files} 个文件: {Path(file_path).name}")

                    # 传递该文件的页码范围
                    file_page_range = page_ranges_dict.get(file_path, "")
                    success, result_content, source_file_stem = self.process_single_file_for_save(
                        file_path, self.ocr_client, model_name, ocr_prompt, scale_factor, max_workers,
                        file_page_range
                    )

                    if success and result_content and source_file_stem:
                        success_count += 1
                        output_file = Path(output_dir) / f"{source_file_stem}_result.md"
                        output_file.parent.mkdir(exist_ok=True)
                        try:
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(result_content)
                            self.logger.info(f"结果已保存至：{output_file}", "FileSave")
                        except Exception as e:
                            self.logger.error(f"保存文件失败 {output_file}: {e}", "FileSave")
                    # OCR和Merge阶段的进度已在 process_single_file_for_save 内部更新

                # 任务完成，设置进度为100%
                self.update_overall_progress("idle", "任务完成")
                self.logger.info(f"任务结束。成功处理 {success_count} / {total_files} 个文件。", "BatchComplete")
                if success_count > 0:
                    messagebox.showinfo("完成",
                                        f"识别并保存完成！成功处理 {success_count} 个文件。\n结果已保存至指定输出目录。")
                else:
                    messagebox.showwarning("完成", f"任务完成，但没有成功处理任何文件。请查看日志了解详情。")

            else:  # 识别并复制模式
                if len(file_list) == 1:
                    self.logger.info("处理单个文件，复用保存模式逻辑...", "SingleFileCopy")
                    # 传递该文件的页码范围
                    file_page_range = page_ranges_dict.get(file_list[0], "")
                    success, result_content, source_file_stem = self.process_single_file_for_save(
                        file_list[0], self.ocr_client, model_name, ocr_prompt, scale_factor, max_workers,
                        file_page_range
                    )
                    if success and result_content:
                        # 进入合并阶段
                        self.update_overall_progress("merge", "正在复制到剪贴板...")
                        copy_success, copy_msg = self._enhanced_copy_to_clipboard(result_content,
                                                                                  method="single_file",
                                                                                  max_retries=4)
                        if copy_success:
                            self.logger.info("剪贴板复制最终验证成功", "Clipboard")
                            messagebox.showinfo("完成",
                                                f"识别并复制完成！\n文件: {source_file_stem}\n结果已复制到剪贴板。")
                        else:
                            self.logger.warning(f"剪贴板复制最终验证失败: {copy_msg}", "Clipboard")
                            temp_file_path = self._save_to_temp_file(result_content, output_dir)
                            if temp_file_path:
                                messagebox.showinfo("完成",
                                                    f"识别完成但剪贴板复制失败！\n结果已保存到临时文件: {temp_file_path}\n错误信息: {copy_msg}")
                            else:
                                messagebox.showerror("错误", f"剪贴板复制和文件保存都失败了！\n错误信息: {copy_msg}")
                    else:
                        # 任务完成，设置进度为100%
                        self.update_overall_progress("idle", "任务完成")
                        messagebox.showwarning("完成", "识别失败或未识别到有效内容。")
                else:
                    self._process_and_copy_all_unified(self.ocr_client, model_name, ocr_prompt, scale_factor,
                                                       max_workers, file_list, output_dir, page_ranges_dict)
                    # 任务完成，设置进度为100%
                    self.update_overall_progress("idle", "任务完成")

        except Exception as e:
            self.logger.error(f"处理过程中发生异常: {str(e)}", "MainProcess")
            self.logger.error(f"异常详情: {traceback.format_exc()}", "MainProcess")
            messagebox.showerror("错误", f"处理过程中发生异常:\n{str(e)}")
        finally:
            self.is_running = False
            self.current_task = None
            # 重置进度显示
            self.root.after(0, self.reset_progress)
            # 更新UI状态
            self.root.after(0, self._update_ui_for_running_state, False)
            # 刷新剪贴板历史显示
            self.root.after(0, self.refresh_clipboard_history)

def _update_ui_for_running_state(self, running):
    """更新UI状态以反映任务运行状态"""
    state = 'disabled' if running else 'normal'

    # 禁用/启用配置输入控件
    widgets_to_disable = [
        self.base_url_entry, self.api_key_entry, self.model_name_entry,
        self.file_paths_entry, self.output_dir_entry,
        self.scale_combobox, self.workers_combobox,
        self.prompt_preset_combobox, self.prompt_text,
        self.page_range_entry,  # 禁用页码范围输入
        self.save_button, self.copy_button, self.reset_button
    ]

    for widget in widgets_to_disable:
        widget.config(state=state)

    # 控制取消按钮
    if running:
        self.cancel_button.config(state='normal')
    else:
        self.cancel_button.config(state='disabled')

def on_closing(self):
    """窗口关闭事件处理"""
    if self.is_running:
        result = messagebox.askyesno("确认退出", "当前有任务正在运行，确定要退出吗？")
        if not result:
            return
        # 取消任务
        self.is_running = False

        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = OCRXGUIClass(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
