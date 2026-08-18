"""YAML 用例路径、结构校验和加载数量的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
from pathlib import Path
import runpy

import pytest
import yaml

from core.case_loader import get_testcase_yaml


@pytest.mark.parametrize(
    "module_name,yaml_name",
    [
        ("test_login.py", "login.yaml"),
        ("test_publish_api.py", "publish_api.yaml"),
        ("test_call_api.py", "call_api.yaml"),
    ],
)
def test_test_modules_reference_existing_yaml_files(module_name, yaml_name):
    module_path = Path("testcases/demo") / module_name
    namespace = runpy.run_path(str(module_path), run_name=f"path_check_{module_name}")
    declared = Path(namespace["YAML_FILE"])
    assert declared.is_file(), f"{module_name} points to missing YAML: {declared}"
    assert declared.name == yaml_name


def test_missing_yaml_file_raises_file_not_found(tmp_path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="missing.yaml"):
        get_testcase_yaml(missing)


def test_invalid_yaml_root_raises_value_error(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("baseInfo: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level list"):
        get_testcase_yaml(path)


def test_missing_testcase_list_raises_value_error(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump([{"baseInfo": {"url": "/x"}}]), encoding="utf-8")
    with pytest.raises(ValueError, match="testCase"):
        get_testcase_yaml(path)


def test_yaml_loader_returns_every_case(tmp_path):
    path = tmp_path / "valid.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "baseInfo": {"url": "/x", "method": "GET"},
                    "testCase": [{"case_name": "a"}, {"case_name": "b"}],
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cases = get_testcase_yaml(path)
    assert [case[1]["case_name"] for case in cases] == ["a", "b"]


@pytest.mark.parametrize(
    "module_name,yaml_name",
    [
        ("test_auth.py", "auth.yaml"),
        ("test_link.py", "link.yaml"),
        ("test_redirect.py", "redirect.yaml"),
        ("test_statistics.py", "statistics.yaml"),
    ],
)
def test_real_shortlink_modules_reference_grouped_yaml_files(module_name, yaml_name):
    """真实项目按业务域保持 4 个 Python 入口 + 4 个 YAML，而不是一个 Case 一个文件。"""
    module_path = Path("testcases/shortlink") / module_name
    namespace = runpy.run_path(str(module_path), run_name=f"real_path_check_{module_name}")
    declared = Path(namespace["YAML_FILE"])
    assert declared.is_file(), f"{module_name} points to missing YAML: {declared}"
    assert declared.name == yaml_name


def test_yaml_case_metadata_becomes_pytest_marks_and_supports_workflow_filter(tmp_path):
    """level/tags/workflow 应由 YAML 驱动 Pytest 参数，而不是每个 Python Case 重复装饰器。"""
    from core.case_loader import get_testcase_params

    path = tmp_path / "cases.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "baseInfo": {"url": "/x", "method": "GET"},
                    "testCase": [
                        {
                            "case_name": "smoke case",
                            "level": "smoke",
                            "tags": ["auth"],
                            "workflow": "direct",
                        },
                        {
                            "case_name": "core case",
                            "level": "core",
                            "tags": ["negative"],
                            "workflow": "other",
                        },
                    ],
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    params = get_testcase_params(path, workflows={"direct"})
    assert len(params) == 1
    assert params[0].id == "smoke case"
    mark_names = {mark.name for mark in params[0].marks}
    assert mark_names == {"smoke", "auth"}


def test_yaml_marker_names_can_be_discovered_before_case_collection(tmp_path):
    """框架应能从 YAML level/tags 自动发现 marker，新项目不需要改 pytest.ini 注册业务标签。"""
    from core.case_loader import get_testcase_marker_names

    path = tmp_path / "domain.yaml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "baseInfo": {"url": "/orders", "method": "GET"},
                    "testCase": [
                        {"case_name": "a", "level": "smoke", "tags": ["order", "database"]},
                        {"case_name": "b", "level": "core", "tags": ["negative", "order"]},
                    ],
                }
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    assert get_testcase_marker_names(path) == {"smoke", "core", "order", "database", "negative"}


def test_shared_pytest_glue_does_not_hardcode_demo_or_real_project_suite_names():
    """公共 conftest 应从环境 YAML 选择 suite，而不是写死当前真实项目/示例项目目录名。"""
    source = Path("conftest.py").read_text(encoding="utf-8").lower()
    assert "shortlink-local" not in source
    assert '"shortlink"' not in source
    assert '"demo"' not in source
