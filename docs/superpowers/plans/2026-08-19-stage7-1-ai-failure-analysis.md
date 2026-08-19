# Stage 7.1 AI Failure Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 AI 辅助接口自动化测试框架增加一个与真实 SUT 解耦、可选、可降级、可审计的 AI 失败日志分析子系统。

**Architecture:** 现有 `run.py -> Pytest -> JUnit/run.json` 主链保持不变；新增独立 `ai/` 包从已完成运行的 Artifact 构建确定性 `FailureEvidence`，先脱敏，再通过 Provider 无关 `AIClient` 调用模型，最后严格校验 hypothesis 对 Fact ID 的引用并输出 `evidence.json / analysis.json / analysis.md`。AI 无 Key、超时、HTTP 错误或非法输出时只降级 AI 分析，不改变测试原始 exit code。

**Tech Stack:** Python 3.11+、stdlib `dataclasses/json/xml.etree.ElementTree/pathlib/re`、Requests、Pytest 9、现有 `utils.sanitizer`。

**Spec:** `docs/superpowers/specs/2026-08-19-stage7-1-ai-failure-analysis-design.md`

## Global Constraints

- 项目主体必须继续是“AI 辅助接口自动化测试框架”，Shortlink 只能作为真实 SUT 示例。
- `ai/` production code 禁止出现 `/api/short-link`、`shortlink-local`、`nurl.ink`、Shortlink 表名或 Redis Key 前缀。
- AI 不能决定或覆盖 Pytest / AssertionEngine 的 PASS/FAIL。
- 第一版不修改 `run.py` 默认测试执行语义，不把 AI 嵌入 Pytest hooks。
- 所有进入模型的数据必须先经过结构化脱敏和文本脱敏。
- AI 输出中的每条 hypothesis 至少引用一个存在的 Fact ID。
- 无 Client/Key、Timeout、HTTP Error、非法 JSON、非法 Fact 引用均必须安全降级。
- 公共 GitHub Actions 不依赖真实 AI Key。
- AI API Key 只来自 OS 环境变量或 Secret Store，不进入 Git、公共 YAML、run.json、evidence.json、analysis.json 或 Artifact。
- 新增/修改的 Python 文件继续使用高密度中文注释：模块 docstring、重要 imports、函数 docstring、关键变量、分支、异常、边界和安全原因都必须说明。
- 不提前实现 Stage 7.2 YAML 草稿生成。
- 不增加 Pydantic 等新运行时依赖；结构校验使用标准库，真实 HTTP Provider 复用现有 `requests`。
- `utils/sanitizer.py` 继续是唯一脱敏实现，不新增重复 sanitizer。
- 测试使用 Fake Client/Fake Session，不在公共测试中调用真实模型网络。

---

## File Structure

### Create

- `ai/__init__.py`
- `ai/contracts.py`
- `ai/failure_analyzer.py`
- `ai/client.py`
- `ai/cli.py`
- `tests/ai/test_contracts.py`
- `tests/ai/test_sanitizer_text.py`
- `tests/ai/test_failure_evidence.py`
- `tests/ai/test_failure_analyzer.py`
- `tests/ai/test_ai_client.py`
- `tests/ai/test_ai_cli.py`
- `tests/fixtures/ai/auth_failure/run.json`
- `tests/fixtures/ai/auth_failure/junit.xml`
- `tests/fixtures/ai/ci_report_pollution/evidence.json`
- `docs/11_AI失败分析接入说明.md`
- `docs/superpowers/specs/2026-08-19-stage7-1-ai-failure-analysis-design.md`
- `docs/superpowers/plans/2026-08-19-stage7-1-ai-failure-analysis.md`

### Modify

- `utils/sanitizer.py`
- `.env.example`
- `pyproject.toml`
- `README.md`
- `AI_API_Autotest_Framework_Project_Plan_Latest.md`

---

### Task 1: 建立 AI Contracts 与严格输出校验

**Files:**
- Create: `ai/__init__.py`
- Create: `ai/contracts.py`
- Test: `tests/ai/test_contracts.py`

