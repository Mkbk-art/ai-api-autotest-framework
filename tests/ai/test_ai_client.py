"""Stage 7.1 V2 Protocol Adapter / Factory 的 TDD 测试。

所有 HTTP 都使用 FakeSession；测试重点是 production code 只按 protocol 路由，任意
Provider Profile 名都能复用同一个协议 Adapter，而不是出现厂商 if/elif 分支。

本文件同时守住 Prompt / Validator 契约：真实 Provider 必须在调用前就被明确告知
confidence 枚举、priority 类型和 Fact 引用要求，不能依赖某个具体模型“猜”出 Schema。
"""
from __future__ import annotations

import json

import pytest

from ai.client import (
    AIClientFactory,
    OpenAIChatCompletionsClient,
    OpenAICompatibleClient,
)
from ai.config import AIProviderConfig


class FakeResponse:
    """只实现 Chat Completions Adapter 所需的最小 Response 协议。"""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        """模拟 Requests 的 HTTP 状态检查。"""
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        """返回预设 Provider JSON。"""
        return self._payload


class FakeSession:
    """记录最后一次 POST 参数，便于验证协议而不真实访问模型网络。"""

    def __init__(self, response):
        self.response = response
        self.last_call = None

    def post(self, url, **kwargs):
        """保存调用并返回固定响应。"""
        self.last_call = (url, kwargs)
        return self.response


def _config(provider: str = "arbitrary-provider") -> AIProviderConfig:
    """构造同一协议的任意 Provider Profile，证明 Factory 不依赖厂商名。"""

    return AIProviderConfig(
        provider=provider,
        protocol="openai_chat_completions",
        base_url="https://model.example/v1",
        model="model-x",
        api_key="unit-test-key",
        timeout=12,
    )


def test_factory_creates_client_by_protocol_not_provider_name():
    """Factory 应根据 protocol 创建 Adapter，而不是判断 Provider 名。"""

    client = AIClientFactory.create(_config(provider="provider-alpha"))

    assert isinstance(client, OpenAIChatCompletionsClient)
    assert client.model == "model-x"


def test_same_protocol_supports_arbitrary_provider_profile_names():
    """同协议不同 Profile 名必须走相同 Client，实现切 Provider 只改 YAML。"""

    first = AIClientFactory.create(_config(provider="vendor-one"))
    second = AIClientFactory.create(_config(provider="internal-company-gateway"))

    assert type(first) is OpenAIChatCompletionsClient
    assert type(second) is OpenAIChatCompletionsClient


def test_factory_rejects_unknown_protocol():
    """未知协议必须明确失败，不能猜测回退到某个厂商实现。"""

    config = AIProviderConfig(
        provider="anything",
        protocol="unsupported_protocol",
        base_url="https://model.example/v1",
        model="model-x",
        api_key="key",
        timeout=12,
    )

    with pytest.raises(ValueError, match="Unsupported AI protocol"):
        AIClientFactory.create(config)


def test_backward_alias_points_to_chat_completions_client():
    """旧公开类名暂时保留 alias，避免 Stage 7.1 第一版调用方突然破坏。"""

    assert OpenAICompatibleClient is OpenAIChatCompletionsClient


def test_chat_completions_client_posts_evidence_and_parses_json():
    """重命名后原 Chat Completions HTTP/JSON 行为必须保持不变。"""

    model_payload = {
        "hypotheses": [],
        "next_checks": [],
        "uncertainties": ["not enough evidence"],
    }
    session = FakeSession(
        FakeResponse(
            {"choices": [{"message": {"content": json.dumps(model_payload)}}]}
        )
    )
    client = OpenAIChatCompletionsClient(
        base_url="https://model.example/v1",
        api_key="unit-test-key",
        model="model-x",
        timeout=12,
        session=session,
    )

    result = client.analyze_failure({"facts": [{"id": "F1", "text": "failed"}]})

    assert result == model_payload
    url, kwargs = session.last_call
    assert url == "https://model.example/v1/chat/completions"
    assert kwargs["timeout"] == 12
    assert kwargs["headers"]["Authorization"] == "Bearer unit-test-key"
    assert kwargs["json"]["model"] == "model-x"
    assert kwargs["json"]["temperature"] == 0


def test_system_prompt_declares_full_validator_contract():
    """System Prompt 必须完整声明 Validator 的字段、枚举、类型和 Fact 引用约束。

    该测试对应真实 Provider 验收中已经复现的缺陷：旧 Prompt 没有说明 confidence 只能
    使用 low/medium/high，模型返回其他值后被 Validator 正确拒绝。修复应补齐 Prompt，
    而不是放宽 Validator 或针对某个 Provider 增加特殊转换。
    """

    model_payload = {
        "hypotheses": [],
        "next_checks": [],
        "uncertainties": [],
    }
    session = FakeSession(
        FakeResponse(
            {"choices": [{"message": {"content": json.dumps(model_payload)}}]}
        )
    )
    client = OpenAIChatCompletionsClient(
        base_url="https://model.example/v1",
        api_key="unit-test-key",
        model="model-x",
        session=session,
    )

    client.analyze_failure({"facts": [{"id": "F1", "text": "failed"}]})

    # 真正检查的是发给 Provider 的 system message，而不是直接读取私有常量，
    # 从而锁住“线上实际请求必须携带完整契约”这一行为。
    _, kwargs = session.last_call
    prompt = kwargs["json"]["messages"][0]["content"]
    normalized = " ".join(prompt.lower().split())

    # hypotheses 内部字段必须全部明确，尤其是这次真实验收触发失败的 confidence 枚举。
    assert '"confidence"' in normalized
    assert "low" in normalized
    assert "medium" in normalized
    assert "high" in normalized
    assert '"reasoning_summary"' in normalized

    # next_checks 的 priority 必须明确要求正整数，避免模型返回 high/P1/字符串等模糊值。
    assert '"priority"' in normalized
    assert "positive integer" in normalized

    # 两类建议都只能引用本次 Evidence 中真实存在的 Fact ID。
    assert '"evidence_refs"' in normalized
    assert "existing fact id" in normalized

    # 字段/枚举不能被中文化或做 Provider 风格变体；输出仍保持严格 JSON。
    assert "do not translate field names or enum values" in normalized
    assert "return json only" in normalized


def test_client_still_never_repairs_invalid_json():
    """模型输出不是 JSON 时仍严格失败，不能为了兼容 Provider 弱化安全边界。"""

    session = FakeSession(
        FakeResponse({"choices": [{"message": {"content": "not-json"}}]})
    )
    client = OpenAIChatCompletionsClient(
        base_url="https://model.example/v1",
        api_key="key",
        model="model-x",
        session=session,
    )

    with pytest.raises(ValueError, match="JSON"):
        client.analyze_failure({"facts": [{"id": "F1"}]})
