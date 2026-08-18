"""受控 Mock Server 主链路与鉴权行为的集成测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import requests

from mock_server.server import MockApiServer


def test_mock_api_supports_login_publish_and_call_flow():
    with MockApiServer() as server:
        login = requests.post(
            f"{server.url}/api/v1/auth/login",
            json={"username": "demo_user", "password": "demo_password"},
            timeout=2,
        )
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]

        publish = requests.post(
            f"{server.url}/api/v1/interface/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "demo", "method": "GET", "path": "/demo"},
            timeout=2,
        )
        assert publish.status_code == 200
        interface_id = publish.json()["data"]["interfaceId"]

        call = requests.post(
            f"{server.url}/api/v1/interface/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"interface_id": interface_id, "params": {"key": "value"}},
            timeout=2,
        )
        assert call.status_code == 200
        assert call.json()["call_status"] == "success"


def test_mock_api_rejects_missing_or_invalid_tokens():
    with MockApiServer() as server:
        missing = requests.post(
            f"{server.url}/api/v1/interface/publish",
            json={"name": "demo", "method": "GET", "path": "/demo"},
            timeout=2,
        )
        invalid = requests.post(
            f"{server.url}/api/v1/interface/call",
            headers={"Authorization": "Bearer invalid"},
            json={"interface_id": 1, "params": {}},
            timeout=2,
        )
        assert missing.status_code == 401
        assert invalid.status_code == 401
