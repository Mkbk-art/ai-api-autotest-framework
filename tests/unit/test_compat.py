"""Allure 兼容层与轻量 JsonPath 工具的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
import importlib


def test_allure_compat_is_importable_without_allure_pytest():
    module = importlib.import_module("utils.allure_compat")
    module.attach("body", "name", module.attachment_type.TEXT)


def test_jsonpath_util_reads_nested_fields_and_lists():
    module = importlib.import_module("utils.jsonpath_util")
    payload = {"data": {"items": [{"id": 1}, {"id": 2}], "token": "abc"}}
    assert module.find_values(payload, "$.data.token") == ["abc"]
    assert module.find_values(payload, "$.data.items[*].id") == [1, 2]
