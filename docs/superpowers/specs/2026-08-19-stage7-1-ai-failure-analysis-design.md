# Stage 7.1 AI 失败日志分析 — 设计规格 V1

> 项目定位：**AI 辅助接口自动化测试框架**  
> 当前阶段：Stage 6 CI/CD 已关闭，正式进入 Stage 7 AI 辅助。  
> 本规格只设计 **7.1 失败日志分析**；7.2 YAML 草稿生成在 7.1 完成后单独进入下一轮。  
> Shortlink 仅作为当前真实 SUT 和真实失败样例，不进入 Framework Core / AI Core 的业务逻辑。

## 1. 目标

为现有框架增加一套**可选、可降级、可审计**的 AI 失败分析能力：

- 从一次已经结束的测试运行目录读取已有证据；
- 在任何数据发送给模型之前统一脱敏；
- 由确定性代码先提取“事实”，AI 不负责创造事实；
- AI 只在事实基础上生成可能原因、排查建议和不确定性；
- AI 输出必须通过结构校验和证据引用校验；
- AI 不可用、未配置、超时或返回非法结果时，不修改 Pytest PASS/FAIL，也不影响现有 `run.py` 主链；
- 分析结果作为额外 Artifact 保存；
- 整套能力与 Shortlink 解耦，未来新 SUT 复用同一 AI Core。

## 2. Stage 7.1 明确不做

- 不自动修改 Python/YAML；
- 不自动把失败改成通过；
- 不让 AI 直接连接 MySQL、Redis 或 SUT；
- 不把完整 Jenkins Console Output 原样发送给模型；
- 不发送 Token、Cookie、密码、API Key、数据库凭据、手机号、邮箱等敏感信息；
- 不把 Shortlink URL、表名、Redis Key、业务错误码写进 `ai/`；
- 不把 AI 设为 `run.py` 的必选依赖；
- 不提前实现 7.2。

## 3. 方案比较与选择

### 方案 A：Console Output 直接交给模型
开发快，但日志噪声大、敏感信息风险高、事实与猜测混杂，难测试。**拒绝。**

### 方案 B：AI 深度嵌入 Pytest hooks
上下文丰富，但侵入已稳定主链，AI 故障可能影响测试。**Stage 7.1 暂不采用。**

### 方案 C：基于现有 Artifact 的离线结构化分析
读取 `run.json`、`junit.xml` 和必要的受控日志片段，确定性代码先构造证据，再调用 AI。  
**采用。**

## 4. 总体架构

```text
run.py / Pytest（保持不变）
        ↓
reports/runs/<run_id>/
├─ run.json
├─ junit.xml
└─ allure-results/...

独立 AI 辅助链
        ↓
FailureEvidenceBuilder
        ↓
Deterministic Facts
        ↓
Sensitive Sanitizer
        ↓
AIClient Protocol
        ↓
FailureAnalysisValidator
        ↓
reports/runs/<run_id>/ai-analysis/
├─ evidence.json
├─ analysis.json
└─ analysis.md
```

核心原则：

> **测试结果由 Pytest / AssertionEngine 决定；AI 只解释已经发生的结果。**

## 5. 模块设计

避免过度碎片化，新增紧凑 `ai/` 包：

```text
ai/
├─ __init__.py
├─ contracts.py
├─ failure_analyzer.py
├─ client.py
└─ cli.py
```

复用并增强：

```text
utils/sanitizer.py
```

测试：

```text
tests/ai/
├─ test_failure_evidence.py
├─ test_failure_analyzer.py
└─ test_ai_cli.py

tests/fixtures/ai/
├─ failed_junit.xml
├─ failed_run.json
└─ sanitized_log.txt
```

### `ai/contracts.py`
定义并校验 `FailureEvidence`、`FailureFact`、`AIHypothesis`、`FailureAnalysis`。

### `ai/failure_analyzer.py`
读取 run 目录、解析 JUnit、生成 facts、脱敏、调用 AI、校验输出、生成 JSON/Markdown。

### `ai/client.py`
定义 Provider 无关接口：

```python
class AIClient(Protocol):
    def analyze_failure(self, evidence: dict) -> dict:
        ...
```

单元测试注入 Fake Client；生产代码不依赖具体 SUT。

### `ai/cli.py`
独立入口：

```bash
python -m ai.cli analyze --run-dir reports/runs/<run_id>
```

**第一版不修改现有 `python run.py ...`。**

## 6. 为什么第一版不改 `run.py`

`run.py` 已稳定承担配置、Pytest、JUnit、Allure、`run.json` 和真实 exit code。  
Stage 7.1 不把模型鉴权、网络超时、Prompt、模型 JSON 校验等塞进主链。

测试执行与 AI 分析保持两个独立命令。后续若接 Jenkins，只能做可选 Post Step，AI 失败也不能覆盖原测试状态。

## 7. 证据模型

`FailureEvidence` 示例：

```json
{
  "schema_version": "1.0",
  "run_id": "jenkins-18",
  "environment": "shortlink-local",
  "level": "smoke",
  "pytest_exit_code": 1,
  "summary": {"failed": 1, "errors": 5},
  "facts": [
    {
      "id": "F1",
      "category": "test_result",
      "text": "认证成功用例失败",
      "source": "junit.xml"
    },
    {
      "id": "F2",
      "category": "assertion",
      "text": "业务 code 未满足成功契约且 token 缺失",
      "source": "junit.xml"
    }
  ],
  "failure_cases": [
    {
      "nodeid": "...",
      "kind": "failure",
      "message": "...",
      "traceback_tail": "..."
    }
  ]
}
```

`facts` 必须由 Python 生成，AI 不能修改。

