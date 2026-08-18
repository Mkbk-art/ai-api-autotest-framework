"""DebugTalk 动态函数库的单元测试。

本模块保护 DebugTalk 的通用环境变量兼容能力、Stage 5 环境 YAML 配置读取能力，
以及错误密码动态生成与真实凭据隔离。短链接登录信息已不再依赖 OS 环境变量。
"""
from __future__ import annotations

import pytest

from utils.debugtalk import DebugTalk


def test_debugtalk_env_reads_required_environment_variable(monkeypatch):
    """存在的环境变量应原样返回，供 YAML ``${env(NAME)}`` 使用。"""
    monkeypatch.setenv("DEMO_REQUIRED_ENV", "demo-user")

    assert DebugTalk().env("DEMO_REQUIRED_ENV") == "demo-user"


def test_debugtalk_env_rejects_missing_environment_variable(monkeypatch):
    """凭据缺失时必须明确失败，避免向真实接口发送空用户名/密码。"""
    monkeypatch.delenv("DEMO_MISSING_ENV", raising=False)

    with pytest.raises(RuntimeError, match="DEMO_MISSING_ENV"):
        DebugTalk().env("DEMO_MISSING_ENV")

def test_invalid_password_is_generated_without_reading_real_secret(monkeypatch):
    """错误密码测试数据不得读取、拼接或泄露真实登录密码。"""
    # 即使 runtime_config 中存在真实形态的密码，错误数据生成函数也必须完全不读取它。
    real_secret = "real-secret-only-for-unit-test"
    debugtalk = DebugTalk(runtime_config={"shortlink": {"password": real_secret}})

    # 调用安全错误密码生成函数；其输入不包含任何凭据参数。
    invalid = debugtalk.invalid_password()

    # 固定前缀让测试报告能识别这是自动化故意制造的错误值。
    assert invalid.startswith("__api_autotest_invalid__")
    # 动态后缀避免多个异常用例长期复用同一个字符串。
    assert len(invalid) > len("__api_autotest_invalid__")
    # 最关键：错误数据不得包含真实密码，避免异常请求或 traceback 暴露真实凭据。
    assert real_secret not in invalid



def test_debugtalk_config_reads_injected_runtime_config_without_environment_variables():
    """YAML 应能直接读取当前环境配置，而不再要求终端 export 登录信息。"""
    runtime_config = {
        "shortlink": {
            "username": "yaml-user",
            "password": "yaml-password",
        }
    }

    debugtalk = DebugTalk(runtime_config=runtime_config)

    assert debugtalk.config("shortlink", "username") == "yaml-user"
    assert debugtalk.config("shortlink", "password") == "yaml-password"


def test_debugtalk_config_rejects_missing_or_placeholder_values():
    """真实环境必填配置缺失时应在发请求前给出明确 YAML 配置错误。"""
    debugtalk = DebugTalk(runtime_config={"shortlink": {"password": "CHANGE_ME"}})

    with pytest.raises(RuntimeError, match="shortlink.password"):
        debugtalk.config("shortlink", "password")
