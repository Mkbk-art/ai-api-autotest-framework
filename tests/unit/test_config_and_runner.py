"""配置优先级与统一命令行 Runner 的单元测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
from pathlib import Path

import yaml

from core.config_manager import ConfigManager
from run import build_pytest_args, resolve_level


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")


def test_config_precedence_cli_over_env_over_named_file_over_defaults(tmp_path):
    write_yaml(
        tmp_path / "config" / "config.yaml",
        {"api": {"host": "http://default", "timeout": 10, "verify_ssl": True}},
    )
    write_yaml(
        tmp_path / "config" / "env.test.yaml",
        {"api": {"host": "http://file", "timeout": 20}},
    )
    manager = ConfigManager(
        project_root=tmp_path,
        environ={"API_HOST": "http://environment", "API_TIMEOUT": "30"},
    )

    config = manager.load(
        "test",
        cli_overrides={"api": {"host": "http://cli"}},
    )

    assert config["api"] == {
        "host": "http://cli",
        "timeout": 30,
        "verify_ssl": True,
    }


def test_invalid_boolean_environment_value_is_rejected(tmp_path):
    write_yaml(tmp_path / "config" / "config.yaml", {"api": {"verify_ssl": True}})
    manager = ConfigManager(project_root=tmp_path, environ={"API_VERIFY_SSL": "sometimes"})
    try:
        manager.load("test")
    except ValueError as exc:
        assert "API_VERIFY_SSL" in str(exc)
    else:
        raise AssertionError("invalid boolean must raise ValueError")


def test_build_pytest_args_separates_junit_and_allure_outputs(tmp_path):
    args = build_pytest_args(
        level="core",
        test_path="testcase",
        results_dir=tmp_path / "allure-results",
        junit_path=tmp_path / "junit.xml",
        allure_enabled=True,
    )
    assert "-m" in args and args[args.index("-m") + 1] == "core"
    assert f"--junitxml={tmp_path / 'junit.xml'}" in args
    assert f"--alluredir={tmp_path / 'allure-results'}" in args
    assert "--clean-alluredir" in args


def test_build_pytest_args_omits_allure_options_when_plugin_missing(tmp_path):
    args = build_pytest_args(
        level="smoke",
        test_path="testcase",
        results_dir=tmp_path / "allure-results",
        junit_path=tmp_path / "junit.xml",
        allure_enabled=False,
    )
    assert not any(arg.startswith("--alluredir=") for arg in args)
    assert "--clean-alluredir" not in args
    assert f"--junitxml={tmp_path / 'junit.xml'}" in args


def test_resolve_level_prefers_explicit_level_and_supports_legacy_flags():
    assert resolve_level("regression", smoke=True, core=False, regression=False) == "regression"
    assert resolve_level(None, smoke=True, core=False, regression=False) == "smoke"
    assert resolve_level(None, smoke=False, core=True, regression=False) == "core"
    assert resolve_level(None, smoke=False, core=False, regression=True) == "regression"


def test_environment_can_disable_mock_mode(tmp_path):
    write_yaml(
        tmp_path / "config" / "config.yaml",
        {"api": {"host": "http://default", "use_mock": True}},
    )
    manager = ConfigManager(project_root=tmp_path, environ={"API_USE_MOCK": "false"})
    assert manager.load("test")["api"]["use_mock"] is False


def test_cli_api_overrides_are_built_from_parser_values():
    from run import _parser, build_cli_overrides

    args = _parser().parse_args(
        [
            "--host",
            "https://cli.test",
            "--timeout",
            "8",
            "--no-verify-ssl",
            "--no-use-mock",
        ]
    )
    assert build_cli_overrides(args) == {
        "api": {
            "host": "https://cli.test",
            "timeout": 8.0,
            "verify_ssl": False,
            "use_mock": False,
        }
    }


def test_shortlink_local_environment_targets_real_gateway_without_mock():
    """真实短链接本地环境应指向 Gateway 8000 且禁止启动框架 Mock。"""
    config = ConfigManager().load("shortlink-local")

    assert config["api"]["host"] == "http://127.0.0.1:8000"
    assert config["api"]["use_mock"] is False
    assert config["api"]["verify_ssl"] is False
