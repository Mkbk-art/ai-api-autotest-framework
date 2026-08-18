"""短链接真实项目接入层的业务编排辅助函数。

本模块属于 ``testcases/shortlink``，不是框架核心。它只负责当前被测系统特有的运行时
上下文：分片表名、Redis Key、Create 前置限流处理和回收清理。请求/断言主体仍由归类后的
YAML + ApiRunner 驱动；换成其他真实项目时新增自己的 ``testcases/<project>`` 适配层即可，
不需要修改 ``core/`` 或 ``db/``。
"""
from __future__ import annotations

# time 只服务“前置数据 Create 被 Sentinel 临时限流”的项目级有限等待。
import time
# Any 用于兼容 ApiRunner/FakeRunner 测试注入，避免 support 反向依赖具体实现类。
from typing import Any
# urlsplit 用于把 Create 返回的绝对短链拆成 Host+Path 与 short_uri 两种业务表示。
from urllib.parse import urlsplit

# 通用 YAML Loader 只负责读取结构；support 再按当前项目 workflow 选择 Case。
from core.case_loader import get_testcase_yaml
# PROJECT_ROOT 统一解决 Windows/Linux 项目根路径差异。
from utils.project_paths import PROJECT_ROOT
# Java HASH_MOD 计算是通用工具，表名前缀仍属于当前项目配置。
from utils.sharding import java_hash_mod


# 当前真实 SUT 的四个业务域 YAML 与 Python 入口放在同一个项目目录下，便于整体迁移/删除。
SHORTLINK_DIR = PROJECT_ROOT / "testcases" / "shortlink"
# 认证域：登录成功、错误密码、Redis 登录态。
AUTH_YAML_PATH = SHORTLINK_DIR / "yaml" / "auth.yaml"
# 链接域：Group/Create/Page/Recycle 及对应存储一致性。
LINK_YAML_PATH = SHORTLINK_DIR / "yaml" / "link.yaml"
# 跳转域：正常、notfound、回收态及 Redis UV/UIP。
REDIRECT_YAML_PATH = SHORTLINK_DIR / "yaml" / "redirect.yaml"
# 统计域：异步 Stats API 与 MySQL 最终持久化。
STATISTICS_YAML_PATH = SHORTLINK_DIR / "yaml" / "statistics.yaml"


def _project_config(request_base: Any) -> dict[str, Any]:
    """返回当前短链接项目适配配置，并在环境 YAML 缺失时快速失败。"""
    # runtime_config 是 ConfigManager 已合并后的当前环境配置，不读取终端 SHORTLINK_* 变量。
    runtime_config = getattr(request_base, "runtime_config", {})
    # ``shortlink`` 节点只属于当前 SUT；其他项目可以使用自己的 project 配置节点。
    values = runtime_config.get("shortlink") if isinstance(runtime_config, dict) else None
    # 缺少整个项目节点时立即失败，避免后面得到模糊 KeyError。
    if not isinstance(values, dict):
        raise RuntimeError("Missing shortlink project config in current environment YAML")
    # 返回项目适配字典；core/db 永远不会调用本函数。
    return values


