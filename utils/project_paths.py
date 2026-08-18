"""项目路径常量和安全的用例文件定位工具。

所有模块统一从这里获取项目根目录、配置、报告和 YAML 用例位置，避免各文件
自行拼接路径导致 Stage 1 曾出现的重复 ``testcase/testcase`` 问题。
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTCASE_DIR = PROJECT_ROOT / "testcases"
YAML_CASE_DIR = TESTCASE_DIR / "yaml"
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"


def testcase_yaml(name: str) -> Path:
    """返回 ``testcases/yaml`` 下指定 YAML 用例文件的绝对路径。

    Args:
        name: 文件名，例如 ``login.yaml``；不允许通过 ``..`` 越出用例目录。

    Raises:
        ValueError: 解析后的路径不位于 YAML 用例目录中。
    """
    path = (YAML_CASE_DIR / name).resolve()
    if path.parent != YAML_CASE_DIR.resolve():
        raise ValueError(f"Invalid testcase YAML name: {name}")
    return path
