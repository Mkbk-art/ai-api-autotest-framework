"""配置优先级、外部私有环境覆盖与统一命令行 Runner 的单元测试。

本模块保护 ConfigManager/Runner 的框架级契约：公共命名环境可被仓库外 YAML 局部覆盖，
但环境变量与 CLI 仍拥有更高优先级；同时验证外部文件路径能贯穿 Runner → Pytest 生命周期。
测试只使用临时目录和占位值，不依赖当前短链接 SUT 的真实密码。
"""
# Path 用于构造 tmp_path 下的公共/私有 YAML，并验证 Runner 的路径解析结果。
from pathlib import Path

# PyYAML 仅用于测试辅助函数生成 UTF-8 YAML，避免手写字符串影响结构断言。
import yaml

# ConfigManager 是本模块主要被测对象，测试它的多层覆盖优先级与 fail-fast 行为。
from core.config_manager import ConfigManager
# build_pytest_args/resolve_level 保留对统一 Runner 历史契约的回归保护。
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


def test_external_env_file_overrides_named_environment_without_copying_full_config(tmp_path):
    """外部私有 YAML 可以只覆盖敏感字段，同时保留公开环境文件中的项目结构。"""
    # config.yaml 提供框架公共默认值，模拟真实项目不会在私有文件里重复维护这些字段。
    write_yaml(
        tmp_path / "config" / "config.yaml",
        {"api": {"host": "http://default", "timeout": 10}},
    )
    # 命名环境文件可以公开提交到 Git：保留 suite 与占位凭据，便于别人参考项目接入方式。
    write_yaml(
        tmp_path / "config" / "env.demo-local.yaml",
        {
            "api": {"host": "http://public-gateway", "timeout": 20},
            "test_selection": {"include_suites": ["demo_project"]},
            "project": {"username": "tester", "password": "CHANGE_ME"},
        },
    )
    # 仓库外覆盖文件只写真正私有/本机差异，不复制整份公开环境 YAML。
    private_file = tmp_path / "private" / "demo-local.override.yaml"
    write_yaml(
        private_file,
        {
            "api": {"timeout": 35},
            "project": {"password": "local-secret-value"},
        },
    )

    config = ConfigManager(project_root=tmp_path, environ={}).load(
        "demo-local",
        env_file=private_file,
    )

    # 公开环境仍决定真实 SUT 地址与 suite，证明外部文件是“覆盖层”而不是第二套完整配置。
    assert config["api"]["host"] == "http://public-gateway"
    assert config["test_selection"]["include_suites"] == ["demo_project"]
    # 私有层只覆盖它声明的字段，因此真实密码和本机 timeout 生效。
    assert config["api"]["timeout"] == 35
    assert config["project"]["password"] == "local-secret-value"


def test_external_env_file_precedence_stays_below_environment_and_cli(tmp_path):
    """外部 YAML 高于公开环境，但仍必须低于环境变量与 CLI 临时覆盖。"""
    write_yaml(tmp_path / "config" / "config.yaml", {"api": {"host": "http://default"}})
    write_yaml(tmp_path / "config" / "env.test.yaml", {"api": {"host": "http://named"}})
    private_file = tmp_path / "private.yaml"
    write_yaml(private_file, {"api": {"host": "http://private"}})
    manager = ConfigManager(project_root=tmp_path, environ={"API_HOST": "http://environment"})

    config = manager.load(
        "test",
        env_file=private_file,
        cli_overrides={"api": {"host": "http://cli"}},
    )

    # 最终值来自 CLI，完整顺序应为 CLI > env vars > external YAML > named YAML > defaults。
    assert config["api"]["host"] == "http://cli"


def test_api_test_env_file_environment_variable_supports_ci_without_business_specific_parameters(tmp_path):
    """Jenkins/其他 CI 只需提供通用文件路径环境变量，不需要知道任何项目业务字段。"""
    write_yaml(tmp_path / "config" / "config.yaml", {"api": {"host": "http://default"}})
    write_yaml(tmp_path / "config" / "env.test.yaml", {"project": {"password": "CHANGE_ME"}})
    private_file = tmp_path / "ci-private.yaml"
    write_yaml(private_file, {"project": {"password": "private-from-file"}})
    manager = ConfigManager(
        project_root=tmp_path,
        environ={"API_TEST_ENV_FILE": str(private_file)},
    )

    config = manager.load("test")

    assert config["project"]["password"] == "private-from-file"


def test_missing_external_env_file_fails_fast_instead_of_using_public_placeholders(tmp_path):
    """显式指定私有文件却不存在时应立即失败，避免误用 CHANGE_ME 后再产生业务层假故障。"""
    write_yaml(tmp_path / "config" / "config.yaml", {"api": {"host": "http://default"}})
    manager = ConfigManager(project_root=tmp_path, environ={})
    missing = tmp_path / "private" / "missing.yaml"

    try:
        manager.load("test", env_file=missing)
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("explicit missing external env file must fail fast")


