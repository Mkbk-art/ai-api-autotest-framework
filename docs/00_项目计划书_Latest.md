# AI 辅助接口自动化测试框架项目计划书

> **项目定位**：契约驱动、变更感知、可复用的 AI 辅助接口自动化测试框架。
> **求职方向**：测试开发 / 测试工程化。
> **真实 SUT**：短链接 SaaS 为第一真实验证项目；框架不依赖短链接业务。
> **文档用途**：统一记录项目目标、架构、阶段任务、验收标准、工程边界、AI 能力和最终交付要求。

---

# 1. 项目基本信息

## 1.1 项目名称

中文：

> **AI 辅助接口自动化测试框架**

英文定位：

> **Contract-driven, Change-aware, AI-assisted API Test Automation Framework**

推荐仓库名：

```text
ai-api-autotest-framework
```

---

## 1.2 项目定位

本项目面向测试开发岗位，目标是构建一个可以重复接入不同 API 项目的自动化测试框架。

框架不是某个短链接项目的专用测试代码，也不是简单的：

```text
Pytest + Requests + Allure + LLM
```

最终框架需要解决以下问题：

1. 普通 API 自动化中大量重复的请求、变量、断言和报告代码；
2. 多项目环境、鉴权、数据库、缓存等公共工程能力；
3. 普通接口 Case 与复杂业务 Workflow 的职责分离；
4. 测试用例结构化管理；
5. API Contract 与测试覆盖之间的映射；
6. API 变化后的影响回归范围判断；
7. 覆盖缺口和风险场景发现；
8. 大量失败用例的聚类和分诊；
9. AI 结果的证据约束和安全使用。

---

## 1.3 项目设计原则

### 原则 1：Framework Core 与 SUT 分离

```text
Framework
≠
Shortlink Test Project
```

Shortlink 只是：

```text
projects/shortlink/
```

下的一个真实项目。

### 原则 2：普通 Case 声明式执行

对于可以表达为：

```text
Request
+
Extract
+
Assertions
+
可选 DB/Redis
+
可选 Polling
```

的 Case，只编写 YAML Test Specification。

### 原则 3：复杂流程使用 Python

只有真正需要：

```text
branch
loop
multi-step state transition
complex cleanup
compensation
```

的流程使用 Python Workflow。

### 原则 4：Python Workflow 复用 YAML Case

Workflow 不重新写：

```text
requests.post
response.json
assert
```

而通过：

```text
case_executor.execute(case_id)
```

复用原子 Case。

### 原则 5：AI 不参与 PASS / FAIL

测试结果由：

```text
Pytest
+
AssertionEngine
```

决定。

AI 失败不能改变 Pytest exit code。

### 原则 6：确定性优先

可以由代码稳定完成的：

```text
Contract Diff
Coverage
直接依赖
Assertion
Fingerprint
Known Failure
```

不交给 LLM。

AI 只处理：

```text
风险推理
语义间接影响
复杂失败假设
```

---

# 2. 项目最终关系

```text
                    被测项目 A
                       │
                projects/project-a
                       │
                       │
被测项目 B ─── projects/project-b
                       │
                       ▼
            AI API Autotest Framework
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Test Runtime     Contract       AI Layer
        │              │              │
   Pytest/YAML     Diff/Coverage   Design/Triage
        │              │              │
        └──────────────┼──────────────┘
                       │
                 CI + Allure
```

---

# 3. 最终项目目标

## 3.1 一句话描述

基于 Pytest + Requests 构建通用 API 自动化测试框架，通过声明式 YAML Test Specification、Python Workflow、统一上下文与断言引擎、MySQL/Redis 数据校验、CI/CD 和 Allure 实现可复用测试执行；进一步通过 API Contract、Coverage Graph 和变更分析进行影响回归选择，并利用大模型完成覆盖缺口驱动的风险测试设计和基于真实证据的失败分诊。

---

## 3.2 最终交付能力

### 测试执行能力

