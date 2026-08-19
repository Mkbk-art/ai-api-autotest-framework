"""Stage 7.1 FailureEvidence Builder 的 TDD 测试。"""
from pathlib import Path

import pytest

from ai.failure_analyzer import (
    FailureArtifactError,
    NoFailureEvidence,
    build_failure_evidence,
)

# 所有历史故障 fixture 都是脱敏/泛化后的本地样例，不依赖真实 SUT 在线运行。
FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "ai"


def test_build_failure_evidence_reads_run_and_junit():
    """run.json 与 JUnit 应被转换成稳定、可引用的确定性证据。"""
    evidence = build_failure_evidence(FIXTURE_ROOT / "auth_failure")

    assert evidence.run_id == "jenkins-history-auth"
    assert evidence.environment == "example-real-sut"
    assert evidence.level == "smoke"
    assert evidence.pytest_exit_code == 1
    assert evidence.summary == {"failed": 1, "errors": 5}
    assert len(evidence.failure_cases) == 6
    assert [fact.id for fact in evidence.facts] == [
        "F1", "F2", "F3", "F4", "F5", "F6", "F7"
    ]


def test_build_failure_evidence_never_exposes_fixture_secrets():
    """JUnit 文本中的故意植入 secret 必须在进入 Evidence 前消失。"""
    evidence = build_failure_evidence(FIXTURE_ROOT / "auth_failure")
    combined = repr(evidence)

    password_sentinel = "SECRET_" + "SENTINEL_PASSWORD"
    token_sentinel = "SECRET_" + "SENTINEL_TOKEN"
    assert password_sentinel not in combined
    assert token_sentinel not in combined


def test_build_failure_evidence_missing_junit_is_explicit(tmp_path):
    """缺失 junit.xml 是输入 Artifact 错误，不允许静默生成空分析。"""
    (tmp_path / "run.json").write_text(
        '{"run_id":"x","environment":"test","level":"smoke","pytest_exit_code":1}',
        encoding="utf-8",
    )

    with pytest.raises(FailureArtifactError, match="junit.xml"):
        build_failure_evidence(tmp_path)


def test_build_failure_evidence_with_no_failed_cases_does_not_need_ai(tmp_path):
    """JUnit 没有 failure/error 时，失败分析应明确停止而不是调用模型。"""
    (tmp_path / "run.json").write_text(
        '{"run_id":"x","environment":"test","level":"smoke","pytest_exit_code":0}',
        encoding="utf-8",
    )
    (tmp_path / "junit.xml").write_text(
        '<testsuites tests="1" failures="0" errors="0"><testsuite><testcase classname="x" name="ok"/></testsuite></testsuites>',
        encoding="utf-8",
    )

    with pytest.raises(NoFailureEvidence):
        build_failure_evidence(tmp_path)
