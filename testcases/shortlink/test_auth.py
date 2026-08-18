"""短链接真实项目：认证域测试入口。

所有认证 Case 都来自 ``auth.yaml``；Smoke/Core/Regression marker 由 YAML 的 ``level`` 和
``tags`` 自动生成。Python 不再为“成功登录、错误密码、Redis 登录态”拆三个文件。
"""
from __future__ import annotations

# Pytest 仅提供参数化入口；Case 层级/标签本身来自 YAML 元数据。
import pytest

# CaseLoader 把 YAML level/tags 自动转换为 pytest marks。
from core.case_loader import get_testcase_params
# 当前 SUT 的静态 username/Redis Key 由项目 adapter 准备，不进入 core。
from testcases.shortlink.support import AUTH_YAML_PATH, prepare_shortlink_static_context


# 一次加载认证业务域的所有 Case；新增普通认证场景通常只需要修改 auth.yaml。
YAML_FILE = AUTH_YAML_PATH
# 这里不按 smoke/core/regression 手工分组，统一由 pytest marker 在运行时筛选。
CASES = get_testcase_params(YAML_FILE)


@pytest.mark.parametrize("base_info,test_case", CASES)
def test_shortlink_auth_cases(base_info, test_case, request_base):
    """按 YAML 执行认证域 Case；登录态 Redis 校验同样由 validation 声明。"""
    # login_redis regression 需要完整 Redis Key；普通 Smoke/Core 写入静态上下文也不会改变请求契约。
    prepare_shortlink_static_context(request_base)
    # ApiRunner 是唯一执行入口：请求、提取、HTTP/Redis 断言全部由 YAML 驱动。
    response = request_base.run(base_info, test_case)
    # 最小 Python 守护只允许当前认证域已知的 HTTP 层结果；业务细节仍由 YAML validation 判断。
    assert response.status_code in {200, 401}
