# AI 辅助接口自动化测试框架

> 当前开发线：Declarative Case Runtime / Contract-driven & Change-aware 架构重构
> 当前离线验证：Framework tests `180 passed`；Mock smoke/core/regression 均 `2 passed, 4 deselected`。
> 真实 SUT：Shortlink SaaS 仅作为第一个验证项目；本轮执行模型重构后的真实 Smoke/Core/Regression 需要在用户本机重新验收。

这是一个面向**测试开发 / 测试工程化**岗位的可复用 API 自动化测试框架。

项目最终定位是：

> **Contract-driven, Change-aware, AI-assisted API Test Automation Framework**

框架本身必须在关闭 AI 时仍然有独立价值；AI 只用于传统确定性程序难以完成的风险推理、间接影响判断和复杂失败分诊。

---

## 1. 这个框架解决什么问题

普通 Pytest + Requests 项目当然可以完成接口自动化，但随着项目和 Case 数量增长，经常出现：

```text
每条 Case 重复写 Requests
每条 Case 重复处理 token / 上下文
每条 Case 重复解析响应和断言
数据库/Redis 校验各写一套
测试数据、业务标签、回归层级散落在 Python
API 变化后通常只能全量回归或人工判断影响
大量失败后逐条查看 Allure
```

本框架把这些问题拆成三层：

```text
Test Specification       ->  普通 API Case：YAML
Workflow Orchestration   ->  真正复杂的业务控制流：Python
Framework Engine         ->  HTTP / Context / Assertion / DB / Redis / Allure / CI
```

以后 Contract/Coverage 层会继续让测试资产可以被机器分析，从而支持 Change-aware Regression 和 AI Test Design。

---

## 2. YAML 和 Python 的正式边界

### 2.1 普通 Case：只写 YAML

当一条测试可以完整表达为：

```text
Request
+ Dynamic Context
+ Extract
+ Deterministic Assertions
+ optional MySQL/Redis
+ optional bounded Polling
```

它就是声明式 Case，不需要项目再写 `test_login.py`、`test_create.py` 这类参数化 wrapper。

示例：

```yaml
version: 2

cases:
  - id: user.login.invalid_password
    name: 错误密码登录应返回业务失败
    operation_id: userLogin
    level: core
    tags: [auth, negative]
    risks: [authentication, invalid_input]

    request:
      method: POST
      path: /api/user/login
      json:
        username: ${config(test_user)}
        password: ${invalid_password()}

    assertions:
      - status_code: 200
      - ne: [$.code, "0"]
      - not_exists: $.data.token
```

Pytest 执行链：

```text
YAML CaseSpec
↓
CaseRegistry
↓
Framework Generic Pytest Runtime
↓
CaseExecutor
↓
ApiRunner
↓
RequestClient / Assertions
↓
Allure
```

项目无需为上面这条 Case 创建 Python 测试函数。

### 2.2 复杂 Workflow：才写 Python

当测试存在真正的程序控制流，例如：

```text
多 API 状态迁移
if / else
循环
复杂等待
补偿
finally cleanup
跨系统资源生命周期
```

保留 Python Workflow。

Workflow 不重新写普通 Requests/断言，而是复用稳定 `case_id` 或 YAML 中的断言组。

```python
# 概念示例
order = case_executor.execute("order.create.success")
payment = case_executor.execute(
    "payment.pay.success",
    overrides={"order_id": order["order_id"]},
)
```

**禁止为了“全 YAML”在 DSL 中加入 `if/for/while/try/finally`。**

---

## 3. 当前目录与职责

当前代码阶段仍保留 `testcases/<project>/`，目录迁移到最终 `projects/<project>/` 会在后续独立阶段处理，避免同时修改执行模型和项目布局。

