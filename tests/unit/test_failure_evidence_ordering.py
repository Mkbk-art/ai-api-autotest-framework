"""Failure evidence ordering regression tests."""

import pytest

from core.api_runner import ApiRunner


def test_earlier_response_assertion_is_not_masked_by_later_missing_runtime_variable():
    """A later datasource variable must not hide an earlier API business failure."""

    payload = {"code": "B001", "message": "create rejected", "data": None}

    class Response:
        status_code = 200
        text = '{"code":"B001","message":"create rejected","data":null}'
        headers = {}
        elapsed = None

        def json(self):
            return payload

    class FakeClient:
        def run(self, **_kwargs):
            return Response()

    runner = ApiRunner(host="http://service.test", client=FakeClient())

    with pytest.raises(AssertionError) as exc_info:
        runner.run(
            {"api_name": "create", "url": "/create", "method": "POST"},
            {
                "case_name": "business failure should win",
                "extract": {"short_url": "$.data.fullShortUrl"},
                "validation": [
                    {"status_code": 200},
                    {"eq": ["$.code", "0"]},
                    {
                        "db_exists": {
                            "source": "default",
                            "sql": "SELECT id FROM links WHERE short_url=%s",
                            "params": ["${short_url}"],
                        }
                    },
                ],
            },
        )

    message = str(exc_info.value)
    assert "eq $.code expected='0' actual='B001'" in message
    assert "short_url" not in message


def test_api_runner_attaches_extract_evidence_with_missing_variables(monkeypatch):
    """Declared extracts should be visible in Allure without exposing raw secrets."""
    import json
    from utils import allure_compat

    captured = []
    monkeypatch.setattr(
        allure_compat,
        "attach",
        lambda body, name, attachment_type=None: captured.append((name, body)),
    )

    class Response:
        status_code = 200
        text = '{"code":"0","data":{"fullShortUrl":"http://nurl.ink/abc"}}'
        headers = {}
        elapsed = None

        def json(self):
            return {"code": "0", "data": {"fullShortUrl": "http://nurl.ink/abc"}}

    class FakeClient:
        def run(self, **_kwargs):
            return Response()

    runner = ApiRunner(host="http://service.test", client=FakeClient())
    runner.run(
        {"api_name": "create", "url": "/create", "method": "POST"},
        {
            "case_name": "extract evidence",
            "extract": {
                "short_url": "$.data.fullShortUrl",
                "missing_id": "$.data.id",
            },
            "validation": [{"status_code": 200}, {"eq": ["$.code", "0"]}],
        },
    )

    body = next(body for name, body in captured if name == "响应提取结果")
    evidence = json.loads(body)
    assert evidence["extracted"]["short_url"] == "http://nurl.ink/abc"
    assert evidence["missing"] == ["missing_id"]
    assert evidence["rules"]["short_url"] == "$.data.fullShortUrl"


def test_request_client_attaches_response_status_metadata(monkeypatch):
    """HTTP status should be explicit evidence next to the existing response body attachment."""
    import json
    import core.request_client as request_client_module
    from core.request_client import RequestClient

    captured = []

    class Response:
        status_code = 202
        text = '{"accepted":true}'

        def json(self):
            return {"accepted": True}

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
        case_name="status evidence",
        method="POST",
        headers={},
        json={"name": "demo"},
    )

    body = next(body for name, body in captured if name == "响应元数据")
    assert json.loads(body) == {"status_code": 202}
