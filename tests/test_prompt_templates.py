# -- coding: utf-8 --
"""默认提示词模板单一事实源测试。"""

from types import SimpleNamespace

from ocrx.config import ConfigManager
from ocrx.gui.handlers.prompt_handler import PromptHandler
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


def test_config_defaults_match_module(tmp_path):
    cm = ConfigManager(str(tmp_path / "config.json"))
    cfg = cm.load()
    assert cfg["prompt_templates"] == DEFAULT_PROMPT_TEMPLATES


def test_prompt_handler_defaults_match_module(tmp_path):
    mw = SimpleNamespace(
        root=None,
        logger=None,
        clipboard_history=None,
        processing_service=None,
        DISPLAY_MAX_LENGTH=5000,
        COPY_MAX_PAGES=10,
    )
    handler = PromptHandler(mw)
    assert handler.default_presets == list(DEFAULT_PROMPT_TEMPLATES.keys())
