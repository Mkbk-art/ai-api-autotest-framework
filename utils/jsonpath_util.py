"""框架内置的轻量 JSONPath 读取工具。

当前实现覆盖项目实际使用的 ``$.a.b``、数组下标和 ``[*]`` 通配符模式，
避免核心测试完全依赖外部 JSONPath 库。若未来 DSL 需要更复杂表达式，再引入
完整实现并为兼容性增加测试。
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"([^\.\[\]]+)|\[(\*|\d+)\]")


def _tokens(expression: str) -> list[str]:
    """把支持的 JSONPath 表达式拆成逐层访问 token。"""
    if not isinstance(expression, str) or not expression.startswith("$"):
        raise ValueError(f"JSONPath must start with '$': {expression!r}")
    if expression == "$":
        return []
    return [field or index for field, index in _TOKEN_RE.findall(expression[1:])]


def find_values(payload: Any, expression: str) -> list[Any]:
    """返回 JSONPath 表达式匹配到的全部值。"""
    current = [payload]
    for token in _tokens(expression):
        next_values: list[Any] = []
        for value in current:
            if token == "*":
                if isinstance(value, list):
                    next_values.extend(value)
                elif isinstance(value, dict):
                    next_values.extend(value.values())
            elif token.isdigit():
                if isinstance(value, list):
                    index = int(token)
                    if 0 <= index < len(value):
                        next_values.append(value[index])
            elif isinstance(value, dict) and token in value:
                next_values.append(value[token])
        current = next_values
        if not current:
            break
    return current


def find_first(payload: Any, expression: str, default: Any = None) -> Any:
    """返回第一个 JSONPath 匹配值；无匹配时返回 default。"""
    values = find_values(payload, expression)
    return values[0] if values else default
