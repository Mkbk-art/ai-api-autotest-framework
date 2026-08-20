"""Mock Demo 的项目上下文注册。

Demo 只用于框架离线验证。这里展示新项目如何注册可复用 Context Provider：普通 YAML
Case 只声明 ``requires``，无需创建业务 ``test_xx.py`` 参数化 wrapper。
"""
from __future__ import annotations

from contextlib import contextmanager


def register_extensions(providers, hooks) -> None:
    """向框架注册 Demo 的登录与已发布资源上下文。"""
    _ = hooks

    @contextmanager
    def authenticated(executor):
        # 复用同一条正式 YAML 登录 Case；token 由 extract 写入 scenario。
        executor.execute("demo.auth.login.success")
        yield

    @contextmanager
    def published_interface(executor):
        # 发布资源前先保证已经登录；Provider 自身可以声明依赖而不污染 Core。
        executor.ensure_context("demo.authenticated")
        executor.execute("demo.interface.publish.success")
        yield

    providers.register("demo.authenticated", authenticated)
    providers.register("demo.published_interface", published_interface)