- 多环境；
- Requests 封装；
- YAML Test Specification；
- Python Workflow；
- 动态变量；
- JsonPath 提取；
- Header / Query / Body；
- 文件、表单、JSON；
- request options；
- Polling；
- fixture / context provider；
- setup / cleanup。

### 断言能力

- status code；
- JsonPath eq / ne；
- exists / not_exists；
- contains；
- in；
- gt / gte / lt / lte；
- Header；
- response time；
- JSON Schema；
- MySQL；
- Redis。

### 测试资产能力

- case_id；
- operation_id；
- level；
- tags；
- risks；
- dependencies；
- Coverage Index；
- Coverage Gap；
- Workflow relationship。

### Contract 能力

- OpenAPI 3.x；
- Static Contract Manifest；
- Operation Model；
- Contract Snapshot；
- Contract Diff；
- Breaking / risky change。

### Smart Regression

- Changed Operation；
- direct impacted Case；
- dependency expansion；
- smoke safety set；
- full regression fallback；
- AI semantic impact supplement；
- machine-readable selection evidence。

### AI Test Design

- Contract Change；
- Coverage Gap；
- Risk Scenario；
- TestIntent；
- Strict Validator；
- deterministic Case Compiler；
- candidate review。

### AI Failure Triage

- JUnit；
- Allure Evidence；
- request / response；
- assertion；
- Fingerprint；
- Cluster；
- Known Classifier；
- AI ambiguous triage；
- Evidence refs；
- Suggested checks。

### 工程化能力

- GitHub Actions；
- Jenkins；
- JUnit；
- Allure；
- Artifact；
- local / SCM / CI 三种运行方式；
- Secret 管理；
- Repo Hygiene；
- Framework Test Suite。

---

# 4. 项目边界

## 4.1 本项目负责

```text
API functional automation
API data consistency
API contract coverage
change-aware regression
AI-assisted test design
failure triage
CI report
```

## 4.2 本项目不做

当前版本不包含：

- Selenium；
- UI POM；
- Mobile 自动化；
- 性能压测平台；
- 完整 Web 测试平台；
- 漏洞扫描平台；
- RAG 知识库；
- AI 自动修改生产代码；
- AI 自动决定测试通过；
- AI 自动提交正式测试 Case；
- 任意语言源码静态分析平台。

---

# 5. 目标目录结构

```text
ai-api-autotest-framework/
├── README.md
├── run.py
├── pytest.ini
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
│
├── core/
│   ├── api_runner.py
│   ├── request_client.py
│   ├── variable_context.py
│   ├── assertion_engine.py
│   ├── extractor.py
│   ├── case_spec.py
│   ├── case_registry.py
│   └── case_executor.py
│
├── pytest_plugin/
│   ├── plugin.py
│   └── yaml_runtime.py
│
├── db/
│   ├── mysql_client.py
│   └── redis_client.py
│
├── contracts/
│   ├── model.py
│   ├── provider.py
│   ├── openapi_provider.py
│   ├── manifest_provider.py
│   └── diff.py
│
├── coverage/
│   ├── index.py
│   ├── dependency_graph.py
│   └── selector.py
│
├── ai/
│   ├── config.py
│   ├── client.py
│   ├── contracts.py
│   ├── test_designer.py
│   ├── impact_analyzer.py
│   ├── failure_triage.py
│   └── prompts/
│
├── reporting/
│   └── allure_enricher.py
│
├── projects/
│   ├── demo/
│   ├── shortlink/
│   │   ├── project.yaml
│   │   ├── contract/
│   │   ├── cases/
│   │   ├── context.py
│   │   ├── hooks.py
│   │   └── workflows/
│   └── <another-project>/
│
├── config/
│   ├── config.yaml
│   ├── ai.yaml
│   └── env.*.yaml
│
├── reports/
├── docs/
└── tests/
```

---

# 6. YAML Test Specification

## 6.1 定位

YAML 不是单纯 Test Data。

项目中的 YAML 定位为：

> **可执行、可分析的 Test Specification。**

它同时描述：

```text
测试身份
API Operation
请求
提取
断言
风险
回归层级
依赖
```

---

## 6.2 示例

