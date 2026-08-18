"""接口测试运行时变量上下文。

本模块用于在同一条 API 测试执行链中保存 token、interface_id 等动态变量，
替代早期版本中共享 ``extract.yaml`` 文件的做法。变量全部保存在内存中，
并按 ``session / scenario / case`` 三个逻辑作用域管理。

注意：三个作用域是 VariableContext 内部的逻辑命名空间；真正的跨测试隔离
由 ``testcases/conftest.py`` 中 function-scoped fixture 为每条测试创建独立实例实现。
"""
from __future__ import annotations

import copy
import re
from typing import Any

_SCOPES = ("session", "scenario", "case")
_LOOKUP_ORDER = ("case", "scenario", "session")
_VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_EXACT_VARIABLE_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


class VariableNotFoundError(KeyError):
    """当请求的运行时变量不存在时抛出。"""


class VariableContext:
    """保存并解析接口测试运行时变量。

    默认写入 ``scenario`` 作用域；未显式指定读取作用域时，按
    ``case -> scenario -> session`` 的顺序查找，使更具体的值可以覆盖
    更通用的同名变量。
    """

    def __init__(self) -> None:
        """创建三个相互独立的逻辑作用域。"""
        self._data: dict[str, dict[str, Any]] = {scope: {} for scope in _SCOPES}

    @staticmethod
    def _validate_scope(scope: str) -> str:
        """校验作用域名称并返回合法名称。"""
        if scope not in _SCOPES:
            raise ValueError(f"Unsupported variable scope: {scope!r}; expected one of {_SCOPES}")
        return scope

    def set(self, key: str, value: Any, scope: str = "scenario") -> None:
        """把变量写入指定作用域。

        Args:
            key: 变量名，例如 ``access_token``。
            value: 任意可保存的 Python 值。
            scope: ``session``、``scenario`` 或 ``case``，默认 ``scenario``。
        """
        self._data[self._validate_scope(scope)][key] = value

    def get(self, key: str, scope: str | None = None) -> Any:
        """读取变量；未指定作用域时按 case -> scenario -> session 查找。

        Raises:
            VariableNotFoundError: 指定变量在目标作用域或全部作用域中不存在。
        """
        if scope is not None:
            selected_scope = self._validate_scope(scope)
            if key in self._data[selected_scope]:
                return self._data[selected_scope][key]
            raise VariableNotFoundError(
                f"Variable {key!r} not found in scope {selected_scope!r}"
            )

        # 更具体的 case 值优先，从而允许单条用例覆盖场景级/会话级默认值。
        for selected_scope in _LOOKUP_ORDER:
            if key in self._data[selected_scope]:
                return self._data[selected_scope][key]
        raise VariableNotFoundError(f"Variable {key!r} not found in runtime context")

    def clear(self, scope: str | None = None) -> None:
        """清空指定作用域；scope=None 时清空整个上下文。"""
        if scope is None:
            for values in self._data.values():
                values.clear()
            return
        self._data[self._validate_scope(scope)].clear()

    def replace_variables(self, value: Any) -> Any:
        """递归替换字符串、字典、列表或元组中的 ``${variable}``。

        精确表达式（如 ``${interface_id}``）保留变量原始类型；嵌入其他文本中的
        表达式（如 ``Bearer ${access_token}``）转换为字符串后替换。

        Raises:
            VariableNotFoundError: 表达式引用了不存在的变量。
        """
        if isinstance(value, str):
            exact = _EXACT_VARIABLE_PATTERN.fullmatch(value)
            if exact:
                # 精确表达式保留 int/list 等原始类型，避免所有数据都被转成字符串。
                return self.get(exact.group(1))

            def replace(match: re.Match[str]) -> str:
                return str(self.get(match.group(1)))

            return _VARIABLE_PATTERN.sub(replace, value)
        if isinstance(value, dict):
            return {key: self.replace_variables(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.replace_variables(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.replace_variables(item) for item in value)
        return value

    def export_debug_snapshot(self) -> dict[str, dict[str, Any]]:
        """返回上下文深拷贝，供调试展示使用且不会暴露内部可变对象。"""
        return copy.deepcopy(self._data)
