"""Stage 7.1 Provider 无关 AI Client 边界与 OpenAI-compatible HTTP Adapter。

``failure_analyzer`` 只依赖 ``AIClient`` Protocol，不直接依赖任何模型厂商 SDK。
真实 HTTP Adapter 复用项目已有 ``requests`` 依赖，并且只从运行环境读取模型地址、
API Key、模型名和超时；这些值不会写进框架公共 YAML 或测试 Artifact。
"""
from __future__ import annotations

# json 只负责把安全 Evidence 编码为模型消息，以及严格解析模型返回 content。
import json
# os.environ 是 CI Secret / 本机 Secret Store 向 Provider Adapter 提供配置的唯一默认入口。
import os
# Any 兼容 requests.Session 与测试 FakeSession；Mapping 方便单测注入独立环境变量字典。
from typing import Any, Mapping, Protocol

# requests 是框架既有运行时依赖；Stage 7.1 不新增厂商 SDK。
import requests


# System Prompt 只定义“证据约束和 JSON 协议”，不包含任何当前真实 SUT 业务知识。
_SYSTEM_PROMPT = """You are an API test failure analysis assistant.
Use only the supplied deterministic facts as evidence.
Do not invent runtime state, database contents, service state, or code behavior.
Return exactly one JSON object with keys:
hypotheses, next_checks, uncertainties.
Every hypothesis and next_check must cite existing fact IDs through evidence_refs.
Do not include secrets or request credentials."""


class AIClient(Protocol):
    """FailureAnalyzer 所依赖的最小模型客户端协议。"""

    def analyze_failure(self, evidence: dict[str, Any]) -> object:
        """分析已经脱敏的确定性 Evidence，并返回待校验模型对象。"""
        ...


class OpenAICompatibleClient:
    """通过 OpenAI-compatible ``/chat/completions`` 协议调用模型的轻量 Adapter。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20.0,
        session: Any = None,
    ) -> None:
        """保存 Provider 连接参数，不在构造阶段发起任何网络请求。

        Args:
            base_url: Provider 的 API 根地址，通常以 ``/v1`` 结尾。
            api_key: 只保存在当前进程内存中的密钥。
            model: Provider 侧模型名称。
            timeout: 单次模型 HTTP 请求超时秒数。
            session: 可注入 requests.Session/FakeSession，便于测试完全离线。
        """

        # 去掉末尾斜杠，后续固定拼接 /chat/completions，避免出现双斜杠。
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = float(timeout)
        # 没有测试注入时才创建真实 Session；构造本身仍不联网。
        self.session = session or requests.Session()

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "OpenAICompatibleClient | None":
        """从 OS 环境变量创建可选 Provider Adapter。

        缺少 base/key/model 任一项时返回 ``None``，表示 AI 能力未配置；这不是框架错误，
        因为 Stage 7.1 必须允许“只生成 Evidence、不调用模型”的安全降级模式。
        """

        values = os.environ if environ is None else environ
        base_url = (values.get("AI_API_BASE") or "").strip()
        api_key = (values.get("AI_API_KEY") or "").strip()
        model = (values.get("AI_MODEL") or "").strip()

        # 三项都属于真实 Provider 调用的必要条件；缺少时不创建半配置 Client。
        if not base_url or not api_key or not model:
            return None

        raw_timeout = (values.get("AI_TIMEOUT") or "20").strip()
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError(f"AI_TIMEOUT must be numeric, got {raw_timeout!r}") from exc
        if timeout <= 0:
            raise ValueError("AI_TIMEOUT must be greater than 0")

        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )

    def analyze_failure(self, evidence: dict[str, Any]) -> object:
        """把安全 Evidence 发给模型，并严格解析 ``choices[0].message.content`` JSON。

        该方法不负责校验 hypothesis 是否引用真实 Fact；那属于 ``contracts`` 的确定性边界。
        这里也不会记录 API Key、完整 Prompt 或 Provider raw body，避免模型接入扩大泄密面。
        """

        # User message 只包含 FailureAnalyzer 已经脱敏后的 Evidence；不读取私有 YAML/原始日志。
        user_content = json.dumps(evidence, ensure_ascii=False)
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                # API Key 只存在实际 HTTP Header 中，不写日志、不写 Artifact。
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                # 失败分析优先稳定可复现，temperature 固定为 0。
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=self.timeout,
        )
        # 非 2xx 交给 Requests/FakeResponse 抛异常，上层统一降级为 ai_status=error。
        response.raise_for_status()

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (TypeError, KeyError, IndexError) as exc:
            # Provider 协议结构非法时给明确错误，但不把 raw response 内容写入异常文本。
            raise ValueError("AI provider response does not contain message content") from exc

        if not isinstance(content, str):
            raise ValueError("AI provider message content must be text JSON")

        try:
            # 只允许严格 JSON；不剥 Markdown fence、不用正则猜 JSON，避免把异常输出伪装成成功。
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("AI provider message content must be valid JSON") from exc
