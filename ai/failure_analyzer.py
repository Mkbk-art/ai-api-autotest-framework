"""基于测试运行 Artifact 构建确定性失败证据，并编排可选 AI 分析。

Stage 7.1 的第一原则是“不让模型定义事实”。本模块先从 ``run.json`` 和 ``junit.xml``
提取失败用例、计数和原始 Pytest 退出码，完成文本脱敏和长度限制后生成 FailureEvidence。
后续 AI 只消费这里的安全证据；当前文件不理解任何具体被测系统业务。
"""
from __future__ import annotations

# json 读取 run.py 已经生成的机器可读运行元数据；不会读取私有环境 YAML。
import json
# ElementTree 足够解析 Pytest JUnit XML，避免为 Stage 7.1 增加新的第三方 XML 依赖。
import xml.etree.ElementTree as ET
# Path 统一处理本地、Jenkins、GitHub Actions 中的 run Artifact 路径。
from pathlib import Path
# Any 用于后续编排结果字典；Evidence 数据主体仍使用强约束 dataclass。
from typing import Any

# Contracts 明确隔离“确定性事实”和未来的“模型推测”。
from ai.client import AIClient
from ai.contracts import (
    FailureCase,
    FailureEvidence,
    FailureFact,
    evidence_to_dict,
    validate_model_analysis,
)
# 自由文本必须在进入 Evidence 前脱敏；模型层不会再接触原始 JUnit 文本。
from utils.sanitizer import sanitize_text


# JUnit message 只保留诊断摘要，防止极端异常把模型输入撑得过大。
_MAX_MESSAGE_CHARS = 2000
# traceback 允许更长上下文，但仍设置硬上限，控制 Token 成本和泄密面。
_MAX_TRACEBACK_CHARS = 6000


class FailureArtifactError(RuntimeError):
    """表示 run Artifact 缺失或结构非法，调用者应停止当前分析。"""


class NoFailureEvidence(RuntimeError):
    """表示 JUnit 没有 failure/error，因此没有失败需要交给 AI。"""


def _trim(text: str, maximum: int) -> str:
    """先脱敏再截断失败文本，避免 secret 留在被截断的一侧。

    Args:
        text: JUnit message/traceback 的原始字符串。
        maximum: 脱敏后允许保留的最大字符数。

    Returns:
        已脱敏并限制长度的字符串。
    """

    # sanitize_text 的顺序必须在截断之前，否则一个 secret 可能跨越截断边界残留。
    safe = sanitize_text(text or "")
    if len(safe) <= maximum:
        return safe
    return safe[:maximum] + "...[truncated]"


def _load_run_metadata(run_path: Path) -> dict[str, Any]:
    """读取并验证 run.json 的 Stage 7.1 所需最小字段。"""

    try:
        raw = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # 输入文件不可读/非法 JSON 都统一提升成 Artifact 层错误，CLI 才能给清晰反馈。
        raise FailureArtifactError(f"invalid run.json: {run_path}") from exc

    if not isinstance(raw, dict):
        raise FailureArtifactError(f"run.json root must be a mapping: {run_path}")

    # environment/run_id 允许历史 Artifact 缺失时回退，但若显式存在则必须是字符串。
    for field in ("run_id", "environment"):
        value = raw.get(field)
        if value is not None and not isinstance(value, str):
            raise FailureArtifactError(f"run.json field {field!r} must be a string")

    level = raw.get("level")
    if level is not None and not isinstance(level, str):
        raise FailureArtifactError("run.json field 'level' must be a string or null")

    # Pytest exit code 来自既有主链，AI 只能读取不能修改；非法值在这里 fail-fast。
    try:
        exit_code = int(raw.get("pytest_exit_code", 1))
    except (TypeError, ValueError) as exc:
        raise FailureArtifactError("run.json field 'pytest_exit_code' must be integer-like") from exc
    raw["pytest_exit_code"] = exit_code
    return raw


