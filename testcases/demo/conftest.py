"""受控 Mock Demo 自己的业务前置 Fixture。

这些 fixture 只服务框架自测示例，不属于公共 testcases/conftest.py。把业务登录和
资源准备留在 suite 内部，可以证明以后接入新的真实项目时不会污染共享框架夹具。
"""
from __future__ import annotations

# Pytest 只负责 Demo fixture 生命周期。
import pytest


@pytest.fixture
def authenticated_context(request_base):
    """Demo 登录成功后把 access_token 写入当前 scenario 上下文。"""
    # 这里调用的是 Mock Demo 自己的固定契约，不影响任何真实项目 suite。
    response = request_base.client.request(
        "POST",
        f"{request_base.host}/api/v1/auth/login",
        json={"username": "demo_user", "password": "demo_password"},
    )
    # fixture 前置失败必须直接中止当前 Demo Case。
    assert response.status_code == 200
    # Token 只进入当前测试 VariableContext，不使用模块级共享变量。
    token = response.json()["data"]["access_token"]
    request_base.context.set("access_token", token, scope="scenario")
    return token


@pytest.fixture
def published_interface_context(request_base, authenticated_context):
    """Demo 独立发布一个接口并保存 interface_id，避免依赖其他测试执行顺序。"""
    # 显式依赖 authenticated_context 保证发布前已经准备好有效 token。
    response = request_base.client.request(
        "POST",
        f"{request_base.host}/api/v1/interface/publish",
        headers={"Authorization": f"Bearer {authenticated_context}"},
        json={"name": "fixture_api", "method": "GET", "path": "/fixture"},
    )
    # 发布失败属于 Setup 失败，不允许后面的调用 Case 使用不存在的资源。
    assert response.status_code == 200
    # 资源 ID 写入 scenario，Demo YAML 后续通过动态表达式读取。
    interface_id = response.json()["data"]["interfaceId"]
    request_base.context.set("interface_id", interface_id, scope="scenario")
    return interface_id