```yaml
version: 2

cases:
  - id: user.login.invalid_password
    name: 错误密码登录应返回业务失败

    operation_id: userLogin

    level: core

    tags:
      - auth
      - negative

    risks:
      - authentication
      - invalid_credential

    request:
      method: POST
      path: /api/user/login

      headers:
        Content-Type: application/json

      json:
        username: ${config(test_user)}
        password: ${invalid_password()}

    assertions:
      - status_code: 200
      - ne: [$.code, "0"]
      - not_exists: $.data.token
```

---

## 6.3 Case ID

要求：

```text
稳定
唯一
机器可读
不随展示名称改变
```

例如：

```text
auth.login.success
auth.login.invalid_password
order.create.success
order.create.missing_sku
```

---

## 6.4 Operation ID

Operation ID 用于：

```text
Contract
Coverage
Diff
Regression Selection
AI Test Design
```

当使用 OpenAPI 时优先采用 `operationId`。

没有 OpenAPI 时使用 Static Contract Manifest 中的 ID。

---

## 6.5 Level

统一：

```text
smoke
core
regression
```

### smoke

最低可用主链。

### core

核心业务和精选异常。

### regression

完整业务、边界、数据一致性等。

---

## 6.6 Risk Metadata

推荐基础风险词表：

```text
authentication
authorization
required_field
invalid_input
boundary
state_transition
persistence
cache_consistency
eventual_consistency
idempotency
rate_limit
compatibility
```

允许项目扩展自己的风险标签。

---

# 7. Python Workflow

## 7.1 定位

Python Workflow 只解决：

```text
复杂控制流
```

而不是普通 API 请求。

---

## 7.2 示例

```python
def test_refund_flow(case_executor):
    order = case_executor.execute("order.create.success")

    try:
        payment = case_executor.execute(
            "payment.pay.success",
            overrides={"order_id": order["order_id"]},
        )

        refund = case_executor.execute(
            "refund.create.success",
            overrides={"order_id": order["order_id"]},
        )

        wait_refund_completed(refund)

    finally:
        cleanup(order)
```

请求和普通断言仍来自 YAML Case。

---

# 8. Project 接入模型

## 8.1 最小接入

一个简单新项目只需要：

```text
projects/<project>/
├── project.yaml
├── contract/
└── cases/
```

如果业务有特殊上下文：

```text
context.py
hooks.py
```

如果存在复杂流程：

```text
workflows/
```

---

## 8.2 Project Context Provider

用于复用：

```text
登录用户
管理员身份
租户
组织
测试订单
临时资源
```

一份 Provider 可以被几十条 YAML Case 使用。

---

## 8.3 Framework Core 不允许出现的内容

不得出现：

```text
shortlink
gid
shortUri
nurl.ink
B100000
t_link
PV/UV/UIP
```

以及任何其他具体 SUT 业务词。

---

# 9. 第一真实 SUT：Shortlink

## 9.1 角色

Shortlink 只用于证明：

```text
框架可以测试真实复杂系统
```

不作为 Framework Core 的产品模型。

---

## 9.2 当前代表性能力

该 SUT 具备：

- Spring Boot；
- Spring Cloud Gateway；
- Token；
- MySQL；
- Redis；
- ShardingSphere；
- Sentinel；
- Redis Stream；
- 302 Redirect；
- Recycle；
- Statistics。

因此可以验证：

```text
普通 REST
鉴权
异常
Redirect
Cache
DB
异步
State Transition
Cleanup
```

---

## 9.3 短链接自动化范围

第一版保持代表性覆盖，不追求穷举所有业务接口。

### Authentication

- success；
- invalid password；
- missing token；
- Redis login state。

### Group / Resource Preparation

- group query；
- gid extract。

### Create

- success；
- invalid URL；
- unauthorized；
- DB persistence。

### Page

- created resource visible。

### Redirect

- success；
- notfound；
- recycled；
- Redis UV/UIP。

### Statistics

- PV / UV / UIP；
- async polling；
- DB persistence。

### Lifecycle

- recycle；
- remove；
- cleanup。

