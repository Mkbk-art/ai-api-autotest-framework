"""日志、报告和后续 AI 输入的敏感数据脱敏工具。

本模块递归处理字典、列表和元组，把 Authorization、Cookie、密码、Token、
API Key 等敏感字段替换为 ``***``。请求真正发送时仍使用原值，只有记录和展示
副本经过脱敏。
"""
from __future__ import annotations

from copy import deepcopy
# re 用于处理 JUnit/日志这类自由文本；结构化字典仍继续走 sanitize()。
import re
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

# 文本脱敏只覆盖当前接口测试框架最常见的安全边界，不声称是完整 DLP 系统。
# 第一组保护 Bearer Token；保留字段名前缀，方便排障时知道“这里曾有鉴权信息”。
_BEARER_PATTERN = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([^\s,;]+)")
# 第二组处理常见 key=value / key:value 凭据；值在空白、逗号、分号、& 处停止，避免吞掉整行错误上下文。
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?i)((?:token|access_token|refresh_token|password|passwd|api_key|apikey)\s*[=:]\s*)([^\s,;&]+)"
)
# Cookie 可能包含多个分号分隔字段，因此整行值全部替换，不尝试保留子字段。
_COOKIE_PATTERN = re.compile(r"(?i)((?:cookie|set-cookie)\s*:\s*)([^\r\n]+)")
# 邮箱和中国大陆常见手机号属于 AI 外发前的个人信息最小保护范围。
_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_CN_MOBILE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def sanitize_text(text: str) -> str:
    """脱敏自由文本日志，保留错误语义但移除常见凭据和个人信息。

    Args:
        text: 已从 JUnit、日志或异常中取出的原始文本。

    Returns:
        可用于日志展示或 AI 输入的脱敏字符串。

    Raises:
        TypeError: 调用者传入非字符串；拒绝隐式 ``str()``，避免对象 repr 意外泄密。
    """

    # 文本边界必须明确，不能把任意对象 repr 后再送给模型。
    if not isinstance(text, str):
        raise TypeError("sanitize_text expects str")

    result = text
    # 先处理 Authorization，避免后续通用 token 规则只遮住一部分 Bearer 值。
    result = _BEARER_PATTERN.sub(lambda match: f"{match.group(1)}***", result)
    # 再处理常见 key=value 凭据，字段名保留用于判断失败发生在哪个数据层。
    result = _KEY_VALUE_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}***", result)
    # Cookie 整体敏感，完整替换行值。
    result = _COOKIE_PATTERN.sub(lambda match: f"{match.group(1)}***", result)
    # 最后处理个人信息；业务错误码、JSONPath、异常类名等诊断信息不受影响。
    result = _EMAIL_PATTERN.sub("***", result)
    result = _CN_MOBILE_PATTERN.sub("***", result)
    return result

