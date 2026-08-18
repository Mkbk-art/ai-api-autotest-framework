"""Runner 退出码、JUnit 与运行元数据证据的集成测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys
import uuid


def test_zero_collected_tests_returns_nonzero_and_writes_metadata(tmp_path):
    empty_suite = tmp_path / "empty"
    empty_suite.mkdir()
    run_id = f"no-tests-{uuid.uuid4().hex}"
    junit = tmp_path / "empty.xml"
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [
            sys.executable,
            "run.py",
            "--env",
            "test",
            "--test-path",
            str(empty_suite),
            "--run-id",
            run_id,
            "--junitxml",
            str(junit),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 5, result.stdout + result.stderr
    metadata_path = project_root / "reports" / "runs" / run_id / "run.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["pytest_exit_code"] == 5
    assert metadata["junit_xml"] == str(junit)
    expected_allure = importlib.util.find_spec("allure_pytest") is not None
    assert metadata["allure_plugin_available"] is expected_allure
    allure_arg_present = any(
        argument.startswith("--alluredir=") for argument in metadata["pytest_args"]
    )
    assert allure_arg_present is expected_allure
    assert (metadata["allure_results"] is not None) is expected_allure
    shutil.rmtree(metadata_path.parent, ignore_errors=True)
