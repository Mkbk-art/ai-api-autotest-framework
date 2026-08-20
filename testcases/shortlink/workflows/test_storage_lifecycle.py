"""Shortlink 回收存储生命周期 Workflow。

这里保留 Python 的唯一原因是测试本身存在多状态控制流：Create -> Save -> 中间数据源
断言 -> Remove -> 终态断言，并且任何中间失败都必须根据已到达的状态执行不同 cleanup。
HTTP Create 规格和 MySQL/Redis 预期仍来自 V2 YAML，Python 不重复定义普通接口 Case。
"""
from __future__ import annotations

# Pytest 只负责把两条 execution=workflow 的结构化 Case 作为独立 Regression Item 展示。
import pytest

from core.case_registry import CaseRegistry
from utils.project_paths import PROJECT_ROOT
from testcases.shortlink.support import (
    cleanup_shortlink,
    create_shortlink_from_case,
    remove_shortlink_from_recycle_bin,
    save_shortlink_to_recycle_bin,
)


# Workflow 仍以同一 CaseRegistry/YAML 为测试资产来源，不维护第二份 Python Case 名单。
_YAML_DIR = PROJECT_ROOT / "testcases" / "shortlink" / "yaml"
_REGISTRY = CaseRegistry.from_paths(sorted(_YAML_DIR.glob("*.yaml")))


def _workflow_params():
    """把 YAML workflow Case 转为保留 level/tags 的 Pytest 参数。"""
    params = []
    for case in _REGISTRY.all_cases():
        if case.execution != "workflow":
            continue
        if case.workflow.get("handler") != "shortlink.storage_lifecycle":
            continue
        marks = [getattr(pytest.mark, name) for name in case.marker_names]
        params.append(pytest.param(case, marks=marks, id=case.case_id))
    return params


# 公开常量便于架构测试证明：当前只有真正复杂的两条生命周期测试保留 Python。
WORKFLOW_CASES = _workflow_params()


@pytest.mark.parametrize("workflow_case", WORKFLOW_CASES)
def test_shortlink_storage_lifecycle(workflow_case, case_executor):
    """按 YAML 声明的断言组观察 Create/Recycle/Remove 三个真实业务状态。"""
    # create_shortlink_from_case 会复用稳定 case_id 的 Create 请求，并建立 gid/URL/DB/Redis 上下文。
    created = create_shortlink_from_case(case_executor)
    moved_to_recycle = False
    removed = False

    try:
        # goto-cache Case 需要先观察 Create 成功后 Redis 缓存是否存在；SQL/Key/expected 仍在 YAML。
        after_create = workflow_case.workflow.get("after_create_assertions")
        if after_create:
            case_executor.runner.validate(after_create)

        # Save/Remove 是当前 SUT 的状态迁移接口，由项目 adapter 封装；Framework Core 不理解回收站。
        save_shortlink_to_recycle_bin(
            case_executor.runner,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
        moved_to_recycle = True

        # 每个 Workflow 可以在同一状态点声明不同 MySQL/Redis 观察，不需要复制 Python 流程。
        after_save = workflow_case.workflow.get("after_save_assertions")
        if after_save:
            case_executor.runner.validate(after_save)

        remove_shortlink_from_recycle_bin(
            case_executor.runner,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
        removed = True

        # DB lifecycle 需要观察逻辑删除后的最终状态；没有该断言组的 Workflow 自动跳过。
        after_remove = workflow_case.workflow.get("after_remove_assertions")
        if after_remove:
            case_executor.runner.validate(after_remove)
    finally:
        # 根据真实到达状态选择最小 cleanup 路径，避免重复 Save/Remove 造成二次业务错误。
        if not moved_to_recycle:
            cleanup_shortlink(
                case_executor.runner,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
        elif not removed:
            remove_shortlink_from_recycle_bin(
                case_executor.runner,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