**Interfaces:**
- Produces:
  - `FailureFact(id: str, category: str, text: str, source: str)`
  - `FailureCase(nodeid: str, kind: str, message: str, traceback_tail: str)`
  - `FailureEvidence(schema_version: str, run_id: str, environment: str, level: str | None, pytest_exit_code: int, summary: dict[str, int], facts: tuple[FailureFact, ...], failure_cases: tuple[FailureCase, ...])`
  - `validate_model_analysis(payload: object, valid_fact_ids: set[str]) -> dict[str, object]`
  - `evidence_to_dict(evidence: FailureEvidence) -> dict[str, object]`

- [ ] **Step 1: Write the failing contract tests**

```python
import pytest

from ai.contracts import (
    FailureCase,
    FailureEvidence,
    FailureFact,
    evidence_to_dict,
    validate_model_analysis,
)


def test_failure_evidence_serializes_stable_schema():
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
    payload = {
        "hypotheses": [],
        "next_checks": [
            {"priority": 0, "action": "bad", "evidence_refs": ["F1"]}
        ],
        "uncertainties": [],
    }
    with pytest.raises(ValueError, match="priority"):
        validate_model_analysis(payload, {"F1"})
```

- [ ] **Step 2: Run the tests and verify RED**

```bash
python -m pytest tests/ai/test_contracts.py -q
```

Expected: `ModuleNotFoundError: No module named 'ai'`.

- [ ] **Step 3: Implement minimal contracts**

`ai/contracts.py` 必须使用不可变 dataclass；`validate_model_analysis()` 只能接受：
- `confidence in {"low","medium","high"}`
- hypothesis 非空 `evidence_refs`
- refs 全部属于 `valid_fact_ids`
- `next_checks.priority` 为正整数
- 所有必填文本为非空字符串

不得自动修复非法模型结构。

- [ ] **Step 4: Run contract tests and verify GREEN**

```bash
python -m pytest tests/ai/test_contracts.py -q
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/__init__.py ai/contracts.py tests/ai/test_contracts.py
git commit -m "feat: define AI failure analysis contracts"
```

---

### Task 2: 在唯一 Sanitizer 中增加文本级脱敏

**Files:**
- Modify: `utils/sanitizer.py`
- Create: `tests/ai/test_sanitizer_text.py`

**Interfaces:**
- Consumes: existing `sanitize(value: Any) -> Any`
- Produces: `sanitize_text(text: str) -> str`

- [ ] **Step 1: Write failing sanitizer tests**

```python
from utils.sanitizer import sanitize_text


def test_sanitize_text_masks_common_secrets_and_personal_data():
    raw = (
        "Authorization: Bearer secret-bearer-123\n"
        "token=secret-token-456\n"
        "password=secret-password-789\n"
        "Cookie: session=secret-cookie\n"
        "api_key=secret-key\n"
        "email=user@example.com phone=13812345678"
    )
    safe = sanitize_text(raw)
    for secret in (
        "secret-bearer-123",
        "secret-token-456",
        "secret-password-789",
        "secret-cookie",
        "secret-key",
        "user@example.com",
        "13812345678",
    ):
        assert secret not in safe
    assert "***" in safe


def test_sanitize_text_preserves_non_sensitive_failure_context():
    raw = "AssertionError: $.code expected='0' actual='A000001'"
    safe = sanitize_text(raw)
    assert "AssertionError" in safe
    assert "$.code" in safe
    assert "A000001" in safe
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m pytest tests/ai/test_sanitizer_text.py -q
```

Expected: `ImportError: cannot import name 'sanitize_text'`.

- [ ] **Step 3: Implement text sanitizer**

在 `utils/sanitizer.py` 新增：
- Bearer Authorization 脱敏；
- token/access_token/refresh_token/password/passwd/api_key/apikey 的 `=` 或 `:` 文本脱敏；
- Cookie / Set-Cookie 行脱敏；
- 邮箱脱敏；
- 常见中国大陆手机号脱敏。

必须先脱敏后截断，且不能删掉非敏感错误码、JSONPath、AssertionError 等诊断上下文。

- [ ] **Step 4: Run selected regression**

```bash
python -m pytest tests/ai/test_sanitizer_text.py tests/unit -q
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add utils/sanitizer.py tests/ai/test_sanitizer_text.py
git commit -m "feat: sanitize AI failure text evidence"
```

---

### Task 3: 从 run.json + JUnit 构建确定性 FailureEvidence

