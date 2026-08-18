"""短链接真实项目：Statistics 域测试入口。

统计请求参数、PV/UV/UIP 响应断言、最终一致性 ``poll`` 配置和 MySQL 持久化断言
全部来自 ``statistics.yaml``。Python 仅先访问一次真实短链触发统计事件。
"""
from __future__ import annotations

# Pytest 只承担参数化和 fixture 生命周期。
import pytest

# level/tags/poll 等 Case 元数据全部由 YAML Loader/ApiRunner 解释。
from core.case_loader import get_testcase_params
# Redirect 主 Case 与 Statistics YAML 都从当前短链接项目目录统一读取。
from testcases.shortlink.support import (
    REDIRECT_YAML_PATH,
    STATISTICS_YAML_PATH,
    shortlink_case,
)


# Statistics 业务域目前包含 Smoke 与 Regression 两个 Case。
YAML_FILE = STATISTICS_YAML_PATH
# marker 从每个 YAML Case 的 level/tags 自动产生，不在 Python 重复装饰。
CASES = get_testcase_params(YAML_FILE)


@pytest.mark.parametrize("base_info,test_case", CASES)
def test_shortlink_statistics_cases(
    base_info,
    test_case,
    request_base,
    shortlink_created_context,
):
    """访问短链后按 YAML poll 等待统计可见；Regression 继续验证真实 MySQL 统计表。"""
    # fixture 已经真实 Create；short_uri 缺失说明前置数据没有建立成功，应立即失败。
    assert shortlink_created_context["short_uri"]
    # 复用 redirect.yaml 的正常第一跳 Case，不在 Statistics Python 中复制 URL/302 规则。
    redirect_base, redirect_case = shortlink_case(REDIRECT_YAML_PATH, "redirect_success")
    # 只触发一次 Redirect，避免轮询过程中重复增加 PV。
    request_base.run(redirect_base, redirect_case)
    # Stats 的请求参数、轮询间隔、响应断言和可选 DB 断言全部由当前 YAML Case 控制。
    request_base.run_polling(base_info, test_case)