---

# 10. Contract Layer

## 10.1 ContractProvider

统一：

```text
ContractProvider
↓
ApiContract
```

第一版提供：

```text
OpenAPIProvider
StaticManifestProvider
```

---

## 10.2 OpenAPI

支持：

```text
OpenAPI 3.x YAML
OpenAPI 3.x JSON
```

读取：

```text
operationId
method
path
parameter
request body
schema
response
```

---

## 10.3 Static Contract Manifest

适用于没有 OpenAPI 的项目。

格式由框架定义，但保持：

```text
语言无关
框架无关
SUT 无关
```

---

# 11. Coverage Intelligence

## 11.1 Coverage Index

生成：

```text
Operation -> Cases
Case -> Risks
Workflow -> Operations
Operation -> Dependencies
```

---

## 11.2 Coverage Gap

回答：

- 哪些 Operation 没有 Case；
- 哪些 Changed Operation 没有 Case；
- 哪些 risk 没有覆盖；
- 哪些字段变化没有对应异常/边界测试。

---

# 12. Change-aware Smart Regression

## 12.1 目标

对每次 API Contract 变化，判断：

```text
Full Regression
或
Impacted Regression
```

---

## 12.2 基础流程

```text
Old Contract
+
New Contract
↓
Contract Diff
↓
Changed Operations
↓
Coverage Index
↓
Dependency Graph
↓
Mandatory Cases
↓
Risk Policy
↓
Optional AI Semantic Impact
↓
Selected Tests
```

---

## 12.3 Deterministic Mandatory Set

必须包含：

- Changed Operation 直接绑定 Case；
- 依赖 Changed Operation 的 Workflow；
- Shared Context 受影响 Case；
- 强制 Smoke Set；
- 用户显式包含的测试。

---

## 12.4 AI 的作用

AI 只分析：

```text
间接语义影响
风险升级
难以由直接关系确定的跨接口影响
```

AI 只能：

```text
Add
Escalate
Recommend Full
```

不能删除 Mandatory Set。

---

## 12.5 Full Regression Fallback

以下情况全量回归：

- Contract 缺失；
- Diff 失败；
- Coverage 不完整；
- 公共 Auth 变化；
- 全局 Schema 变化；
- 依赖无法确认；
- 高风险基础能力变化；
- 用户强制 Full。

---

# 13. AI Risk-based Test Design

## 13.1 目标

AI 不负责简单：

```text
接口说明 -> YAML
```

而负责：

> **根据 Contract Change 和 Coverage Gap 推理还应该测试什么。**

---

## 13.2 输入

```text
Contract Change
Existing Coverage
Coverage Gap
Risk Metadata
Project-safe context
```

---

## 13.3 输出

严格 `TestIntent`：

```text
operation
risk
scenario
priority
expected behavior
evidence refs
```

---

## 13.4 Candidate Compiler

```text
TestIntent
↓
Validator
↓
Case Compiler
↓
candidate YAML
↓
人工 Review
```

正式 Case 不由 AI 自动写入。

---

# 14. Evidence-based Failure Triage

## 14.1 Evidence

数据来源：

```text
run.json
JUnit
Allure Result
Request
Response
Assertion
Exception
Case Metadata
Operation ID
Dependency
```

发送模型前统一脱敏。

---

## 14.2 单失败

```text
Failure
↓
Known Classifier
↓
明确？
├─ YES -> deterministic result
└─ NO -> AI Triage
```

---

## 14.3 多失败

```text
Failures
↓
Fingerprint
↓
Cluster
↓
Known Classification
↓
Ambiguous Cluster
↓
AI Triage
```

目标示例：

```text
18 failed
↓
3 clusters

Authentication dependency: 12
Redis connectivity: 4
Business behavior: 2
```

---

# 15. Allure

## 15.1 报告中心

最终只保留一个主报告：

> **Allure**

不建设独立 AI Dashboard。

---

## 15.2 Test Result 内容

至少包含：

```text
Case Metadata
Request
Response
Extract
Assertions
DB/Redis checks
Failure
Cluster
AI Triage
Suggested Checks
```