def _parse_junit_cases(junit_path: Path) -> list[FailureCase]:
    """从 JUnit 中提取 failure/error，并对所有自由文本先脱敏。"""

    try:
        xml_root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise FailureArtifactError(f"invalid junit.xml: {junit_path}") from exc

    cases: list[FailureCase] = []
    for testcase in xml_root.iter("testcase"):
        # 一条 testcase 正常只会存在 failure 或 error 之一；若两者同时出现，优先保留 failure。
        failure = testcase.find("failure")
        error = testcase.find("error")
        element = failure if failure is not None else error
        if element is None:
            # passed/skipped case 不是失败分析输入，直接跳过。
            continue

        kind = "failure" if failure is not None else "error"
        classname = (testcase.get("classname") or "").strip()
        name = (testcase.get("name") or "").strip()
        # classname 缺失时仍保留 name，避免为了格式差异丢掉真实失败证据。
        nodeid = f"{classname}::{name}" if classname else name

        cases.append(
            FailureCase(
                nodeid=nodeid,
                kind=kind,
                # message 可能为空；空值本身也是允许的 JUnit 状态。
                message=_trim(element.get("message") or "", _MAX_MESSAGE_CHARS),
                # traceback/body 是最容易泄露请求凭据的区域，因此同样强制走 sanitize_text。
                traceback_tail=_trim(element.text or "", _MAX_TRACEBACK_CHARS),
            )
        )
    return cases


def build_failure_evidence(run_dir: str | Path) -> FailureEvidence:
    """读取一次运行的 run.json/junit.xml，生成模型无关的确定性失败证据。

    Args:
        run_dir: 一次测试运行目录，例如 ``reports/runs/jenkins-18``。

    Returns:
        已脱敏、不可变的 FailureEvidence。

    Raises:
        FailureArtifactError: 必需 Artifact 缺失、JSON/XML 非法或元数据类型错误。
        NoFailureEvidence: JUnit 中没有 failure/error。
    """

    root = Path(run_dir).expanduser().resolve()
    run_path = root / "run.json"
    junit_path = root / "junit.xml"

    # 两个 Artifact 都是 Stage 7.1 的确定性输入；缺任意一个都不能凭模型补事实。
    if not run_path.is_file():
        raise FailureArtifactError(f"run.json not found: {run_path}")
    if not junit_path.is_file():
        raise FailureArtifactError(f"junit.xml not found: {junit_path}")

    metadata = _load_run_metadata(run_path)
    cases = _parse_junit_cases(junit_path)
    if not cases:
        # 成功运行不需要“失败分析”；这里也确保后续不会无意义调用付费模型。
        raise NoFailureEvidence("junit.xml contains no failure/error")

    failed = sum(case.kind == "failure" for case in cases)
    errors = sum(case.kind == "error" for case in cases)

    # F1 固定为 run 级总结；后续 Fact ID 顺序完全由 JUnit testcase 顺序决定，便于复现。
    facts: list[FailureFact] = [
        FailureFact(
            id="F1",
            category="run_result",
            text=(
                f"pytest exit_code={metadata['pytest_exit_code']}; "
                f"failed={failed}; errors={errors}"
            ),
            source="run.json+junit.xml",
        )
    ]

    for index, case in enumerate(cases, start=2):
        # 这里只描述“发生了什么”，不解释“为什么发生”；因果推断留给受证据约束的 AI。
        facts.append(
            FailureFact(
                id=f"F{index}",
                category="test_failure",
                text=f"{case.kind}: {case.nodeid}; message={case.message}",
                source="junit.xml",
            )
        )

    # environment/run_id 只使用非敏感逻辑值；外部私有 YAML 路径不会进入 Evidence。
    run_id_value = metadata.get("run_id") or root.name
    environment_value = metadata.get("environment") or "unknown"
    return FailureEvidence(
        schema_version="1.0",
        run_id=run_id_value,
        environment=environment_value,
        level=metadata.get("level"),
        pytest_exit_code=metadata["pytest_exit_code"],
        summary={"failed": failed, "errors": errors},
        facts=tuple(facts),
        failure_cases=tuple(cases),
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """以 UTF-8/缩进 JSON 写入分析 Artifact，便于人读和机器处理。"""

    # ensure_ascii=False 保留中文诊断文本；Artifact 内容在此之前已经完成脱敏和结构校验。
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _base_analysis_payload(evidence: FailureEvidence, status: str) -> dict[str, Any]:
    """构建 analysis.json 的公共确定性部分，避免不同降级分支字段漂移。"""

    safe = evidence_to_dict(evidence)
    return {
        "schema_version": "1.0",
        "ai_status": status,
        # 这些元数据来自既有 run Artifact，不由模型生成。
        "run_id": safe["run_id"],
        "environment": safe["environment"],
        "level": safe["level"],
        "pytest_exit_code": safe["pytest_exit_code"],
        "summary": safe["summary"],
        # Facts 直接复制确定性 Evidence；模型只能通过 evidence_refs 引用它们。
        "facts": safe["facts"],
        "hypotheses": [],
        "next_checks": [],
        "uncertainties": [],
    }


def _render_markdown(result: dict[str, Any]) -> str:
    """把已经校验的分析结果渲染为人类可读 Markdown。

    渲染器不接触 Provider 原始响应，也不尝试二次解释文本；因此 Markdown 与
    ``analysis.json`` 使用同一可信数据源，避免展示层绕过 Validator。
    """

    lines = [
        "# AI Failure Analysis",
        "",
        f"- Run ID: `{result.get('run_id', '')}`",
        f"- Environment: `{result.get('environment', '')}`",
        f"- Level: `{result.get('level', '')}`",
        f"- Pytest exit code: `{result.get('pytest_exit_code', '')}`",
        f"- AI status: `{result.get('ai_status', '')}`",
        "",
        "## Deterministic facts",
        "",
    ]
    facts = result.get("facts") or []
    if facts:
        for fact in facts:
            lines.append(
                f"- **{fact['id']}** [{fact['category']}] {fact['text']} "
                f"(source: {fact['source']})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## AI hypotheses", ""])
    hypotheses = result.get("hypotheses") or []
    if hypotheses:
        for item in hypotheses:
            refs = ", ".join(item["evidence_refs"])
            lines.append(
                f"- **{item['title']}** ({item['confidence']}; evidence: {refs}) — "
                f"{item['reasoning_summary']}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Next checks", ""])
    checks = sorted(result.get("next_checks") or [], key=lambda item: item["priority"])
    if checks:
        for item in checks:
            refs = ", ".join(item["evidence_refs"])
            lines.append(f"{item['priority']}. {item['action']} (evidence: {refs})")
    else:
        lines.append("- None")

    lines.extend(["", "## Uncertainties", ""])
    uncertainties = result.get("uncertainties") or []
    if uncertainties:
        for item in uncertainties:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    # 末尾保留换行，方便 Artifact 在终端/cat 中显示完整。
    return "\n".join(lines) + "\n"


