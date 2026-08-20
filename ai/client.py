"""Stage 7.1 V2 Provider 无关 AI Client 与协议 Adapter Factory。

本模块只理解“协议”，不理解 DeepSeek、Qwen、OpenAI 等 Provider 厂商名。Provider、
Base URL、Model 和 Key 都由 ``AIConfigResolver`` 解析为 ``AIProviderConfig``；Factory
只根据 ``protocol`` 选择实现。这样同一协议下新增任意厂商或企业内部网关只需要改 YAML。

第一版只实现 ``openai_chat_completions``。未来遇到真正不同的 API 协议时，再新增新的
Protocol Adapter，而不是为每个 Provider 增加 if/elif 分支。
"""
from __future__ import annotations

# json 只负责把已经脱敏的 Evidence 编码为模型消息，以及严格解析 Provider JSON content。
import json
# Any 兼容 requests.Session 与测试 FakeSession；Protocol 定义 FailureAnalyzer 的最小依赖边界。
from typing import Any, Protocol

# requests 是框架既有运行时依赖；Stage 7.1 不为了不同 Provider 引入厂商 SDK。
import requests

# Factory 消费解析后的不可变配置；配置来源/YAML 优先级不属于 Client 职责。
from ai.config import AIProviderConfig


# System Prompt 只定义“事实约束 + Stage 7.1 输出协议”，不包含任何真实 SUT 或模型厂商知识。
#
# 这里必须与 ai.contracts.validate_model_analysis() 保持同一契约：
# - hypotheses 的 confidence 只能是 low / medium / high；
# - next_checks.priority 必须是正整数；
# - hypotheses / next_checks 必须引用真实 Fact ID；
# - 字段名和枚举值禁止翻译。
#
# 之前真实 Provider 验收曾出现：
#   Provider JSON 解析成功，但 confidence 返回了 Validator 不接受的值，
# 最终被正确降级为 invalid_model_output。
# 根因不是 Provider/YAML/HTTP，而是旧 Prompt 只说明了顶层 keys，没有完整说明内部 Schema。
# 因此这里补齐契约，但仍保持 Validator 严格，不在 Python 中为某个厂商做特殊兼容。
_SYSTEM_PROMPT = """You are an API test failure analysis assistant.
Use only the supplied deterministic facts as evidence.
Do not invent runtime state, database contents, service state, or code behavior.

Return JSON only.
Do not wrap the JSON in Markdown, code fences, or explanatory text.
Return exactly one JSON object with this schema:

{
  "hypotheses": [
    {
      "title": "non-empty string",
      "confidence": "low | medium | high",
      "evidence_refs": ["F1"],
      "reasoning_summary": "non-empty string"
    }
  ],
  "next_checks": [
    {
      "priority": 1,
      "action": "non-empty string",
      "evidence_refs": ["F1"]
    }
  ],
  "uncertainties": ["non-empty string"]
}

Rules:
- "confidence" must be exactly one of: "low", "medium", "high".
- "priority" must be a positive integer.
- "evidence_refs" must be a non-empty list containing only existing Fact IDs supplied in the evidence.
- "title", "reasoning_summary", and "action" must be non-empty strings when their parent item exists.
- "hypotheses", "next_checks", and "uncertainties" must always be JSON arrays; use [] when empty.
- Do not translate field names or enum values.
- Do not add fields outside this contract.
- Do not include secrets or request credentials."""


class AIClient(Protocol):
    """FailureAnalyzer 所依赖的最小模型客户端协议。"""

    def analyze_failure(self, evidence: dict[str, Any]) -> object:
        """分析已经脱敏的确定性 Evidence，并返回待校验模型对象。"""
        ...


class OpenAIChatCompletionsClient:
    """实现 OpenAI-compatible ``/chat/completions`` 协议的轻量 Adapter。

    类名故意描述协议而不是厂商：任何兼容该协议的 Provider Profile 都能复用本实现。
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20.0,
        session: Any = None,
    ) -> None:
        """保存单次 Provider 连接参数，不在构造阶段联网或记录 Secret。

        Args:
            base_url: 当前 Profile 的 API 根地址；Adapter 固定在其后拼接 ``/chat/completions``。
            api_key: 仅存在当前 Client 内存中的鉴权值，绝不主动写入日志/Artifact。
            model: Provider 暴露的模型 ID；完全由 YAML/CLI 决定。
            timeout: 单次模型 HTTP 请求超时秒数。
            session: 可注入 requests.Session/FakeSession，保证公共测试完全离线。
        """

        # 去掉末尾斜杠，后续拼接固定协议路径时避免 ``//chat/completions``。
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = float(timeout)
        # 只有没有测试注入时才创建真实 Session；构造本身仍不发请求。
        self.session = session or requests.Session()

    def analyze_failure(self, evidence: dict[str, Any]) -> object:
        """发送安全 Evidence，并严格解析 ``choices[0].message.content`` 的 JSON。

        Fact ID 是否真实存在由 ``contracts`` Validator 负责；本层只实现 HTTP 协议。为了避免
        把 Provider 异常输出伪装成成功，这里不剥 Markdown fence、不做正则 JSON 修复。
        """

        # User message 只包含 FailureAnalyzer 已脱敏 Evidence；Client 不读取私有 YAML 或原始日志。
        user_content = json.dumps(evidence, ensure_ascii=False)
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                # API Key 只放到真实 HTTP Header；不会被 Framework Logger 主动输出。
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                # 故障分析强调稳定和可复现，因此协议层固定 temperature=0。
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=self.timeout,
        )
        # 非 2xx 由 Requests/FakeResponse 抛出；FailureAnalyzer 上层统一降级为 ai_status=error。
        response.raise_for_status()

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (TypeError, KeyError, IndexError) as exc:
            # 异常只说明协议结构缺失，不拼 raw response，避免第三方响应意外携带敏感值。
            raise ValueError("AI provider response does not contain message content") from exc

        if not isinstance(content, str):
            raise ValueError("AI provider message content must be text JSON")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("AI provider message content must be valid JSON") from exc


class AIClientFactory:
    """按 ``AIProviderConfig.protocol`` 创建模型客户端，而不是按 Provider 厂商名分支。"""

    # 映射键是协议标识。新增同协议 Provider 不改此表；只有新增“新协议”才新增 Adapter。
    _PROTOCOLS: dict[str, type[OpenAIChatCompletionsClient]] = {
        "openai_chat_completions": OpenAIChatCompletionsClient,
    }

    @classmethod
    def create(cls, config: AIProviderConfig) -> AIClient:
        """根据已解析配置创建对应 Protocol Adapter，未知协议明确失败。"""

        client_type = cls._PROTOCOLS.get(config.protocol)
        if client_type is None:
            # 错误只包含协议名，不包含整份 config/repr，从源头避免 Key 被拼进异常。
            raise ValueError(f"Unsupported AI protocol: {config.protocol}")
        return client_type(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            timeout=config.timeout,
        )


# Stage 7.1 第一版曾公开该类名；保留 alias 只为兼容，不再承担环境变量配置职责。
OpenAICompatibleClient = OpenAIChatCompletionsClient
