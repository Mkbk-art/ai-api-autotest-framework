"""AI 失败分析的数据契约与确定性校验。

本模块把“确定性事实”和“模型推测”明确分开：FailureEvidence 由本地代码生成，
模型只能返回 hypotheses / next_checks / uncertainties，并且必须引用真实 Fact ID。
这里不做网络请求，也不理解任何具体 SUT，因而可以被所有项目适配层复用。
"""
from __future__ import annotations

# dataclass 让证据对象保持简单可审计；frozen=True 防止进入 AI 阶段后被意外改写。
from dataclasses import asdict, dataclass
# Any 用于接收不可信模型 JSON；校验完成前不假设它具有固定结构。
from typing import Any


@dataclass(frozen=True)
class FailureFact:
    """由确定性代码生成、允许 AI 引用但不允许 AI 改写的一条事实。"""

    # id 是跨 facts/hypotheses 的稳定证据引用键，例如 F1/F2。
    id: str
    # category 只表达通用事实类别，例如 run_result/test_failure。
    category: str
    # text 是已经脱敏后的可读事实，不包含真实密码、Token 等敏感值。
    text: str
    # source 标记事实来源，便于人类判断证据可信边界。
    source: str


@dataclass(frozen=True)
class FailureCase:
    """一条从 JUnit 中提取出的 failure/error 失败证据。"""

    # nodeid 由 classname + testcase name 规范化得到，用于定位失败用例。
    nodeid: str
    # kind 目前只允许上游 Evidence Builder 写入 failure 或 error。
    kind: str
    # message 是 JUnit failure/error 的简要原因，进入本对象前必须完成脱敏。
    message: str
    # traceback_tail 保存有限长度的失败文本，便于 AI 看上下文但控制 Token 与泄密面。
    traceback_tail: str


@dataclass(frozen=True)
class FailureEvidence:
    """一次测试运行供 AI 使用的安全结构化证据。"""

    # schema_version 为后续演进保留兼容边界；Stage 7.1 固定使用 1.0。
    schema_version: str
    # run_id 对应 reports/runs/<run_id>，不包含任何凭据。
    run_id: str
    # environment 只记录逻辑环境名，不记录外部私有 YAML 路径。
    environment: str
    # level 对应 smoke/core/regression；历史 Artifact 缺失时允许 None。
    level: str | None
    # pytest_exit_code 是既有测试结论的原始退出码，AI 不得修改。
    pytest_exit_code: int
    # summary 只保存 failed/errors 等确定性计数。
    summary: dict[str, int]
    # facts 是 AI 唯一允许引用的事实集合。
    facts: tuple[FailureFact, ...]
    # failure_cases 保存更细粒度但仍已脱敏的 JUnit 上下文。
    failure_cases: tuple[FailureCase, ...]


def evidence_to_dict(evidence: FailureEvidence) -> dict[str, Any]:
    """把不可变 Evidence 转换成可直接 JSON 序列化的普通字典。

    ``dataclasses.asdict`` 会递归复制嵌套 dataclass，因此调用者无法通过修改返回值
    反向修改原始 Evidence，这一点对“事实不可被 AI 覆盖”的边界很重要。
    """

    return asdict(evidence)


def _require_non_empty_string(value: Any, field: str) -> str:
    """校验模型返回的必填文本，并统一去除首尾空白。"""

    # 模型输出属于不可信输入：类型不对或只有空白都直接拒绝，不做自动猜测/修复。
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_refs(value: Any, valid_fact_ids: set[str], field: str) -> list[str]:
    """校验证据引用必须非空，而且每个引用都指向真实 Fact ID。"""

    # hypothesis/next_check 没有证据引用就无法区分“证据驱动分析”和“模型自由发挥”。
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}.evidence_refs must be a non-empty list")

    refs: list[str] = []
    for item in value:
        # 每个引用先做字符串校验，再检查是否属于本次 Evidence 的真实 ID 集合。
        ref = _require_non_empty_string(item, f"{field}.evidence_refs")
        if ref not in valid_fact_ids:
            raise ValueError(f"unknown fact reference: {ref}")
        refs.append(ref)
    return refs


def validate_model_analysis(payload: object, valid_fact_ids: set[str]) -> dict[str, Any]:
    """严格校验 AI 返回的分析 JSON，并返回规范化副本。

    该函数故意不尝试“修 JSON”或猜字段：非法结构会明确抛 ``ValueError``，
    上层 FailureAnalyzer 再把它降级为 ``invalid_model_output``。这样可以避免模型输出
    看似成功但实际上突破证据约束。
    """

    # 顶层必须是 JSON Object/Mapping；字符串、列表都不是合法 Stage 7.1 协议。
    if not isinstance(payload, dict):
        raise ValueError("model analysis must be a mapping")

    hypotheses = payload.get("hypotheses")
    next_checks = payload.get("next_checks")
    uncertainties = payload.get("uncertainties")

    # 三个顶层字段必须全部存在且是列表，避免下游 Markdown/JSON 需要猜默认结构。
    if not isinstance(hypotheses, list):
        raise ValueError("hypotheses must be a list")
    if not isinstance(next_checks, list):
        raise ValueError("next_checks must be a list")
    if not isinstance(uncertainties, list):
        raise ValueError("uncertainties must be a list")

    clean_hypotheses: list[dict[str, Any]] = []
    for index, item in enumerate(hypotheses):
        # 每条 hypothesis 都必须是 Object；否则不能安全读取 title/confidence 等字段。
        if not isinstance(item, dict):
            raise ValueError(f"hypotheses[{index}] must be a mapping")

        confidence = item.get("confidence")
        # 固定枚举既减少模型自由度，也让报告层能稳定排序/展示。
        if confidence not in {"low", "medium", "high"}:
            raise ValueError(f"hypotheses[{index}].confidence is invalid")

        clean_hypotheses.append(
            {
                "title": _require_non_empty_string(
                    item.get("title"), f"hypotheses[{index}].title"
                ),
                "confidence": confidence,
                "evidence_refs": _validate_refs(
                    item.get("evidence_refs"),
                    valid_fact_ids,
                    f"hypotheses[{index}]",
                ),
                "reasoning_summary": _require_non_empty_string(
                    item.get("reasoning_summary"),
                    f"hypotheses[{index}].reasoning_summary",
                ),
            }
        )

    clean_checks: list[dict[str, Any]] = []
    for index, item in enumerate(next_checks):
        # 排查建议同样是受控结构，而不是任意 Markdown 文本。
        if not isinstance(item, dict):
            raise ValueError(f"next_checks[{index}] must be a mapping")

        priority = item.get("priority")
        # bool 是 int 的子类，因此必须显式排除 True/False。
        if not isinstance(priority, int) or isinstance(priority, bool) or priority <= 0:
            raise ValueError(f"next_checks[{index}].priority must be a positive integer")

        clean_checks.append(
            {
                "priority": priority,
                "action": _require_non_empty_string(
                    item.get("action"), f"next_checks[{index}].action"
                ),
                "evidence_refs": _validate_refs(
                    item.get("evidence_refs"),
                    valid_fact_ids,
                    f"next_checks[{index}]",
                ),
            }
        )

    # uncertainties 允许为空，但每个存在的元素仍必须是非空文本。
    clean_uncertainties = [
        _require_non_empty_string(item, f"uncertainties[{index}]")
        for index, item in enumerate(uncertainties)
    ]

    # 返回新对象而不是原 payload，保证后续 Artifact 只包含已经校验过的字段。
    return {
        "hypotheses": clean_hypotheses,
        "next_checks": clean_checks,
        "uncertainties": clean_uncertainties,
    }
