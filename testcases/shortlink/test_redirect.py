"""短链接真实项目：Redirect 域测试入口。

正常跳转、不存在短码、回收态和 Redis UV/UIP 校验集中在 ``redirect.yaml``。Python 只在
需要先创建/回收真实短链时负责编排生命周期，302/Location/Redis 断言继续由 YAML 驱动。
"""
from __future__ import annotations

# Pytest 负责参数化与 fixture 生命周期，业务请求数据不写在测试函数中。
import pytest

# YAML level/tags 会自动转成 marks，workflow 用于选择不同前置流程。
from core.case_loader import get_testcase_params
# 这些 helper 只属于当前短链接 SUT 适配层，不进入通用 core/db。
from testcases.shortlink.support import (
    REDIRECT_YAML_PATH,
    create_shortlink_from_yaml,
    remove_shortlink_from_recycle_bin,
    save_shortlink_to_recycle_bin,
)


# 四组 workflow 都来自同一份 redirect.yaml，避免为每个异常场景新建文件。
YAML_FILE = REDIRECT_YAML_PATH
# 正常 Redirect 依赖“已创建短链” fixture。
SUCCESS = get_testcase_params(YAML_FILE, workflows={"redirect_success"})
# 不存在短码不依赖登录或 Create，可直接执行。
NOTFOUND = get_testcase_params(YAML_FILE, workflows={"redirect_notfound"})
# 回收态需要 Python 编排 Create -> Save -> Redirect -> Remove。
RECYCLED = get_testcase_params(YAML_FILE, workflows={"redirect_recycled"})
# Redis UV/UIP Regression 在 Redirect 后再执行 YAML post_validation。
REDIS_STATS = get_testcase_params(YAML_FILE, workflows={"redirect_redis"})


@pytest.mark.parametrize("base_info,test_case", SUCCESS)
def test_shortlink_redirect_success(base_info, test_case, request_base, shortlink_created_context):
    """新创建短链第一跳必须返回 YAML 声明的 302/Location 契约。"""
    # fixture 已经真实 Create；short_uri 是 redirect.yaml URL 的动态来源。
    assert shortlink_created_context["short_uri"]
    # 302、Location 和 allow_redirects=false 都由 YAML 驱动。
    request_base.run(base_info, test_case)


@pytest.mark.parametrize("base_info,test_case", NOTFOUND)
def test_shortlink_redirect_notfound(base_info, test_case, request_base):
    """随机不存在短码直接访问 Project，不依赖登录或其他测试执行顺序。"""
    # random_string()、绝对 URL、302 与 notfound Location 都已经声明在 YAML。
    request_base.run(base_info, test_case)


@pytest.mark.parametrize("base_info,test_case", RECYCLED)
def test_shortlink_redirect_recycled(
    base_info,
    test_case,
    request_base,
    shortlink_group_context,
):
    """Create -> Save 后访问同一 shortUri 应按 YAML 跳到 notfound，最后再 Remove。"""
    # Group fixture 只保证真实 gid/token 前置存在，不决定 Redirect 的业务断言。
    _ = shortlink_group_context
    # 前置 Create 复用 link.yaml/create_success，避免本流程再维护一份请求体。
    created = create_shortlink_from_yaml(request_base)
    # moved 用于保证 finally 只在 Save 成功后执行对应 Remove。
    moved = False
    try:
        # 先通过真实业务 API 将当前短链移入回收站。
        save_shortlink_to_recycle_bin(
            request_base, gid=created["gid"], full_short_url=created["full_short_url"]
        )
        # Save 成功后记录状态，保证异常路径也能正确清理。
        moved = True
        # Redirect URL、关闭自动跟随和 notfound 断言全部来自 redirect.yaml。
        request_base.run(base_info, test_case)
    finally:
        # 测试完成后恢复环境，不让回收站测试数据持续污染真实 SUT。
        if moved:
            remove_shortlink_from_recycle_bin(
                request_base, gid=created["gid"], full_short_url=created["full_short_url"]
            )


@pytest.mark.parametrize("base_info,test_case", REDIS_STATS)
def test_shortlink_redirect_redis_state(
    base_info,
    test_case,
    request_base,
    shortlink_created_context,
):
    """Redirect 后 UV/UIP Redis Set 的通用 scard 断言由 YAML post_validation 执行。"""
    # Create fixture 已将 full_short_url 映射为 uv_redis_key/uip_redis_key 运行时变量。
    assert shortlink_created_context["short_uri"]
    # 先执行真实 Redirect，并由 YAML 校验第一跳 302/Location。
    request_base.run(base_info, test_case)
    # 再执行 YAML post_validation；Python 不知道具体 Redis Key 前缀或 Set 结构细节。
    request_base.validate(test_case.get("post_validation"))
