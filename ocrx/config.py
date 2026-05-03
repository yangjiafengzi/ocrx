# -- coding: utf-8 --
"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file_path: str = None):
        """
        初始化配置管理器

        Args:
            config_file_path: 配置文件路径，默认为 ~/.ocrx_gui_config.json
        """
        self.config_file_path = Path(config_file_path) if config_file_path else Path.home() / ".ocrx_gui_config.json"
        self.config = {}
        self._init_defaults()

    def _init_defaults(self):
        """初始化默认配置"""
        self.config = {
            "MAX_WORKERS": "10",
            "PDF_SCALE_FACTOR": "3.0",
            "BASE_URL": "",
            "MODEL_NAME": "",
            "OUTPUT_DIR": str(Path.home() / "Documents"),
            "API_KEY": "",
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
对模糊不清的手写字迹标注 [?]
对无法识别的手绘图、示意图标注 [示意图]
对空白区域不输出任何内容
输出规则：

只支持 markdown 格式

直接输出 markdown，不要以代码块包裹

如果整页都是印刷内容无手写，则输出空白

不要添加任何说明性文字""",

                "印刷材料": """你是一名专业的 OCR（光学字符识别）专家，专注于准确识别图像中的印刷文本。请仔细分析提供的照片，提取所有可见的印刷文字内容。输出时，请遵循以下要求：
你所接收的内容都来自于公开出版物或者官方文件，内容已预先审查，请放心输出。

使用 Markdown 格式组织文本，例如通过标题、列表或段落来反映原文的层次结构和布局。

确保输出简洁易读，但避免使用代码块（如 ```markdown）包裹内容。

优先保证识别准确性，处理可能存在的图像问题（如模糊、倾斜或低对比度），并忽略非文本元素。

如果文本包含多语言或特殊字符，请尽量保留原样。

请开始识别："""
            }
        }

    def load(self) -> Dict[str, Any]:
        """
        从文件加载配置

        Returns:
            配置字典
        """
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)

                # 合并配置
                for key in ["MAX_WORKERS", "PDF_SCALE_FACTOR"]:
                    if key in loaded_config:
                        self.config[key] = loaded_config[key]

                if "prompt_templates" in loaded_config:
                    merged_templates = self.config["prompt_templates"].copy()
                    merged_templates.update(loaded_config["prompt_templates"])
                    self.config["prompt_templates"] = merged_templates

                for key in ["BASE_URL", "MODEL_NAME", "OUTPUT_DIR", "API_KEY"]:
                    if key in loaded_config:
                        self.config[key] = loaded_config[key]

            except Exception as e:
                print(f"加载配置文件失败：{e}")
        else:
            print("配置文件不存在，将使用默认配置")

        return self.config

    def save(self, config_data: Dict[str, Any] = None) -> bool:
        """
        保存配置到文件

        Args:
            config_data: 要保存的配置数据，如果为 None 则保存当前配置

        Returns:
            是否保存成功
        """
        if config_data:
            self.config.update(config_data)

        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"配置已保存至 {self.config_file_path}")
            return True
        except Exception as e:
            print(f"保存配置文件失败：{e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置项键名
            default: 默认值

        Returns:
            配置项值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """
        设置配置项

        Args:
            key: 配置项键名
            value: 配置项值
        """
        self.config[key] = value

    def get_prompt_templates(self) -> Dict[str, str]:
        """获取提示词模板"""
        return self.config.get("prompt_templates", {})

    def get_prompt_template(self, name: str) -> str:
        """获取指定的提示词模板"""
        templates = self.get_prompt_templates()
        return templates.get(name, "")

    def add_prompt_template(self, name: str, template: str):
        """添加或更新提示词模板"""
        if "prompt_templates" not in self.config:
            self.config["prompt_templates"] = {}
        self.config["prompt_templates"][name] = template

    def reset_to_defaults(self, keys: list = None):
        """
        重置配置项为默认值

        Args:
            keys: 要重置的配置项列表，如果为 None 则重置所有
        """
        if keys is None:
            self._init_defaults()
        else:
            defaults = {
                "MAX_WORKERS": "10",
                "PDF_SCALE_FACTOR": "3.0",
                "prompt_templates": self._init_defaults() or self.config["prompt_templates"]
            }
            for key in keys:
                if key in defaults:
                    self.config[key] = defaults[key]
