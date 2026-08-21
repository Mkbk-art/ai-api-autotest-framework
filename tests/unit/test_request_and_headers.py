"""HTTP 请求封装、Header 合并、异常和脱敏行为的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import importlib

import pytest

from core.api_runner import ApiRunner
from core.request_client import RequestClient


def test_request_client_forwards_json_exactly_once():
    client = RequestClient()
    captured = {}

    class Response:
        status_code = 200
        text = "{}"

        def json(self):
            return {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return Response()

    client.session.request = fake_request
    response = client.request("POST", "http://example.test/items", json={"name": "demo"})

    assert response.status_code == 200
    assert captured["json"] == {"name": "demo"}
    assert "json_body" not in captured


def test_case_headers_override_base_headers():
    merged = ApiRunner.merge_headers(
        {"Content-Type": "application/json", "Authorization": "Bearer base"},
        {"Authorization": "Bearer case", "X-Trace": "case-1"},
    )
    assert merged == {
        "Content-Type": "application/json",
        "Authorization": "Bearer case",
        "X-Trace": "case-1",
    }


def test_null_case_header_removes_inherited_header():
    merged = ApiRunner.merge_headers(
        {"Content-Type": "application/json", "Authorization": "Bearer base"},
        {"Authorization": None},
    )
    assert merged == {"Content-Type": "application/json"}


def test_sanitizer_masks_sensitive_headers_recursively():
    sanitizer = importlib.import_module("utils.sanitizer")
    value = {
        "headers": {
            "Authorization": "Bearer secret-token",
            "Cookie": "session=secret",
            "X-Trace": "safe",
        },
        "nested": {"api_key": "secret-key"},
    }
    sanitized = sanitizer.sanitize(value)
    assert sanitized["headers"]["Authorization"] == "***"
    assert sanitized["headers"]["Cookie"] == "***"
    assert sanitized["headers"]["X-Trace"] == "safe"
    assert sanitized["nested"]["api_key"] == "***"


def test_request_base_applies_runtime_timeout_and_tls_verification():
    runner = ApiRunner(host="https://service.test", timeout=4.5, verify_ssl=False)
    assert runner.client.timeout == 4.5
    assert runner.client.verify is False


@pytest.mark.parametrize(
    "argument_name,value",
    [
        ("data", {"form": "value"}),
        ("params", {"page": 1}),
        ("files", {"file": ("demo.txt", b"demo")}),
    ],
)
def test_request_client_forwards_non_json_payload_types(argument_name, value):
    client = RequestClient()
    captured = {}

    class Response:
        status_code = 200
        text = "{}"

        def json(self):
            return {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return Response()

    client.session.request = fake_request
    client.request("POST", "http://example.test/items", **{argument_name: value})
    assert captured[argument_name] == value


def test_request_client_reraises_timeout():
    import requests

    client = RequestClient()

    def fake_request(**_kwargs):
        raise requests.exceptions.Timeout("simulated timeout")

    client.session.request = fake_request
    with pytest.raises(requests.exceptions.Timeout):
        client.request("GET", "http://example.test/slow")


def test_request_client_reraises_connection_error():
    import requests

    client = RequestClient()

    def fake_request(**_kwargs):
        raise requests.exceptions.ConnectionError("simulated connection failure")

    client.session.request = fake_request
    with pytest.raises(requests.exceptions.ConnectionError):
        client.request("GET", "http://example.test/offline")


def test_allure_request_header_attachment_is_sanitized(monkeypatch):
    import json
    import core.request_client as request_client_module

    captured = []

    class Response:
        status_code = 200
        text = '{"ok": true}'

        def json(self):
            return {"ok": True}

    client = RequestClient()
    client.session.request = lambda **_kwargs: Response()
    monkeypatch.setattr(
        request_client_module.allure,
        "attach",
        lambda body, name, attachment_type=None: captured.append((name, body)),
    )

    client.run(
        api_name="demo",
        url="http://example.test/items",
        case_name="sanitized",
        method="GET",
        headers={"Authorization": "Bearer super-secret", "X-Trace": "safe"},
    )

    header_body = next(body for name, body in captured if name == "请求头")
    decoded = json.loads(header_body)
    assert decoded["Authorization"] == "***"
    assert decoded["X-Trace"] == "safe"
    assert "super-secret" not in header_body


def test_api_runner_uses_absolute_yaml_url_and_forwards_request_options():
    """绝对 URL 和 request_options 应通过 YAML 主链传给 RequestClient。"""

    captured = {}

    class Response:
        status_code = 302
        text = ""
        headers = {"Location": "https://github.com/"}
        elapsed = None

        def json(self):
            raise ValueError("redirect response has no JSON body")

    class FakeClient:
        def run(self, **kwargs):
            captured.update(kwargs)
            return Response()

    runner = ApiRunner(host="http://127.0.0.1:8000", client=FakeClient())
    runner.context.set("short_uri", "AbC123", scope="scenario")

    response = runner.run(
        {
            "api_name": "redirect",
            "url": "http://nurl.ink:8001/${short_uri}",
            "method": "GET",
        },
        {
            "case_name": "keep first redirect",
            "request_options": {"allow_redirects": False},
            "validation": [
                {"status_code": 302},
                {"header_eq": ["Location", "https://github.com/"]},
            ],
        },
    )

    assert response.status_code == 302
    assert captured["url"] == "http://nurl.ink:8001/AbC123"
    assert captured["method"] == "GET"
    assert captured["allow_redirects"] is False


def test_api_runner_still_prefixes_host_for_relative_yaml_urls():
    """普通相对路径仍应拼接 API host，避免 Redirect 扩展破坏现有接口。"""

    captured = {}

    class Response:
        status_code = 200
        text = '{"code":"0"}'
        headers = {}
        elapsed = None

        def json(self):
            return {"code": "0"}

    class FakeClient:
        def run(self, **kwargs):
            captured.update(kwargs)
            return Response()

    runner = ApiRunner(host="http://127.0.0.1:8000", client=FakeClient())
    runner.run(
        {"api_name": "relative", "url": "/api/demo", "method": "GET"},
        {"case_name": "relative-url", "validation": [{"status_code": 200}]},
    )

    assert captured["url"] == "http://127.0.0.1:8000/api/demo"


def test_api_runner_uses_service_specific_host_for_contract_relative_url():
    captured = {}

    class Response:
        status_code = 200
        text = '{}'
        headers = {}
        elapsed = None

        def json(self):
            return {}

    class FakeClient:
        def run(self, **kwargs):
            captured.update(kwargs)
            return Response()

    runner = ApiRunner(
        host="http://gateway.test",
        client=FakeClient(),
        runtime_config={"api": {"service_hosts": {"billing": "http://billing.test:8001"}}},
    )
    runner.run(
        {"api_name": "billing", "url": "/abc", "method": "GET", "service": "billing"},
        {"case_name": "service-route", "validation": [{"status_code": 200}]},
    )

    assert captured["url"] == "http://billing.test:8001/abc"


def test_api_runner_falls_back_to_default_host_when_service_has_no_override():
    captured = {}

    class Response:
        status_code = 200
        text = '{}'
        headers = {}
        elapsed = None

        def json(self):
            return {}

    class FakeClient:
        def run(self, **kwargs):
            captured.update(kwargs)
            return Response()

    runner = ApiRunner(
        host="http://gateway.test",
        client=FakeClient(),
        runtime_config={"api": {"service_hosts": {"project": "http://project.test:8001"}}},
    )
    runner.run(
        {"api_name": "users", "url": "/api/users", "method": "GET", "service": "user"},
        {"case_name": "default-route", "validation": [{"status_code": 200}]},
    )

    assert captured["url"] == "http://gateway.test/api/users"