---

## 15.3 Raw / Enriched

```text
allure-results-raw
↓
Triage / Enricher
↓
allure-results-enriched
↓
allure report
```

Raw Artifact 不可修改。

---

# 16. AI 配置

## 16.1 配置优先级

```text
CLI
>
config/ai.local.yaml
>
config/ai.yaml / home ai.yaml
>
ENV fallback
```

---

## 16.2 Provider / Protocol

Provider 只是 Profile。

Factory 只识别 Protocol。

第一协议：

```text
openai_chat_completions
```

同协议 Provider 不改 Python。

---

## 16.3 Secret

- Public Repo 不保存真实 Key；
- 最终本地用户可以合法在自己的 YAML 中配置；
- Git 用户推荐 `ai.local.yaml`；
- CLI 只支持隐藏输入；
- 日志 / Artifact / repr 不显示 Key。

---

# 17. CI/CD

## 17.1 Local Mode

```text
Python
YAML
Pytest
Allure
```

不要求 Git/Jenkins。

---

## 17.2 Team SCM Mode

可以使用：

```text
GitHub
GitLab
Gitee
Internal Git
Jenkins optional
```

---

## 17.3 Framework Development Mode

当前框架工程验证可继续使用：

```text
GitHub Actions
+
Jenkins
```

---

## 17.4 Change-aware CI

目标流水线：

```text
Checkout
↓
Resolve Project
↓
Contract Diff
↓
Select Regression
↓
Run Pytest
↓
PASS?
├─ YES -> Allure
└─ NO
    ↓
  Fingerprint / Cluster
    ↓
  AI if needed
    ↓
  Allure Enrich
↓
Archive
↓
Return original Pytest result
```

---

# 18. 阶段实施计划

# Stage 0：项目定位与工程基线

## 阶段目标

建立：

- 项目边界；
- Framework / SUT 分离；
- 统一测试入口；
- 开源归属；
- 安全约束；
- 框架测试基线。

## 产出

- 基线源码审查；
- README；
- LICENSE / Notices；
- Framework tests。

## 当前状态

```text
✅ 已具备稳定基础
```

---

# Stage 1：通用 API 执行引擎

## 阶段目标

提供稳定可复用的 API Test Runtime。

## 能力

- RequestClient；
- ApiRunner；
- VariableContext；
- Extractor；
- AssertionEngine；
- ConfigManager；
- Mock Server；
- logging；
- Allure attachments。

## 验收

- HTTP 主方法；
- 非 JSON；
- timeout；
- connection error；
- 动态变量；
- Header；
- Allure 脱敏；
- Mock smoke/core/regression。

## 当前状态

```text
✅ 已具备稳定基础
```

---

# Stage 2：数据源与深层一致性

## 阶段目标

支持接口响应之外的真实数据一致性验证。

## 能力

- MySQL named source；
- Redis named source；
- read-only probe；
- DB assertions；
- Redis assertions；
- polling；
- Sharding utility。

## 验收

- DB/Redis 只读；
- 参数绑定；
- 延迟一致性；
- 数据源懒连接。

## 当前状态

```text
✅ 已具备稳定基础
```

---

# Stage 3：真实 SUT 与 CI 工程验证

## 阶段目标

使用真实复杂系统证明框架不仅能跑 Mock。

## 第一 SUT

```text
Shortlink SaaS
```

## 工程化

- real smoke；
- core；
- regression；
- Jenkins；
- GitHub Actions；
- JUnit；
- Artifact；
- Allure；
- external private config。

## 当前状态

```text
✅ 已建立真实验证基础
```

---

# Stage 4：Declarative Case Runtime

## 阶段目标

实现真正的：

> 普通 Case 只写 YAML。

## 任务

1. CaseSpec V2；
2. JSON Schema / parser；
3. CaseRegistry；
4. Generic Pytest Runtime；
5. YAML marker；
6. case_id；
7. risk metadata；
8. Project Context Provider；
9. Workflow CaseExecutor；
10. Shortlink 迁移。

