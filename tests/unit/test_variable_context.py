"""作用域 VariableContext 的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import pytest

from core.variable_context import VariableContext, VariableNotFoundError


def test_scope_precedence_and_explicit_scope_lookup():
    context = VariableContext()
    context.set("token", "session-token", scope="session")
    context.set("token", "scenario-token", scope="scenario")
    context.set("token", "case-token", scope="case")

    assert context.get("token") == "case-token"
    assert context.get("token", scope="scenario") == "scenario-token"
    assert context.get("token", scope="session") == "session-token"


def test_exact_placeholder_preserves_value_type_and_embedded_placeholder_becomes_text():
    context = VariableContext()
    context.set("interface_id", 42, scope="scenario")

    assert context.replace_variables("${interface_id}") == 42
    assert context.replace_variables("id=${interface_id}") == "id=42"


def test_replace_variables_recurses_through_dict_list_and_tuple():
    context = VariableContext()
    context.set("token", "abc", scope="scenario")
    context.set("count", 3, scope="case")

    value = {
        "header": "Bearer ${token}",
        "items": ["${count}", {"token": "${token}"}],
        "tuple": ("${count}", "count=${count}"),
    }

    assert context.replace_variables(value) == {
        "header": "Bearer abc",
        "items": [3, {"token": "abc"}],
        "tuple": (3, "count=3"),
    }


def test_missing_variable_raises_clear_error():
    context = VariableContext()

    with pytest.raises(VariableNotFoundError, match="missing"):
        context.replace_variables("Bearer ${missing}")


def test_clear_can_target_one_scope_or_all_scopes():
    context = VariableContext()
    context.set("session_value", 1, scope="session")
    context.set("scenario_value", 2, scope="scenario")
    context.set("case_value", 3, scope="case")

    context.clear("case")
    assert context.get("scenario_value") == 2
    with pytest.raises(VariableNotFoundError):
        context.get("case_value")

    context.clear()
    with pytest.raises(VariableNotFoundError):
        context.get("session_value")
    with pytest.raises(VariableNotFoundError):
        context.get("scenario_value")


def test_instances_are_isolated_and_snapshot_is_a_copy():
    first = VariableContext()
    second = VariableContext()
    first.set("token", "first", scope="scenario")

    assert first.get("token") == "first"
    with pytest.raises(VariableNotFoundError):
        second.get("token")

    snapshot = first.export_debug_snapshot()
    snapshot["scenario"]["token"] = "changed"
    assert first.get("token") == "first"
