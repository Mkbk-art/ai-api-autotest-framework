"""Stage 7.1 AI 数据契约的 TDD 测试。

本文件只验证结构化证据与模型输出校验，不调用任何真实模型服务，确保公共 CI 可重复。
"""
import pytest

from ai.contracts import (
    FailureCase,
    FailureEvidence,
    FailureFact,
    evidence_to_dict,
    validate_model_analysis,
)


def test_failure_evidence_serializes_stable_schema():
    """确定性证据必须稳定序列化为 JSON 可写的普通字典。"""
    evidence = FailureEvidence(
        schema_version="1.0",
        run_id="run-1",
        environment="test",
        level="smoke",
        pytest_exit_code=1,
        summary={"failed": 1, "errors": 0},
        facts=(
            FailureFact(
                id="F1",
                category="test_result",
                text="one test failed",
                source="junit.xml",
            ),
        ),
        failure_cases=(
            FailureCase(
                nodeid="tests/test_demo.py::test_x",
                kind="failure",
                message="assert 1 == 2",
                traceback_tail="AssertionError",
            ),
        ),
    )

    payload = evidence_to_dict(evidence)

    assert payload["schema_version"] == "1.0"
    assert payload["facts"][0]["id"] == "F1"
    assert payload["failure_cases"][0]["kind"] == "failure"


def test_validate_model_analysis_accepts_fact_bound_output():
    """AI 只要结构合法且引用真实 Fact，就允许进入后续 Artifact。"""
    payload = {
        "hypotheses": [
            {
                "title": "shared setup may be failing",
                "confidence": "high",
                "evidence_refs": ["F1"],
                "reasoning_summary": "The observed failure is referenced directly.",
            }
        ],
        "next_checks": [
            {
                "priority": 1,
                "action": "inspect the shared setup",
                "evidence_refs": ["F1"],
            }
        ],
        "uncertainties": ["The current evidence does not include database state."],
    }

    result = validate_model_analysis(payload, {"F1"})

    assert result["hypotheses"][0]["confidence"] == "high"


@pytest.mark.parametrize("confidence", ["certain", "", "HIGH"])
def test_validate_model_analysis_rejects_unknown_confidence(confidence):
    """置信度使用固定枚举，避免模型自由文本破坏下游展示与比较。"""
    payload = {
        "hypotheses": [
            {
                "title": "bad",
                "confidence": confidence,
                "evidence_refs": ["F1"],
                "reasoning_summary": "bad",
            }
        ],
        "next_checks": [],
        "uncertainties": [],
    }

    with pytest.raises(ValueError, match="confidence"):
        validate_model_analysis(payload, {"F1"})


def test_validate_model_analysis_rejects_unknown_fact_reference():
    """模型不得凭空引用不存在的证据编号。"""
    payload = {
        "hypotheses": [
            {
                "title": "invented evidence",
                "confidence": "low",
                "evidence_refs": ["F99"],
                "reasoning_summary": "unsupported",
            }
        ],
        "next_checks": [],
        "uncertainties": [],
    }

    with pytest.raises(ValueError, match="F99"):
        validate_model_analysis(payload, {"F1"})


def test_validate_model_analysis_rejects_hypothesis_without_fact():
    """每条假设都必须绑定至少一条确定性 Fact。"""
    payload = {
        "hypotheses": [
            {
                "title": "unsupported",
                "confidence": "low",
                "evidence_refs": [],
                "reasoning_summary": "unsupported",
            }
        ],
        "next_checks": [],
        "uncertainties": [],
    }

    with pytest.raises(ValueError, match="evidence_refs"):
        validate_model_analysis(payload, {"F1"})


def test_validate_model_analysis_rejects_non_positive_priority():
    """排查建议优先级必须是正整数，便于 CLI/Markdown 稳定排序。"""
    payload = {
        "hypotheses": [],
        "next_checks": [
            {"priority": 0, "action": "bad", "evidence_refs": ["F1"]}
        ],
        "uncertainties": [],
    }

    with pytest.raises(ValueError, match="priority"):
        validate_model_analysis(payload, {"F1"})