## 8. AI 输出模型

AI 只生成：

```json
{
  "hypotheses": [
    {
      "title": "测试环境认证数据可能与预期不一致",
      "confidence": "high",
      "evidence_refs": ["F1", "F2"],
      "reasoning_summary": "..."
    }
  ],
  "next_checks": [
    {
      "priority": 1,
      "action": "检查当前环境测试账号是否存在且有效",
      "evidence_refs": ["F2"]
    }
  ],
  "uncertainties": [
    "现有证据无法确认数据库中的实际记录"
  ]
}
```

最终 `analysis.json` = 本地确定性 facts + AI hypotheses/next_checks/uncertainties。

## 9. 证据引用约束

每条 hypothesis 必须引用真实 `F#`。  
`F99` 不存在时 Validator 必须拒绝。  
模型不能把“没有证据的猜测”升级成事实。

## 10. 脱敏

当前仓库已有 `utils/sanitizer.py`，已处理嵌套字典中的 Authorization、Cookie、password、token、API Key 等。Stage 7.1 扩展**文本级脱敏**，至少覆盖：

```text
Authorization: Bearer ...
token=...
password=...
Cookie: ...
Set-Cookie: ...
api_key=...
邮箱
常见中国大陆手机号
```

要求：

> Fake Client 收到的 evidence 中不得出现测试 fixture 故意植入的 secret sentinel。

## 11. AI Client 与密钥

AI Core 依赖 `AIClient Protocol`，不直接绑定厂商 SDK。  
真实 Provider Adapter 后续可接 OpenAI-compatible 或其他服务。

API Key 只允许来自运行环境/Secret Store，不进入：
- Git
- 公共 YAML
- `run.json`
- `evidence.json`
- `analysis.json`
- Jenkins Artifact

公共 CI 不要求真实 AI Key。

## 12. 降级策略

- **无 AI Client/Key**：仍生成 `evidence.json`，状态为 `ai_status=unavailable`；
- **Timeout/HTTP Error**：保存 evidence，记录 AI 调用失败，不修改原测试结论；
- **非法模型 JSON**：标记 `invalid_model_output`，不强行“修 JSON”冒充成功；
- **引用不存在 Fact**：Validator 拒绝。

## 13. CLI 输出

```bash
python -m ai.cli analyze --run-dir reports/runs/jenkins-18
```

输出：

```text
reports/runs/jenkins-18/ai-analysis/evidence.json
reports/runs/jenkins-18/ai-analysis/analysis.json
reports/runs/jenkins-18/ai-analysis/analysis.md
```

控制台只显示 run_id、失败数量、AI 状态和文件位置，不输出 Prompt/API Key/Token/Cookie/私有 YAML。

## 14. CI 边界

Stage 7.1 第一轮不修改 Jenkins 主 Test Stage。  
模块完成后再考虑：

```text
测试结束
  ↓
可选 AI_ANALYSIS=true
  ↓
独立 AI Post Step
  ↓
保存 ai-analysis/*
```

AI Post Step 失败时，原构建的测试判定保持不变。

## 15. TDD 验收矩阵

### Evidence
- JUnit `failure` 可转换为 FailureCase；
- JUnit `error` 可转换为 FailureCase；
- 正确读取 `run.json`；
- 缺少 JUnit 时明确报输入错误；
- 无失败时不调用 AI。

### Sanitizer
- Dict password/token；
- Bearer Token；
- Cookie；
- 文本 password/token；
- email/手机号；
- Fake Client 收不到 secret sentinel。

### Validator
- 合法结构通过；
- 非 Mapping 拒绝；
- confidence 只允许 `low/medium/high`；
- hypothesis 必须引用至少一个 fact；
- 不存在的 fact id 拒绝；
- priority 必须为正整数。

### Degradation
- 无 Client 仍生成 evidence；
- Client Timeout 不影响 evidence；
- Client 异常不修改已有 `run.json`；
- AI 失败不改变测试 exit code 语义。

### Architecture Guard
`ai/` production code 禁止出现：
- `/api/short-link`
- `nurl.ink`
- Shortlink 表名
- Shortlink Redis Key 前缀
- `shortlink-local`

## 16. 使用真实历史故障做验证

不制造“看起来真实”的故障。

### 样例 1：真实认证失败
期望 AI 能识别“共同认证前置失败导致后续 setup error”，不把 5 个连锁 error 当 5 个独立 Bug。

### 样例 2：Jenkins 旧 JUnit 污染
期望 AI 区分“当前 Pytest 2/2 passed”与“CI 报告聚合导致 UNSTABLE”，优先建议检查 JUnit 收集范围，而不是修改测试用例。

## 17. Stage 7.1 完成标准

1. `ai/` 无 SUT 业务硬编码；
2. Evidence Builder 可读取真实 run artifacts；
3. Facts 由确定性代码生成；
4. 模型前完成结构化 + 文本脱敏；
5. Fake Client 可跑完整分析链；
6. AI 输出严格校验并引用 facts；
7. 无 Key/Timeout/非法输出安全降级；
8. 不修改 `run.py` 默认测试结果语义；
9. 公共 CI 无真实 AI Key；
10. 两类真实历史故障 fixture 通过测试；
11. 全量 framework tests 不回归；
12. 文档明确 AI 是辅助解释器，不是测试判定器。

## 18. 与 7.2 的边界

7.2 后续可复用：
- `AIClient`
- 脱敏
- Provider Adapter
- JSON 校验思想

但 7.2 单独实现 API Spec 输入、YAML Draft Schema、DSL 语义校验、draft 目录与人工确认门。

**7.1 不提前实现 7.2。**