**Files:**
- Create: `ai/failure_analyzer.py`
- Create: `tests/ai/test_failure_evidence.py`
- Create: `tests/fixtures/ai/auth_failure/run.json`
- Create: `tests/fixtures/ai/auth_failure/junit.xml`

**Interfaces:**
- Produces:
  - `build_failure_evidence(run_dir: str | Path) -> FailureEvidence`
  - `FailureArtifactError`
  - `NoFailureEvidence`
- Constants:
  - `_MAX_MESSAGE_CHARS = 2000`
  - `_MAX_TRACEBACK_CHARS = 6000`

- [ ] **Step 1: Add sanitized historical fixture**

`run.json` 固定为：

```json
{
  "run_id": "jenkins-history-auth",
  "environment": "example-real-sut",
  "level": "smoke",
  "pytest_exit_code": 1,
  "pytest_args": ["-m", "smoke"],
  "junit_xml": "junit.xml"
}
```

`junit.xml` 包含：
- 1 个 direct failure；
- 5 个共享认证 fixture 导致的 setup error；
- failure body 故意写入 `fixture password/token sentinel`。

Fixture 不出现 Shortlink URL/表名/Redis Key。

- [ ] **Step 2: Write failing Evidence Builder tests**

```python
from pathlib import Path

import pytest

from ai.failure_analyzer import (
    FailureArtifactError,
    NoFailureEvidence,
    build_failure_evidence,
)

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "ai"


def test_build_failure_evidence_reads_run_and_junit():
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
    evidence = build_failure_evidence(FIXTURE_ROOT / "auth_failure")
    combined = repr(evidence)
    assert password_sentinel not in combined
    assert token_sentinel not in combined


def test_build_failure_evidence_missing_junit_is_explicit(tmp_path):
    (tmp_path / "run.json").write_text(
        '{"run_id":"x","environment":"test","level":"smoke","pytest_exit_code":1}',
        encoding="utf-8",
    )
    with pytest.raises(FailureArtifactError, match="junit.xml"):
        build_failure_evidence(tmp_path)


def test_build_failure_evidence_with_no_failed_cases_does_not_need_ai(tmp_path):
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
```

- [ ] **Step 3: Verify RED**

```bash
python -m pytest tests/ai/test_failure_evidence.py -q
```

Expected: import/function errors.

- [ ] **Step 4: Implement deterministic builder**

Rules are exact:
- `F1` summarizes run-level `pytest_exit_code + failed + errors`;
- every JUnit failure/error creates one subsequent Fact;
- ordering follows JUnit testcase order;
- Fact text only contains `kind + nodeid + sanitized message`;
- no SUT-specific semantic inference;
- `failure` and `error` are kept distinct;
- text is sanitized before truncation;
- invalid/missing `run.json` or `junit.xml` becomes `FailureArtifactError`;
- no failures becomes `NoFailureEvidence`.

- [ ] **Step 5: Run evidence + sanitizer tests**

```bash
python -m pytest tests/ai/test_failure_evidence.py tests/ai/test_sanitizer_text.py -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add ai/failure_analyzer.py tests/ai/test_failure_evidence.py tests/fixtures/ai/auth_failure
git commit -m "feat: build deterministic AI failure evidence"
```

---

### Task 4: 增加 Provider 无关 AIClient 与 OpenAI-compatible HTTP Adapter

**Files:**
- Create: `ai/client.py`
- Create: `tests/ai/test_ai_client.py`
- Modify: `.env.example`

**Interfaces:**
- Produces:
  - `AIClient(Protocol)`
  - `OpenAICompatibleClient`
  - `OpenAICompatibleClient.from_env(...)`
- Environment:
  - `AI_API_BASE`
  - `AI_API_KEY`
  - `AI_MODEL`
  - `AI_TIMEOUT`

- [ ] **Step 1: Write failing Fake Session tests**

Tests must verify:
- 缺 key/base/model 任意一个 -> `from_env()` returns `None`;
- POST URL is `<base>/chat/completions`;
- header contains key only inside actual HTTP call;
- body uses configured model and `temperature=0`;
- model message content is parsed via one strict `json.loads`;
- non-JSON content raises `ValueError`;
- no real network.

- [ ] **Step 2: Verify RED**

```bash
python -m pytest tests/ai/test_ai_client.py -q
```

Expected: module/class missing.

- [ ] **Step 3: Implement client boundary**

Protocol:

