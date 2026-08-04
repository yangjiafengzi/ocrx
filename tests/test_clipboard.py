# -- coding: utf-8 --
"""ClipboardHistory 单元测试。"""

import hashlib

import pytest

import ocrx.clipboard as cb


def test_add_record_fields():
    ch = cb.ClipboardHistory()
    ch.add_record("hello", success=True, method="tkinter")
    rec = ch.get_history()[0]
    assert rec["content"] == "hello"
    assert rec["content_length"] == 5
    assert rec["success"] is True
    assert rec["method"] == "tkinter"
    assert rec["content_hash"] == hashlib.md5(b"hello").hexdigest()[:8]
    assert rec["content_preview"] == "hello"


def test_add_record_preview_truncated():
    ch = cb.ClipboardHistory()
    ch.add_record("x" * 150)
    assert ch.get_history()[0]["content_preview"].endswith("...")


def test_max_history_eviction():
    ch = cb.ClipboardHistory(max_history=3)
    for i in range(5):
        ch.add_record(str(i))
    history = ch.get_history()
    assert len(history) == 3
    assert [r["content"] for r in history] == ["2", "3", "4"]


def test_get_content_by_index_bounds():
    ch = cb.ClipboardHistory()
    ch.add_record("a")
    ch.add_record("b")
    assert ch.get_content_by_index(0) == "a"
    assert ch.get_content_by_index(1) == "b"
    assert ch.get_content_by_index(-1) is None
    assert ch.get_content_by_index(2) is None


def test_clear_history():
    ch = cb.ClipboardHistory()
    ch.add_record("a")
    ch.clear_history()
    assert ch.get_history() == []


def test_get_record_by_hash():
    ch = cb.ClipboardHistory()
    ch.add_record("hello")
    h = hashlib.md5(b"hello").hexdigest()[:8]
    assert ch.get_record_by_hash(h)["content"] == "hello"
    assert ch.get_record_by_hash("nope") is None


def test_get_recent_records():
    ch = cb.ClipboardHistory(max_history=10)
    for i in range(6):
        ch.add_record(str(i))
    assert [r["content"] for r in ch.get_recent_records(3)] == ["3", "4", "5"]
    assert len(ch.get_recent_records(99)) == 6


def test_copy_to_clipboard_success(monkeypatch):
    copied = []

    class FakeTk:
        def __init__(self):
            self.destroyed = False

        def withdraw(self):
            pass

        def clipboard_clear(self):
            pass

        def clipboard_append(self, content):
            copied.append(content)

        def update(self):
            pass

        def destroy(self):
            self.destroyed = True

    monkeypatch.setattr(cb.tk, "Tk", lambda: FakeTk())
    ch = cb.ClipboardHistory()
    assert ch.copy_to_clipboard("abc") is True
    assert copied == ["abc"]
    assert len(ch.get_history()) == 1
    assert ch.get_history()[0]["success"] is True


def test_copy_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(cb.time, "sleep", lambda s: None)
    state = {"n": 0}

    class FlakyTk:
        def __init__(self):
            state["n"] += 1
            if state["n"] == 1:
                raise RuntimeError("clipboard busy")

        def withdraw(self):
            pass

        def clipboard_clear(self):
            pass

        def clipboard_append(self, content):
            pass

        def update(self):
            pass

        def destroy(self):
            pass

    monkeypatch.setattr(cb.tk, "Tk", FlakyTk)
    ch = cb.ClipboardHistory()
    assert ch.copy_to_clipboard("abc", max_retries=2) is True
    assert state["n"] == 2
    assert ch.get_history()[-1]["success"] is True


def test_copy_fails_after_all_retries(monkeypatch):
    monkeypatch.setattr(cb.time, "sleep", lambda s: None)

    class BrokenTk:
        def __init__(self):
            raise RuntimeError("no clipboard")

    monkeypatch.setattr(cb.tk, "Tk", BrokenTk)
    ch = cb.ClipboardHistory()
    assert ch.copy_to_clipboard("abc", max_retries=1) is False
    last = ch.get_history()[-1]
    assert last["success"] is False
    assert last["error_msg"] == "no clipboard"


def test_copy_with_provided_root(monkeypatch):
    """回归测试：传入可复用根窗口时不应再新建 tk.Tk()。"""
    copied = []

    class FakeRoot:
        def clipboard_clear(self):
            pass

        def clipboard_append(self, content):
            copied.append(content)

        def update(self):
            pass

    def boom():
        raise AssertionError("不应创建新的 tk.Tk()")

    monkeypatch.setattr(cb.tk, "Tk", boom)
    ch = cb.ClipboardHistory(root=FakeRoot())
    assert ch.copy_to_clipboard("abc") is True
    assert copied == ["abc"]
    assert ch.get_history()[-1]["success"] is True