```text
ai-api-autotest-framework/
├── run.py
├── conftest.py
│
├── core/
│   ├── api_runner.py
│   ├── request_client.py
│   ├── variable_context.py
│   ├── assertion_engine.py
│   ├── extractor.py
│   ├── case_spec.py
│   ├── case_registry.py
│   ├── context_provider.py
│   └── case_executor.py
│
├── db/
│   ├── mysql_client.py
│   └── redis_client.py
│
├── ai/
│   ├── config.py
│   ├── client.py
│   ├── contracts.py
│   └── failure_analyzer.py
│
├── testcases/
│   ├── test_yaml_cases.py      # 框架唯一普通 YAML Test Runtime
│   ├── demo/
│   │   ├── context.py
│   │   └── yaml/
│   └── shortlink/
│       ├── context.py
│       ├── support.py
│       ├── yaml/
│       └── workflows/
│
├── config/
├── tests/
├── reports/
└── docs/
```

`core/`、`db/`、`ai/` 不允许出现 Shortlink 的 `gid`、`shortUri`、`nurl.ink`、`B100000`、`t_link_*` 等业务知识。

---

## 4. Declarative Case Runtime

### 4.1 CaseSpec V2

V2 YAML 固定顶层：

```yaml
version: 2
cases:
  - ...
```

每条 Case 的核心机器字段：

```text
id             稳定唯一 Case ID
name           报告展示名
level          smoke/core/regression
operation_id   API Contract Operation ID
 tags           Pytest / 业务标签
risks          风险元数据
requires       项目 Context Provider
execution      declarative 或 workflow
request        HTTP 规格
extract        响应变量
assertions     统一断言
poll           可选最终一致性轮询
hooks          项目扩展生命周期
```

### 4.2 CaseRegistry

`CaseRegistry` 负责：

- 检查 `case_id` 唯一；
- `case_id -> CaseSpec`；
- `operation_id -> Cases`；
- 过滤 declarative/workflow；
- 为后续 Coverage/Smart Regression 提供结构化测试资产入口。

### 4.3 Context Provider

普通 Case 经常需要“已登录用户”“已创建订单”“已准备租户”之类的前置。

这并不意味着它必须升级成 Python Workflow。

项目可以注册一次 Context Provider：

```text
project.authenticated
project.created_resource
project.admin_user
```

YAML 只声明：

```yaml
requires:
  - project.authenticated
```

一份 Provider 可以被几十条 YAML Case 复用。

### 4.4 Case Hook

项目特有的响应规范化和 cleanup 可以通过：

```text
before_case
after_response
teardown
```

挂接。

Core 只负责生命周期，不认识具体业务。

---

## 5. 通用执行和断言能力

### HTTP Runtime

- GET / POST / PUT / DELETE / PATCH；
- JSON / Form / Params / Files；
- timeout；
- TLS verification；
- 相对 URL / 绝对 URL；
- `allow_redirects` 受控 Requests option；
- Request / Response 日志；
- Allure 附件；
- Header/Body 敏感信息脱敏。

### VariableContext

```text
session
scenario
case
```

支持：

```text
${token}
${resource_id}
${config(section,key)}
DebugTalk 动态函数
```

### Assertions

响应断言：

```text
status_code
eq / ne
exists / not_exists
contains
in / not_in
gt / gte / lt / lte
header_eq / header_contains
response_time_lt
list_contains
```

数据源断言：

```text
db_exists
db_eq
db_gte
redis_exists
redis_eq
redis_hfield_exists
redis_ttl_between
redis_scard_gte
```

MySQL/Redis Client 是命名数据源、懒连接、只读 Probe，不理解具体 SUT 表和 Key。

---

## 6. 第一个真实 SUT：Shortlink SaaS

Shortlink 只用于证明框架能面对真实复杂系统。

真实后端包含：

```text
Spring Boot / Spring Cloud Gateway
MySQL / Redis
ShardingSphere
Sentinel
Redis Stream
302 Redirect
Recycle
Statistics
```

当前仍保持 18 条代表性 Case：

```text
Smoke       6
Core        6
Regression  6
```

本轮执行模型重构后：

