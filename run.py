"""接口自动化框架统一命令行入口。

本模块把多环境配置、可选仓库外环境覆盖 YAML、smoke/core/regression 分层、Pytest 参数、
JUnit 输出、Allure Results/HTML 以及每次运行的 ``run.json`` 元数据统一组织起来。
业务开发者优先通过 ``python run.py ...`` 启动测试，而不是在不同环境中手工拼装复杂的
Pytest 命令；真实项目的私有凭据仍保存在 YAML 文件中，Runner 只接收文件路径。
"""
from __future__ import annotations

# argparse 定义统一 CLI；所有 CI 平台最终都应调用这一个入口而不是各自拼 Pytest 参数。
import argparse
# importlib.util 用于判断当前隔离环境是否安装 allure-pytest。
import importlib.util
# json 负责把一次运行的机器可读证据写入 run.json。
import json
# os 负责向同进程 Pytest collection/fixtures 暴露当前环境与可选外部 YAML 路径。
import os
# shutil/subprocess 用于在 Allure CLI 可用时生成 HTML，不把它设为测试成功的硬依赖。
import shutil
import subprocess
# sys 只在 __main__ 入口把真实 Pytest 退出码返回给 Shell/Jenkins。
import sys
# contextmanager 保证临时 API_TEST_ENV_FILE 即使异常也能恢复，避免同进程后续运行串配置。
from contextlib import contextmanager
# UTC 时间戳用于生成默认 run_id，方便报告目录跨时区保持稳定。
from datetime import datetime, timezone
# Path 统一处理报告目录与外部环境 YAML 路径。
from pathlib import Path
# Iterator/Sequence 分别描述上下文管理器返回值和 main(argv) 的可测试参数。
from typing import Iterator, Sequence

# pytest.main 让统一 Runner 在当前 Python 进程执行 collection、fixtures 与业务用例。
import pytest

# ConfigManager 负责所有配置层级合并；run.py 不理解任何具体 SUT 字段。
from core.config_manager import ConfigManager
# PROJECT_ROOT 保证相对路径与报告目录不依赖命令执行位置。
from utils.project_paths import PROJECT_ROOT

_LEVELS = ("smoke", "core", "regression")


@contextmanager
def _runtime_env_file(env_file: str | Path | None) -> Iterator[Path | None]:
    """在一次 ``run_tests`` 生命周期内临时暴露外部环境 YAML 路径。

    ConfigManager 在 Runner 启动阶段可以直接接收 ``env_file``，但 Pytest collection
    与 fixture 会在 ``conftest.py`` 中重新构造 ConfigManager。这里临时写入统一的
    ``API_TEST_ENV_FILE``，保证 Runner、collection hooks 与 fixtures 使用完全相同的
    外部覆盖文件；运行结束后恢复旧值，避免同一 Python 进程的下一次测试串用配置。
    """
    # 没有 CLI 显式文件时不改环境，让用户/CI 预先设置的 API_TEST_ENV_FILE 原样生效。
    if env_file is None:
        yield None
        return

    # 相对路径按框架根目录解析，与 ConfigManager 的路径语义保持一致。
    resolved = Path(env_file).expanduser()
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    resolved = resolved.resolve()

    # 记录旧值；finally 无论 Pytest 成功、失败还是抛异常都恢复进程环境。
    previous = os.environ.get("API_TEST_ENV_FILE")
    os.environ["API_TEST_ENV_FILE"] = str(resolved)
    try:
        yield resolved
    finally:
        if previous is None:
            os.environ.pop("API_TEST_ENV_FILE", None)
        else:
            os.environ["API_TEST_ENV_FILE"] = previous


def resolve_level(
    level: str | None,
    *,
    smoke: bool,
    core: bool,
    regression: bool,
) -> str | None:
    """解析新 ``--level`` 参数以及历史兼容的独立层级参数。"""
    if level is not None:
        return level
    selected = [name for name, enabled in zip(_LEVELS, (smoke, core, regression)) if enabled]
    if len(selected) > 1:
        raise ValueError("Choose only one legacy level flag")
    return selected[0] if selected else None


