"""Stage 7.1 AI 分析编排、降级和 Artifact 的 TDD 测试。"""
import json
from pathlib import Path

from ai.contracts import validate_model_analysis
from ai.failure_analyzer import analyze_run

# 两类真实历史故障都被泛化成离线 fixture，保证测试可公开、可重复。
FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "ai"


class RecordingFakeClient:
    """记录收到的 Evidence，并按测试需要返回合法/非法输出或抛异常。"""

    def __init__(self, payload=None, error=None):
        self.payload = payload or {
            "hypotheses": [
                {
                    "title": "A shared authentication prerequisite may be the main blocker",
                    "confidence": "high",
                    "evidence_refs": ["F1", "F2"],
                    "reasoning_summary": "One direct failure is followed by shared setup errors.",
                }
            ],
            "next_checks": [
                {
                    "priority": 1,
                    "action": "Inspect the shared authentication prerequisite first.",
                    "evidence_refs": ["F2"],
                }
            ],
            "uncertainties": ["The evidence does not include persistent data state."],
        }
        self.error = error
        self.received = None

    def analyze_failure(self, evidence):
        """模拟 Provider 调用，同时保存真正送入模型的结构供安全断言。"""
        self.received = evidence
        if self.error:
            raise self.error
        return self.payload


def _copy_auth_fixture(tmp_path):
    """复制历史认证失败 Artifact，避免分析输出污染仓库 fixture。"""
    source = FIXTURE_ROOT / "auth_failure"
    for name in ("run.json", "junit.xml"):
        (tmp_path / name).write_bytes((source / name).read_bytes())


def test_analyze_run_writes_evidence_and_validated_analysis(tmp_path):
    """合法 Fake AI 输出应生成三类 Artifact，并且模型输入不含 secret sentinel。"""
    _copy_auth_fixture(tmp_path)
    client = RecordingFakeClient()

    result = analyze_run(tmp_path, client=client)

    assert result["ai_status"] == "success"
    assert (tmp_path / "ai-analysis" / "evidence.json").is_file()
    assert (tmp_path / "ai-analysis" / "analysis.json").is_file()
    assert (tmp_path / "ai-analysis" / "analysis.md").is_file()
    assert "SECRET_SENTINEL" not in json.dumps(client.received)


def test_analyze_run_without_client_is_safe_degradation(tmp_path):
    """未配置 Provider 时仍必须保存确定性 Evidence，而不是让分析命令失败。"""
    _copy_auth_fixture(tmp_path)

    result = analyze_run(tmp_path, client=None)

    assert result["ai_status"] == "unavailable"
    assert (tmp_path / "ai-analysis" / "evidence.json").is_file()
    assert (tmp_path / "ai-analysis" / "analysis.json").is_file()


def test_analyze_run_client_exception_is_safe_degradation(tmp_path):
    """模型超时只能降级 AI，Artifact 中不能持久化原异常详情。"""
    _copy_auth_fixture(tmp_path)
    client = RecordingFakeClient(error=TimeoutError("model timeout with secret=do-not-store"))

    result = analyze_run(tmp_path, client=client)

    assert result["ai_status"] == "error"
    assert result["error_type"] == "TimeoutError"
    serialized = (tmp_path / "ai-analysis" / "analysis.json").read_text(encoding="utf-8")
    assert "do-not-store" not in serialized


def test_analyze_run_invalid_fact_reference_is_rejected(tmp_path):
    """模型引用不存在的 Fact 时必须降级为 invalid_model_output。"""
    _copy_auth_fixture(tmp_path)
    client = RecordingFakeClient(
        payload={
            "hypotheses": [
                {
                    "title": "invented",
                    "confidence": "high",
                    "evidence_refs": ["F999"],
                    "reasoning_summary": "invented",
                }
            ],
            "next_checks": [],
            "uncertainties": [],
        }
    )

    result = analyze_run(tmp_path, client=client)

    assert result["ai_status"] == "invalid_model_output"


def test_analyze_run_never_modifies_original_run_metadata(tmp_path):
    """AI 辅助链只能新增 ai-analysis/，不能回写原测试证据。"""
    _copy_auth_fixture(tmp_path)
    before = (tmp_path / "run.json").read_bytes()

    analyze_run(tmp_path, client=RecordingFakeClient())

    assert (tmp_path / "run.json").read_bytes() == before


def test_historical_ci_pollution_analysis_must_cite_ci_facts():
    """第二类真实历史故障用于证明“当前测试成功”和“CI 聚合异常”可以分开表达。"""
    evidence = json.loads(
        (FIXTURE_ROOT / "ci_report_pollution" / "evidence.json").read_text(encoding="utf-8")
    )
    valid_ids = {fact["id"] for fact in evidence["facts"]}
    payload = {
        "hypotheses": [
            {
                "title": "JUnit report aggregation may include stale build reports",
                "confidence": "high",
                "evidence_refs": ["F1", "F2", "F3"],
                "reasoning_summary": "Current tests passed while CI became unstable after broad JUnit publishing.",
            }
        ],
        "next_checks": [
            {
                "priority": 1,
                "action": "Restrict JUnit publishing to the current build run directory.",
                "evidence_refs": ["F2", "F3"],
            }
        ],
        "uncertainties": [],
    }

    result = validate_model_analysis(payload, valid_ids)

    assert result["hypotheses"][0]["evidence_refs"] == ["F1", "F2", "F3"]
    assert "current build" in result["next_checks"][0]["action"].lower()
