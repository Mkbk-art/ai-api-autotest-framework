"""统一断言引擎的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import pytest

from core.assertion_engine import Assertions


@pytest.fixture
def response_body():
    return {
        "success": True,
        "msg": "ok: created",
        "data": {
            "token": "abc",
            "count": 3,
            "role": "admin",
        },
    }


def test_legacy_contains_eq_and_ne_rules_remain_supported(response_body):
    Assertions().assert_all(
        [
            {"contains": {"status_code": 200, "msg": "created"}},
            {"eq": {"success": True}},
            {"ne": {"success": False}},
        ],
        response_body,
        200,
    )


def test_selector_based_assertions_cover_common_response_checks(response_body):
    Assertions().assert_all(
        [
            {"status_code": 200},
            {"exists": "$.data.token"},
            {"not_exists": "$.data.error"},
            {"eq": ["$.data.count", 3]},
            {"ne": ["$.data.role", "guest"]},
            {"in": ["$.data.role", ["admin", "owner"]]},
            {"not_in": ["$.data.role", ["guest", "anonymous"]]},
            {"gt": ["$.data.count", 2]},
            {"gte": ["$.data.count", 3]},
            {"lt": ["$.data.count", 4]},
            {"lte": ["$.data.count", 3]},
            {"header_eq": ["Content-Type", "application/json"]},
            {"response_time_lt": 0.5},
        ],
        response_body,
        200,
        headers={"content-type": "application/json"},
        elapsed_seconds=0.12,
    )


def test_failed_assertions_report_rule_and_actual_value(response_body):
    with pytest.raises(AssertionError) as exc_info:
        Assertions().assert_all(
            [{"eq": ["$.data.count", 9]}, {"status_code": 201}],
            response_body,
            200,
        )

    message = str(exc_info.value)
    assert "$.data.count" in message
    assert "actual=3" in message
    assert "status_code" in message
    assert "actual=200" in message


def test_unsupported_assertion_type_fails_explicitly(response_body):
    with pytest.raises(AssertionError, match="unsupported assertion type"):
        Assertions().assert_all([{"unknown_rule": {"value": 1}}], response_body, 200)


def test_database_assertions_are_generic_and_yaml_shaped(response_body):
    """db_exists/db_eq/db_gte 应只依赖通用 MySQL Client 接口。"""
    class Mysql:
        def fetch_one(self, sql, params=None):
            assert sql.startswith("SELECT")
            return {"id": 1}

        def fetch_scalar(self, sql, params=None):
            if "count" in sql:
                return 3
            return "ok"

    Assertions(mysql_client_factory=lambda source: Mysql()).assert_all(
        [
            {"db_exists": {"sql": "SELECT id FROM demo WHERE id=%s", "params": [1]}},
            {"db_eq": {"sql": "SELECT value FROM demo", "expected": "ok"}},
            {"db_gte": {"sql": "SELECT count FROM demo", "expected": 1}},
        ],
        response_body,
        200,
    )


def test_redis_assertions_are_generic_and_yaml_shaped(response_body):
    """Redis 规则验证通用 key/hash/set 能力，不包含任何业务 Key 前缀。"""
    class Redis:
        def exists(self, key):
            return key == "demo:key"

        def get(self, key):
            return "origin"

        def hexists(self, key, field):
            return key == "login" and field == "token"

        def ttl(self, key):
            return 1200

        def scard(self, key):
            return 2

    Assertions(redis_client_factory=lambda source: Redis()).assert_all(
        [
            {"redis_exists": {"key": "demo:key"}},
            {"redis_eq": {"key": "demo:key", "expected": "origin"}},
            {"redis_hfield_exists": {"key": "login", "field": "token"}},
            {"redis_ttl_between": {"key": "login", "min": 1, "max": 1800}},
            {"redis_scard_gte": {"key": "uv", "expected": 1}},
        ],
        response_body,
        200,
    )


def test_exists_and_numeric_comparison_fail_when_selector_is_missing(response_body):
    with pytest.raises(AssertionError) as exc_info:
        Assertions().assert_all(
            [{"exists": "$.data.missing"}, {"gt": ["$.data.missing", 0]}],
            response_body,
            200,
        )

    assert "$.data.missing" in str(exc_info.value)


def test_header_contains_supports_relative_or_absolute_redirect_locations(response_body):
    """header_contains 应只要求响应头包含关键片段，兼容 Servlet 相对/绝对 Location。"""
    Assertions().assert_all(
        [{"header_contains": ["Location", "/page/notfound"]}],
        response_body,
        302,
        headers={"Location": "http://nurl.ink:8001/page/notfound"},
    )


def test_header_contains_reports_missing_fragment(response_body):
    """Location 不包含预期片段时应给出明确失败信息。"""
    with pytest.raises(AssertionError) as exc_info:
        Assertions().assert_all(
            [{"header_contains": ["Location", "/page/notfound"]}],
            response_body,
            302,
            headers={"Location": "https://www.doubao.com/"},
        )

    message = str(exc_info.value)
    assert "header_contains" in message
    assert "/page/notfound" in message


def test_redis_hash_failure_does_not_echo_dynamic_field_value(response_body):
    """Hash field 可能是 token 等敏感运行时值，失败信息不能把真实 field 原文带进 traceback。"""
    class Redis:
        def hexists(self, key, field):
            return False

    secret_field = "runtime-secret-field-value"
    with pytest.raises(AssertionError) as exc_info:
        Assertions(redis_client_factory=lambda source: Redis()).assert_all(
            [{"redis_hfield_exists": {"key": "demo:login", "field": secret_field}}],
            response_body,
            200,
        )

    message = str(exc_info.value)
    assert "redis_hfield_exists" in message
    assert secret_field not in message
