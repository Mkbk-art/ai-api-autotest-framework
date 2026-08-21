"""单条接口测试用例的执行编排器。

本模块把 YAML 中的接口基础信息和具体测试数据串成完整执行链：合并请求头、
解析动态函数与上下文变量、调用 HTTP 客户端、提取响应变量并执行统一断言。
它负责“怎样执行一条接口用例”，但不直接实现底层网络通信。
"""
from __future__ import annotations

# Callable 用于把 sleep/monotonic 注入 polling，便于离线测试不真的等待。
from typing import Any, Callable
# time 只服务显式 YAML polling；普通请求不会自动重试。
import time

from core.assertion_engine import Assertions
from core.extractor import extract_from_response
from core.request_client import RequestClient
from core.variable_context import VariableContext
from utils.debugtalk import DebugTalk


class ApiRunner:
    """编排一条 YAML 接口测试用例的完整生命周期。"""

    def __init__(
        self,
        host: str = "http://localhost:8080",
        timeout: float = 30,
        verify_ssl: bool = True,
        client: RequestClient | None = None,
        context: VariableContext | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> None:
        """创建用例执行器并注入 HTTP 客户端与变量上下文。

        Args:
            host: 被测 API 根地址。
            timeout: 默认 HTTP 请求超时秒数。
            verify_ssl: 是否校验 HTTPS 证书。
            client: 可选自定义 RequestClient，主要用于测试注入。
            context: 当前测试运行时变量上下文；未提供时创建新实例。
            runtime_config: ConfigManager 已合并完成的当前环境 YAML 配置。
        """
        self.host = host.rstrip("/")
        self.client = client or RequestClient(timeout=timeout, verify=verify_ssl)
        self.context = context or VariableContext()
        # 保存最终环境配置；统一断言引擎按需从这里创建命名 MySQL/Redis 数据源。
        self.runtime_config = runtime_config or {}
        self.assertions = Assertions(runtime_config=self.runtime_config)
        # DebugTalk 既能读取 VariableContext 动态变量，也能读取当前环境 YAML 配置。
        self.debugtalk = DebugTalk(self.context, runtime_config=self.runtime_config)

    @staticmethod
    def merge_headers(
        base_headers: dict[str, Any] | None,
        case_headers: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """合并基础请求头和用例请求头，case 中的 ``None`` 表示删除继承字段。"""
        merged = dict(base_headers or {})
        for key, value in (case_headers or {}).items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        return merged

    def resolve_dynamic(self, data: Any) -> Any:
        """公开解析 YAML 动态值，供需要复用用例数据的项目前置编排使用。

        该方法只做 ``${config(...)}``、DebugTalk 函数和 VariableContext 替换，不发送网络
        请求。项目适配层可在复杂前置流程中复用它解析同一份 YAML 数据，而无需复制请求字段。
        """
        return self._replace_dynamic_params(data)

    def _replace_dynamic_params(self, data: Any) -> Any:
        """递归解析 DebugTalk 函数表达式和普通上下文变量表达式。"""
        if data is None:
            return data
        if isinstance(data, str):
            # 先解析旧版 DSL 中的 ${func(args)}，以兼容已有 YAML；如果整个字符串
            # 就是函数表达式，则直接返回函数原始类型，而不是强制转成字符串。
            if data.startswith("${") and data.endswith("}") and data.count("${") == 1:
                inner = data[2:-1]
                if "(" in inner and inner.endswith(")"):
                    func_name = inner[: inner.index("(")]
                    args_str = inner[inner.index("(") + 1 : -1]
                    args = [item.strip() for item in args_str.split(",")] if args_str else []
                    func = getattr(self.debugtalk, func_name, None)
                    if func is not None:
                        return func(*args)

            result = data
            # 一个字符串可以包含多个动态函数，例如前缀 + ${random_string(4)}。
            while "${" in result and "}" in result:
                start = result.index("${")
                end = result.index("}", start)
                full = result[start : end + 1]
                inner = full[2:-1]
                if "(" not in inner or not inner.endswith(")"):
                    break
                func_name = inner[: inner.index("(")]
                args_str = inner[inner.index("(") + 1 : -1]
                args = [item.strip() for item in args_str.split(",")] if args_str else []
                func = getattr(self.debugtalk, func_name, None)
                if func is None:
                    break
                result = result.replace(full, str(func(*args)), 1)

            # 动态函数处理完后，再解析 ${token} 这类普通运行时变量。
            return self.context.replace_variables(result)
        if isinstance(data, dict):
            return {key: self._replace_dynamic_params(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._replace_dynamic_params(item) for item in data]
        if isinstance(data, tuple):
            return tuple(self._replace_dynamic_params(item) for item in data)
        return data

    def _resolve_url(self, raw_url: Any, *, service: str | None = None) -> str:
        """解析请求 URL，并按 Contract service 选择环境 base URL。

        Contract-bound Case 传入的始终是相对 Contract path；若当前环境在
        ``api.service_hosts`` 中为该 service 配置了专用地址，则优先使用它，否则回退
        ``api.host``。Standalone Case 仍可传完整 ``http://`` / ``https://`` URL。
        """

        # URL 与 Header/Body 一样属于运行时数据，因此先解析 ``${resource_id}`` 等动态变量。
        resolved_url = self._replace_dynamic_params(raw_url)
        # URL 必须最终解析成非空字符串，否则 RequestClient 无法构造合法 HTTP 请求。
        if not isinstance(resolved_url, str) or not resolved_url:
            raise ValueError(f"YAML baseInfo.url must resolve to a non-empty string, actual={resolved_url!r}")

        # Standalone Case 仍可显式使用完整 URL；Contract-bound Case 在 Parser 层禁止该重复事实源。
        if resolved_url.startswith(("http://", "https://")):
            return resolved_url

        base_host = self.host
        api_config = self.runtime_config.get("api", {})
        if not isinstance(api_config, dict):
            raise TypeError("runtime_config.api must be a mapping")
        service_hosts = api_config.get("service_hosts", {})
        if service_hosts is None:
            service_hosts = {}
        if not isinstance(service_hosts, dict):
            raise TypeError("api.service_hosts must be a mapping")
        if service:
            candidate = service_hosts.get(service)
            if candidate is not None:
                if not isinstance(candidate, str) or not candidate.strip():
                    raise ValueError(f"api.service_hosts.{service} must be a non-empty URL")
                candidate = candidate.strip().rstrip("/")
                if not candidate.startswith(("http://", "https://")):
                    raise ValueError(f"api.service_hosts.{service} must start with http:// or https://")
                base_host = candidate

        if not resolved_url.startswith("/"):
            resolved_url = f"/{resolved_url}"
        return f"{base_host}{resolved_url}"

    def _request_options(self, test_case: dict[str, Any]) -> dict[str, Any]:
        """读取 YAML 的底层 Requests 行为选项，并限制为框架明确支持的安全集合。

        例如 ``allow_redirects: false`` 可禁止 Requests 自动跟随 302，
        这样统一断言引擎才能看到被测服务返回的第一跳状态码和 Location Header。
        """

        # 没有 request_options 时返回空字典，保持所有既有 YAML 的行为完全不变。
        raw_options = test_case.get("request_options", {})
        # 配置格式错误应在发请求前明确失败，避免神秘地透传到 requests 才报错。
        if not isinstance(raw_options, dict):
            raise TypeError("request_options must be a mapping")

        # 当前只开放框架已明确支持的 allow_redirects；其他底层参数按通用需求逐项加入。
        supported_options = {"allow_redirects"}
        unsupported = set(raw_options) - supported_options
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ValueError(f"unsupported request_options: {names}")

        # request_options 也允许使用 ``${变量}``，统一遵守框架的运行时替换规则。
        return self._replace_dynamic_params(raw_options)

    # 复杂工作流的“请求步骤”仍由 YAML 定义；Python 仅在步骤之间调用这个统一断言入口。
    def validate(self, validations: list[dict[str, Any]] | None) -> None:
        """执行一组不依赖当前 HTTP Response 的 YAML 数据源断言。

        复杂业务流程可能需要在第二个/第三个 API 步骤后再验证数据库或 Redis。此方法仍然
        复用统一 VariableContext、动态函数和 AssertionEngine，Python 只负责流程编排，
        SQL/Key/预期值继续写在 YAML 中。
        """
        # DB/Redis SQL、Key 和 expected 可能引用前序步骤产生的 `${变量}`，因此执行前统一解析。
        resolved = self._replace_dynamic_params(validations or [])
        # 这里没有新的 HTTP Response；传空响应体只为复用同一个 Assertions 执行器。
        self.assertions.assert_all(resolved, {}, 0, headers={}, elapsed_seconds=None)

    def run_polling(
        self,
        base_info: dict[str, Any],
        test_case: dict[str, Any],
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        """按 YAML ``poll`` 配置有界重试同一只读查询型接口。

        只有显式声明 ``poll`` 的 Case 才会重试；网络异常继续立即抛出。这里仅捕获断言失败，
        适合统计/缓存等最终一致性查询，避免在普通业务请求上滥用重试掩盖缺陷。
        """
        # poll 完全由 YAML 显式开启；没有配置的 Case 严格保持单次请求语义。
        poll = test_case.get("poll")
        if not isinstance(poll, dict):
            return self.run(base_info, test_case)
        # timeout 控制总等待上限，interval 控制相邻两次查询间隔，二者都可按项目调整。
        timeout_seconds = float(poll.get("timeout_seconds", 15))
        interval_seconds = float(poll.get("interval_seconds", 1))
        if timeout_seconds < 0 or interval_seconds < 0:
            raise ValueError("poll timeout_seconds/interval_seconds must be >= 0")

        # monotonic 不受系统时钟回拨影响，适合作为超时截止时间基准。
        started = monotonic_fn()
        # 只保留最后一次断言错误用于超时报告，不吞掉网络/配置等其他异常。
        last_error: AssertionError | None = None
        # 每轮重新执行完整只读查询 Case，确保响应提取和断言使用最新数据。
        while True:
            try:
                return self.run(base_info, test_case)
            except AssertionError as exc:
                # “数据还没达到期望”属于最终一致性等待条件；其他异常不会进入此分支。
                last_error = exc
            # 每次失败后重新计算已用时间，到达上限立即把最后断言原因带回 Pytest。
            elapsed = monotonic_fn() - started
            if elapsed >= timeout_seconds:
                raise AssertionError(
                    f"YAML polling timed out after {timeout_seconds}s; last_error={last_error}"
                ) from last_error
            # 最后一轮睡眠不会超过剩余预算，避免实际等待时间显著超过 YAML timeout。
            sleep_fn(min(interval_seconds, max(0.0, timeout_seconds - elapsed)))

    def run(self, base_info: dict[str, Any], test_case: dict[str, Any]):
        """执行一条 YAML 用例并返回 Requests Response。

        执行顺序为：URL/请求信息解析 -> 动态变量替换 -> HTTP 请求 -> 响应提取 -> 断言。
        任何网络错误、变量缺失或断言失败都会向上抛给 Pytest，使测试真实失败。
        """
        # api_name 只用于日志与 Allure 标识，不参与真实网络路由。
        api_name = base_info.get("api_name", "unknown")
        # URL 统一由 _resolve_url 处理：Contract 相对路径按 service 选择环境 host；Standalone 绝对 URL 直连。
        url = self._resolve_url(base_info.get("url", ""), service=base_info.get("service"))
        # HTTP Method 统一转成大写，避免 YAML 大小写差异影响底层客户端。
        method = base_info.get("method", "GET").upper()
        # 基础 Header 与 Case Header 合并后再做运行时变量替换。
        raw_headers = self.merge_headers(base_info.get("header", {}), test_case.get("header", {}))
        headers = self._replace_dynamic_params(raw_headers)
        # case_name 用于日志和报告定位具体参数化案例。
        case_name = test_case.get("case_name", "unnamed")
        # validation 暂不在发请求前解析。当前响应可能 extract 出 token/id，数据库/Redis
        # 断言需要使用这些刚产生的变量，因此必须在提取完成后再统一替换。

        # request_kwargs 是最终交给 RequestClient.run 的请求参数集合。
        request_kwargs: dict[str, Any] = {}
        # data/json/params 是框架现有的三类 YAML 请求载荷入口。
        for param_type in ("data", "json", "params"):
            if param_type in test_case:
                request_kwargs[param_type] = self._replace_dynamic_params(test_case[param_type])
        # request_options 专门描述底层 Requests 行为，例如禁止自动跟随 302。
        request_kwargs.update(self._request_options(test_case))

        # RequestClient 仍然是唯一真正发送 HTTP 请求的网络层，ApiRunner 只负责组装和编排。
        response = self.client.run(
            api_name=api_name,
            url=url,
            case_name=case_name,
            method=method,
            headers=headers,
            **request_kwargs,
        )

        try:
            response_body = response.json()
        except Exception:
            # 非 JSON 接口仍应进入断言流程，因此退化为原始文本而不是直接失败。
            response_body = response.text

        # extract 只处理当前响应并写入 VariableContext；后续 Case/数据断言都从统一上下文取值。
        if test_case.get("extract"):
            extract_from_response(test_case["extract"], response.text, context=self.context)

        # extract 已写入当前 VariableContext，现在再解析 validation，允许同一个 YAML Case
        # 使用本次响应刚提取出的 token/id 等值做数据库和缓存一致性校验。
        validations = self._replace_dynamic_params(test_case.get("validation", []))

        # Requests 的 elapsed 可能在 Fake Response 中缺失，因此响应时间断言按可选值传入。
        elapsed = getattr(response, "elapsed", None)
        elapsed_seconds = elapsed.total_seconds() if elapsed is not None else None
        # HTTP、JSON、Header、MySQL、Redis 等断言最终都由同一个 Assertions 实例解释。
        self.assertions.assert_all(
            validations,
            response_body,
            response.status_code,
            headers=getattr(response, "headers", None),
            elapsed_seconds=elapsed_seconds,
        )
        return response