def test_parser_accepts_external_env_file_path_without_putting_secret_values_on_cli(tmp_path):
    """CLI 只传外部 YAML 路径；真实账号密码继续留在本地文件中。"""
    from run import _parser

    private_file = tmp_path / "private.yaml"
    args = _parser().parse_args(["--env", "demo-local", "--env-file", str(private_file)])

    assert args.env == "demo-local"
    assert args.env_file == str(private_file)


def test_run_tests_temporarily_exposes_cli_env_file_to_pytest_runtime(monkeypatch, tmp_path):
    """run.py 的 --env-file 必须让 Pytest collection/fixtures 读到同一文件，并在结束后恢复进程环境。"""
    # 只验证统一 Runner 的配置传播，不真正启动业务测试；Pytest main 用轻量替身记录调用时环境。
    import os
    import run as run_module

    private_file = tmp_path / "private.yaml"
    write_yaml(private_file, {"project": {"password": "private-value"}})
    observed: dict[str, object] = {}

    def fake_load(self, env_name="test", env_file=None, cli_overrides=None):
        """记录 Runner 交给 ConfigManager 的外部文件，并返回最小可运行配置。"""
        observed["load_env_name"] = env_name
        observed["load_env_file"] = str(env_file) if env_file is not None else None
        return {
            "api": {
                "host": "http://127.0.0.1:1",
                "timeout": 1,
                "verify_ssl": False,
                "use_mock": False,
            },
            "report": {"root_dir": str(tmp_path / "runs")},
        }

    def fake_pytest_main(args):
        """Pytest 真正开始 collection 时，conftest 依赖该环境变量找到同一私有覆盖文件。"""
        observed["pytest_env_file"] = os.environ.get("API_TEST_ENV_FILE")
        observed["pytest_args"] = list(args)
        return 0

    monkeypatch.setattr(run_module.ConfigManager, "load", fake_load)
    monkeypatch.setattr(run_module.pytest, "main", fake_pytest_main)
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: False)
    monkeypatch.delenv("API_TEST_ENV_FILE", raising=False)

    exit_code = run_module.run_tests(
        env_name="demo-local",
        env_file=private_file,
        level="smoke",
        run_id="external-env-test",
        junit_path=tmp_path / "junit.xml",
    )

    assert exit_code == 0
    assert observed["load_env_name"] == "demo-local"
    assert observed["load_env_file"] == str(private_file.resolve())
    assert observed["pytest_env_file"] == str(private_file.resolve())
    # CLI 显式覆盖只在本次运行期间生效，避免同一 Python 进程的下一次 run_tests 串用旧私有文件。
    assert "API_TEST_ENV_FILE" not in os.environ


def test_generate_allure_html_executes_resolved_windows_cmd_via_comspec(monkeypatch, tmp_path):
    """npm 安装的 allure.cmd 应由 Windows command processor 启动，而不是作为裸命令交给 CreateProcess。"""
    import run as run_module

    results = tmp_path / "allure-results"
    report = tmp_path / "allure-report"
    results.mkdir()
    allure_cmd = r"C:\Users\tester\.npm-global\allure.cmd"
    comspec = r"C:\Windows\System32\cmd.exe"
    observed: dict[str, object] = {}

    monkeypatch.setattr(run_module.shutil, "which", lambda name: allure_cmd if name == "allure" else None)
    monkeypatch.setenv("COMSPEC", comspec)

    def fake_run(command, *, check):
        observed["command"] = command
        observed["check"] = check

    monkeypatch.setattr(run_module.subprocess, "run", fake_run)

    assert run_module._generate_allure_html(results, report) is True
    assert observed["command"] == [
        comspec,
        "/d",
        "/c",
        allure_cmd,
        "generate",
        str(results),
        "-o",
        str(report),
        "--clean",
    ]
    assert observed["check"] is True


def test_run_tests_preserves_pytest_exit_code_when_allure_process_cannot_start(monkeypatch, tmp_path):
    """Allure HTML 是报告增强；CLI 启动失败不能覆盖已经通过的 Pytest 退出码。"""
    import json
    import run as run_module

    def fake_load(self, env_name="test", env_file=None, cli_overrides=None):
        return {
            "api": {
                "host": "http://127.0.0.1:1",
                "timeout": 1,
                "verify_ssl": False,
                "use_mock": False,
            },
            "report": {"root_dir": str(tmp_path / "runs")},
        }

    monkeypatch.setattr(run_module.ConfigManager, "load", fake_load)
    monkeypatch.setattr(run_module.pytest, "main", lambda args: 0)
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: True)
    monkeypatch.setattr(
        run_module,
        "_generate_allure_html",
        lambda results, report: (_ for _ in ()).throw(FileNotFoundError("allure launcher missing")),
    )

    exit_code = run_module.run_tests(
        env_name="test",
        level="regression",
        run_id="allure-launch-failure",
        junit_path=tmp_path / "junit.xml",
    )

    assert exit_code == 0
    metadata = json.loads(
        (tmp_path / "runs" / "allure-launch-failure" / "run.json").read_text(encoding="utf-8")
    )
    assert metadata["pytest_exit_code"] == 0
    assert metadata["allure_html_generated"] is False
