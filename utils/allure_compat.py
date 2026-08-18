"""Allure 可选依赖兼容层。

框架核心代码统一通过本模块调用 Allure。当 ``allure-pytest`` 已安装时转发到
真实 Allure API；未安装时提供无副作用的兼容对象，使单元测试和 JUnit 执行
仍能正常进行，而不是因为报告插件缺失导致核心测试无法启动。
"""
from __future__ import annotations

from enum import Enum
from typing import Any

try:  # pragma: no cover - 安装 allure-pytest 的真实环境走该分支。
    import allure as _allure
except ModuleNotFoundError:  # 本地最小环境/单元测试降级。
    _allure = None


class _AttachmentType(str, Enum):
    """Allure 不可用时需要的最小附件类型枚举。"""

    TEXT = "text/plain"
    JSON = "application/json"


attachment_type = _allure.attachment_type if _allure is not None else _AttachmentType


def attach(body: Any, name: str, attachment_type: Any = None) -> None:
    """附加报告内容；Allure 未安装时安全地忽略该操作。"""
    if _allure is not None:
        _allure.attach(body, name, attachment_type)


class _Dynamic:
    """Allure 不可用时的 dynamic API 兼容对象。"""

    def title(self, value: str) -> None:
        """设置动态标题；无 Allure 环境下为空操作。"""
        if _allure is not None:
            _allure.dynamic.title(value)

    def story(self, value: str) -> None:
        """设置动态 Story；无 Allure 环境下为空操作。"""
        if _allure is not None:
            _allure.dynamic.story(value)


dynamic = _allure.dynamic if _allure is not None else _Dynamic()


def is_available() -> bool:
    """返回当前 Python 环境是否可以使用真实 Allure API。"""
    return _allure is not None