## 验收

```text
普通 Case 无项目 Python wrapper
复杂 Workflow 可执行
pytest marker 正常
Allure 正常
fixture/context 正常
真实 SUT 主链不回归
```

## 当前状态

```text
🟡 已完成代码与离线回归验证，等待真实 Shortlink SUT 的 Smoke/Core/Regression 复验
```

---

# Stage 5：Contract & Coverage Intelligence

## 阶段目标

让测试用例从“可以执行”升级为：

> **可以被框架分析。**

## 任务

1. Contract Model；
2. OpenAPI Provider；
3. Static Manifest Provider；
4. operation_id；
5. Case -> Operation；
6. Workflow -> Operation；
7. risk coverage；
8. Coverage Index；
9. Coverage Gap。

## 验收

输出：

```text
contract.json
coverage-index.json
coverage-gap.json
```

---

# Stage 6：Change-aware Smart Regression

## 阶段目标

根据接口变化选择合适回归范围。

## 任务

1. Contract Snapshot；
2. Contract Diff；
3. Changed Operation；
4. Dependency Graph；
5. mandatory selection；
6. safety fallback；
7. AI indirect impact；
8. selection CLI；
9. CI integration。

## CLI 目标

```text
python run.py \
  --project <name> \
  --selection auto
```

## 验收

必须能解释：

```text
为什么选这些测试
为什么没全量
为什么必须全量
哪些是直接影响
哪些是依赖影响
哪些是 AI 增补
```

---

# Stage 7：AI Risk-based Test Design

## 阶段目标

利用 AI 帮助测试人员发现：

> “还应该测试什么？”

## 任务

- Changed Contract；
- Coverage Gap；
- TestIntent；
- AI Prompt；
- Validator；
- candidate compiler；
- review flow。

## 验收

AI 不得：

- 发明不存在字段；
- 发明不存在 Operation；
- 自动进入正式 Regression；
- 修改 PASS/FAIL。

---

# Stage 8：Failure Triage & Allure Enrichment

## 阶段目标

把大量失败转换为少量可排查问题。

## 任务

1. Allure Evidence；
2. Fingerprint；
3. Cluster；
4. Known Failure Classifier；
5. Single-failure policy；
6. AI ambiguous triage；
7. Allure Enricher；
8. CI automatic triage。

## 验收

### 单失败

明确问题无需 AI。

### 多失败

能够形成：

```text
N failures
→ M clusters
```

### Allure

失败详情中直接看到 Triage。

---

# Stage 9：第二 SUT 与最终可复用性验证

## 阶段目标

证明：

> Shortlink 不是框架成立的前提。

## 第二 SUT 选择原则

优先选择：

- 轻量；
- 独立可运行；
- 有 OpenAPI；
- 业务与短链接明显不同；
- 有认证或状态业务；
- CI 可启动。

## 硬验收

第二 SUT 接入过程中不得修改：

```text
core/
db/
ai/
contracts/
coverage/
pytest_plugin/
```

只增加：

```text
projects/<project>/
config/env.<project>.yaml
```

---

# 19. 当前总进度

| 能力 | 状态 |
|---|---|
| HTTP Runtime | ✅ |
| Variable Context | ✅ |
| Unified Assertions | ✅ |
| MySQL / Redis | ✅ |
| Allure | ✅ |
| CI/CD | ✅ |
| Real Shortlink SUT | ✅ |
| AI Provider / Config / Sanitizer | ✅ |
| Evidence-based AI Foundation | ✅ |
| YAML-only Generic Runtime | ⏳ |
| Case Registry | ⏳ |
| Contract Model | ⏳ |
| Coverage Index | ⏳ |
| Smart Regression | ⏳ |
| Risk-based Test Design | ⏳ |
| Failure Clustering | ⏳ |
| Allure AI Enrichment | ⏳ |
| Second SUT Proof | ⏳ |

---

# 20. 推荐剩余实施排期

## 第 1 周：Declarative Runtime

- CaseSpec；
- CaseRegistry；
- Generic Pytest Runtime；
- Context Provider；
- Demo migration。

