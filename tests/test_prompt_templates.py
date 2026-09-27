# -- coding: utf-8 --
"""默认提示词模板单一事实源测试。"""

from ocrx.config import ConfigManager
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


def test_config_defaults_match_module(tmp_path):
    cm = ConfigManager(str(tmp_path / "config.json"))
    cfg = cm.load()
    assert cfg["prompt_templates"] == DEFAULT_PROMPT_TEMPLATES