```python
class AIClient(Protocol):
    def analyze_failure(self, evidence: dict[str, Any]) -> object:
        ...
```

`OpenAICompatibleClient` constructor:

```python
def __init__(
    self,
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 20.0,
    session: Any = None,
) -> None:
    ...
```

System prompt fixed to:

```text
You are an API test failure analysis assistant.
Use only the supplied deterministic facts as evidence.
Do not invent runtime state, database contents, service state, or code behavior.
Return exactly one JSON object with keys:
hypotheses, next_checks, uncertainties.
Every hypothesis and next_check must cite existing fact IDs through evidence_refs.
Do not include secrets or request credentials.
```

Request:
- reuse `requests.Session`;
- POST `/chat/completions`;
- do not log key/prompt/raw provider body;
- `raise_for_status()`;
- parse only `choices[0].message.content`;
- one strict `json.loads`;
- do not repair Markdown fences or malformed JSON.

- [ ] **Step 4: Update `.env.example`**

Append only comments:

```dotenv
# Stage 7.1 可选 AI 失败分析；不配置时普通测试与离线 Evidence 仍正常工作。
# AI_API_BASE=https://your-openai-compatible-endpoint/v1
# AI_API_KEY=CHANGE_ME
# AI_MODEL=your-model-name
# AI_TIMEOUT=20
```

- [ ] **Step 5: Run client tests**

```bash
python -m pytest tests/ai/test_ai_client.py -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add ai/client.py tests/ai/test_ai_client.py .env.example
git commit -m "feat: add optional AI provider adapter"
```

---

### Task 5: 编排分析、严格降级并生成 AI Artifact

**Files:**
- Modify: `ai/failure_analyzer.py`
- Create: `tests/ai/test_failure_analyzer.py`
- Create: `tests/fixtures/ai/ci_report_pollution/evidence.json`

**Interfaces:**
- Produces:
  - `analyze_run(run_dir: str | Path, client: AIClient | None = None) -> dict[str, Any]`
- Outputs:
  - `<run_dir>/ai-analysis/evidence.json`
  - `<run_dir>/ai-analysis/analysis.json`
  - `<run_dir>/ai-analysis/analysis.md`

- [ ] **Step 1: Add second sanitized historical fixture**

`ci_report_pollution/evidence.json` uses generic facts only:

```json
{
  "schema_version": "1.0",
  "run_id": "jenkins-history-report",
  "environment": "test",
  "level": "smoke",
  "pytest_exit_code": 0,
  "summary": {"failed": 0, "errors": 0},
  "facts": [
    {
      "id": "F1",
      "category": "test_result",
      "text": "Current Pytest run completed with 2 passed and 0 failed.",
      "source": "current build"
    },
    {
      "id": "F2",
      "category": "ci_result",
      "text": "The CI build finished UNSTABLE after JUnit publishing.",
      "source": "historical Jenkins evidence"
    },
    {
      "id": "F3",
      "category": "ci_configuration",
      "text": "JUnit publisher matched reports/runs/**/junit.xml in a persistent workspace.",
      "source": "historical Jenkins configuration"
    }
  ],
  "failure_cases": []
}
```

- [ ] **Step 2: Write failing orchestration tests**

Tests must cover:
- valid Fake Client -> `ai_status=success`;
- `evidence.json`, `analysis.json`, `analysis.md` all created;
- Fake Client input contains no `SECRET_SENTINEL`;
- client is `None` -> `ai_status=unavailable`;
- client raises `TimeoutError` -> `ai_status=error` and only `error_type` persisted;
- client returns unknown `F999` -> `ai_status=invalid_model_output`;
- existing `run.json` bytes before and after analysis are identical.

- [ ] **Step 3: Verify RED**

```bash
python -m pytest tests/ai/test_failure_analyzer.py -q
```

Expected: `analyze_run` missing.

- [ ] **Step 4: Implement orchestration**

Exact status contract:
- `success`
- `unavailable`
- `error`
- `invalid_model_output`

Security:
- never persist `str(exc)`;
- only persist exception class name as `error_type`;
- never persist provider raw response;
- never persist prompt;
- never modify original `run.json/junit.xml`.

Markdown renderer only renders already validated result fields.

- [ ] **Step 5: Add historical CI pollution validator test**

