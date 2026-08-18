"""短链接真实项目：Group、Create、Page、Recycle/Storage 业务域测试入口。

``link.yaml`` 集中管理该业务域的 9 个 Case。普通单接口 Case 直接交给 ApiRunner；只有
回收状态迁移这种多步骤流程保留少量 Python 编排，MySQL/Redis 预期仍全部声明在 YAML。
"""
from __future__ import annotations

# Pytest 只负责参数化和 fixture 生命周期；level/tags 已从 YAML 自动生成 marker。
import pytest

# CaseLoader 负责把同一业务域 YAML 按 workflow 切分到不同前置方式。
from core.case_loader import get_testcase_params
# support 中的函数全部属于当前短链接 SUT 适配层，不进入通用框架 core/db。
from testcases.shortlink.support import (
    LINK_YAML_PATH,
    capture_created_link_context,
    cleanup_shortlink,
    create_shortlink_from_yaml,
    prepare_shortlink_static_context,
    remove_shortlink_from_recycle_bin,
    save_shortlink_to_recycle_bin,
)


# 一个业务域只维护一份 link.yaml；下面只是按“是否需要前置/多步骤”选择 Case。
YAML_FILE = LINK_YAML_PATH
# 正常 Group 需要先登录，成功后会 extract gid。
GROUP_SUCCESS = get_testcase_params(YAML_FILE, workflows={"group_success"})
# 缺 token Group 必须绕开登录 fixture，才能真实验证 Gateway 401。
GROUP_UNAUTHORIZED = get_testcase_params(YAML_FILE, workflows={"group_unauthorized"})
# 正常、非法 URL、MySQL Create 一致性都共享 Login -> Group 前置。
CREATE_AUTHENTICATED = get_testcase_params(
    YAML_FILE, workflows={"create_success", "create_invalid", "create_db"}
)
# 缺 token Create 不建立任何鉴权前置。
CREATE_UNAUTHORIZED = get_testcase_params(YAML_FILE, workflows={"create_unauthorized"})
# Page 需要一条刚创建的真实短链用于精确定位记录。
PAGE_SUCCESS = get_testcase_params(YAML_FILE, workflows={"page_success"})
# 回收 MySQL 和 goto Redis 都属于 Create -> Save -> Remove 多步骤状态流。
STORAGE_WORKFLOWS = get_testcase_params(YAML_FILE, workflows={"recycle_db", "goto_cache"})


@pytest.mark.parametrize("base_info,test_case", GROUP_SUCCESS)
def test_shortlink_group_cases(base_info, test_case, request_base, shortlink_authenticated_context):
    """登录后 Group Smoke 完全由 YAML 请求、提取和响应断言驱动。"""
    # 显式 fixture 依赖保证 username/token 已经由 auth.yaml 写入 VariableContext。
    _ = shortlink_authenticated_context
    # Group URL/Header、gid extract 和业务断言全部由 link.yaml 驱动。
    request_base.run(base_info, test_case)


@pytest.mark.parametrize("base_info,test_case", GROUP_UNAUTHORIZED)
def test_shortlink_group_unauthorized(base_info, test_case, request_base):
    """缺 token Group Case 不执行登录前置，真实验证 Gateway 401。"""
    # 这里只准备环境 YAML 中的 username；绝不产生 token。
    prepare_shortlink_static_context(request_base)
    # link.yaml 的 unauthorized baseInfo 本身就没有 token Header。
    request_base.run(base_info, test_case)


@pytest.mark.parametrize("base_info,test_case", CREATE_AUTHENTICATED)
def test_shortlink_create_cases(base_info, test_case, request_base, shortlink_group_context):
    """正常/非法/DB 持久化 Create 共用一份业务域 YAML 和同一前置链。"""
    # Group fixture 已完成真实 Login -> Group，并准备 gid / link_table 上下文。
    _ = shortlink_group_context
    # ApiRunner 按当前 Case 执行 YAML Create；Regression 的 DB 断言也在同一 validation 中完成。
    response = request_base.run(base_info, test_case)
    # 读取响应只用于判断“是否产生真实测试数据需要清理”，不重复 YAML 业务断言。
    payload = response.json()
    # 非法 originUrl 等负向 Case 不会产生短链，因此不做伪造 Cleanup。
    if isinstance(payload, dict) and payload.get("code") == "0":
        # 成功 Case 将响应统一规范化为 short_uri/full_short_url 等运行时变量。
        created = capture_created_link_context(request_base, payload["data"])
        try:
            # created_gid 与前置 Group gid 必须属于同一 scenario，避免清理错数据。
            assert created["gid"] == request_base.context.get("gid", scope="scenario")
        finally:
            # 无论后续 Python 守护是否失败，都通过真实业务 API 回收本次创建数据。
            cleanup_shortlink(
                request_base,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )


