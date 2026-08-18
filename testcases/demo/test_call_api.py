"""Mock 接口调用 regression 用例。

用例通过 ``published_interface_context`` 独立完成登录和资源创建，验证回归层在
没有前置测试文件的情况下仍能执行正常调用和鉴权失败场景。
"""
import pytest

from core.case_loader import get_testcase_yaml
from utils.project_paths import testcase_yaml as case_yaml_path

YAML_FILE = case_yaml_path("call_api.yaml")


@pytest.mark.regression
@pytest.mark.parametrize("base_info,test_case", get_testcase_yaml(YAML_FILE))
def test_call_api(base_info, test_case, request_base, published_interface_context):
    """执行 Mock 调用接口的全部 YAML regression 场景。"""
    request_base.run(base_info, test_case)