```text
16 条普通 Case
→ 4 份 V2 YAML
→ Generic Runtime
→ 0 个项目普通 Python wrapper

2 条复杂 Regression
→ Python storage lifecycle Workflow
→ Create -> Recycle -> Remove 多状态校验
```

Shortlink 自己的：

```text
Gateway username/token
ShardingSphere HASH_MOD
B100000 Sentinel 限流
nurl.ink
Recycle API
Redis Key / 物理表规则
```

全部留在 `testcases/shortlink/` 和项目环境配置，不能进入 Core。

---

## 7. 安全和 GitHub 边界

当前仓库已用于公开 GitHub，因此必须遵守：

- 不提交真实测试账号密码；
- 不提交数据库真实密码；
- 不提交 AI API Key；
- 不提交 `config/ai.local.yaml`；
- 不提交 `.env`；
- 不提交运行产生的 `reports/*` / `logs/*`；
- Public YAML 只保留 `CHANGE_ME`、null 或其他明确占位值。

仓库已经绑定 GitHub 时，真实 SUT 账号/数据库密码推荐放在：

```text
config/env.<project>.private.yaml
```

然后通过 `run.py --env-file` 作为本机私有覆盖；该文件名模式不会进入 Git。示例见
`docs/examples/env.shortlink-local.private.example.yaml`。

`.gitignore` 已保护：

```text
.env
config/ai.local.yaml
config/env.*.private.yaml
reports/*
logs/*
.idea/
```

最终用户如果完全不使用 Git，可以在自己的本地配置中写真实凭据；“公共 GitHub 安全规则”不能被错误实现成 Runtime 禁止本地真实配置。

---

## 8. AI Provider 基础设施

已经保留并验证的 AI 基础：

- `AIConfigResolver`；
- YAML-first；
- `CLI > ai.local.yaml > ai.yaml/Home > ENV`；
- Provider / Protocol 解耦；
- `openai_chat_completions` Adapter；
- API Key 隐藏输入；
- Sanitizer；
- Evidence/Facts；
- Strict JSON；
- Validator；
- 真实 Provider 已在前一阶段完成本地 `ai_status=success` 验收。

这些基础会服务新的 AI 方向，而不是继续把“单条失败解释”和“手填接口说明生成 YAML”当最终卖点。

---

## 9. AI 最终三个价值点

### 9.1 Risk-based Test Design

回答：

> **接口变化以后，还有哪些风险场景没有测？**

```text
Contract Change
+
Existing Coverage
+
Coverage Gap
↓
AI TestIntent
↓
Validator
↓
Deterministic Candidate Compiler
↓
Human Review
```

AI 不直接把未经验证的 Case 写进正式 Regression。

### 9.2 Change-aware Smart Regression

回答：

> **这次应该跑哪些测试？需要全量回归吗？**

```text
Old Contract + New Contract
↓
Deterministic Diff
↓
Changed Operations
↓
Coverage / Dependency
↓
Mandatory Tests
↓
Optional AI Semantic Impact
↓
Selected Regression / Full Regression
```

AI 只能增加、升级风险或建议 Full Regression，不能删除确定性规则选中的 Mandatory Tests。

### 9.3 Evidence-based Failure Triage

回答：

> **这些失败到底是几个独立问题，应该先排查哪里？**

```text
Failure Evidence
↓
Fingerprint
↓
Cluster
↓
Known deterministic classifier
↓
Ambiguous cluster only -> AI Triage
```

单个明确的 Timeout、Connection、缺 Token 等故障不浪费 LLM 调用；单个但证据冲突的问题仍可以进入 AI Triage。

---

## 10. Allure 最终定位

Allure 是唯一主要测试报告 UI，不建设第二套 AI Dashboard。

目标：

```text
allure-results-raw
↓
Failure Analysis
↓
allure-results-enriched
↓
Final Allure HTML
```

最终失败详情可以包含：

```text
Request
Response
Assertion
Failure Cluster
AI Triage
Evidence refs
Suggested checks
```

Raw 测试结果不可被 AI 修改，AI 成功/失败也不能覆盖原 Pytest exit code。

---

