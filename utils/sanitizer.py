"""日志、报告和后续 AI 输入的敏感数据脱敏工具。

本模块递归处理字典、列表和元组，把 Authorization、Cookie、密码、Token、
API Key 等敏感字段替换为 ``***``。请求真正发送时仍使用原值，只有记录和展示
副本经过脱敏。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

_SENSITIVE_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
}
_NORMALIZED_SENSITIVE_KEYS = {item.replace("-", "_") for item in _SENSITIVE_KEYS}


def _is_sensitive(key: Any) -> bool:
    """判断字段名是否属于框架约定的敏感字段。"""
    normalized = str(key).strip().lower().replace("-", "_")
    return normalized in _NORMALIZED_SENSITIVE_KEYS


def sanitize(value: Any) -> Any:
    """返回脱敏后的深拷贝，不修改调用方原始数据。"""
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive(key) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)
    return deepcopy(value)