def shortlink_case(path: Any, workflow: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """按 YAML ``workflow`` 读取唯一 Case，供 fixture/复杂流程复用同一声明源。"""
    # 读取完整业务域 YAML，再只筛选指定 workflow；这样前置 fixture 与正式用例共用同一 Case。
    matches = [
        (base_info, test_case)
        for base_info, test_case in get_testcase_yaml(path)
        if test_case.get("workflow") == workflow
    ]
    # workflow 在同一 YAML 内必须唯一，否则 fixture 不知道应复用哪条声明。
    if len(matches) != 1:
        raise AssertionError(
            f"expected one workflow={workflow!r} in {path}, actual={len(matches)}"
        )
    # 返回 Loader 原始二元组，后续仍交给 ApiRunner 处理动态变量和断言。
    return matches[0]


def prepare_shortlink_static_context(request_base: Any) -> None:
    """把账号和登录 Redis Key 等静态项目变量写入当前 scenario。"""
    # 账号从 env.shortlink-local.yaml 读取，用户后续只改 YAML 即可切换本地测试账号。
    config = _project_config(request_base)
    # username 是 Header 和登录 Redis Key 的共同业务输入。
    username = config.get("username")
    # 空值或占位符说明真实环境尚未配置，不允许静默带着错误账号继续执行。
    if not isinstance(username, str) or not username.strip() or username.strip() == "CHANGE_ME":
        raise RuntimeError("shortlink.username is not configured in environment YAML")
    # 去除误输入的前后空格，避免 Header 与 Redis Key 身份不一致。
    username = username.strip()
    # username 写入 scenario 后，YAML 可统一使用 ${username}。
    request_base.context.set("username", username, scope="scenario")

    # storage 节点保存当前 SUT 的物理资源命名规则，不让这些前缀污染通用 RedisClient。
    storage = config.get("storage")
    # 缺失 storage 时数据库/缓存 Regression 无法计算资源名，应给明确配置错误。
    if not isinstance(storage, dict):
        raise RuntimeError("shortlink.storage is not configured in environment YAML")
    # 登录态 Redis Key 前缀属于当前业务项目。
    prefix = storage.get("redis_login_key_prefix")
    # 前缀必须是非空字符串；通用断言引擎只消费最终 Key。
    if not isinstance(prefix, str) or not prefix:
        raise RuntimeError("shortlink.storage.redis_login_key_prefix is not configured")
    # 将“项目规则 + 当前 username”转换为运行时变量，auth.yaml 只引用 ${login_redis_key}。
    request_base.context.set("login_redis_key", f"{prefix}{username}", scope="scenario")


def prepare_shortlink_storage_context(
    request_base: Any,
    *,
    gid: str | None = None,
    full_short_url: str | None = None,
) -> None:
    """根据项目适配 YAML 生成物理表名和 Redis Key，不让通用断言知道业务规则。"""
    # 所有物理资源命名规则都从当前 SUT 配置读取，而不是 Python 常量写死。
    config = _project_config(request_base)
    # storage 是项目适配边界：表前缀、Key 前缀、分片数量都属于短链接系统。
    storage = config.get("storage")
    # 配置缺失时明确失败，避免 SQL 执行到错误表才报错。
    if not isinstance(storage, dict):
        raise RuntimeError("shortlink.storage is not configured in environment YAML")
    # shard_count 允许环境 YAML 动态修改，默认 16 只是当前真实 SUT 的兼容值。
    shard_count = int(storage.get("shard_count", 16))

    # gid 只影响 t_link 一类以 gid 为分片键的资源；未提供时不计算。
    if gid is not None:
        # 物理表前缀由项目 YAML 提供，support 不假定固定表名。
        link_prefix = storage.get("link_table_prefix")
        # 空前缀意味着项目适配配置不完整。
        if not isinstance(link_prefix, str) or not link_prefix:
            raise RuntimeError("shortlink.storage.link_table_prefix is not configured")
        # java_hash_mod 是通用算法；“前缀 + 后缀”才组成当前 SUT 的真实物理表名。
        request_base.context.set(
            "link_table", f"{link_prefix}{java_hash_mod(gid, shard_count)}", scope="scenario"
        )

    # full_short_url 同时参与 goto 分片和多个 Redis Key；没有该值时只保留 gid 相关上下文。
    if full_short_url is not None:
        # goto 表前缀同样来自项目配置，而不是写进 db/mysql_client.py。
        goto_prefix = storage.get("goto_table_prefix")
        # 某些项目可能没有 goto 表，所以只有配置存在时才生成上下文变量。
        if isinstance(goto_prefix, str) and goto_prefix:
            # 使用同一通用 Java HASH_MOD 算法计算真实物理后缀。
            request_base.context.set(
                "goto_table",
                f"{goto_prefix}{java_hash_mod(full_short_url, shard_count)}",
                scope="scenario",
            )

        # 三类 Redis Key 的“业务含义 -> 配置项”映射只存在项目 adapter。
        mappings = (
            ("goto_redis_key", "redis_goto_key_prefix"),
            ("uv_redis_key", "redis_uv_key_prefix"),
            ("uip_redis_key", "redis_uip_key_prefix"),
        )
        # 对每个项目 Key 生成最终运行时字符串，统一 RedisClient 完全不需要知道 short-link 前缀。
        for context_name, config_name in mappings:
            # 读取该资源类型在当前环境中的 Key 前缀。
            prefix = storage.get(config_name)
            # 缺任何一个 Regression 所需 Key 前缀都应立即暴露配置问题。
            if not isinstance(prefix, str) or not prefix:
                raise RuntimeError(f"shortlink.storage.{config_name} is not configured")
            # 最终 Key 写入 scenario，项目 YAML 之后只引用 ${..._redis_key}。
            request_base.context.set(
                context_name, f"{prefix}{full_short_url}", scope="scenario"
            )


def capture_created_link_context(request_base: Any, data: dict[str, Any]) -> dict[str, str]:
    """规范化 Create 响应，并准备后续 YAML/DB/Redis 断言需要的运行时变量。"""
    # 三个字段都是当前短链接 SUT Create 成功响应的核心契约。
    gid = data.get("gid")
    origin_url = data.get("originUrl")
    short_url = data.get("fullShortUrl")
    # 这些 assert 属于项目响应规范化边界；普通响应契约仍由 YAML validation 完成。
    assert isinstance(gid, str) and gid, "create response missing data.gid"
    assert isinstance(origin_url, str) and origin_url, "create response missing data.originUrl"
    assert isinstance(short_url, str) and short_url, "create response missing data.fullShortUrl"

    # Create 返回的 fullShortUrl 带 scheme；Redirect 与 DB 又需要不同表示，因此统一在这里解析。
    parsed = urlsplit(short_url)
    # 必须是可访问的 HTTP(S) 绝对地址，否则无法安全构造后续短链访问。
    assert parsed.scheme in {"http", "https"} and parsed.netloc, (
        f"create response fullShortUrl must be absolute HTTP URL, actual={short_url!r}"
    )
    # short_uri 取最后一个 Path Segment，供 redirect.yaml 动态 URL 使用。
    short_uri = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    # 空短码说明 Create 响应格式异常，应立即失败而不是发根路径请求。
    assert short_uri, f"create response fullShortUrl missing short uri: {short_url!r}"
    # 数据库保存的 full_short_url 不含 scheme，因此规范化为 netloc + path。
    full_short_url = f"{parsed.netloc}{parsed.path}".rstrip("/")

    # created 同时作为 fixture 返回值和 VariableContext 的统一来源，避免每个测试各自拆 URL。
    created = {
        "gid": gid,
        "origin_url": origin_url,
        "short_url": short_url,
        "full_short_url": full_short_url,
        "short_uri": short_uri,
    }
    # 所有规范化业务变量写入同一个 scenario，后续 YAML 可直接使用 ${变量名}。
    for name, value in created.items():
        request_base.context.set(name, value, scope="scenario")

    # 最后把业务标识映射为物理表/Redis Key 变量；AssertionEngine 只消费最终字符串。
    prepare_shortlink_storage_context(
        request_base, gid=gid, full_short_url=full_short_url
    )
    # 返回相同规范化字典给 Python 多步骤流程使用。
    return created


def _auth_headers(request_base: Any) -> dict[str, str]:
    """从当前 scenario 读取 Gateway 需要的 username/token Header。"""
    # username 来自环境 YAML/登录前置，不在 helper 内写死。
    username = request_base.context.get("username", scope="scenario")
    # token 来自 auth.yaml extract，不通过 fixture 返回值传播以降低日志泄露风险。
    token = request_base.context.get("token", scope="scenario")
    # 缺 username 说明调用者没有建立正确业务前置。
    assert isinstance(username, str) and username, "scenario context missing username"
    # 缺 token 时不能执行需要鉴权的 Cleanup API。
    assert isinstance(token, str) and token, "scenario context missing token"
    # Header 只在发请求时临时构造，返回对象不包含 password。
    return {"username": username, "token": token}


def _assert_business_success(response: Any, operation: str) -> dict[str, Any]:
    """校验当前短链接项目 HTTP 200 + 业务 ``code == '0'`` 约定。"""
    # Cleanup/前置 Create 是项目编排 helper，需要自己确认 HTTP 层成功。
    assert response.status_code == 200, (
        f"{operation} HTTP status expected 200, actual={response.status_code}"
    )
    # 当前项目业务响应约定为 JSON Object。
    payload = response.json()
    # 非对象响应属于协议异常，不继续读取 code。
    assert isinstance(payload, dict), f"{operation} response must be JSON object"
    # code=0 是当前 SUT 的成功约定；这里不属于通用 AssertionEngine 的业务知识。
    assert payload.get("code") == "0", (
        f"{operation} business code expected '0', actual={payload.get('code')!r}, "
        f"message={payload.get('message')!r}"
    )
    # 返回 payload 供前置 Create 等项目流程继续解析 data。
    return payload


def _create_retry_settings(request_base: Any) -> tuple[int, float]:
    """读取 fixture 前置 Create 的有限 Sentinel 重试配置。"""
    # 这是当前 SUT 的项目级策略，不是 RequestClient 的全局重试规则。
    retry = _project_config(request_base).get("create_retry", {})
    # 非 mapping 时回落到空配置，让后面的默认值接管。
    retry = retry if isinstance(retry, dict) else {}
    # max_attempts 可在 env.shortlink-local.yaml 动态修改。
    max_attempts = int(retry.get("max_attempts", 3))
    # interval_seconds 对应当前 Sentinel QPS 窗口的本地测试等待策略。
    interval_seconds = float(retry.get("interval_seconds", 1.1))
    # 不允许 0 次或负等待，避免配置错误造成无限/异常行为。
    if max_attempts < 1 or interval_seconds < 0:
        raise ValueError("shortlink.create_retry values are invalid")
    # 返回最小项目策略数据，不把 B100000 逻辑放入通用 core。
    return max_attempts, interval_seconds


def create_shortlink_from_yaml(request_base: Any) -> dict[str, str]:
    """复用 ``link.yaml/create_success`` 创建前置数据，并仅处理已知 B100000 临时限流。"""
    # 正式 Smoke Create 与 fixture 前置 Create 共用同一 YAML Case，避免两份 originUrl/Body。
    base_info, test_case = shortlink_case(LINK_YAML_PATH, "create_success")
    # 只读取 YAML json；字段内容仍然由 YAML 维护。
    raw_body = test_case.get("json")
    # Create 前置必须有 mapping Body，否则说明项目 YAML 被错误修改。
    if not isinstance(raw_body, dict):
        raise AssertionError("create_success YAML json must be a mapping")

    # 使用 ApiRunner 的通用动态解析能力处理 config()/gid/timestamp 等表达式。
    body = request_base.resolve_dynamic(raw_body)
    # Header 同样复用 baseInfo，并从 VariableContext 注入 username/token。
    headers = request_base.resolve_dynamic(base_info.get("header", {}))
    # URL 仍走 ApiRunner 的相对/绝对地址解析规则。
    url = request_base._resolve_url(base_info.get("url", ""))
    # 重试次数和间隔来自当前项目环境 YAML。
    max_attempts, interval_seconds = _create_retry_settings(request_base)

    # 这里只给“测试前置数据准备”有限重试；正式 Create 用例仍执行一次并严格失败。
    for attempt in range(1, max_attempts + 1):
        # 通过统一 RequestClient 发真实 HTTP 请求；这里只绕过成功 validation 以便识别 B100000。
        response = request_base.client.request(
            str(base_info.get("method", "POST")).upper(),
            url,
            headers=headers,
            json=body,
        )
        # Sentinel 临时限流也通过 HTTP 200 返回，因此 HTTP 非 200 直接失败而不重试。
        assert response.status_code == 200, (
            f"Short-link prerequisite create HTTP status expected 200, actual={response.status_code}"
        )
        # 读取当前 SUT JSON 业务响应以判断成功或已知临时限流。
        payload = response.json()
        # code=0 表示前置数据已经真实创建成功。
        if isinstance(payload, dict) and payload.get("code") == "0":
            # data 必须是对象，后续才能统一规范化业务变量。
            data = payload.get("data")
            assert isinstance(data, dict), "create prerequisite response missing object data"
            # 成功后立即写入 short_uri/full_short_url/物理资源 Key 等上下文。
            return capture_created_link_context(request_base, data)
        # 仅当前项目明确的 Sentinel B100000 可以在还有剩余次数时等待后重试。
        if isinstance(payload, dict) and payload.get("code") == "B100000" and attempt < max_attempts:
            # 等待一个配置化窗口，不把固定 sleep 时间写死在测试函数中。
            time.sleep(interval_seconds)
            continue
        # 任何其他业务错误或最后一次 B100000 都真实失败，不能被重试掩盖。
        _assert_business_success(response, "Short-link prerequisite create")

    # 正常循环路径都会 return 或 raise；保留防御性错误便于未来修改时暴露逻辑漏洞。
    raise AssertionError("Short-link prerequisite create exhausted unexpectedly")


def _recycle_path(request_base: Any, key: str) -> str:
    """从项目环境 YAML 读取回收接口路径，避免 support 再维护固定 URL。"""
    # Save/Remove 路径都属于当前 SUT 环境配置，可在 YAML 动态调整。
    value = _project_config(request_base).get(key)
    # 这里只接受 API 相对路径，防止误把任意外部地址当作 Cleanup 目标。
    if not isinstance(value, str) or not value.startswith("/"):
        raise RuntimeError(f"shortlink.{key} is not configured as an API path")
    # 返回相对路径，由调用者与当前 ApiRunner host 拼接。
    return value


def save_shortlink_to_recycle_bin(
    request_base: Any, *, gid: str, full_short_url: str
) -> None:
    """通过真实业务 API 把短链移入回收站，不直接写数据库。"""
    # Cleanup 也必须走真实业务接口，不能为了测试方便直接 UPDATE MySQL。
    response = request_base.client.request(
        "POST",
        f"{request_base.host}{_recycle_path(request_base, 'recycle_save_path')}",
        headers=_auth_headers(request_base),
        # Body 只包含真实回收 API 所需的业务标识。
        json={"gid": gid, "fullShortUrl": full_short_url},
    )
    # 回收失败必须让测试/teardown 可见，不能静默吞掉环境污染。
    _assert_business_success(response, "Short-link recycle-bin save")


def remove_shortlink_from_recycle_bin(
    request_base: Any, *, gid: str, full_short_url: str
) -> None:
    """通过真实业务 API 从回收站执行逻辑删除。"""
    # Remove 是当前 SUT 的真实逻辑删除入口，路径仍来自项目 YAML 配置。
    response = request_base.client.request(
        "POST",
        f"{request_base.host}{_recycle_path(request_base, 'recycle_remove_path')}",
        headers=_auth_headers(request_base),
        # 使用同一 gid/fullShortUrl 精确操作本次测试创建的数据。
        json={"gid": gid, "fullShortUrl": full_short_url},
    )
    # 逻辑删除必须成功，否则最终环境仍可能残留回收站数据。
    _assert_business_success(response, "Short-link recycle-bin remove")


def cleanup_shortlink(request_base: Any, *, gid: str, full_short_url: str) -> None:
    """按真实业务状态迁移 ``save -> remove`` 清理自动化测试数据。"""
    # 第一步先从正常列表移动到回收站，保持与真实用户操作一致。
    save_shortlink_to_recycle_bin(request_base, gid=gid, full_short_url=full_short_url)
    # 第二步再从回收站执行逻辑删除，避免直接绕过业务状态机。
    remove_shortlink_from_recycle_bin(request_base, gid=gid, full_short_url=full_short_url)
