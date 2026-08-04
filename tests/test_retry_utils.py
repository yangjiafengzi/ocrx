# -- coding: utf-8 --
"""重试工具测试。"""

import pytest

import ocrx.retry_utils as ru


def test_retry_operation_success():
    assert ru.retry_operation(lambda: "ok") == "ok"


def test_retry_operation_retries_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ru.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert ru.retry_operation(op, max_retries=3, base_delay=1) == "ok"
    assert calls["n"] == 3
    assert abs(sum(sleeps) - 3.0) < 1e-6  # 1 秒 + 2 秒（分段睡眠）


def test_retry_operation_exhausted(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        ru.retry_operation(op, max_retries=2)
    assert calls["n"] == 3


def test_retry_operation_on_retry_callback(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    retries = []
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("x")
        return 1

    ru.retry_operation(op, max_retries=3, on_retry=lambda a, d, e: retries.append((a, d)))
    assert retries == [(1, 1.0), (2, 2.0)]


def test_retry_operation_exception_filter(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise ValueError("v")

    with pytest.raises(ValueError):
        ru.retry_operation(op, exceptions=(KeyError,), max_retries=2)
    assert calls["n"] == 1


def test_retry_with_backoff_decorator(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    calls = {"n": 0}

    @ru.retry_with_backoff(max_retries=2, base_delay=1)
    def op():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("x")
        return "done"

    assert op() == "done"
    assert calls["n"] == 2


def test_operation_cancelled_error_is_defined():
    assert issubclass(ru.OperationCancelledError, Exception)


def test_operation_cancelled_error_not_retried(monkeypatch):
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise ru.OperationCancelledError("取消")

    with pytest.raises(ru.OperationCancelledError):
        ru.retry_operation(op, max_retries=3, exceptions=(ValueError,))
    assert calls["n"] == 1


def test_content_refused_error_is_defined():
    assert issubclass(ru.ContentRefusedError, Exception)


def test_retry_operation_cancel_during_retry(monkeypatch):
    """回归测试：重试等待期间取消应立即生效，不再睡满整个延迟。"""
    monkeypatch.setattr(ru.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        raise ValueError("x")

    def cancel_check():
        return calls["n"] >= 1

    with pytest.raises(ru.OperationCancelledError, match="取消"):
        ru.retry_operation(op, max_retries=3, cancel_check=cancel_check)
    assert calls["n"] == 1