## 第 2 周：Shortlink Project Migration

- Shortlink Case V2；
- Workflow；
- real Smoke/Core/Regression；
- architecture guard。

## 第 3 周：Contract / Coverage

- OpenAPI；
- Static Manifest；
- Coverage；
- Gap。

## 第 4 周：Smart Regression

- Diff；
- dependency；
- selector；
- fallback；
- CI selection。

## 第 5 周：AI Test Design + Triage

- TestIntent；
- compiler；
- fingerprint；
- cluster；
- AI ambiguous reasoning。

## 第 6 周：Allure + Second SUT + Finalization

- Allure enrich；
- second SUT；
- README；
- architecture diagram；
- resume；
- interview material。

---

# 21. P0 / P1 / P2 优先级

## P0：必须完成

- YAML-only ordinary Case；
- Python Workflow boundary；
- Project isolation；
- CaseRegistry；
- operation_id；
- Contract Provider；
- Coverage Index；
- deterministic regression selection；
- Failure fingerprint/cluster；
- Allure single-report integration；
- second SUT proof。

## P1：AI 核心亮点

- AI indirect impact；
- Risk-based Test Design；
- ambiguous failure triage；
- candidate compiler。

## P2：可选增强

- 更多 Contract Provider；
- OpenAI Responses；
- Anthropic；
- history trend；
- flaky analysis；
- richer risk taxonomy。

---

# 22. 工程质量要求

- Framework tests 必须长期绿色；
- 新能力 TDD；
- type hints；
- module docs；
- Secret 不泄漏；
- Public Repo 无私有配置；
- Raw Artifact immutable；
- SUT hardcoding guard；
- Provider hardcoding guard；
- Project boundary guard；
- deterministic selection safety guard。

---

# 23. 文档清单

最终建议：

```text
docs/
├── 01_项目定位与架构.md
├── 02_API执行引擎.md
├── 03_YAML_Test_Specification.md
├── 04_Python_Workflow.md
├── 05_Project接入指南.md
├── 06_断言与数据源.md
├── 07_Contract与Coverage.md
├── 08_Smart_Regression.md
├── 09_AI_Test_Design.md
├── 10_Failure_Triage.md
├── 11_Allure与CI.md
├── 12_Shortlink真实验证.md
├── 13_第二SUT验证.md
└── 14_面试讲解.md
```

---

# 24. 最终 README 必须回答

1. 这个框架解决什么问题？
2. 为什么不是普通 Pytest Scripts？
3. YAML 和 Python 的边界是什么？
4. 如何接入新项目？
5. Simple Case 如何只写 YAML？
6. Complex Workflow 如何写？
7. Contract 怎么接？
8. Coverage 怎么算？
9. Smart Regression 怎么保证不漏测？
10. AI 为什么有意义？
11. AI 失败是否影响测试？
12. Shortlink 为什么只是示例？
13. 如何本地运行？
14. 如何 CI 运行？
15. 如何查看 Allure？

---

# 25. 最终简历描述

以下描述只在对应能力完成真实验收后使用。

## 项目名称

**AI 辅助接口自动化测试框架**

## 技术栈

```text
Python
Pytest
Requests
YAML
Allure
MySQL
Redis
OpenAPI
GitHub Actions
Jenkins
LLM API
```

## 项目描述

基于 Pytest + Requests 设计并实现可复用 API 自动化测试框架，将普通接口场景抽象为声明式 YAML Test Specification，并为复杂状态流程保留 Python Workflow；框架支持动态上下文、统一断言、MySQL/Redis 一致性验证、CI/CD 和 Allure 报告。进一步建立 API Contract 与测试用例 Coverage 关系，通过 Contract Diff 与依赖图实现变更感知回归选择，并利用 LLM 对覆盖缺口进行风险测试设计、对复杂失败进行证据驱动分诊。

## 最终亮点

- 普通接口 Case 无需重复编写 Python wrapper；
- 新 SUT 不修改 Framework Core；
- Contract Change -> Coverage -> Regression Selection 闭环；
- AI 只处理语义风险和复杂故障推理；
- 多失败自动聚类；
- AI 结果嵌入 Allure；
- 第二真实 SUT 验证可复用性。

