"""接口响应变量提取器。

本模块根据 YAML ``extract`` 规则，从响应文本中使用正则表达式或 JSONPath
提取动态值，并写入当前 :class:`VariableContext`。它只负责提取和存储，
不负责变量替换或断言。
"""
from __future__ import annotations

import json
import re
from typing import Any

from core.variable_context import VariableContext
from utils.jsonpath_util import find_values


def extract_from_response(
    extract_rules: dict[str, str] | None,
    response_text: Any,
    *,
    context: VariableContext,
    scope: str = "scenario",
) -> dict[str, Any]:
    """按规则提取响应值并写入上下文。

    Args:
        extract_rules: ``变量名 -> 正则/JSONPath`` 映射。
        response_text: HTTP 响应文本，JSONPath 分支也允许已解析对象。
        context: 当前测试独享的变量上下文。
        scope: 提取结果写入的逻辑作用域，默认 ``scenario``。

    Returns:
        本次成功提取的变量字典。
    """
    if not extract_rules or not isinstance(extract_rules, dict):
        return {}

    extracted: dict[str, Any] = {}
    for var_name, expression in extract_rules.items():
        value = None
        if any(pattern in expression for pattern in ["(.*?)", "(.+?)", r"(\d+)", r"(\d*)"]):
            match = re.search(expression, response_text)
            if match:
                value = match.group(1) if match.groups() else match.group()
        elif expression.startswith("$"):
            # JSONPath 规则只有在需要时才解析 JSON，非 JSON 响应仍可以走正则提取。
            resp_json = json.loads(response_text) if isinstance(response_text, str) else response_text
            results = find_values(resp_json, expression)
            if results:
                value = results[0]
        if value is not None:
            context.set(var_name, value, scope=scope)
            extracted[var_name] = value
    return extracted