@pytest.mark.parametrize("base_info,test_case", CREATE_UNAUTHORIZED)
def test_shortlink_create_unauthorized(base_info, test_case, request_base):
    """缺 token Create 不建立登录/Group 前置，确保失败层次确实是 Gateway。"""
    # 只准备当前项目 username 等静态变量，不调用 Login，避免偷偷得到 token。
    prepare_shortlink_static_context(request_base)
    # YAML Body 保持业务结构合法，验证变量只有“缺 token”这一项。
    request_base.run(base_info, test_case)


@pytest.mark.parametrize("base_info,test_case", PAGE_SUCCESS)
def test_shortlink_page_cases(base_info, test_case, request_base, shortlink_created_context):
    """Page records 应精确包含当前测试刚创建的短链。"""
    # Page HTTP/业务 code/records 存在性已经由 YAML validation 校验。
    response = request_base.run(base_info, test_case)
    # 下面只做“当前创建实体必须出现在列表中”的跨步骤业务关联检查。
    records = response.json()["data"]["records"]
    # full_short_url 是本次 fixture Create 的唯一业务标识之一。
    expected = shortlink_created_context["full_short_url"]
    # Page 接口当前不能按 fullShortUrl 精确查询，所以从首 100 条记录中做精确匹配。
    matched = next((item for item in records if item.get("fullShortUrl") == expected), None)
    # 找不到刚创建的数据说明读写链路不一致，应让测试真实失败。
    assert matched is not None, f"created short link {expected!r} not found in page records"
    # gid 必须与当前创建记录一致。
    assert matched["gid"] == shortlink_created_context["gid"]
    # originUrl 必须与本次 YAML Create 的真实值一致，不写死站点。
    assert matched["originUrl"] == shortlink_created_context["origin_url"]
    # 新创建且未回收的短链应处于可用状态。
    assert matched["enableStatus"] == 0


@pytest.mark.parametrize("base_info,test_case", STORAGE_WORKFLOWS)
def test_shortlink_storage_workflows(
    base_info,
    test_case,
    request_base,
    shortlink_group_context,
):
    """按 YAML workflow 验证回收 MySQL 状态或 Redis goto 缓存生命周期。"""
    # baseInfo 的接口元信息由 YAML 保存；真实 Save/Remove 调用由项目 adapter 统一执行。
    _ = base_info, shortlink_group_context
    # 前置短链仍复用 link.yaml/create_success，不再维护第二份 Create Body。
    created = create_shortlink_from_yaml(request_base)
    # 两个布尔状态用于 finally 判断当前真实业务生命周期已经走到哪一步。
    moved_to_recycle = False
    removed = False
    # workflow 决定执行哪组 YAML 数据源断言，但 SQL/Redis Key 规则不写在 Python。
    workflow = test_case["workflow"]

    try:
        # goto_cache 需要先观察 Create 后缓存存在，因此在 Save 之前执行第一组 YAML 断言。
        if workflow == "goto_cache":
            request_base.validate(test_case.get("after_create_validation"))

        # 通过真实回收 API 将当前短链从正常态迁移到回收态。
        save_shortlink_to_recycle_bin(
            request_base,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
        # 只有 Save 确认成功才更新状态，避免 finally 错误执行 Remove。
        moved_to_recycle = True
        # MySQL enable_status / Redis goto Key 等预期全部从 YAML 读取。
        request_base.validate(test_case.get("after_save_validation"))

        # 完成真实业务逻辑删除，确保测试结束后不在回收站残留数据。
        remove_shortlink_from_recycle_bin(
            request_base,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
        # Remove 成功后记录终态，finally 不再重复清理。
        removed = True
        # 只有 recycle_db 需要额外观察 Remove 后 del_flag/del_time 的最终持久化状态。
        if workflow == "recycle_db":
            request_base.validate(test_case.get("after_remove_validation"))
    finally:
        # 如果连 Save 都没有成功，按正常 cleanup 的 save -> remove 流程兜底清理。
        if not moved_to_recycle:
            cleanup_shortlink(
                request_base,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
        # 如果 Save 已成功但 Remove 前测试失败，则只补最后一步 Remove。
        elif not removed:
            remove_shortlink_from_recycle_bin(
                request_base,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
