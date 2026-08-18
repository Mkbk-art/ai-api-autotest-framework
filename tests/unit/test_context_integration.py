"""VariableContext 与提取/动态替换链路的集成式单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
from pathlib import Path

from core.api_runner import ApiRunner
from core.extractor import extract_from_response
from core.variable_context import VariableContext


def test_extractor_writes_jsonpath_value_to_injected_context():
    context = VariableContext()

    extract_from_response(
        {"access_token": "$.data.access_token"},
        '{"data": {"access_token": "token-123"}}',
        context=context,
    )

    assert context.get("access_token") == "token-123"


def test_request_base_dynamic_replacement_reads_its_own_context():
    context = VariableContext()
    context.set("access_token", "token-abc")
    context.set("interface_id", 7)
    runner = ApiRunner(context=context)

    assert runner._replace_dynamic_params("Bearer ${get_extract_data(access_token)}") == "Bearer token-abc"
    assert runner._replace_dynamic_params("${interface_id}") == 7


def test_runtime_context_does_not_create_extract_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = VariableContext()
    context.set("token", "abc")
    runner = ApiRunner(context=context)

    assert runner._replace_dynamic_params("${token}") == "abc"
    assert not Path("extract.yaml").exists()


def test_api_runner_resolves_validation_after_current_response_extract():
    """同一 YAML Case 的 DB/Redis 断言应能使用刚从当前响应提取出的变量。"""
    import json

    class Response:
        status_code = 200
        headers = {}
        elapsed = None

        def __init__(self):
            self.text = json.dumps({"data": {"token": "token-from-response"}})

        def json(self):
            return json.loads(self.text)

    class Client:
        def run(self, **kwargs):
            return Response()

    captured = []

    class Assert:
        def assert_all(self, validations, *args, **kwargs):
            captured.extend(validations)

    runner = ApiRunner(client=Client())
    runner.assertions = Assert()
    runner.run(
        {"url": "/login", "method": "POST"},
        {
            "case_name": "extract then validate",
            "extract": {"token": "$.data.token"},
            "validation": [{"redis_hfield_exists": {"key": "login", "field": "${token}"}}],
        },
    )

    assert captured == [
        {"redis_hfield_exists": {"key": "login", "field": "token-from-response"}}
    ]


def test_api_runner_polling_retries_only_when_yaml_explicitly_requests_it():
    """最终一致性轮询应是通用 YAML 能力，普通 Case 不会被框架偷偷重试。"""
    import json

    responses = [0, 1]

    class Response:
        status_code = 200
        headers = {}
        elapsed = None

        def __init__(self, value):
            self.text = json.dumps({"data": {"count": value}})

        def json(self):
            return json.loads(self.text)

    class Client:
        def __init__(self):
            self.calls = 0

        def run(self, **kwargs):
            value = responses[min(self.calls, len(responses) - 1)]
            self.calls += 1
            return Response(value)

    client = Client()
    runner = ApiRunner(client=client)
    runner.run_polling(
        {"url": "/stats", "method": "GET"},
        {
            "case_name": "eventual stats",
            "validation": [{"gte": ["$.data.count", 1]}],
            "poll": {"timeout_seconds": 1, "interval_seconds": 0},
        },
        sleep_fn=lambda _: None,
    )
    assert client.calls == 2
