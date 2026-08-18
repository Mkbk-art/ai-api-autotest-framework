"""不同运行环境的业务用例收集隔离测试。

本模块保护 Stage 3 Mock Demo 与 Stage 4 真实短链接业务用例之间的边界：
``test`` 环境只收集 Demo，``shortlink-local`` 只收集真实短链接用例，避免错误
环境中的用例被意外执行。
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _collect_for_environment(
    env_name: str,
    run_id: str,
    *,
    level: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """通过统一 Runner 收集指定环境/层级的业务用例，不真正发送网络请求。"""
    environment = os.environ.copy()
    # 外部 Shell 中可能残留 API_* 变量；集成测试必须只验证命名环境文件本身。
    for name in ("API_TEST_ENV", "API_HOST", "API_TIMEOUT", "API_VERIFY_SSL", "API_USE_MOCK"):
        environment.pop(name, None)
    # 基础参数始终只做 collection；真实业务请求不会在 collect-only 阶段执行。
    command = [
        sys.executable,
        "run.py",
        "--env",
        env_name,
        "--test-path",
        "testcases",
        "--collect-only",
        "--run-id",
        run_id,
    ]
    # 指定 level 时额外验证 smoke/core 等 marker 分层；未指定则检查该环境全部业务用例。
    if level is not None:
        command.extend(["--level", level])

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    shutil.rmtree(PROJECT_ROOT / "reports" / "runs" / run_id, ignore_errors=True)
    return result


def test_test_environment_collects_only_six_demo_cases():
    """Stage 3 Mock 环境继续只暴露 6 条 Demo 业务用例。"""
    result = _collect_for_environment("test", "collect-demo")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 tests collected" in result.stdout, result.stdout


def test_shortlink_local_environment_collects_only_real_business_cases():
    """真实环境应收集 6 条 Smoke + 6 条 Core + 6 条 Stage 5 Regression，共 18 条且不混入 Demo。"""
    result = _collect_for_environment("shortlink-local", "collect-shortlink")
    assert result.returncode == 0, result.stdout + result.stderr
    # 使用完整 ``collected 18 items`` 边界，避免子串匹配把旧数量误判为当前集合。
    assert "collected 18 items" in result.stdout, result.stdout
    assert "testcases/demo" not in result.stdout
    assert "test_login[base_info" not in result.stdout
    assert "test_publish_api[base_info" not in result.stdout
    assert "test_call_api[base_info" not in result.stdout


def test_shortlink_smoke_level_remains_six_happy_path_cases():
    """YAML ``level=smoke`` 必须只选择六条已真实验证的成功主链。"""
    result = _collect_for_environment("shortlink-local", "collect-shortlink-smoke", level="smoke")
    assert result.returncode == 0, result.stdout + result.stderr
    # 总集合保持 18 条；marker 已从每个 YAML Case 的 level 元数据自动转换。
    assert "collected 18 items / 12 deselected / 6 selected" in result.stdout, result.stdout
    # 短链接项目按业务域合并 Python 入口，Smoke 不再依赖“一 Case 一文件”的旧结构。
    for module_name in ("test_auth.py", "test_link.py", "test_redirect.py", "test_statistics.py"):
        assert module_name in result.stdout


def test_shortlink_core_level_collects_six_yaml_negative_cases():
    """YAML ``level=core`` 必须收集六条鉴权、输入、notfound 与回收状态异常 Case。"""
    result = _collect_for_environment("shortlink-local", "collect-shortlink-core", level="core")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "collected 18 items / 12 deselected / 6 selected" in result.stdout, result.stdout
    # Core 的六条异常现在归并到认证、链接、跳转三个业务域入口中。
    for module_name in ("test_auth.py", "test_link.py", "test_redirect.py"):
        assert module_name in result.stdout
    # Statistics 当前没有 Core 异常 Case，因此不应该为了文件数量人为混入本层。
    assert "<Module test_statistics.py>" not in result.stdout


def test_shortlink_regression_level_collects_six_yaml_data_source_cases():
    """YAML ``level=regression`` 必须选择六条 MySQL/Redis 深层一致性 Case。"""
    result = _collect_for_environment("shortlink-local", "collect-shortlink-regression", level="regression")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "collected 18 items / 12 deselected / 6 selected" in result.stdout, result.stdout
    # 数据源断言分布在真实业务域 YAML 中，而不是另建 Stage5 专用测试脚本。
    for module_name in ("test_auth.py", "test_link.py", "test_redirect.py", "test_statistics.py"):
        assert module_name in result.stdout
    assert "test_stage5_mysql.py" not in result.stdout
    assert "test_stage5_redis.py" not in result.stdout