---

# 26. 面试讲解主线

建议按以下顺序：

### 1. 为什么做

传统接口脚本：

```text
重复 Requests
重复断言
重复上下文
重复报告
测试资产难分析
变更后通常全量回归
失败后逐条排查
```

### 2. 第一层解决

统一：

```text
Request
Context
Assertion
DB/Redis
Allure
CI
```

### 3. 第二层解决

普通 Case：

```text
YAML Test Specification
```

复杂 Case：

```text
Python Workflow
```

### 4. 第三层解决

```text
Contract
↓
Coverage
↓
Change
↓
Regression Selection
```

### 5. AI 放在哪里

```text
Before Test:
Risk-based Test Design

Before Regression:
Semantic Impact

After Test:
Failure Triage
```

### 6. 为什么可信

```text
AI 不决定 PASS/FAIL
AI 不删除 Mandatory Tests
AI 输出有 Validator
AI 引用真实 Evidence
AI 失败安全降级
```

### 7. 如何证明可复用

```text
Shortlink SUT
+
Second SUT
+
Core zero business change
```

---

# 27. 风险与约束

## 27.1 YAML 过度设计

禁止把 YAML 做成：

```text
if
for
while
try
finally
```

复杂控制流回 Python。

## 27.2 AI 幻觉

必须：

- schema；
- refs；
- validator；
- fallback；
- human review。

## 27.3 Smart Regression 漏测

必须：

- deterministic mandatory set；
- smoke；
- dependency expansion；
- full fallback；
- AI only adds。

## 27.4 Contract 不完整

Contract 缺失时：

```text
不能假装精准选择
```

必须安全回退。

## 27.5 SUT 污染 Core

所有项目特有逻辑必须留在 `projects/<name>/`。

---

# 28. 最终验收标准

## 28.1 可复用

- 至少两个不同 SUT；
- 第二 SUT 接入 Core 零修改；
- Project 目录可独立删除。

## 28.2 可执行

- simple YAML Case；
- complex Workflow；
- smoke/core/regression；
- MySQL/Redis；
- Allure；
- CI。

## 28.3 可分析

- case_id；
- operation_id；
- risk；
- coverage；
- dependency；
- contract diff。

## 28.4 可智能回归

- direct impact；
- dependency；
- full fallback；
- selection evidence；
- AI semantic supplement。

## 28.5 AI 有实际价值

- Coverage Gap -> TestIntent；
- multi-failure -> clusters；
- ambiguous failure -> triage；
- known single failure -> no unnecessary AI。

## 28.6 安全

- no secret leak；
- raw artifacts immutable；
- AI no PASS/FAIL；
- AI no mandatory test deletion。

## 28.7 可展示

最终演示至少包含：

```text
1. 新增 YAML Case，无 Python wrapper，Pytest 自动执行
2. Complex Workflow 复用 case_id
3. Contract 变化
4. Smart Regression 选择测试
5. Coverage Gap
6. AI 生成 TestIntent
7. 构造多个失败
8. Failure Cluster
9. AI Triage
10. Allure 查看完整结果
11. 第二 SUT 执行
```

---

# 29. 最终项目完成定义

只有当以下命题全部成立时，项目才算真正完成：

> **不用 AI，这仍然是一个有价值的通用 API 自动化测试框架。**

> **换一个 SUT，Framework Core 不需要为了业务修改。**

> **普通 Case 的 YAML 真正替代了重复 Python 测试 wrapper。**

> **复杂业务仍然可以使用 Python，而不是被迫塞进 YAML。**

> **测试资产可以通过 Contract / Coverage 被分析。**

> **API 变化后可以解释为什么全量或为什么只跑部分回归。**

> **AI 只在风险推理、语义影响和复杂失败分析中发挥作用。**

> **AI 的每个结论都有结构化输入、约束、证据和安全降级。**

达到以上标准后，再进入最终发布、简历和面试材料封板。
