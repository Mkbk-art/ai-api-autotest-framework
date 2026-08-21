"""Shortlink 真实 SUT 的 V2 项目上下文与 Case Hook 注册。

本模块只解决当前被测项目特有的“前置资源如何准备、响应后如何规范化、测试数据如何
清理”。通用 Framework Core 只认识 Provider/Hook 的字符串名称，不理解登录、gid、
短链、回收站等业务概念。换一个 SUT 时新增自己的项目扩展模块即可。
"""
from __future__ import annotations

# contextmanager 让“创建资源 -> 使用 -> 清理”的项目生命周期可以被 CaseExecutor ExitStack 管理。
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import urlsplit

# Registry 是 Framework Core 暴露的项目扩展接口；本模块只做注册，不修改 Core 行为。
from core.context_provider import CaseHookRegistry, ContextProviderRegistry
from core.variable_context import VariableNotFoundError
# 这些 helper 都属于 Shortlink 项目适配层，包含当前 SUT 特有的业务状态和存储命名规则。
from testcases.shortlink.support import (
    capture_created_link_context,
    cleanup_shortlink,
    create_shortlink_from_case,
    prepare_shortlink_static_context,
    prepare_shortlink_storage_context,
    remove_shortlink_from_recycle_bin,
    save_shortlink_to_recycle_bin,
)


def _context_value(executor: Any, name: str) -> Any | None:
    """安全读取运行时变量；缺失时返回 None，便于失败路径判断是否真的产生了资源。"""
    try:
        return executor.runner.context.get(name, scope="scenario")
    except VariableNotFoundError:
        return None


