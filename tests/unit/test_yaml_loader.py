"""YAML V1 兼容 Loader 与 V2 Test Specification 资产边界测试。"""
from pathlib import Path

import pytest
import yaml

from core.case_loader import get_testcase_yaml
from core.case_spec import load_case_specs


@pytest.mark.parametrize(
    "yaml_name,expected_count",
    [
        ("login.yaml", 2),
        ("publish_api.yaml", 2),
        ("call_api.yaml", 2),
    ],
)
def test_demo_v2_yaml_files_are_directly_executable_without_python_wrappers(yaml_name, expected_count):
    """Demo 普通场景应只保留 V2 YAML，不再依赖同名 ``test_xx.py`` 参数化壳。"""
    demo_dir = Path("testcases/demo")
    path = demo_dir / "yaml" / yaml_name
    assert path.is_file()
    assert len(load_case_specs(path)) == expected_count
    assert not list(demo_dir.glob("test_*.py"))


def test_missing_yaml_file_raises_file_not_found(tmp_path):
    """旧 V1 Loader 在兼容期仍应对缺失文件给出明确错误。"""
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
    """保留 V1 Loader 的最小回归，迁移期不会破坏外部已有旧 Case。"""
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


def test_real_shortlink_v2_assets_are_four_grouped_yaml_files_without_ordinary_wrappers():
    """第一个真实 SUT 只维护 4 个业务域 YAML；普通 Case 不再维护 Python wrapper。"""
    shortlink_dir = Path("testcases/shortlink")
    yaml_dir = shortlink_dir / "yaml"
    files = sorted(path.name for path in yaml_dir.glob("*.yaml"))
    assert files == ["auth.yaml", "link.yaml", "redirect.yaml", "statistics.yaml"]
    assert not list(shortlink_dir.glob("test_*.py"))
    assert sum(len(load_case_specs(yaml_dir / name)) for name in files) == 18


def test_v2_case_metadata_exposes_level_tags_and_stable_ids(tmp_path):
    """V2 CaseSpec 将 level/tags/id 提升为结构化资产，Pytest Runtime 不再读取 Python 装饰器。"""
    path = tmp_path / "cases.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "cases": [
                    {
                        "id": "orders.query.success",
                        "name": "query order",
                        "level": "smoke",
                        "tags": ["order", "database"],
                        "operation_id": "queryOrder",
                        "request": {},
                        "assertions": [{"status_code": 200}],
                    }
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    case = load_case_specs(path)[0]
    assert case.case_id == "orders.query.success"
    assert case.operation_id == "queryOrder"
    assert case.marker_names == ("smoke", "order", "database")


def test_shared_pytest_glue_does_not_hardcode_demo_or_real_project_suite_names():
    """公共 conftest 应根据环境 YAML 动态加载项目，而不是写死当前两个示例项目。"""
    source = Path("conftest.py").read_text(encoding="utf-8").lower()
    assert "shortlink-local" not in source
    assert '"shortlink"' not in source
    assert '"demo"' not in source