The expected valid AI output must cite:
- F1 current tests passed;
- F2 CI became UNSTABLE;
- F3 broad JUnit glob.

The recommended next check must be “restrict JUnit collection to current build”, not “modify API test case”.

- [ ] **Step 6: Run analyzer tests**

```bash
python -m pytest tests/ai/test_failure_analyzer.py -q
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add ai/failure_analyzer.py tests/ai/test_failure_analyzer.py tests/fixtures/ai/ci_report_pollution
git commit -m "feat: orchestrate safe AI failure analysis"
```

---

### Task 6: 增加独立 AI CLI

**Files:**
- Create: `ai/cli.py`
- Create: `tests/ai/test_ai_cli.py`

**Interfaces:**
- CLI:
  - `python -m ai.cli analyze --run-dir <path>`
  - `python -m ai.cli analyze --run-dir <path> --no-ai`
- Exit:
  - `0`: analysis artifacts produced, including degraded AI statuses;
  - `2`: invalid/missing artifacts or no failure to analyze.

- [ ] **Step 1: Write failing CLI tests**

Verify:
- `--no-ai` creates deterministic evidence/analysis without model;
- missing `run.json/junit.xml` returns `2`;
- console output never contains sentinel secret;
- console only prints run_id, failure count, ai_status, output path.

- [ ] **Step 2: Verify RED**

```bash
python -m pytest tests/ai/test_ai_cli.py -q
```

Expected: `ai.cli` missing.

- [ ] **Step 3: Implement CLI**

Parser:

```text
ai.cli analyze --run-dir PATH [--no-ai]
```

Default path:
- no `--no-ai`: `OpenAICompatibleClient.from_env()`;
- missing AI env -> client `None`, still succeeds with `unavailable`.

Catch only `FailureArtifactError` and `NoFailureEvidence`; programmer errors must not be swallowed.

- [ ] **Step 4: Run CLI tests**

```bash
python -m pytest tests/ai/test_ai_cli.py -q
```

Expected: all PASS.

- [ ] **Step 5: Manual deterministic replay**

```bash
python -m ai.cli analyze \
  --run-dir tests/fixtures/ai/auth_failure \
  --no-ai
```

Expected:
- exit code `0`;
- `ai-analysis/` generated.

Delete generated fixture output before commit:

```bash
rm -rf tests/fixtures/ai/auth_failure/ai-analysis
```

- [ ] **Step 6: Commit**

```bash
git add ai/cli.py tests/ai/test_ai_cli.py
git commit -m "feat: add standalone AI failure analysis CLI"
```

---

### Task 7: 文档、Coverage、架构守门与完整回归

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `docs/11_AI失败分析接入说明.md`
- Create: `docs/superpowers/specs/2026-08-19-stage7-1-ai-failure-analysis-design.md`
- Create: `docs/superpowers/plans/2026-08-19-stage7-1-ai-failure-analysis.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md`
- Create: `tests/integration/test_ai_architecture_contract.py`

- [ ] **Step 1: Add architecture guard tests**

```python
from pathlib import Path

ROOT = Path(__file__).parents[2]
AI_DIR = ROOT / "ai"

FORBIDDEN_SUT_TOKENS = (
    "/api/short-link",
    "shortlink-local",
    "nurl.ink",
    "t_link_",
    "short-link:goto:",
)


def test_ai_production_code_has_no_real_sut_hardcoding():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in AI_DIR.glob("*.py")
    ).lower()
    for token in FORBIDDEN_SUT_TOKENS:
        assert token.lower() not in source


def test_run_py_does_not_import_ai_analysis():
    source = (ROOT / "run.py").read_text(encoding="utf-8")
    assert "from ai." not in source
    assert "import ai." not in source
```

- [ ] **Step 2: Run architecture guard**

```bash
python -m pytest tests/integration/test_ai_architecture_contract.py -q
```

Expected: `2 passed`.

- [ ] **Step 3: Update coverage**

`pyproject.toml`:

```toml
[tool.coverage.run]
source = ["core", "utils", "db", "mock_server", "ai"]
```

No new third-party dependency.

- [ ] **Step 4: Write AI integration documentation**

`docs/11_AI失败分析接入说明.md` headings:

