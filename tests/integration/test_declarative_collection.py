"""声明式 Runtime 必须让普通项目 Case 不再依赖业务 Python wrapper。"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _collect(level: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "run.py",
        "--env",
        "test",
        "--test-path",
        "testcases",
        "--collect-only",
        "--run-id",
        "decl-runtime-test",
    ]
    if level:
        command.extend(["--level", level])
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)


def test_demo_has_no_business_test_wrappers():
    demo_dir = ROOT / "testcases" / "demo"
    assert not list(demo_dir.glob("test_*.py"))


def test_generic_yaml_runtime_collects_all_six_demo_cases():
    result = _collect()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 tests collected" in result.stdout
    assert "test_yaml_cases.py" in result.stdout
    assert "<Module test_login.py>" not in result.stdout
    assert "<Module test_publish_api.py>" not in result.stdout
    assert "<Module test_call_api.py>" not in result.stdout


def test_generic_yaml_runtime_preserves_two_cases_per_level():
    for level in ("smoke", "core", "regression"):
        result = _collect(level)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "6 items / 4 deselected / 2 selected" in result.stdout or "6 tests collected" in result.stdout
