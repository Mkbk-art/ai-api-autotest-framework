"""接口自动化框架统一命令行入口。

本模块把多环境配置、smoke/core/regression 分层、Pytest 参数、JUnit 输出、
Allure Results/HTML 以及每次运行的 ``run.json`` 元数据统一组织起来。业务开发者
优先通过 ``python run.py ...`` 启动测试，而不是在不同环境中手工拼装复杂的
Pytest 命令。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pytest

from core.config_manager import ConfigManager
from utils.project_paths import PROJECT_ROOT

_LEVELS = ("smoke", "core", "regression")


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
    config = ConfigManager().load(env_name, cli_overrides=cli_overrides)
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
    exit_code = int(pytest.main(args))

    html_generated = False
    if allure_enabled and not collect_only:
        try:
            html_generated = _generate_allure_html(results, report)
        except subprocess.CalledProcessError:
            # HTML 展示属于报告增强，不覆盖 Pytest 的真实测试退出码。
            html_generated = False

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