def _created_identity_from_context(executor: Any) -> tuple[str, str] | None:
    """从已提取的 Create 变量恢复 cleanup 所需 gid/fullShortUrl 身份。

    ApiRunner 的 extract 发生在 validation 之前，因此即使后续 DB/Redis 断言失败，只要 SUT
    已经成功创建资源，``short_url`` 与 ``created_gid`` 仍然存在。这个函数让 teardown 在
    失败路径同样能够清理测试数据，而不要求修改通用 ApiRunner 的执行顺序。
    """
    gid = _context_value(executor, "gid") or _context_value(executor, "created_gid")
    full_short_url = _context_value(executor, "full_short_url")
    if isinstance(gid, str) and gid and isinstance(full_short_url, str) and full_short_url:
        return gid, full_short_url

    short_url = _context_value(executor, "short_url")
    if not (isinstance(gid, str) and gid and isinstance(short_url, str) and short_url):
        return None
    parsed = urlsplit(short_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.path:
        return None
    return gid, f"{parsed.netloc}{parsed.path}".rstrip("/")


def _static_provider(executor: Any) -> None:
    """准备 username、登录 Redis Key 等不会发 HTTP 的项目静态上下文。"""
    prepare_shortlink_static_context(executor.runner)


def _authenticated_provider(executor: Any) -> None:
    """复用 YAML 登录 Case 建立 token，而不是在 fixture/helper 再写一份登录请求。"""
    executor.ensure_context("shortlink.static")
    executor.execute("shortlink.auth.login.success")


def _group_provider(executor: Any) -> None:
    """复用 YAML Group Case 获取 gid，并由 Hook 生成后续物理表上下文。"""
    executor.ensure_context("shortlink.authenticated")
    executor.execute("shortlink.group.query.success")


@contextmanager
def _created_provider(executor: Any) -> Iterator[dict[str, str]]:
    """准备一条可用短链，并在整个 Case/Workflow 结束时通过真实业务 API 清理。"""
    executor.ensure_context("shortlink.group")
    created = create_shortlink_from_case(executor)
    try:
        yield created
    finally:
        cleanup_shortlink(
            executor.runner,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )


@contextmanager
def _recycled_provider(executor: Any) -> Iterator[dict[str, str]]:
    """准备“已进入回收站但尚未 Remove”的短链状态，供单接口 Redirect 负向 Case 使用。"""
    executor.ensure_context("shortlink.group")
    created = create_shortlink_from_case(executor)
    moved_to_recycle = False
    removed = False
    try:
        save_shortlink_to_recycle_bin(
            executor.runner,
            gid=created["gid"],
            full_short_url=created["full_short_url"],
        )
        moved_to_recycle = True
        yield created
    finally:
        # Save 失败时仍按正常 save -> remove 业务路径兜底；Save 成功时只补 Remove。
        if not moved_to_recycle:
            cleanup_shortlink(
                executor.runner,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
        elif not removed:
            remove_shortlink_from_recycle_bin(
                executor.runner,
                gid=created["gid"],
                full_short_url=created["full_short_url"],
            )
            removed = True


@contextmanager
def _visited_provider(executor: Any) -> Iterator[dict[str, str] | None]:
    """准备“一条短链已经真实访问一次”的统计前置，并复用 Redirect YAML Case 触发访问。"""
    executor.ensure_context("shortlink.created")
    executor.execute("shortlink.redirect.success")
    yield None


def _capture_group_hook(executor: Any, _case: Any, _response: Any) -> None:
    """Group extract 完成后生成当前 gid 对应的物理分表上下文。"""
    gid = executor.runner.context.get("gid", scope="scenario")
    if not isinstance(gid, str) or not gid:
        raise AssertionError("group response did not extract a valid gid")
    prepare_shortlink_storage_context(executor.runner, gid=gid)


def _capture_created_hook(executor: Any, _case: Any, response: Any) -> None:
    """Create 成功后统一规范化 short_uri/full_short_url 以及项目存储 Key。"""
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("code") != "0":
        return
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AssertionError("create response missing object data")
    created = capture_created_link_context(executor.runner, data)
    # 当前 Create Case 的 gid 必须与前置 Group 相同，避免 cleanup 误操作其他测试资源。
    expected_gid = executor.runner.context.get("gid", scope="scenario")
    assert created["gid"] == expected_gid


def _cleanup_created_hook(executor: Any, _case: Any, _response: Any) -> None:
    """Create Case 无论后续断言成功或失败，只要资源已产生都执行真实业务清理。"""
    identity = _created_identity_from_context(executor)
    if identity is None:
        # 非法 URL、Gateway 401 等负向 Case 没有创建资源，不应伪造 cleanup 请求。
        return
    gid, full_short_url = identity
    cleanup_shortlink(executor.runner, gid=gid, full_short_url=full_short_url)


def register_extensions(
    providers: ContextProviderRegistry,
    hooks: CaseHookRegistry,
) -> None:
    """向 Framework Registry 注册当前 SUT 的上下文 Provider 与 Hook。"""
    # Provider 名称是 YAML ``requires`` 的稳定公共引用；实现细节完全留在本项目模块。
    # Dependency metadata covers the Provider's whole lifecycle (setup + cleanup).
    # Stage 6 reads these explicit relations; Core never parses project Python source.
    providers.register("shortlink.static", _static_provider, requires=(), operations=())
    providers.register(
        "shortlink.authenticated",
        _authenticated_provider,
        requires=("shortlink.static",),
        operations=("shortlinkUserLogin",),
    )
    providers.register(
        "shortlink.group",
        _group_provider,
        requires=("shortlink.authenticated",),
        operations=("shortlinkGroupList",),
    )
    providers.register(
        "shortlink.created",
        _created_provider,
        requires=("shortlink.group",),
        operations=("shortlinkCreate", "shortlinkRecycleSave", "shortlinkRecycleRemove"),
    )
    providers.register(
        "shortlink.recycled",
        _recycled_provider,
        requires=("shortlink.group",),
        operations=("shortlinkCreate", "shortlinkRecycleSave", "shortlinkRecycleRemove"),
    )
    providers.register(
        "shortlink.visited",
        _visited_provider,
        requires=("shortlink.created",),
        operations=("shortlinkRedirect",),
    )

    # Hook 只在对应 Case 显式声明时运行，不把项目业务钩进所有框架请求。
    hooks.register("shortlink.capture_group", _capture_group_hook)
    hooks.register("shortlink.capture_created", _capture_created_hook)
    hooks.register("shortlink.cleanup_created", _cleanup_created_hook)
