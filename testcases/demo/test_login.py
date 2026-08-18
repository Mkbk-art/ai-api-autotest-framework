"""Mock 登录接口 smoke 用例。

本模块从 ``login.yaml`` 参数化登录成功和密码错误场景，用于快速验证最基本的
YAML 加载、HTTP 请求和断言链路。
"""
import pytest

from core.case_loader import get_testcase_yaml
from utils.project_paths import testcase_yaml as case_yaml_path

YAML_FILE = case_yaml_path("login.yaml")


@pytest.mark.smoke
@pytest.mark.parametrize("base_info,test_case", get_testcase_yaml(YAML_FILE))
def test_login(base_info, test_case, request_base):
    """执行 Mock 登录接口的全部 YAML smoke 场景。"""
    request_base.run(base_info, test_case)
