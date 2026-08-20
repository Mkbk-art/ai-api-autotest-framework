"""Stage 7.1 V2 独立 AI CLI 的 TDD 测试。

CLI 必须让最终用户直接使用 YAML，同时保留临时参数覆盖；真实 Key 不允许作为普通
命令行参数出现，只能来自 YAML、ENV fallback 或 ``--api-key-prompt`` 隐藏输入。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.cli import _parser, main
from ai.config import AIConfigResolver


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "ai"


def _copy_auth_fixture(tmp_path: Path) -> Path:
    """复制历史失败输入，避免 CLI 生成 Artifact 污染仓库 fixture。"""

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    source = FIXTURE_ROOT / "auth_failure"
    for name in ("run.json", "junit.xml"):
        (run_dir / name).write_bytes((source / name).read_bytes())
    return run_dir


def _write_ai_yaml(project: Path, *, key: str | None = "yaml-secret") -> None:
    """写一份可直接运行的最终用户 YAML；key=None 用于 getpass 覆盖测试。"""

    key_value = "null" if key is None else key
    config_path = project / "config" / "ai.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f"""
ai:
  provider: user-profile
  timeout: 20
  providers:
    user-profile:
      protocol: openai_chat_completions
      base_url: https://yaml.example/v1
      model: yaml-model
      api_key: {key_value}
