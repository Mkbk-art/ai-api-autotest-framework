"""项目上下文 Provider 与 Case Hook 的通用注册机制。

框架只认识字符串名称和统一调用协议；登录、租户、测试资源、清理等具体业务实现
由项目适配层注册。这样 YAML 可以声明“需要什么上下文”，而不让 Core 知道 SUT 细节。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ContextProviderError(RuntimeError):
    """表示 Provider 未注册、循环依赖或生命周期使用错误。"""


ContextProvider = Callable[[Any], Any]
CaseHook = Callable[[Any, Any, Any], None]


class ContextProviderRegistry:
    """保存项目级上下文 Provider。"""

    def __init__(self) -> None:
        self._providers: dict[str, ContextProvider] = {}

    def register(self, name: str, provider: ContextProvider) -> None:
        """注册一个稳定名称的 Provider；重复注册视为项目配置错误。"""
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized:
            raise ContextProviderError("context provider name must be non-empty")
        if normalized in self._providers:
            raise ContextProviderError(f"context provider already registered: {normalized}")
        self._providers[normalized] = provider

    def get(self, name: str) -> ContextProvider:
        """读取 Provider；未知名称在发 HTTP 前快速失败。"""
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ContextProviderError(f"unknown context provider: {name}") from exc


class CaseHookRegistry:
    """保存 before/after/teardown 可调用的项目 Hook。"""

    def __init__(self) -> None:
        self._hooks: dict[str, CaseHook] = {}

    def register(self, name: str, hook: CaseHook) -> None:
        """注册一个项目 Hook。"""
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized:
            raise ContextProviderError("case hook name must be non-empty")
        if normalized in self._hooks:
            raise ContextProviderError(f"case hook already registered: {normalized}")
        self._hooks[normalized] = hook

    def run(self, name: str, executor: Any, case: Any, response: Any) -> None:
        """执行指定 Hook。"""
        try:
            hook = self._hooks[name]
        except KeyError as exc:
            raise ContextProviderError(f"unknown case hook: {name}") from exc
        hook(executor, case, response)
