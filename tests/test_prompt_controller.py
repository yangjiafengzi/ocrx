# -- coding: utf-8 --
"""PromptController unit tests (real ConfigManager on tmp_path)."""

from ocrx.config import ConfigManager
from ocrx.gui.controllers.prompt_controller import PromptController
from ocrx.prompt_templates import DEFAULT_PROMPT_TEMPLATES


def _make(tmp_path):
    cfg = ConfigManager(str(tmp_path / "cfg.json"))
    cfg.load()
    return cfg, PromptController(cfg)


def test_prompt_controller_crud(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("自定义", "内容") is True
    assert ctrl.rename("自定义", "新名字") is True
    assert ctrl.delete("新名字") is True


def test_save_new_rejects_empty_and_default_names(tmp_path):
    _cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("", "text") is False
    for name in DEFAULT_PROMPT_TEMPLATES:
        assert ctrl.save_new(name, "text") is False


def test_save_new_persists_template(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert reloaded.get_prompt_template("custom") == "body"
    assert cfg.get_prompt_template("custom") == "body"


def test_rename_rejects_default_missing_and_empty(tmp_path):
    _cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    for name in DEFAULT_PROMPT_TEMPLATES:
        assert ctrl.rename(name, "renamed") is False
        assert ctrl.rename("custom", name) is False
    assert ctrl.rename("missing", "renamed") is False
    assert ctrl.rename("custom", "") is False


def test_rename_persists_template(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    assert ctrl.rename("custom", "renamed") is True
    assert "custom" not in cfg.get_prompt_templates()
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert reloaded.get_prompt_template("renamed") == "body"
    assert reloaded.get_prompt_template("custom") == ""


def test_delete_rejects_default_and_missing_names(tmp_path):
    _cfg, ctrl = _make(tmp_path)
    for name in DEFAULT_PROMPT_TEMPLATES:
        assert ctrl.delete(name) is False
    assert ctrl.delete("missing") is False


def test_delete_persists_template_removal(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    assert ctrl.delete("custom") is True
    assert "custom" not in cfg.get_prompt_templates()
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert "custom" not in reloaded.get_prompt_templates()


def test_reset_restores_default_templates(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    ctrl.reset()
    assert set(cfg.get_prompt_templates()) == set(DEFAULT_PROMPT_TEMPLATES)
    assert "custom" not in cfg.get_prompt_templates()
