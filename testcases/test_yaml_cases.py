"""框架统一的声明式 YAML Case 执行入口。

普通项目不再创建 ``test_login.py``、``test_create.py`` 等参数化壳文件。Pytest collection
由根 ``conftest.py`` 根据当前环境选择的项目自动注入 ``yaml_case`` 参数，这个唯一的
Generic Runtime 只负责把 CaseSpec 交给 CaseExecutor。
"""


def test_yaml_case(yaml_case, case_executor):
    """执行一条由项目 YAML 声明的普通 API Case。"""
    case_executor.execute(yaml_case)
