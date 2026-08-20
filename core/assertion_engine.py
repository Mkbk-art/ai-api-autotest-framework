"""接口响应统一断言引擎。

本模块把 YAML ``validation`` 规则转换为真实断言，支持状态码、相等/不等、
包含、存在性、集合、数值比较、响应头等值/包含和响应耗时等常用规则，并保留 Stage 1
旧 YAML 的映射式 ``contains/eq/ne`` 兼容。所有失败会汇总为一条 AssertionError，
不支持的断言类型明确失败，避免“配置了但实际上没有校验”。
"""
from __future__ import annotations

# Mapping 用于校验 YAML 断言配置；Callable 允许测试注入假的数据源工厂。
from typing import Any, Callable, Mapping

# MySQL/Redis 客户端只提供通用只读访问，具体 SQL/Key 始终来自项目 YAML。
from db.mysql_client import MySQLClient
from db.redis_client import RedisClient

# JSONPath 工具统一解析响应字段，避免断言引擎自己维护第二套 selector 语法。
from utils.jsonpath_util import find_values

# 独立哨兵区分“字段真的不存在”和“字段存在但值恰好是 None”。
_MISSING = object()


def _recursive_values(payload: Any, key: str) -> list[Any]:
    """兼容旧版按字段名递归查找，不影响新版 JSONPath 选择器。"""
    # 收集所有同名字段；调用方只取第一个值以保持历史行为。
    values: list[Any] = []
    # 字典先检查当前层，再递归遍历所有 value。
    if isinstance(payload, dict):
        # 当前层命中时仍继续遍历，保证函数语义是“收集全部”而不是“找到即停”。
        if key in payload:
            values.append(payload[key])
        # 嵌套对象可能把同名字段放在任意深度，因此递归继续向下。
        for value in payload.values():
            values.extend(_recursive_values(value, key))
    # 列表中的每个元素都可能是对象或下一层列表。
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value, key))
    return values


def _selector_value(payload: Any, selector: str) -> Any:
    """把统一 selector 解析成一个实际值；不存在时返回 _MISSING。"""
    # `$` 表示整个响应体，适合对标量或完整对象进行比较。
    if selector == "$":
        return payload
    # `$...` 统一按 JSONPath 处理；空结果不能与 None 混淆。
    if selector.startswith("$"):
        values = find_values(payload, selector)
        return values[0] if values else _MISSING
    # 非 JSONPath 的简单字段名先查顶层，兼容早期 YAML 写法。
    if isinstance(payload, dict) and selector in payload:
        return payload[selector]
    # 顶层未命中时才启用历史递归字段名搜索。
    values = _recursive_values(payload, selector)
    return values[0] if values else _MISSING


def _pair(value: Any, assert_type: str) -> tuple[str, Any]:
    """校验 `[selector, expected]` 二元断言格式并返回规范化结果。"""
    # 在统一入口拒绝错误结构，避免每种响应断言重复写格式检查。
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise AssertionError(
            f"{assert_type} requires [selector, expected], got {value!r}"
        )
    # selector 必须是文本；expected 保留 YAML 原始类型，支持数值/布尔/列表比较。
    selector, expected = value
    if not isinstance(selector, str):
        raise AssertionError(f"{assert_type} selector must be a string, got {selector!r}")
    return selector, expected


def _header_value(headers: Any, name: str) -> Any:
    """以不区分大小写的方式读取响应 Header。"""
    # 非 HTTP 数据源断言没有 Header，因此允许 None 并返回缺失哨兵。
    if headers is None:
        return _MISSING
    # Requests 的 CaseInsensitiveDict 可直接 get；普通测试字典则由下面的循环兜底。
    if hasattr(headers, "get"):
        direct = headers.get(name, _MISSING)
        if direct is not _MISSING:
            return direct
        # 自定义 Fake Response 可能使用普通 dict，因此手工做一次大小写归一化。
        lowered = name.lower()
        for key, value in headers.items():
            if str(key).lower() == lowered:
                return value
    return _MISSING


