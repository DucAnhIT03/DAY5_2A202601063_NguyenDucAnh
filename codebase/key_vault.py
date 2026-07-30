from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_PATH = ROOT / ".runtime" / "gemini-key-pool.dpapi"
CRYPTPROTECT_UI_FORBIDDEN = 0x01


class KeyVaultError(RuntimeError):
    """A sanitized vault error safe to show in the UI."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _require_windows() -> None:
    if os.name != "nt":
        raise KeyVaultError("Lưu key mã hóa hiện chỉ hỗ trợ Windows.")


def _blob_from_bytes(value: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    return _DataBlob(len(value), buffer), buffer


def _free_blob(blob: _DataBlob) -> None:
    local_free = ctypes.windll.kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p
    local_free(blob.pbData)


def _protect(value: bytes) -> bytes:
    _require_windows()
    input_blob, input_buffer = _blob_from_bytes(value)
    output_blob = _DataBlob()
    crypt_protect = ctypes.windll.crypt32.CryptProtectData
    crypt_protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_protect.restype = wintypes.BOOL
    protected = crypt_protect(
        ctypes.byref(input_blob),
        "taphoammo Gemini key pool",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    _ = input_buffer  # Keep the input buffer alive through the native call.
    if not protected:
        raise KeyVaultError("Windows không thể mã hóa pool API key.")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        _free_blob(output_blob)


def _unprotect(value: bytes) -> bytes:
    _require_windows()
    input_blob, input_buffer = _blob_from_bytes(value)
    output_blob = _DataBlob()
    crypt_unprotect = ctypes.windll.crypt32.CryptUnprotectData
    crypt_unprotect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt_unprotect.restype = wintypes.BOOL
    unprotected = crypt_unprotect(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    _ = input_buffer
    if not unprotected:
        raise KeyVaultError(
            "Không thể mở pool API key đã lưu bằng tài khoản Windows này."
        )
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        _free_blob(output_blob)


def _normalize(keys: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for key in keys:
        candidate = str(key).strip()
        if candidate and candidate not in seen:
            normalized.append(candidate)
            seen.add(candidate)
    return normalized


def load_key_pool(path: Path = DEFAULT_VAULT_PATH) -> list[str]:
    if not path.exists():
        return []
    try:
        plaintext = _unprotect(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError, KeyVaultError) as error:
        raise KeyVaultError("Không thể đọc pool API key đã mã hóa.") from error
    return _normalize(plaintext.splitlines())


def save_key_pool(
    keys: Iterable[str], path: Path = DEFAULT_VAULT_PATH
) -> bool:
    normalized = _normalize(keys)
    if not normalized:
        clear_key_pool(path)
        return False

    try:
        if path.exists() and load_key_pool(path) == normalized:
            return False
    except KeyVaultError:
        pass

    encrypted = _protect("\n".join(normalized).encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_bytes(encrypted)
        os.replace(temporary_path, path)
    except OSError as error:
        raise KeyVaultError("Không thể lưu pool API key đã mã hóa.") from error
    return True


def clear_key_pool(path: Path = DEFAULT_VAULT_PATH) -> bool:
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        raise KeyVaultError("Không thể xóa pool API key đã lưu.") from error
    return not path.exists()
