"""Stage 7.1 独立 AI CLI 的 TDD 测试。"""
import json
from pathlib import Path

from ai.cli import main

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "ai"


def _copy_auth_fixture(tmp_path):
    """复制历史失败输入，避免 CLI 生成 Artifact 污染仓库 fixture。"""
    source = FIXTURE_ROOT / "auth_failure"
    for name in ("run.json", "junit.xml"):
        (tmp_path / name).write_bytes((source / name).read_bytes())


def test_cli_no_ai_generates_deterministic_artifacts(tmp_path, capsys):
    """--no-ai 应只生成确定性证据，并以 0 表示分析命令执行成功。"""
    _copy_auth_fixture(tmp_path)

    exit_code = main(["analyze", "--run-dir", str(tmp_path), "--no-ai"])

    assert exit_code == 0
    payload = json.loads(
        (tmp_path / "ai-analysis" / "analysis.json").read_text(encoding="utf-8")
    )
    assert payload["ai_status"] == "unavailable"
    output = capsys.readouterr().out
    assert "SECRET_SENTINEL" not in output
    assert "ai_status=unavailable" in output


def test_cli_missing_artifacts_returns_input_failure(tmp_path, capsys):
    """输入目录缺失 run.json/junit.xml 时返回 2，并给出简洁 stderr。"""
    exit_code = main(["analyze", "--run-dir", str(tmp_path), "--no-ai"])

    assert exit_code == 2
    assert "run.json" in capsys.readouterr().err
