# -- coding: utf-8 --
"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
from pathlib import Path
from typing import Any, Dict

from .prompt_templates import DEFAULT_PROMPT_TEMPLATES
from .secret_store import decrypt_secret, encrypt_secret, is_encryption_available


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
            "prompt_templates": dict(DEFAULT_PROMPT_TEMPLATES),
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

                for key in ["BASE_URL", "MODEL_NAME", "OUTPUT_DIR"]:
                    if key in loaded_config:
                        self.config[key] = loaded_config[key]

                # API Key：优先读取加密字段，兼容旧的明文字段
                if "API_KEY_ENC" in loaded_config:
                    try:
                        decrypted = decrypt_secret(loaded_config["API_KEY_ENC"])
                        if decrypted:
                            self.config["API_KEY"] = decrypted
                    except Exception as e:
                        print(f"解密 API Key 失败：{e}")
                        self.config["API_KEY"] = ""
                elif "API_KEY" in loaded_config:
                    self.config["API_KEY"] = loaded_config["API_KEY"]

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

        # 写入前加密 API Key：磁盘上不保留明文（不可用平台除外）
        payload = dict(self.config)
        api_key = payload.get("API_KEY", "")
        if is_encryption_available():
            if api_key:
                try:
                    payload["API_KEY_ENC"] = encrypt_secret(api_key)
                except Exception as e:
                    print(f"加密 API Key 失败：{e}")
                    return False
            payload.pop("API_KEY", None)
        else:
            payload.pop("API_KEY_ENC", None)

        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
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
        defaults = {
            "MAX_WORKERS": "10",
            "PDF_SCALE_FACTOR": "3.0",
            "prompt_templates": dict(DEFAULT_PROMPT_TEMPLATES),
        }

        if keys is None:
            self._init_defaults()
            return

        for key in keys:
            if key in defaults:
                self.config[key] = defaults[key]