```markdown
# AI 失败分析接入说明
## 1. 定位
## 2. 输入证据
## 3. 本地无 AI 模式
## 4. OpenAI-compatible Provider
## 5. 输出 Artifact
## 6. 安全边界
## 7. 降级
## 8. 真实历史故障验证
## 9. 与真实 SUT 的关系
```

Explicitly say:
- AI is an interpreter, not a judge;
- Shortlink is only an example;
- no real provider success may be claimed before user runs one.

- [ ] **Step 5: Update README**

Add:
- `python -m ai.cli analyze --run-dir reports/runs/<run_id> --no-ai`
- optional `AI_API_BASE / AI_API_KEY / AI_MODEL / AI_TIMEOUT`
- no claim of real-provider success yet.

- [ ] **Step 6: Add approved spec + this plan to repo docs**

Exact paths:

```text
docs/superpowers/specs/2026-08-19-stage7-1-ai-failure-analysis-design.md
docs/superpowers/plans/2026-08-19-stage7-1-ai-failure-analysis.md
```

- [ ] **Step 7: Update canonical project plan**

Set:

```text
Stage 6 CI/CD      ✅
Stage 7.1 Design   ✅
Stage 7.1 Offline deterministic/Fake AI verification  ✅ after tests pass
Stage 7.1 Real provider verification  ⏳
Stage 7.2          ⏳
Stage 8            ⏳
```

Do not mark 7.1 fully complete until one real provider run succeeds, unless user explicitly accepts offline-only provider validation.

- [ ] **Step 8: Run AI suite**

```bash
python -m pytest tests/ai tests/integration/test_ai_architecture_contract.py -q
```

Expected: all PASS.

- [ ] **Step 9: Run full framework suite**

```bash
python -m pytest tests -q
```

Expected: all PASS, zero regressions.

- [ ] **Step 10: Re-run Mock Smoke through original runner**

```bash
python run.py --env test --level smoke --run-id stage7-ai-regression
```

Expected:

```text
2 passed, 4 deselected
```

- [ ] **Step 11: Compile all Python**

```bash
python -m compileall ai core db utils testcases tests run.py
```

Expected: exit code `0`.

- [ ] **Step 12: Verify no SUT hardcoding and no secret leakage**

```bash
python -c "from pathlib import Path; s='\n'.join(p.read_text(encoding='utf-8') for p in Path('ai').glob('*.py')).lower(); banned=['/api/short-link','shortlink-local','nurl.ink','t_link_','short-link:goto:']; assert not [x for x in banned if x in s]"
```

Expected: exit code `0`.

```bash
对 fixture 之外的仓库文件执行 sentinel 泄漏扫描
```

Expected: no matches outside fixture.

- [ ] **Step 13: Commit docs and guards**

```bash
git add \
  pyproject.toml \
  README.md \
  docs/11_AI失败分析接入说明.md \
  docs/superpowers/specs/2026-08-19-stage7-1-ai-failure-analysis-design.md \
  docs/superpowers/plans/2026-08-19-stage7-1-ai-failure-analysis.md \
  AI_API_Autotest_Framework_Project_Plan_Latest.md \
  tests/integration/test_ai_architecture_contract.py

git commit -m "docs: document AI failure analysis architecture"
```

---

## Final Stage 7.1 Verification Gate

Before claiming implementation complete:

```text
[ ] tests/ai all PASS
[ ] AI architecture contract PASS
[ ] full tests/ all PASS
[ ] run.py test/smoke remains 2 passed, 4 deselected
[ ] compileall PASS
[ ] Fake Client receives no SECRET_SENTINEL
[ ] no Shortlink hardcoding inside ai/
[ ] evidence.json generated without AI client
[ ] valid Fake AI output generates analysis.json + analysis.md
[ ] invalid Fact reference -> invalid_model_output
[ ] client Timeout -> ai_status=error without modifying run.json
[ ] OpenAI-compatible adapter tested with Fake HTTP session
[ ] public CI requires no real AI key
[ ] README does not overclaim real-provider success
```

After the user configures a real Provider key, perform a separate real-provider acceptance:

```bash
python -m ai.cli analyze --run-dir <sanitized failed run>
```

Real-provider acceptance requires:
- `ai_status=success`;
- valid `analysis.json`;
- no secret leakage;
- every hypothesis references existing Facts;
- original `run.json/junit.xml` remain untouched.

Only then mark Stage 7.1 fully complete and move to Stage 7.2.
