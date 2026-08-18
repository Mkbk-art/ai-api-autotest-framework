"""smoke/core/regression 三个 marker 独立执行能力的集成测试。

本模块用于保护已验证框架行为，防止后续重构引入回归。
"""
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.parametrize("level", ["smoke", "core", "regression"])
def test_each_marker_level_runs_independently(level, tmp_path):
    junit = tmp_path / f"{level}.xml"
    project_root = Path(__file__).resolve().parents[2]
    run_id = f"integration-{level}"
    result = subprocess.run(
        [
            sys.executable,
            "run.py",
            "--env",
            "test",
            "--level",
            level,
            "--run-id",
            run_id,
            "--junitxml",
            str(junit),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    root = ET.parse(junit).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    assert suite is not None
    assert int(suite.attrib.get("tests", "0")) > 0
    assert int(suite.attrib.get("failures", "0")) == 0
    assert int(suite.attrib.get("errors", "0")) == 0
    shutil.rmtree(project_root / "reports" / "runs" / run_id, ignore_errors=True)
