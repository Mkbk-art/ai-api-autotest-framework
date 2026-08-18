"""短链接真实项目的业务前置 Fixture。

Fixture 只负责编排“登录 -> 分组 -> 创建 -> 清理”这类前置生命周期，真实接口定义仍从
4 份业务域 YAML 读取并交给 ApiRunner。MySQL/Redis 连接不再由短链接 fixture 创建，
而是统一断言引擎在遇到 YAML 数据源断言时按需加载通用 ``db/`` Client。
"""
from __future__ import annotations

# Pytest 只负责 fixture 生命周期；接口参数和断言都不在这里重新定义。
import pytest

# support 是当前短链接 SUT 的适配层，core/db 不依赖这些业务 helper。
from testcases.shortlink.support import (
    AUTH_YAML_PATH,
    LINK_YAML_PATH,
    capture_created_link_context,
    cleanup_shortlink,
    create_shortlink_from_yaml,
    prepare_shortlink_static_context,
    prepare_shortlink_storage_context,
    shortlink_case,
)


@pytest.fixture
def shortlink_authenticated_context(request_base):
    """执行 YAML 登录成功 Case，并把 username/token 留在当前 scenario。"""
    # 先从 env.shortlink-local.yaml 写入 username 等项目静态变量。
    prepare_shortlink_static_context(request_base)
    # 登录请求本身从 auth.yaml 的 login_success workflow 读取，fixture 不复制 Body/Header。
    base_info, test_case = shortlink_case(AUTH_YAML_PATH, "login_success")
    # ApiRunner 完成动态变量替换、真实请求、token 提取和 YAML 响应断言。
    response = request_base.run(base_info, test_case)
    # 这条 assert 保护 fixture 自身的前置契约；业务 code/token 已由 YAML validation 验证。
    assert response.status_code == 200
    # 返回值只暴露后续 fixture 真正需要的 username；token 保留在 VariableContext 中。
    return {"username": request_base.context.get("username", scope="scenario")}


@pytest.fixture
def shortlink_group_context(request_base, shortlink_authenticated_context):
    """执行 YAML Group 成功 Case，并准备当前 gid 对应的物理分片上下文。"""
    # 显式依赖 authenticated fixture，保证 Group 前 username/token 已准备完成。
    _ = shortlink_authenticated_context
    # Group 请求和 gid extract 都复用 link.yaml，而不是 Python helper 再发一套请求。
    base_info, test_case = shortlink_case(LINK_YAML_PATH, "group_success")
    # 统一 ApiRunner 执行真实 Group 接口。
    response = request_base.run(base_info, test_case)
    # 业务成功与 gid 存在由 YAML 断言保证，这里仅守护前置 HTTP 状态。
    assert response.status_code == 200
    # gid 已由 YAML extract 写入 scenario，后续 Create/Page 使用 ${gid}。
    gid = request_base.context.get("gid", scope="scenario")
    # 项目 adapter 根据真实 ShardingSphere 规则准备 link_table 等运行时变量。
    prepare_shortlink_storage_context(request_base, gid=gid)
    # fixture 返回最小业务上下文，避免把 token/密码塞进可打印对象。
    return {"gid": gid}


@pytest.fixture
def shortlink_created_context(request_base, shortlink_group_context):
    """复用 YAML Create 主 Case 创建一条短链，并在测试结束后通过业务 API 清理。"""
    # 依赖 Group fixture，确保 gid 和鉴权上下文已经存在。
    _ = shortlink_group_context
    # 前置 Create 仍读取 link.yaml/create_success；仅项目适配层处理已知 Sentinel 临时限流。
    created = create_shortlink_from_yaml(request_base)
    try:
        # yield 之前属于 Pytest Setup，测试函数收到的是本次真实创建结果。
        yield created
    finally:
        # 无论测试 Call 成功还是失败，都通过真实回收业务 API 清理测试数据。
        cleanup_shortlink(
            request_base,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
