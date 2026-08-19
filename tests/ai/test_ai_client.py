"""Stage 7.1 Provider Adapter 的 TDD 测试。

所有 HTTP 都使用 FakeSession，公共测试绝不会访问真实模型服务或读取真实 API Key。
"""
import json

import pytest

from ai.client import OpenAICompatibleClient


class FakeResponse:
    """只实现 client 所需最小 Response 协议。"""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def raise_for_status(self):
        """模拟 Requests 的 HTTP 状态检查。"""
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        """返回预设 Provider JSON。"""
        return self._payload


class FakeSession:
    """记录最后一次 POST 参数，便于验证网络边界而不真实联网。"""

    def __init__(self, response):
        self.response = response
        self.last_call = None

    def post(self, url, **kwargs):
        """保存调用并返回固定响应。"""
        self.last_call = (url, kwargs)
        return self.response


def test_from_env_returns_none_without_required_secret():
    """缺少任一必需 Provider 配置时，AI 应作为可选能力自动关闭。"""
    client = OpenAICompatibleClient.from_env(
        {
            "AI_API_BASE": "https://model.example/v1",
            "AI_MODEL": "model-x",
        }
    )

    assert client is None


def test_openai_compatible_client_posts_evidence_and_parses_json():
    """Adapter 应只发送结构化 evidence，并严格解析模型 JSON content。"""
    model_payload = {
        "hypotheses": [],
        "next_checks": [],
        "uncertainties": ["not enough evidence"],
    }
    session = FakeSession(
        FakeResponse(
            {
                "choices": [
                    {"message": {"content": json.dumps(model_payload)}}
                ]
            }
        )
    )
    client = OpenAICompatibleClient(
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


def test_client_does_not_attempt_to_repair_non_json_model_content():
    """模型输出不是 JSON 时必须失败，不能用正则或 code fence 猜测性修复。"""
    session = FakeSession(
        FakeResponse({"choices": [{"message": {"content": "not-json"}}]})
    )
    client = OpenAICompatibleClient(
        base_url="https://model.example/v1",
        api_key="key",
        model="model-x",
        session=session,
    )

    with pytest.raises(ValueError, match="JSON"):
        client.analyze_failure({"facts": [{"id": "F1"}]})


def test_from_env_rejects_invalid_timeout():
    """AI_TIMEOUT 非数字时应明确失败，而不是偷偷使用错误超时。"""
    with pytest.raises(ValueError, match="AI_TIMEOUT"):
        OpenAICompatibleClient.from_env(
            {
                "AI_API_BASE": "https://model.example/v1",
                "AI_API_KEY": "key",
                "AI_MODEL": "model-x",
                "AI_TIMEOUT": "abc",
            }
        )
