"""非 JSON、超时等 HTTP 异常路径的集成测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import pytest
import requests

from core.request_client import RequestClient
from mock_server.server import MockApiServer


def test_mock_server_exposes_non_json_response_and_client_handles_it():
    with MockApiServer() as server:
        response = RequestClient(timeout=1).run(
            api_name="plain",
            url=f"{server.url}/api/v1/plain",
            case_name="plain response",
            method="GET",
            headers={},
        )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.text == "plain-response"


def test_mock_server_can_trigger_real_request_timeout():
    with MockApiServer() as server:
        client = RequestClient(timeout=0.03)
        with pytest.raises(requests.exceptions.Timeout):
            client.request("GET", f"{server.url}/api/v1/slow?delay=0.15")
