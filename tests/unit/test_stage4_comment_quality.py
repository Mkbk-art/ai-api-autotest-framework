"""声明式 Runtime 与真实项目扩展的可维护性说明守护测试。

用户要求交付代码具有充分中文解释。本测试不再用“注释行占比”逼迫 YAML/Python 机械堆注释，
而是检查真正能帮助维护者理解架构的内容：模块说明、公共函数说明、YAML 文件级说明以及
CaseSpec 的稳定元数据。这样既保持可读性，也避免注释数量反过来污染结构化测试资产。
"""
from __future__ import annotations

import ast
from pathlib import Path

from core.case_spec import load_case_specs
from utils.project_paths import PROJECT_ROOT


SHORTLINK_DIR = PROJECT_ROOT / "testcases" / "shortlink"
SHORTLINK_YAML_DIR = SHORTLINK_DIR / "yaml"


def _assert_module_and_functions_documented(path: Path) -> None:
    """要求模块和本轮正式函数都具有用途说明；下划线私有 helper 同样属于项目维护边界。"""
    module = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(module), f"missing module docstring: {path}"
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert ast.get_docstring(node), f"missing docstring for {node.name}: {path}"


def test_shortlink_project_python_modules_keep_architecture_explanations():
    """真实 SUT 的 adapter/context/workflow 都必须说明其职责和生命周期。"""
    paths = [
        SHORTLINK_DIR / "support.py",
        SHORTLINK_DIR / "context.py",
        SHORTLINK_DIR / "workflows" / "test_storage_lifecycle.py",
    ]
    for path in paths:
        assert path.is_file(), f"missing project module: {path}"
        _assert_module_and_functions_documented(path)


def test_shortlink_v2_yaml_files_keep_file_guidance_and_structured_metadata():
    """YAML 重点守住“可执行 Test Specification”信息，而不是追求无意义的注释比例。"""
    yaml_files = sorted(SHORTLINK_YAML_DIR.glob("*.yaml"))
    assert [path.name for path in yaml_files] == [
        "auth.yaml",
        "link.yaml",
        "redirect.yaml",
        "statistics.yaml",
    ]
    for path in yaml_files:
        text = path.read_text(encoding="utf-8")
        # 每份真实项目 YAML 顶部至少保留四条中文/架构说明，解释它属于 SUT 而非 Core。
        header_comments = [line for line in text.splitlines()[:8] if line.lstrip().startswith("#")]
        assert len(header_comments) >= 4, f"missing YAML guidance comments: {path}"
        cases = load_case_specs(path)
        assert cases
        for case in cases:
            assert case.case_id
            assert case.name
            assert case.level in {"smoke", "core", "regression"}
            assert case.risks, f"case risk metadata missing: {case.case_id}"
            if case.execution == "declarative":
                assert case.operation_id, f"operation_id missing: {case.case_id}"


DECLARATIVE_RUNTIME_FILES = [
    PROJECT_ROOT / "core" / "case_spec.py",
    PROJECT_ROOT / "core" / "case_registry.py",
    PROJECT_ROOT / "core" / "case_executor.py",
    PROJECT_ROOT / "core" / "context_provider.py",
    PROJECT_ROOT / "core" / "api_runner.py",
    PROJECT_ROOT / "core" / "assertion_engine.py",
    PROJECT_ROOT / "conftest.py",
    PROJECT_ROOT / "testcases" / "test_yaml_cases.py",
    PROJECT_ROOT / "testcases" / "demo" / "context.py",
]


def test_declarative_runtime_files_keep_module_and_api_docstrings():
    """本轮新增/修改的通用 Runtime 必须能通过模块和公共接口说明独立理解职责。"""
    for path in DECLARATIVE_RUNTIME_FILES:
        assert path.is_file(), f"missing declarative runtime module: {path}"
        _assert_module_and_functions_documented(path)


ENV_YAMLS = [
    PROJECT_ROOT / "config" / "config.yaml",
    PROJECT_ROOT / "config" / "env_template.yaml",
    PROJECT_ROOT / "config" / "env.test.yaml",
    PROJECT_ROOT / "config" / "env.shortlink-local.yaml",
]


def test_environment_yaml_still_contains_explanatory_comments():
    """公共环境配置保留说明；本机 ignored 私有配置是否存在不应影响 Runtime 测试。"""
    for path in ENV_YAMLS:
        assert path.is_file(), f"missing environment YAML: {path}"
        comments = [line for line in path.read_text(encoding="utf-8").splitlines() if line.lstrip().startswith("#")]
        assert len(comments) >= 5, f"insufficient environment explanations: {path}"
