"""
Windows DPAPI 加密工具 (via ctypes, 无额外依赖)

使用 CryptProtectData / CryptUnprotectData 将数据绑定到当前 Windows 用户账户。
加密后的数据只能在同一台机器的同一用户会话下解密。

存储格式: base64 编码的 DPAPI blob (prefix: "dpapi:")
"""

import base64
import ctypes
import ctypes.wintypes
import logging

logger = logging.getLogger(__name__)

# DPAPI 存储前缀，用于区分已加密值与明文值
_DPAPI_PREFIX = "dpapi:"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(plaintext: str) -> str:
    """
    使用 Windows DPAPI 加密字符串，返回带前缀的 base64 编码 blob。
    绑定到当前用户账户（CRYPTPROTECT_UI_FORBIDDEN 标志）。
    """
    data = plaintext.encode("utf-8")
    blob_in = _DATA_BLOB(
        len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_char))
    )
    blob_out = _DATA_BLOB()

    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),  # pDataIn
        None,  # szDataDescr (description, optional)
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        0x01,  # dwFlags: CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out),  # pDataOut
    )

    if not result:
        error_code = ctypes.GetLastError()
        raise RuntimeError(f"DPAPI CryptProtectData 失败，错误码: {error_code}")

    try:
        encrypted_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
        return _DPAPI_PREFIX + base64.b64encode(encrypted_bytes).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _dpapi_decrypt(ciphertext_with_prefix: str) -> str:
    """
    解密带前缀的 base64 DPAPI blob，返回原始明文字符串。
    """
    b64_data = ciphertext_with_prefix[len(_DPAPI_PREFIX) :]
    encrypted_bytes = base64.b64decode(b64_data)

    blob_in = _DATA_BLOB(
        len(encrypted_bytes),
        ctypes.cast(ctypes.c_char_p(encrypted_bytes), ctypes.POINTER(ctypes.c_char)),
    )
    blob_out = _DATA_BLOB()

    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),  # pDataIn
        None,  # ppszDataDescr
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        0x01,  # dwFlags: CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out),  # pDataOut
    )

    if not result:
        error_code = ctypes.GetLastError()
        raise RuntimeError(f"DPAPI CryptUnprotectData 失败，错误码: {error_code}")

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


# ── 公开 API ────────────────────────────────────────────────────────────────


def is_encrypted(value: str) -> bool:
    """判断一个值是否已经过 DPAPI 加密（通过前缀检测）。"""
    return value.startswith(_DPAPI_PREFIX)


def encrypt_value(plaintext: str) -> str:
    """
    加密一个字符串。
    - 如果已经是加密格式，直接原样返回。
    - 如果是空字符串，原样返回（不加密空值）。
    """
    if not plaintext or is_encrypted(plaintext):
        return plaintext
    try:
        return _dpapi_encrypt(plaintext)
    except Exception as e:
        logger.error("DPAPI 加密失败: %s", e)
        raise


def decrypt_value(value: str) -> str:
    """
    解密一个值。
    - 如果是加密格式（带前缀），解密后返回明文。
    - 如果不带前缀（旧明文数据），直接返回原值（向后兼容迁移期）。
    - 如果是空字符串，原样返回。
    """
    if not value or not is_encrypted(value):
        return value
    try:
        return _dpapi_decrypt(value)
    except Exception as e:
        logger.error("DPAPI 解密失败: %s", e)
        raise
