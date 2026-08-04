# -- coding: utf-8 --
"""OCRClient 单元测试。"""

from types import SimpleNamespace

import pytest

import ocrx.ocr_client as oc


def fake_response(content="OK"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def make_fake_openai(monkeypatch, completions):
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(oc, "OpenAI", lambda **kwargs: fake)
    return fake


def test_init_allows_missing_api_key():
    # 回归测试：首次运行未配置 API Key 时，创建客户端不应抛异常
    client = oc.OCRClient(api_key="", base_url="")
    assert client.api_key == ""
    assert client._client is None


def test_call_without_api_key_raises_clear_error(monkeypatch):
    # 缺配置应直接报错，不进入重试等待
    def boom(*args):
        raise AssertionError("缺少 API Key 时不应进入重试等待")

    monkeypatch.setattr(oc.time, "sleep", boom)
    client = oc.OCRClient(api_key="", base_url="")
    with pytest.raises(ValueError, match="API Key"):
        client.chat_completions_create(model="m", messages=[])


def test_chat_completions_success(monkeypatch):
    calls = {"n": 0}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            calls["kwargs"] = kwargs
            return fake_response("识别结果")

    make_fake_openai(monkeypatch, FakeCompletions())
    client = oc.OCRClient(api_key="sk-test", base_url="https://api.example.com")
    result = client.chat_completions_create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
    assert result.choices[0].message.content == "识别结果"
    assert calls["n"] == 1
    assert calls["kwargs"]["model"] == "gpt-4o"
    assert calls["kwargs"]["timeout"] == 300


def test_chat_completions_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class FlakyCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("network")
            return fake_response("OK")

    make_fake_openai(monkeypatch, FlakyCompletions())
    client = oc.OCRClient(api_key="k", base_url="http://x", max_retries=3, retry_delay=1)
    assert client.chat_completions_create(model="m", messages=[]) is not None
    assert calls["n"] == 2


def test_chat_completions_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class BrokenCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            raise RuntimeError("always fails")

    make_fake_openai(monkeypatch, BrokenCompletions())
    client = oc.OCRClient(api_key="k", base_url="http://x", max_retries=2)
    with pytest.raises(RuntimeError, match="always fails"):
        client.chat_completions_create(model="m", messages=[])
    assert calls["n"] == 3


def test_retry_delay_does_not_grow_after_failure(monkeypatch):
    """回归测试：重试使用局部延迟，实例配置的 retry_delay 不应被翻倍。"""
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class FlakyCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("network")
            return fake_response("OK")

    make_fake_openai(monkeypatch, FlakyCompletions())
    client = oc.OCRClient(api_key="k", base_url="http://x", max_retries=3, retry_delay=1)
    client.chat_completions_create(model="m", messages=[])
    assert client.retry_delay == 1


def test_update_config_recreates_client(monkeypatch):
    clients = []
    monkeypatch.setattr(
        oc,
        "OpenAI",
        lambda **kwargs: clients.append(kwargs) or SimpleNamespace(chat=SimpleNamespace(completions=object())),
    )
    client = oc.OCRClient(api_key="old", base_url="http://old")
    client.update_config(api_key="new", base_url="http://new")
    assert client.api_key == "new"
    assert client.base_url == "http://new"
    assert client._client is None


def test_cancel_check_stops_before_api_call():
    client = oc.OCRClient(api_key="k", base_url="http://x")
    with pytest.raises(oc.OperationCancelledError, match="取消"):
        client.chat_completions_create(model="m", messages=[], cancel_check=lambda: True)


def test_cancel_check_stops_between_retries(monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            raise ConnectionError("network")

    make_fake_openai(monkeypatch, FakeCompletions())
    client = oc.OCRClient(api_key="k", base_url="http://x", max_retries=3)
    cancelled = {"flag": False}

    def cancel_check():
        return cancelled["flag"]

    # 第一次调用后置取消标志，下一次重试前应立刻停止
    def flaky_check():
        if calls["n"] >= 1:
            cancelled["flag"] = True
        return cancelled["flag"]

    with pytest.raises(oc.OperationCancelledError):
        client.chat_completions_create(model="m", messages=[], cancel_check=flaky_check)
    assert calls["n"] == 1
