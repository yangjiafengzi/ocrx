# -- coding: utf-8 --
"""API 密钥本机加密存储测试。"""

import pytest

import ocrx.secret_store as ss


def test_encrypt_decrypt_roundtrip_with_fake(monkeypatch):
    monkeypatch.setattr(ss, "_protect", lambda data: data[::-1])
    monkeypatch.setattr(ss, "_unprotect", lambda data: data[::-1])
    encrypted = ss.encrypt_secret("机密内容")
    assert encrypted != "机密内容"
    assert ss.decrypt_secret(encrypted) == "机密内容"


def test_empty_secret_roundtrip():
    assert ss.encrypt_secret("") == ""
    assert ss.decrypt_secret("") == ""


def test_real_dpapi_roundtrip():
    if not ss.is_encryption_available():
        pytest.skip("当前环境不支持 DPAPI")
    encrypted = ss.encrypt_secret("hello-dpapi")
    assert encrypted != "hello-dpapi"
    assert ss.decrypt_secret(encrypted) == "hello-dpapi"