def analyze_run(
    run_dir: str | Path,
    client: AIClient | None = None,
) -> dict[str, Any]:
    """对一次失败测试运行生成安全 Evidence，并可选调用 AI 分析。

    Args:
        run_dir: 已结束测试运行目录，必须包含 ``run.json`` 与 ``junit.xml``。
        client: 可选 Provider Client；``None`` 表示只做确定性证据整理。

    Returns:
        与 ``analysis.json`` 一致的普通字典。

    Notes:
        Provider 的任何失败只改变 ``ai_status``，不会修改原 ``run.json``、JUnit，
        更不会改变原始 Pytest exit code。这是 Stage 7.1 与测试判定主链的硬边界。
    """

    root = Path(run_dir).expanduser().resolve()
    # Evidence Builder 是唯一读取原始测试 Artifact 的位置；它返回时自由文本已完成脱敏。
    evidence = build_failure_evidence(root)
    safe_evidence = evidence_to_dict(evidence)

    output_dir = root / "ai-analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    # evidence.json 永远先写，即使 AI 未配置/超时，仍保留确定性排障材料。
    _write_json(output_dir / "evidence.json", safe_evidence)

    if client is None:
        # 未配置模型是受支持状态，不是异常；普通接口测试框架可完全不依赖 AI。
        result = _base_analysis_payload(evidence, "unavailable")
        result["uncertainties"] = ["AI client is not configured."]
    else:
        try:
            # 传给 Provider 的对象就是已经脱敏并 JSON-safe 的 Evidence，不追加原日志/私有配置。
            raw_model_output = client.analyze_failure(safe_evidence)
            valid_fact_ids = {fact["id"] for fact in safe_evidence["facts"]}
            validated = validate_model_analysis(raw_model_output, valid_fact_ids)

            result = _base_analysis_payload(evidence, "success")
            result.update(validated)
        except ValueError as exc:
            # ValueError 表示 Provider JSON/结构/Fact 引用不符合协议；只记录异常类型，不记录内容。
            result = _base_analysis_payload(evidence, "invalid_model_output")
            result["error_type"] = type(exc).__name__
            result["uncertainties"] = [
                "Model output failed deterministic validation."
            ]
        except Exception as exc:  # noqa: BLE001 - AI 边界必须把第三方运行时故障降级
            # 网络超时、Provider SDK/Session 异常都不能破坏确定性 Evidence 或测试结论。
            # 绝不持久化 str(exc)，因为第三方异常可能回显 URL/Header/Provider response。
            result = _base_analysis_payload(evidence, "error")
            result["error_type"] = type(exc).__name__
            result["uncertainties"] = ["AI analysis was unavailable for this run."]

    # analysis.json 与 Markdown 都只使用受控 result；不会持久化 raw_model_output。
    _write_json(output_dir / "analysis.json", result)
    (output_dir / "analysis.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )
    return result