## 11. 安装

推荐 Python 3.11：

```bash
conda create -n autotest python=3.11 pip -y
conda activate autotest
python -m pip install -r requirements-dev.txt -c constraints.txt
```

含义：

- 第一条创建独立 Python 3.11 Conda 环境；
- 第二条进入该环境；
- 第三条按项目开发依赖和锁定约束安装 Python 包。

---

## 12. 当前执行方式

### Mock Demo

```bash
python run.py --env test --level smoke
python run.py --env test --level core
python run.py --env test --level regression
```

含义：

- `--env test`：读取 Mock 测试环境；
- `--level`：只执行对应 smoke/core/regression 层级；
- 当前三个层级均应得到 `2 passed, 4 deselected`。

### 查看 Shortlink 收集结果但不发真实请求

```bash
python run.py --env shortlink-local --level smoke --collect-only
```

`--collect-only` 只让 Pytest 展示会执行哪些 Case，不发送 HTTP 请求；适合在真正连接 SUT 前检查收集范围。当前应从 18 条中选中 6 条 Smoke。

真实 SUT 启动且本机私有环境配置完成后，再去掉 `--collect-only` 执行真实测试。

### Contract / Coverage 分析

Contract/Coverage 不发送业务 HTTP 请求，只读取环境配置、Contract 与 V2 Test Specification：

```bash
python -m coverage_engine.cli --env shortlink-local
```

有 OpenAPI 的项目配置 `provider: openapi`；没有 OpenAPI 的项目准备经过核查的 Static Manifest，并配置 `provider: static_manifest`。默认输出到：

```text
reports/coverage/<env>/contract.json
reports/coverage/<env>/coverage-index.json
reports/coverage/<env>/coverage-gap.json
```

---

## 13. 当前验证状态

### Framework / Runtime

```text
Framework tests      211 passed
Demo smoke           2 passed, 4 deselected
Demo core            2 passed, 4 deselected
Demo regression      2 passed, 4 deselected
Shortlink cases      18 total
Shortlink smoke      6 / 18
Shortlink core       6 / 18
Shortlink regression 6 / 18
```

Declarative Runtime 已在真实 Shortlink Smoke/Core/Regression、本地 Allure、GitHub Actions 和 Jenkins 中完成验证。

### Stage 5 Contract / Coverage 离线证据

```text
Stage 5 focused tests    34 passed
Shortlink mappings       43
External operations      27
Covered operations        8
Operation coverage    29.63%
Untested operations      19
Unknown bindings          0
Unbound cases             0
```

该 Coverage 是当前 18 条代表性测试资产的真实映射结果，不把百分比包装成“质量分数”。它用于让 API 覆盖缺口可计算，并为下一阶段 Contract Diff / Change-aware Regression 提供输入。

---

## 14. 下一阶段路线

```text
Declarative Case Runtime          ✅
↓
Contract Provider + Coverage      当前：代码与离线验收完成，待本机复验/CI 后封板
↓
Change-aware Smart Regression
↓
AI Risk-based Test Design
↓
Failure Fingerprint / Cluster / Triage
↓
Allure Enrichment
↓
Second SUT Reusability Proof
↓
README / Resume / Interview Finalization
```

---

## 15. 新项目接入目标

最终，一个普通新项目应主要增加：

```text
project config
contract
YAML cases
optional context providers
optional complex workflows
```

而不修改：

```text
core/
db/
ai/
contract/
coverage/
pytest runtime
```

第二个业务明显不同的真实 SUT 将作为最终“可复用性”硬验收：如果接入第二个 SUT 仍需要修改 Framework Core，就说明框架边界还没有真正设计好。

---

## 16. 开源来源

上游基线来源和 MIT 许可信息见：

- `LICENSE`
- `BASELINE_SOURCE.md`
- `THIRD_PARTY_NOTICES.md`

当前仓库不应把上游 Demo 能力直接冒充为个人实现；所有最终简历描述必须以当前代码、测试、CI 或真实 SUT 证据为依据。
