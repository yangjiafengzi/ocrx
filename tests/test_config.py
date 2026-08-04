# -- coding: utf-8 --
"""ConfigManager 单元测试。"""

import json

import pytest

import ocrx.config as config_mod
from ocrx.config import ConfigManager


def make_manager(tmp_path):
    return ConfigManager(str(tmp_path / "config.json"))


@pytest.fixture(autouse=True)
def fake_secret_store(monkeypatch):
    """用可逆的假加密让配置测试跨平台、可预测。"""
    monkeypatch.setattr(config_mod, "is_encryption_available", lambda: True)
    monkeypatch.setattr(config_mod, "encrypt_secret", lambda s: f"ENC({s})")
    monkeypatch.setattr(
        config_mod,
        "decrypt_secret",
        lambda s: s[4:-1] if s.startswith("ENC(") else s,
    )


def test_defaults(tmp_path):
    cm = make_manager(tmp_path)
    cfg = cm.load()
    assert cfg["MAX_WORKERS"] == "10"
    assert cfg["PDF_SCALE_FACTOR"] == "3.0"
    assert "手写笔记" in cfg["prompt_templates"]
    assert "印刷材料" in cfg["prompt_templates"]


def test_save_and_load_roundtrip(tmp_path):
    cm = make_manager(tmp_path)
    cm.load()
    cm.set("BASE_URL", "https://api.example.com")
    cm.set("API_KEY", "sk-test")
    cm.add_prompt_template("自定义", "模板内容")
    assert cm.save()

    cm2 = make_manager(tmp_path)
    cfg2 = cm2.load()
    assert cfg2["BASE_URL"] == "https://api.example.com"
    assert cfg2["API_KEY"] == "sk-test"
    assert cfg2["prompt_templates"]["自定义"] == "模板内容"


def test_load_merges_user_templates_with_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"prompt_templates": {"自定义": "template"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    cm = ConfigManager(str(path))
    cfg = cm.load()
    assert cfg["prompt_templates"]["自定义"] == "template"
    assert "手写笔记" in cfg["prompt_templates"]


def test_corrupt_config_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad json", encoding="utf-8")
    cm = ConfigManager(str(path))
    cfg = cm.load()
    assert cfg["MAX_WORKERS"] == "10"


def test_prompt_template_crud(tmp_path):
    cm = make_manager(tmp_path)
    cm.add_prompt_template("测试", "内容")
    assert cm.get_prompt_template("测试") == "内容"
    assert "测试" in cm.get_prompt_templates()


def test_reset_all_restores_defaults(tmp_path):
    cm = make_manager(tmp_path)
    cm.load()
    cm.set("MAX_WORKERS", "99")
    cm.add_prompt_template("自定义", "x")
    cm.reset_to_defaults()
    assert cm.get("MAX_WORKERS") == "10"
    assert "自定义" not in cm.get_prompt_templates()


def test_save_encrypts_api_key(tmp_path):
    cm = make_manager(tmp_path)
    cm.load()
    cm.set("API_KEY", "sk-secret")
    assert cm.save()

    payload = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert "API_KEY" not in payload
    assert payload["API_KEY_ENC"] == "ENC(sk-secret)"

    cm2 = make_manager(tmp_path)
    assert cm2.load()["API_KEY"] == "sk-secret"


def test_load_migrates_plaintext_api_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"API_KEY": "sk-plain"}, ensure_ascii=False), encoding="utf-8")
    cm = ConfigManager(str(path))
    assert cm.load()["API_KEY"] == "sk-plain"


def test_load_encrypted_api_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"API_KEY_ENC": "ENC(sk-enc)"}, ensure_ascii=False), encoding="utf-8")
    cm = ConfigManager(str(path))
    assert cm.load()["API_KEY"] == "sk-enc"