class Assertions:
    """统一响应/数据库/缓存断言引擎。

    数据源通过 runtime_config 的命名连接懒加载；测试可注入 factory 做纯离线验证。
    这里不包含任何具体项目表名、Redis Key 或业务字段。
    """

    def __init__(
        self,
        *,
        runtime_config: Mapping[str, Any] | None = None,
        mysql_client_factory: Callable[[str], Any] | None = None,
        redis_client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        """保存通用数据源配置和可注入客户端工厂。"""
        # 保存一次运行合并后的环境配置；这里不复制业务字段到框架常量。
        self.runtime_config = dict(runtime_config or {})
        # factory 主要服务单元测试和未来可插拔连接实现；生产默认走 db/ 通用客户端。
        self._mysql_factory = mysql_client_factory
        self._redis_factory = redis_client_factory
        # 客户端按命名 source 缓存，避免一条用例的多条断言重复建立连接对象。
        self._mysql_clients: dict[str, Any] = {}
        self._redis_clients: dict[str, Any] = {}

    def _mysql(self, source: str) -> Any:
        """按 source 懒加载并缓存一个通用 MySQL Client。"""
        # 只有第一次使用某个 source 时才创建客户端，纯 HTTP 用例不会触发数据库依赖。
        if source not in self._mysql_clients:
            # 测试注入工厂优先，保证断言逻辑可以完全离线验证。
            if self._mysql_factory is not None:
                self._mysql_clients[source] = self._mysql_factory(source)
            else:
                # 真实运行从 `data_sources.mysql.<source>` 读取连接，不在代码里写死主机/库名。
                self._mysql_clients[source] = MySQLClient.from_runtime_config(
                    self.runtime_config, source=source
                )
        return self._mysql_clients[source]

    def _redis(self, source: str) -> Any:
        """按 source 懒加载并缓存一个通用 Redis Client。"""
        # Redis 与 MySQL 同样按需加载；没有 redis_* 断言时不会建立 Redis 客户端。
        if source not in self._redis_clients:
            # 注入假的 Redis 客户端可精确测试 Key/TTL/集合断言，而无需本地启动 Redis。
            if self._redis_factory is not None:
                self._redis_clients[source] = self._redis_factory(source)
            else:
                # 真实连接统一来自 `data_sources.redis.<source>`，框架不认识项目 Key 前缀。
                self._redis_clients[source] = RedisClient.from_runtime_config(
                    self.runtime_config, source=source
                )
        return self._redis_clients[source]

    def _legacy_contains(
        self,
        expected: dict[str, Any],
        response: Any,
        status_code: int,
    ) -> list[str]:
        # 兼容规则也采用“收集全部失败”策略，避免用户一次只看到一个差异。
        failures: list[str] = []
        for key, value in expected.items():
            # 旧格式允许把 status_code 混在 mapping 中，需要单独与 HTTP 状态比较。
            if key == "status_code":
                if value != status_code:
                    failures.append(
                        f"contains status_code expected={value!r} actual={status_code!r}"
                    )
                continue
            # 其他 key 继续复用统一 selector 解析，避免兼容路径与新路径行为分叉。
            actual = _selector_value(response, key)
            if actual is _MISSING or str(value) not in str(actual):
                rendered = "<missing>" if actual is _MISSING else repr(actual)
                failures.append(
                    f"contains {key!r} expected substring={value!r} actual={rendered}"
                )
        return failures

    def _legacy_mapping_compare(
        self,
        assert_type: str,
        expected: dict[str, Any],
        response: Any,
    ) -> list[str]:
        # eq/ne 的旧 mapping 格式也保留聚合失败行为。
        failures: list[str] = []
        for key, expected_value in expected.items():
            actual = _selector_value(response, key)
            if assert_type == "eq":
                if actual is _MISSING or actual != expected_value:
                    rendered = "<missing>" if actual is _MISSING else repr(actual)
                    failures.append(
                        f"eq {key!r} expected={expected_value!r} actual={rendered}"
                    )
            else:
                if actual is not _MISSING and actual == expected_value:
                    failures.append(
                        f"ne {key!r} expected!={expected_value!r} actual={actual!r}"
                    )
        return failures

    def assert_all(
        self,
        validations: list[dict[str, Any]] | None,
        response_body: Any,
        status_code: int,
        *,
        headers: Any = None,
        elapsed_seconds: float | None = None,
    ) -> None:
        """执行全部 YAML 断言并在最后统一抛出失败明细。

        Args:
            validations: YAML validation 规则列表。
            response_body: 已解析 JSON 或非 JSON 文本响应体。
            status_code: HTTP 状态码。
            headers: 可选响应头，用于 ``header_eq``。
            elapsed_seconds: 可选响应耗时，用于 ``response_time_lt``。

        Raises:
            AssertionError: 任意规则失败、规则格式非法或断言类型不受支持。
        """
        # 所有断言先记录失败，最后统一抛出一条 AssertionError，报告一次展示完整差异。
        failures: list[str] = []

        # YAML 每个 validation 元素必须只声明一种断言类型。
        for rule in validations or []:
            # 结构错误也是测试配置错误，不能被忽略成“断言未执行”。
            if not isinstance(rule, dict) or len(rule) != 1:
                failures.append(f"invalid assertion rule: {rule!r}")
                continue

            # 拆出断言名和参数；后续每个分支只处理一种明确语义。
            assert_type, assert_value = next(iter(rule.items()))

            # contains 同时兼容旧 mapping 和新版 [selector, expected] 写法。
            if assert_type == "contains":
                if isinstance(assert_value, dict):
                    failures.extend(
                        self._legacy_contains(assert_value, response_body, status_code)
                    )
                else:
                    selector, expected = _pair(assert_value, assert_type)
                    actual = _selector_value(response_body, selector)
                    if actual is _MISSING or str(expected) not in str(actual):
                        rendered = "<missing>" if actual is _MISSING else repr(actual)
                        failures.append(
                            f"contains {selector} expected substring={expected!r} actual={rendered}"
                        )
                continue

            # 历史 eq/ne mapping 只在值为 dict 时启用，新格式走下面统一比较分支。
            if assert_type in {"eq", "ne"} and isinstance(assert_value, dict):
                failures.extend(
                    self._legacy_mapping_compare(assert_type, assert_value, response_body)
                )
                continue

            # HTTP 状态码直接使用 Response.status_code，不从 JSON Body 猜测业务 code。
            if assert_type == "status_code":
                if status_code != assert_value:
                    failures.append(
                        f"status_code expected={assert_value!r} actual={status_code!r}"
                    )
                continue

            # 存在性只关心 selector 是否命中；命中且值为 None 仍视为“字段存在”。
            if assert_type in {"exists", "not_exists"}:
                if not isinstance(assert_value, str):
                    failures.append(f"{assert_type} selector must be a string")
                    continue
                actual = _selector_value(response_body, assert_value)
                exists = actual is not _MISSING
                if assert_type == "exists" and not exists:
                    failures.append(f"exists {assert_value} actual=<missing>")
                elif assert_type == "not_exists" and exists:
                    failures.append(f"not_exists {assert_value} actual={actual!r}")
                continue

            # 常规值比较统一走 selector + expected 模式，保留 YAML 原始数据类型。
            if assert_type in {
                "eq",
                "ne",
                "in",
                "not_in",
                "gt",
                "gte",
                "lt",
                "lte",
            }:
                # selector 缺失时直接记录失败，不让 Python 比较表达式产生误导性的类型错误。
                selector, expected = _pair(assert_value, assert_type)
                actual = _selector_value(response_body, selector)
                if actual is _MISSING:
                    failures.append(f"{assert_type} {selector} actual=<missing>")
                    continue
                # 比较操作按断言名映射，集中处理类型不兼容场景。
                try:
                    passed = {
                        "eq": lambda: actual == expected,
                        "ne": lambda: actual != expected,
                        "in": lambda: actual in expected,
                        "not_in": lambda: actual not in expected,
                        "gt": lambda: actual > expected,
                        "gte": lambda: actual >= expected,
                        "lt": lambda: actual < expected,
                        "lte": lambda: actual <= expected,
                    }[assert_type]()
                # 例如字符串与整数做大小比较时，明确报告 comparison error 而不是中断剩余断言。
                except (TypeError, ValueError) as exc:
                    failures.append(
                        f"{assert_type} {selector} comparison error: {exc}; "
                        f"expected={expected!r} actual={actual!r}"
                    )
                    continue
                if not passed:
                    failures.append(
                        f"{assert_type} {selector} expected={expected!r} actual={actual!r}"
                    )
                continue

            if assert_type == "list_contains":
                # 用于列表型响应的声明式成员匹配：selector 必须定位到 list，where 中所有字段
                # 必须在同一个对象上同时满足。这样分页/查询类 Case 不需要为“找一条记录”写 Python。
                if not isinstance(assert_value, Mapping):
                    failures.append("list_contains requires a mapping")
                    continue
                selector = assert_value.get("selector")
                expected_fields = assert_value.get("where")
                if not isinstance(selector, str) or not selector:
                    failures.append("list_contains.selector must be a non-empty string")
                    continue
                if not isinstance(expected_fields, Mapping) or not expected_fields:
                    failures.append("list_contains.where must be a non-empty mapping")
                    continue
                actual = _selector_value(response_body, selector)
                if actual is _MISSING:
                    failures.append(f"list_contains {selector} actual=<missing>")
                    continue
                if not isinstance(actual, list):
                    failures.append(
                        f"list_contains {selector} expected list actual={type(actual).__name__}"
                    )
                    continue
                matched = any(
                    isinstance(item, Mapping)
                    and all(item.get(key, _MISSING) == expected for key, expected in expected_fields.items())
                    for item in actual
                )
                if not matched:
                    failures.append(
                        f"list_contains {selector} expected one item matching={dict(expected_fields)!r}"
                    )
                continue

            if assert_type in {"header_eq", "header_contains"}:
                # Header 断言与 JSON selector 不同：先按不区分大小写的响应头名称取真实值。
                header_name, expected = _pair(assert_value, assert_type)
                actual = _header_value(headers, header_name)

                # header_eq 用于 Location 等值固定的场景，例如正常短链必须精确跳回 originUrl。
                if assert_type == "header_eq":
                    if actual is _MISSING or actual != expected:
                        rendered = "<missing>" if actual is _MISSING else repr(actual)
                        failures.append(
                            f"header_eq {header_name} expected={expected!r} actual={rendered}"
                        )
                    continue

                # Servlet sendRedirect 对相对地址可能输出相对或绝对 Location；header_contains
                # 只验证关键路径片段，既保留业务约束，又避免绑定容器对 Location 的序列化方式。
                if actual is _MISSING or str(expected) not in str(actual):
                    rendered = "<missing>" if actual is _MISSING else repr(actual)
                    failures.append(
                        f"header_contains {header_name} expected substring={expected!r} actual={rendered}"
                    )
                continue

            # 数据库规则是框架级 YAML 能力：SQL、参数和 source 都由当前项目 YAML 声明。
            if assert_type in {"db_exists", "db_eq", "db_gte"}:
                # DB 断言需要 mapping 承载 source/sql/params/expected，拒绝模糊的列表格式。
                if not isinstance(assert_value, Mapping):
                    failures.append(f"{assert_type} requires a mapping")
                    continue
                # SQL 必须显式提供；真正的只读限制还会由 MySQLClient 再做第二层保护。
                sql = assert_value.get("sql")
                if not isinstance(sql, str) or not sql.strip():
                    failures.append(f"{assert_type}.sql must be a non-empty string")
                    continue
                # source 默认 default，允许同一测试环境配置多个数据库连接而不改框架代码。
                source = str(assert_value.get("source", "default"))
                # params 必须通过参数绑定传给驱动，禁止业务 YAML 拼接运行时字符串进 SQL。
                params = assert_value.get("params", [])
                if not isinstance(params, (list, tuple)):
                    failures.append(f"{assert_type}.params must be a list/tuple")
                    continue
                try:
                    # 连接在真正遇到 DB 断言时才懒加载，普通 API Case 不受数据库配置影响。
                    client = self._mysql(source)
                    # db_exists 只验证至少返回一行，不绑定具体字段结构。
                    if assert_type == "db_exists":
                        if client.fetch_one(sql, params) is None:
                            failures.append(f"db_exists source={source!r} returned no row")
                        continue
                    # 值比较只取结果第一行第一列，适合 count/status/id 等单值一致性校验。
                    actual = client.fetch_scalar(sql, params)
                    expected = assert_value.get("expected")
                    # db_eq 保留严格类型比较，避免字符串 "1" 与整数 1 被误判相等。
                    if assert_type == "db_eq" and actual != expected:
                        failures.append(
                            f"db_eq source={source!r} expected={expected!r} actual={actual!r}"
                        )
                    # db_gte 用于计数/统计最终一致性，实际值只需达到 YAML 声明下限。
                    if assert_type == "db_gte":
                        try:
                            passed = actual is not None and actual >= expected
                        except TypeError:
                            passed = False
                        if not passed:
                            failures.append(
                                f"db_gte source={source!r} expected>={expected!r} actual={actual!r}"
                            )
                except Exception as exc:
                    # 不把 SQL params 拼进错误文本，降低 token/用户标识等动态参数泄露风险。
                    failures.append(f"{assert_type} source={source!r} error={exc}")
                continue

            # Redis 规则同样是通用断言；Key 前缀和字段名属于项目 YAML/adapter，而非 core。
            if assert_type in {
                "redis_exists",
                "redis_eq",
                "redis_hfield_exists",
                "redis_ttl_between",
                "redis_scard_gte",
            }:
                if not isinstance(assert_value, Mapping):
                    failures.append(f"{assert_type} requires a mapping")
                    continue
                # 每条 Redis 规则都必须有解析后的完整 Key，动态 `${...}` 已由 ApiRunner 先替换。
                key = assert_value.get("key")
                if not isinstance(key, str) or not key:
                    failures.append(f"{assert_type}.key must be a non-empty string")
                    continue
                # 命名 source 允许一个环境同时连接多个 Redis 实例/逻辑用途。
                source = str(assert_value.get("source", "default"))
                try:
                    # 与 MySQL 一样按需加载客户端，纯 HTTP 测试不会被 Redis 可用性绑架。
                    client = self._redis(source)
                    # exists 用于验证 Key 生命周期，expected=false 也属于正式业务契约。
                    if assert_type == "redis_exists":
                        actual = bool(client.exists(key))
                        expected = bool(assert_value.get("expected", True))
                        if actual != expected:
                            failures.append(
                                f"redis_exists source={source!r} key={key!r} "
                                f"expected={expected!r} actual={actual!r}"
                            )
                    # redis_eq 读取普通 String Key，并与 YAML expected 做严格比较。
                    elif assert_type == "redis_eq":
                        actual = client.get(key)
                        expected = assert_value.get("expected")
                        if actual != expected:
                            failures.append(
                                f"redis_eq source={source!r} key={key!r} "
                                f"expected={expected!r} actual={actual!r}"
                            )
                    # Hash field 存在性常用于会话/映射状态，不要求读取可能敏感的 value。
                    elif assert_type == "redis_hfield_exists":
                        field = assert_value.get("field")
                        if not isinstance(field, str) or not field:
                            failures.append("redis_hfield_exists.field must be a non-empty string")
                        elif not client.hexists(key, field):
                            # Hash field 经常承载 token/session id；失败信息只说明 field 缺失，
                            # 不回显动态 field 原文，避免 Pytest traceback 把敏感运行时值泄露到日志。
                            failures.append(
                                f"redis_hfield_exists source={source!r} key={key!r} "
                                "field=<redacted> actual=False"
                            )
                    # TTL 用区间而非精确值断言，避免网络/执行耗时造成毫秒级脆弱测试。
                    elif assert_type == "redis_ttl_between":
                        actual = client.ttl(key)
                        minimum = int(assert_value.get("min", 0))
                        maximum = int(assert_value.get("max", 2**31 - 1))
                        if not minimum <= actual <= maximum:
                            failures.append(
                                f"redis_ttl_between source={source!r} key={key!r} "
                                f"expected=[{minimum},{maximum}] actual={actual!r}"
                            )
                    else:
                        # 剩余分支即 redis_scard_gte，用集合基数下限验证去重/成员状态。
                        actual = client.scard(key)
                        expected = int(assert_value.get("expected", 0))
                        if actual < expected:
                            failures.append(
                                f"redis_scard_gte source={source!r} key={key!r} "
                                f"expected>={expected!r} actual={actual!r}"
                            )
                except Exception as exc:
                    # 错误信息只保留 source 与异常，不主动附加动态 Redis field/token。
                    failures.append(f"{assert_type} source={source!r} error={exc}")
                continue

            # 响应耗时基于 Requests elapsed；没有 HTTP Response 的数据源-only validate 不使用此规则。
            if assert_type == "response_time_lt":
                if elapsed_seconds is None or elapsed_seconds >= float(assert_value):
                    failures.append(
                        f"response_time_lt expected<{float(assert_value)!r} "
                        f"actual={elapsed_seconds!r}"
                    )
                continue

            # 未注册的断言必须显式失败，这是防止 YAML 拼错名称却“绿灯”的最后保险。
            failures.append(f"unsupported assertion type: {assert_type}")

        # 只有遍历完全部规则后才统一抛错，让一次运行能看到所有断言差异。
        if failures:
            details = "\n - ".join(failures)
            raise AssertionError(f"Assertions failed ({len(failures)}):\n - {details}")
