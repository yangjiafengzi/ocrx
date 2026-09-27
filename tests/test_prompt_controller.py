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


def test_reset_only_restores_prompt_templates(tmp_path):
    cfg, ctrl = _make(tmp_path)
    cfg.set("API_KEY", "secret-key")
    cfg.set("BASE_URL", "https://example.test/v1")
    cfg.set("MODEL_NAME", "m")
    cfg.set("OUTPUT_DIR", str(tmp_path / "out"))
    cfg.set("MAX_WORKERS", "4")
    assert ctrl.save_new("custom", "body") is True
    ctrl.reset()
    assert set(cfg.get_prompt_templates()) == set(DEFAULT_PROMPT_TEMPLATES)
    assert "custom" not in cfg.get_prompt_templates()
    assert cfg.get("API_KEY") == "secret-key"
    assert cfg.get("BASE_URL") == "https://example.test/v1"
    assert cfg.get("MODEL_NAME") == "m"
    assert cfg.get("OUTPUT_DIR") == str(tmp_path / "out")
    assert cfg.get("MAX_WORKERS") == "4"


def test_reset_persists_scoped_restore(tmp_path):
    cfg, ctrl = _make(tmp_path)
    cfg.set("API_KEY", "secret-key")
    assert ctrl.save_new("custom", "body") is True
    ctrl.reset()
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert set(reloaded.get_prompt_templates()) == set(DEFAULT_PROMPT_TEMPLATES)
    assert "custom" not in reloaded.get_prompt_templates()
    assert reloaded.get("API_KEY") == "secret-key"


def test_rename_collision_returns_false_and_keeps_both(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("alpha", "A") is True
    assert ctrl.save_new("beta", "B") is True
    assert ctrl.rename("alpha", "beta") is False
    templates = cfg.get_prompt_templates()
    assert templates["alpha"] == "A"
    assert templates["beta"] == "B"
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert reloaded.get_prompt_template("alpha") == "A"
    assert reloaded.get_prompt_template("beta") == "B"


def test_save_new_existing_custom_name_returns_false(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "body") is True
    assert ctrl.save_new("custom", "other") is False
    assert cfg.get_prompt_template("custom") == "body"


class _ExplodingConfig:
    """ConfigManager stand-in that raises on every mutation/read."""

    def get_prompt_templates(self):
        raise RuntimeError("config exploded")

    def add_prompt_template(self, name, template):
        raise RuntimeError("config exploded")

    def reset_to_defaults(self, keys=None):
        raise RuntimeError("config exploded")

    def save(self):
        raise RuntimeError("config exploded")

    @property
    def config(self):
        raise RuntimeError("config exploded")


def test_prompt_controller_swallows_unexpected_config_errors():
    ctrl = PromptController(_ExplodingConfig())
    assert ctrl.save_new("custom", "body") is False
    assert ctrl.rename("a", "b") is False
    assert ctrl.delete("a") is False
    assert ctrl.update("a", "body") is False
    assert ctrl.reset() is None


def test_update_edits_custom_template_body(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.save_new("custom", "old") is True
    assert ctrl.update("custom", "new") is True
    assert cfg.get_prompt_template("custom") == "new"
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert reloaded.get_prompt_template("custom") == "new"


def test_update_edits_default_template_body(tmp_path):
    cfg, ctrl = _make(tmp_path)
    name = next(iter(DEFAULT_PROMPT_TEMPLATES))
    assert ctrl.update(name, "edited default body") is True
    assert cfg.get_prompt_template(name) == "edited default body"
    reloaded = ConfigManager(str(tmp_path / "cfg.json"))
    reloaded.load()
    assert reloaded.get_prompt_template(name) == "edited default body"


def test_update_missing_name_returns_false(tmp_path):
    cfg, ctrl = _make(tmp_path)
    assert ctrl.update("missing", "body") is False
    assert cfg.get_prompt_template("missing") == ""


class _SaveFailsConfig(ConfigManager):
    """ConfigManager whose save() always reports failure."""

    def save(self, config_data=None):
        return False


def test_update_save_failure_keeps_previous_body(tmp_path):
    cfg = _SaveFailsConfig(str(tmp_path / "cfg.json"))
    cfg.load()
    cfg.add_prompt_template("custom", "old")
    ctrl = PromptController(cfg)
    assert ctrl.update("custom", "new") is False
    assert cfg.get_prompt_template("custom") == "old"


def test_save_new_save_failure_is_rolled_back(tmp_path):
    cfg = _SaveFailsConfig(str(tmp_path / "cfg.json"))
    cfg.load()
    ctrl = PromptController(cfg)
    assert ctrl.save_new("custom", "body") is False
    assert "custom" not in cfg.get_prompt_templates()


def test_rename_save_failure_is_rolled_back(tmp_path):
    cfg = _SaveFailsConfig(str(tmp_path / "cfg.json"))
    cfg.load()
    cfg.add_prompt_template("custom", "body")
    ctrl = PromptController(cfg)
    assert ctrl.rename("custom", "renamed") is False
    assert cfg.get_prompt_template("custom") == "body"
    assert "renamed" not in cfg.get_prompt_templates()


def test_delete_save_failure_is_rolled_back(tmp_path):
    cfg = _SaveFailsConfig(str(tmp_path / "cfg.json"))
    cfg.load()
    cfg.add_prompt_template("custom", "body")
    ctrl = PromptController(cfg)
    assert ctrl.delete("custom") is False
    assert cfg.get_prompt_template("custom") == "body"