""".strip()
        + "\n",
        encoding="utf-8",
    )


class RecordingClient:
    """返回严格合法的 AI 分析结果，并记录收到的 Evidence。"""

    def __init__(self):
        self.evidence = None

    def analyze_failure(self, evidence):
        self.evidence = evidence
        return {
            "hypotheses": [
                {
                    "title": "shared prerequisite may be failing",
                    "confidence": "high",
                    "evidence_refs": ["F1"],
                    "reasoning_summary": "The run-level fact confirms a failed run.",
                }
            ],
            "next_checks": [
                {
                    "priority": 1,
                    "action": "Inspect the shared prerequisite first.",
                    "evidence_refs": ["F1"],
                }
            ],
            "uncertainties": [],
        }


def test_cli_no_ai_generates_deterministic_artifacts(tmp_path, capsys):
    """--no-ai 应绕过全部 Provider 配置，只生成确定性 Evidence。"""

    run_dir = _copy_auth_fixture(tmp_path)

    exit_code = main(["analyze", "--run-dir", str(run_dir), "--no-ai"])

    assert exit_code == 0
    payload = json.loads(
        (run_dir / "ai-analysis" / "analysis.json").read_text(encoding="utf-8")
    )
    assert payload["ai_status"] == "unavailable"
    output = capsys.readouterr().out
    assert "SECRET_SENTINEL" not in output
    assert "ai_status=unavailable" in output


def test_cli_reads_project_ai_yaml_without_environment(tmp_path, monkeypatch, capsys):
    """最终用户只写项目 ai.yaml、不配置 AI_* 环境变量也能创建真实 Provider Client。"""

    project = tmp_path / "project"
    _write_ai_yaml(project)
    run_dir = _copy_auth_fixture(tmp_path)
    resolver = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={})
    captured = {}
    fake_client = RecordingClient()

    def fake_create(config):
        captured["config"] = config
        return fake_client

    monkeypatch.setattr("ai.cli.AIClientFactory.create", fake_create)

    exit_code = main(["analyze", "--run-dir", str(run_dir)], resolver=resolver)

    assert exit_code == 0
    assert captured["config"].provider == "user-profile"
    assert captured["config"].model == "yaml-model"
    assert "ai_status=success" in capsys.readouterr().out


def test_cli_model_override_beats_yaml(tmp_path, monkeypatch):
    """--model 是单次运行最高优先级，不需要修改主 YAML。"""

    project = tmp_path / "project"
    _write_ai_yaml(project)
    run_dir = _copy_auth_fixture(tmp_path)
    resolver = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={})
    captured = {}

    def fake_create(config):
        captured["config"] = config
        return RecordingClient()

    monkeypatch.setattr("ai.cli.AIClientFactory.create", fake_create)

    exit_code = main(
        ["analyze", "--run-dir", str(run_dir), "--model", "cli-model"],
        resolver=resolver,
    )

    assert exit_code == 0
    assert captured["config"].model == "cli-model"


def test_cli_api_key_prompt_uses_getpass_not_argument(tmp_path, monkeypatch, capsys):
    """控制台临时 Key 必须通过 getpass 隐藏输入，并覆盖 YAML/ENV。"""

    project = tmp_path / "project"
    _write_ai_yaml(project, key=None)
    run_dir = _copy_auth_fixture(tmp_path)
    resolver = AIConfigResolver(
        project_root=project,
        home_dir=tmp_path / "home",
        environ={"AI_API_KEY": "env-secret"},
    )
    captured = {}

    monkeypatch.setattr("ai.cli.getpass.getpass", lambda prompt: "prompt-secret")

    def fake_create(config):
        captured["config"] = config
        return RecordingClient()

    monkeypatch.setattr("ai.cli.AIClientFactory.create", fake_create)

    exit_code = main(
        ["analyze", "--run-dir", str(run_dir), "--api-key-prompt"],
        resolver=resolver,
    )

    assert exit_code == 0
    assert captured["config"].api_key == "prompt-secret"
    console = capsys.readouterr()
    assert "prompt-secret" not in console.out
    assert "prompt-secret" not in console.err


def test_parser_has_no_plain_api_key_argument(capsys):
    """显式 --api-key VALUE 必须被 argparse 拒绝，防止 Secret 进入 shell history。"""

    with pytest.raises(SystemExit) as exc_info:
        _parser().parse_args(
            ["analyze", "--run-dir", "somewhere", "--api-key", "visible-secret"]
        )

    assert exc_info.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_cli_unconfigured_ai_degrades_to_unavailable(tmp_path, capsys):
    """主 YAML provider=null 时分析仍成功生成 Evidence，只把 AI 状态标为 unavailable。"""

    project = tmp_path / "project"
    _write_ai_yaml(project)
    # 覆盖为显式未配置状态，模拟公共仓库默认 ai.yaml。
    (project / "config" / "ai.yaml").write_text(
        "ai:\n  provider: null\n  timeout: 20\n  providers: {}\n",
        encoding="utf-8",
    )
    run_dir = _copy_auth_fixture(tmp_path)
    resolver = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={})

    exit_code = main(["analyze", "--run-dir", str(run_dir)], resolver=resolver)

    assert exit_code == 0
    assert "ai_status=unavailable" in capsys.readouterr().out


def test_cli_invalid_ai_config_returns_2_without_secret(tmp_path, capsys):
    """已选 Provider 配置残缺时明确返回 2，stderr 不能回显 YAML 中已有 Secret。"""

    project = tmp_path / "project"
    config_path = project / "config" / "ai.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
ai:
  provider: broken
  providers:
    broken:
      protocol: openai_chat_completions
      api_key: should-never-print
""".strip()
        + "\n",
        encoding="utf-8",
    )
    run_dir = _copy_auth_fixture(tmp_path)
    resolver = AIConfigResolver(project_root=project, home_dir=tmp_path / "home", environ={})

    exit_code = main(["analyze", "--run-dir", str(run_dir)], resolver=resolver)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "base_url" in captured.err
    assert "should-never-print" not in captured.err
    assert "should-never-print" not in captured.out


def test_cli_missing_artifacts_returns_input_failure(tmp_path, capsys):
    """输入目录缺失 run.json/junit.xml 时返回 2，并给出简洁 stderr。"""

    exit_code = main(["analyze", "--run-dir", str(tmp_path), "--no-ai"])

    assert exit_code == 2
    assert "run.json" in capsys.readouterr().err
