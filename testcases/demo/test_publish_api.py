"""Mock 发布接口 core 用例。

用例通过 ``authenticated_context`` 自己准备登录状态，验证 core 层可以脱离
smoke 测试独立运行，同时覆盖正常发布和缺失 Token 的负向场景。
"""
import pytest

from core.case_loader import get_testcase_yaml
from utils.project_paths import testcase_yaml as case_yaml_path

YAML_FILE = case_yaml_path("publish_api.yaml")


@pytest.mark.core
@pytest.mark.parametrize("base_info,test_case", get_testcase_yaml(YAML_FILE))
def test_publish_api(base_info, test_case, request_base, authenticated_context):
    """执行 Mock 发布接口的全部 YAML core 场景。"""
    request_base.run(base_info, test_case)