def build_pytest_args(
    *,
    level: str | None,
    test_path: str | Path,
    results_dir: str | Path,
    junit_path: str | Path,
    allure_enabled: bool,
    collect_only: bool = False,
) -> list[str]:
    """根据一次运行配置构造最终传给 ``pytest.main`` 的参数列表。"""
    args = ["-s", "-v", str(test_path), f"--junitxml={junit_path}"]
    if level:
        args.extend(["-m", level])
    if collect_only:
        args.append("--collect-only")
    if allure_enabled:
        args.extend([f"--alluredir={results_dir}", "--clean-alluredir"])
    return args


def _allure_plugin_available() -> bool:
    """检测当前 Python 环境是否安装 ``allure-pytest``。"""
    return importlib.util.find_spec("allure_pytest") is not None


def _generate_allure_html(results_dir: Path, report_dir: Path) -> bool:
    """在 Allure CLI 可用时生成 HTML；缺少 CLI 时返回 False 而不影响测试结论。"""
    if not results_dir.exists() or shutil.which("allure") is None:
        return False
    subprocess.run(
        ["allure", "generate", str(results_dir), "-o", str(report_dir), "--clean"],
        check=True,
    )
    return True


def _new_run_id() -> str:
    """生成 UTC 时间戳形式的唯一运行批次 ID。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def run_tests(
    *,
    env_name: str = "test",
    env_file: str | Path | None = None,
    level: str | None = None,
    test_path: str | Path = "testcases",
    run_id: str | None = None,
    results_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
    junit_path: str | Path | None = None,
    collect_only: bool = False,
    cli_overrides: dict | None = None,
) -> int:
    """执行一次完整测试运行并返回真实 Pytest 退出码。

    本函数负责加载配置、准备报告目录、向 Pytest fixture 暴露运行环境变量、
    调用 Pytest、尝试生成 Allure HTML，并把关键运行证据写入 ``run.json``。
    """
    # CLI 显式 --env-file 需要在整个 Pytest 生命周期中可见；若未指定，则尊重外部已有环境变量。
    with _runtime_env_file(env_file) as resolved_env_file:
        # ConfigManager 只读取文件内容并按层级合并；不会把业务字段写进框架代码。
        config = ConfigManager().load(
            env_name,
            env_file=resolved_env_file,
            cli_overrides=cli_overrides,
        )
        run_id = run_id or _new_run_id()
        root = PROJECT_ROOT / config.get("report", {}).get("root_dir", "reports/runs") / run_id
        root.mkdir(parents=True, exist_ok=True)
        results = Path(results_dir) if results_dir else root / "allure-results"
        report = Path(report_dir) if report_dir else root / "allure-report"
        junit = Path(junit_path) if junit_path else root / "junit.xml"
        results.parent.mkdir(parents=True, exist_ok=True)
        junit.parent.mkdir(parents=True, exist_ok=True)

        # 把最终 API 配置暴露给 Pytest 进程，使 conftest 与统一 Runner 使用同一配置来源。
        api = config.get("api", {})
        os.environ["API_TEST_ENV"] = env_name
        os.environ["API_HOST"] = str(api.get("host", ""))
        os.environ["API_TIMEOUT"] = str(api.get("timeout", 30))
        os.environ["API_VERIFY_SSL"] = str(bool(api.get("verify_ssl", True))).lower()
        os.environ["API_USE_MOCK"] = str(bool(api.get("use_mock", False))).lower()

        allure_enabled = _allure_plugin_available()
        args = build_pytest_args(
            level=level,
            test_path=test_path,
            results_dir=results,
            junit_path=junit,
            allure_enabled=allure_enabled,
            collect_only=collect_only,
        )
        # pytest.main 在同一进程执行，所以 collection hooks/fixtures 能读取临时 API_TEST_ENV_FILE。
        exit_code = int(pytest.main(args))

        html_generated = False
        if allure_enabled and not collect_only:
            try:
                html_generated = _generate_allure_html(results, report)
            except subprocess.CalledProcessError:
                # HTML 展示属于报告增强，不覆盖 Pytest 的真实测试退出码。
                html_generated = False

        # 证据只记录逻辑环境名和测试产物，不记录外部私有 YAML 的路径或内容。
        metadata = {
            "run_id": run_id,
            "environment": env_name,
            "level": level,
            "pytest_exit_code": exit_code,
            "pytest_args": args,
            "allure_plugin_available": allure_enabled,
            "allure_html_generated": html_generated,
            "junit_xml": str(junit),
            "allure_results": str(results) if allure_enabled else None,
            "allure_report": str(report) if html_generated else None,
        }
        (root / "run.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return exit_code


def _parser() -> argparse.ArgumentParser:
    """定义项目支持的命令行参数。"""
    parser = argparse.ArgumentParser(description="API 自动化测试框架")
    parser.add_argument("--env", default="test", help="配置环境名称，如 test/stage")
    # --env-file 只传仓库外 YAML 路径，不在命令行暴露真实账号、密码等具体敏感值。
    parser.add_argument(
        "--env-file",
        help="可选外部环境覆盖 YAML；高于 env.<name>.yaml，适合本机/CI 私有配置",
    )
    parser.add_argument("--level", choices=_LEVELS, help="用例层级")
    parser.add_argument("--smoke", action="store_true", help="兼容旧参数")
    parser.add_argument("--core", action="store_true", help="兼容旧参数")
    parser.add_argument("--regression", action="store_true", help="兼容旧参数")
    parser.add_argument("--test-path", default="testcases")
    parser.add_argument("--host", help="覆盖 API host")
    parser.add_argument("--timeout", type=float, help="覆盖请求超时秒数")

    tls_group = parser.add_mutually_exclusive_group()
    tls_group.add_argument("--verify-ssl", dest="verify_ssl", action="store_true")
    tls_group.add_argument("--no-verify-ssl", dest="verify_ssl", action="store_false")
    parser.set_defaults(verify_ssl=None)

    mock_group = parser.add_mutually_exclusive_group()
    mock_group.add_argument("--use-mock", dest="use_mock", action="store_true")
    mock_group.add_argument("--no-use-mock", dest="use_mock", action="store_false")
    parser.set_defaults(use_mock=None)

    parser.add_argument("--run-id")
    parser.add_argument("--alluredir")
    parser.add_argument("--reportdir")
    parser.add_argument("--junitxml")
    parser.add_argument("--collect-only", action="store_true")
    return parser


def build_cli_overrides(args) -> dict:
    """把命令行中的 API 覆盖参数转换成 ConfigManager 可合并的字典。"""
    api = {}
    if args.host is not None:
        api["host"] = args.host
    if args.timeout is not None:
        api["timeout"] = args.timeout
    if args.verify_ssl is not None:
        api["verify_ssl"] = args.verify_ssl
    if args.use_mock is not None:
        api["use_mock"] = args.use_mock
    return {"api": api} if api else {}


def main(argv: Sequence[str] | None = None) -> int:
    """解析 CLI 参数并启动一次框架测试运行。"""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        level = resolve_level(
            args.level,
            smoke=args.smoke,
            core=args.core,
            regression=args.regression,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return run_tests(
        env_name=args.env,
        env_file=args.env_file,
        level=level,
        test_path=args.test_path,
        run_id=args.run_id,
        results_dir=args.alluredir,
        report_dir=args.reportdir,
        junit_path=args.junitxml,
        collect_only=args.collect_only,
        cli_overrides=build_cli_overrides(args),
    )


if __name__ == "__main__":
    sys.exit(main())
