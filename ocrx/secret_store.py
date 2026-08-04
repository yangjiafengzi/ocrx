# -- coding: utf-8 --
"""
敏感信息的本机加密存储。

Windows 上使用 DPAPI（CryptProtectData/CryptUnprotectData）加密，
密钥绑定当前 Windows 用户，不需要额外依赖。非 Windows 平台自动降级为明文，
由调用方（ConfigManager）决定是否允许保存。
"""

import base64
import ctypes
import ctypes.wintypes
import sys

_crypt32 = None
_kernel32 = None


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _init_windows_api():
    """初始化 Windows API（仅 Windows；失败时保持 None）。"""
    global _crypt32, _kernel32
    if sys.platform != "win32" or _crypt32 is not None:
        return

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = ctypes.wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.wintypes.BOOL

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.wintypes.HLOCAL]
    kernel32.LocalFree.restype = ctypes.wintypes.HLOCAL

    _crypt32 = crypt32
    _kernel32 = kernel32


def is_encryption_available() -> bool:
    """当前平台是否支持本机加密。"""
    if sys.platform != "win32":
        return False
    try:
        # 做一次往返验证，确保当前用户会话可用
        return _protect(b"probe") is not None
    except Exception:
        return False


def _protect(data: bytes) -> bytes:
    """使用 DPAPI 加密字节数据（绑定当前用户）。"""
    if sys.platform != "win32":
        raise OSError("DPAPI 仅支持 Windows")
    _init_windows_api()

    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()

    if not _crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        if blob_out.pbData:
            _kernel32.LocalFree(blob_out.pbData)


def _unprotect(data: bytes) -> bytes:
    """使用 DPAPI 解密字节数据。"""
    if sys.platform != "win32":
        raise OSError("DPAPI 仅支持 Windows")
    _init_windows_api()

    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()

    if not _crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        if blob_out.pbData:
            _kernel32.LocalFree(blob_out.pbData)


def encrypt_secret(plaintext: str) -> str:
    """加密字符串并返回 base64 文本。"""
    if not plaintext:
        return ""
    return base64.b64encode(_protect(plaintext.encode("utf-8"))).decode("ascii")


def decrypt_secret(encoded: str) -> str:
    """解密 base64 文本。解密失败会抛出异常。"""
    if not encoded:
        return ""
    return _unprotect(base64.b64decode(encoded)).decode("utf-8")
