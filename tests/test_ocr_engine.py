# -- coding: utf-8 --
"""OCREngine 单元测试。"""

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import ocrx.retry_utils as ru
from ocrx.ocr_engine import OCREngine


def make_engine():
    engine = OCREngine(api_key="k", base_url="http://x", model_name="gpt-4o")
    engine.client = MagicMock()
    return engine


def fake_response(content="识别文本"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_image_to_base64():
    engine = make_engine()
    assert engine.image_to_base64(b"abc") == base64.b64encode(b"abc").decode()


def test_process_single_image_success():
    engine = make_engine()
    engine.client.chat_completions_create.return_value = fake_response("识别文本")
    result = engine.process_single_image("提示词", ("file", 1), b"img")
    assert result == (("file", 1), "识别文本")
    assert engine.client.chat_completions_create.call_args.kwargs["timeout"] == 120


def test_process_single_image_messages_structure():
    engine = make_engine()
    engine.client.chat_completions_create.return_value = fake_response("ok")
    engine.process_single_image("系统提示", ("f", 2), b"target")
    messages = engine.client.chat_completions_create.call_args.kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "系统提示"}
    assert messages[-1]["role"] == "user"
    assert "data:image/png;base64," in messages[-1]["content"][0]["image_url"]["url"]


def test_process_single_image_few_shot_roles(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    engine = make_engine()
    engine.client.chat_completions_create.return_value = fake_response("ok")
    examples = [("示例文本1", b"img1"), ("示例文本2", b"img2")]
    engine.process_single_image("系统提示", ("f", 1), b"target", example_images=examples)
    messages = engine.client.chat_completions_create.call_args.kwargs["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert messages[1]["content"][0]["image_url"]["url"].endswith("aW1nMQ==")  # base64(img1)
    assert messages[2]["content"] == "示例文本1"
    assert messages[3]["content"][0]["image_url"]["url"].endswith("aW1nMg==")
    assert messages[4]["content"] == "示例文本2"


def test_process_single_image_empty_content_returns_error(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    engine = make_engine()
    engine.client.chat_completions_create.return_value = fake_response("")
    identifier, content = engine.process_single_image("p", ("f", 1), b"img", max_retries=1)
    assert identifier == ("f", 1)
    assert content.startswith("识别失败")
    assert engine.client.chat_completions_create.call_count == 2


def test_process_single_image_none_content_returns_error(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    engine = make_engine()
    engine.client.chat_completions_create.return_value = fake_response(None)
    _, content = engine.process_single_image("p", ("f", 1), b"img", max_retries=1)
    assert content.startswith("识别失败")


def test_process_single_image_does_not_retry_network_errors(monkeypatch):
    """回归测试：网络错误只由 OCRClient 重试，引擎不应再嵌套重试放大请求量。"""
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    engine = make_engine()
    engine.client.chat_completions_create.side_effect = RuntimeError("network down")
    identifier, content = engine.process_single_image("p", ("f", 1), b"img", max_retries=3)
    assert identifier == ("f", 1)
    assert content.startswith("识别失败")
    assert engine.client.chat_completions_create.call_count == 1


def test_process_single_image_cancel_before_call():
    engine = make_engine()
    identifier, content = engine.process_single_image("p", ("f", 1), b"img", cancel_check=lambda: True)
    assert identifier == ("f", 1)
    assert "取消" in content
    engine.client.chat_completions_create.assert_not_called()


def test_process_single_image_cancel_mid_retry(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    engine = make_engine()
    cancelled = {"flag": False}

    def cancel_check():
        return cancelled["flag"]

    def side_effect(**kwargs):
        # 第一次 API 调用后置取消标志，下一次重试应立即停止
        cancelled["flag"] = True
        return fake_response("")

    engine.client.chat_completions_create.side_effect = side_effect

    identifier, content = engine.process_single_image("p", ("f", 1), b"img", max_retries=3, cancel_check=cancel_check)
    assert identifier == ("f", 1)
    assert "取消" in content
    assert engine.client.chat_completions_create.call_count == 1


def test_update_config_clears_values(monkeypatch):
    """回归测试：清空字段（空字符串）也应生效。"""
    engine = make_engine()
    engine.update_config(api_key="", base_url="", model_name="", max_workers=0)
    assert engine.api_key == ""
    assert engine.base_url == ""
    assert engine.model_name == ""
    assert engine.max_workers == 0
