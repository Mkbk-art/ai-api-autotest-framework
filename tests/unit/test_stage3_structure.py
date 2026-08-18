"""Stage 3 架构约束测试。

本模块用于防止后续迭代重新引入开源基线遗留的 ``base/common/testcase``
目录，同时检查正式 Python 模块是否具备最基本的模块和公共 API 说明。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_DIRS = ("core", "utils", "db", "testcases")
LEGACY_DIRS = ("base", "common", "testcase")
PRODUCTION_DIRS = ("core", "utils", "db", "mock_server", "testcases")


def _python_files_under(directory: str) -> list[Path]:
    """返回指定正式源码目录中的全部 Python 文件。"""
    return sorted((PROJECT_ROOT / directory).rglob("*.py"))


def test_stage3_uses_new_package_layout_without_legacy_directories():
    """验证 Stage 3 只保留正式的新目录结构。"""
    for directory in TARGET_DIRS:
        assert (PROJECT_ROOT / directory).is_dir(), f"missing target directory: {directory}"
    for directory in LEGACY_DIRS:
        assert not (PROJECT_ROOT / directory).exists(), f"legacy directory still exists: {directory}"


def test_core_api_runner_is_importable_from_new_location():
    """验证用例编排器已经迁移并使用更准确的 ApiRunner 命名。"""
    from core.api_runner import ApiRunner

    assert ApiRunner.__name__ == "ApiRunner"


@pytest.mark.parametrize("directory", PRODUCTION_DIRS)
def test_production_python_modules_have_module_docstrings(directory):
    """验证正式源码模块顶部都说明模块用途。"""
    files = _python_files_under(directory)
    assert files, f"no Python modules found under {directory}"
    missing = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not ast.get_docstring(tree):
            missing.append(str(path.relative_to(PROJECT_ROOT)))
    assert not missing, f"modules missing top-level docstrings: {missing}"


def test_core_and_utils_public_apis_have_docstrings():
    """验证正式框架公共类和公共函数都有可读说明。"""
    missing = []
    for directory in ("core", "utils", "db"):
        for path in _python_files_under(directory):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.startswith("_"):
                        continue
                    if not ast.get_docstring(node):
                        missing.append(f"{path.relative_to(PROJECT_ROOT)}::{node.name}")
    assert not missing, f"public APIs missing docstrings: {missing}"
